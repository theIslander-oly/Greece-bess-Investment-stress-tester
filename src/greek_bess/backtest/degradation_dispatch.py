"""Day-by-day perfect-foresight dispatch with evolving degraded capacity.

**The aggregate is a simulation, not a bound.** Each market day is solved optimally under the
limits it begins with, which makes every *day* a perfect-foresight ceiling for that day. The
total over many days is not, because the state those days begin with depends on what the earlier
days chose to discharge. The daily policy is myopic with respect to any lifetime budget: given
one warranted cycle and two days whose spreads are EUR 1 and EUR 100, it spends the cycle on the
first day and earns EUR 1, where waiting earns EUR 100. A lifetime optimum is therefore at least
as large as this total, which makes it a lower bound on that optimum and not an upper bound on
achievable margin.

This module keeps the daily policy. It does not introduce a lifetime optimizer; it declares what
the result it produces actually is, so nothing downstream can read the total as a ceiling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical
from ..degradation import (
    DegradationConfig,
    complete_degradation_day,
    degradation_cohort_table,
    initialize_degradation_state,
    prepare_degradation_day,
    warranty_discharge_headroom_mwh,
)
from ..dispatch import BatteryDispatchConfig, optimize_perfect_foresight

DEGRADED_DISPATCH_LABEL = (
    "Day-by-day perfect-foresight Greek DAM gross-margin simulation with endogenous "
    "illustrative degradation and augmentation. Each day is solved optimally under the state "
    "it begins with; because that state evolves with what earlier days chose, the total is "
    "what this daily policy achieved and not a lifetime optimum or an upper bound. Not "
    "expected investment revenue."
)

#: Why the aggregate is a simulation rather than a bound, in one recordable sentence. A reader
#: who sees only the total needs the reason attached to it, not left in a docstring.
DEGRADED_DISPATCH_BASIS_NOTE = (
    "Each market day is dispatched optimally under its beginning-of-day degraded limits, and "
    "those limits depend on what earlier days discharged. The daily policy is therefore myopic "
    "with respect to any lifetime budget: with one warranted cycle remaining it takes today's "
    "small spread and cannot take tomorrow's larger one. A lifetime optimum would be at least "
    "as large, so this total is a lower bound on that optimum rather than an upper bound on "
    "achievable margin."
)


class DegradationDispatchInputError(ValueError):
    """Raised when prices, dispatch and degradation assumptions are inconsistent."""


@dataclass(frozen=True)
class DegradationDispatchResult:
    interval_schedule: pd.DataFrame
    daily_results: pd.DataFrame
    cohort_states: pd.DataFrame
    summary: dict[str, Any]


def simulate_degradation_dispatch(
    prices: pd.DataFrame,
    battery_config: BatteryDispatchConfig,
    degradation_config: DegradationConfig,
) -> DegradationDispatchResult:
    """Dispatch each complete market day using its beginning-of-day degraded limits.

    Each day restores the configured initial SOC fraction at day-end. Realized cell
    discharge from that solve updates cycle fade after dispatch; the next day's limits
    therefore use only previously realized throughput.
    """

    if not np.isclose(
        battery_config.initial_soc_fraction,
        battery_config.effective_terminal_soc_fraction,
    ):
        raise DegradationDispatchInputError(
            "Degradation dispatch requires terminal_soc_fraction to equal "
            "initial_soc_fraction for independent daily solves"
        )

    data = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(
        data,
        require_complete_days=battery_config.require_complete_market_days,
    )
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise DegradationDispatchInputError(
            f"Price data failed degradation-dispatch quality checks: {errors}"
        )

    working = data.copy()
    working["market_day"] = working["delivery_start_market"].dt.date
    first_day = working["market_day"].min()
    if first_day < degradation_config.project_start_day:
        raise DegradationDispatchInputError(
            "Price horizon cannot begin before degradation project_start_day"
        )

    state = initialize_degradation_state(
        nominal_energy_mwh=battery_config.energy_capacity_mwh,
        nominal_charge_power_mw=battery_config.charge_power_mw,
        nominal_discharge_power_mw=battery_config.discharge_power_mw,
        config=degradation_config,
    )
    interval_outputs: list[pd.DataFrame] = []
    daily_outputs: list[dict[str, Any]] = []
    if any(event.day < first_day for event in degradation_config.augmentation_events):
        raise DegradationDispatchInputError(
            "Augmentation before the price horizon requires a prior energy and cost history"
        )
    # Stored energy is allocated proportionally to usable cohort capacity. When
    # capacity fades, the same fraction of that cohort's energy becomes unavailable;
    # it is explicitly recorded, never silently reset or sold to the grid.
    stored = {"initial": battery_config.initial_soc_fraction * battery_config.energy_capacity_mwh}
    capacities = {"initial": battery_config.energy_capacity_mwh}

    for market_day, day_with_key in working.groupby("market_day", sort=True):
        day = day_with_key.loc[:, data.columns].reset_index(drop=True)
        prepared, start, events = prepare_degradation_day(
            state, market_day, degradation_config
        )
        opening_energy = sum(stored.values())
        boundary_energy = dict(stored)
        boundary_capacities = dict(capacities)
        retired_energy = 0.0
        commissioning_energy = 0.0
        for event in events:
            for key in event.retired_cohort_ids:
                retired_energy += boundary_energy.pop(key)
                boundary_capacities.pop(key)
            boundary_energy[event.event_id] = event.commissioning_energy_mwh
            boundary_capacities[event.event_id] = event.added_energy_mwh
            commissioning_energy += event.commissioning_energy_mwh
        calendar_loss = 0.0
        initial_energy = 0.0
        for cohort in start.cohorts:
            key = cohort.cohort_id
            retained_energy = (
                boundary_energy[key] * cohort.usable_energy_mwh / boundary_capacities[key]
                if boundary_capacities[key] > 0 else 0.0
            )
            calendar_loss += boundary_energy[key] - retained_energy
            if retained_energy > cohort.usable_energy_mwh + 1e-8:
                raise DegradationDispatchInputError("Commissioning energy exceeds usable capacity")
            initial_energy += retained_energy
        if start.usable_energy_mwh <= 1e-9:
            raise DegradationDispatchInputError(
                f"{market_day} has zero usable energy under degradation assumptions"
            )
        if start.usable_charge_power_mw <= 1e-9 or start.usable_discharge_power_mw <= 1e-9:
            raise DegradationDispatchInputError(
                f"{market_day} has zero usable power under degradation assumptions"
            )
        initial_soc = initial_energy / start.usable_energy_mwh
        if not battery_config.soc_min_fraction - 1e-9 <= initial_soc <= (
            battery_config.soc_max_fraction + 1e-9
        ):
            raise DegradationDispatchInputError(
                f"{market_day} carried and commissioned energy is outside SOC limits; "
                "declare commissioning energy or an admissible SOC range"
            )
        initial_soc = float(np.clip(
            initial_soc, battery_config.soc_min_fraction, battery_config.soc_max_fraction
        ))

        warranty_headroom_cell = warranty_discharge_headroom_mwh(
            start, degradation_config
        )
        allowed_grid_discharge = np.inf
        if battery_config.max_daily_equivalent_cycles is not None:
            allowed_grid_discharge = (
                battery_config.max_daily_equivalent_cycles
                * start.usable_energy_mwh
            )
        if (
            degradation_config.enforce_warranty_throughput_limit
            and warranty_headroom_cell is not None
        ):
            allowed_grid_discharge = min(
                allowed_grid_discharge,
                warranty_headroom_cell * battery_config.discharge_efficiency,
            )
        dynamic_daily_cycles = (
            None
            if np.isinf(allowed_grid_discharge)
            else max(0.0, allowed_grid_discharge / start.usable_energy_mwh)
        )
        dynamic_battery = replace(
            battery_config,
            charge_power_mw=start.usable_charge_power_mw,
            discharge_power_mw=start.usable_discharge_power_mw,
            energy_capacity_mwh=start.usable_energy_mwh,
            max_daily_equivalent_cycles=dynamic_daily_cycles,
            initial_soc_fraction=initial_soc,
            terminal_soc_fraction=battery_config.effective_terminal_soc_fraction,
        )

        dispatched = optimize_perfect_foresight(day, dynamic_battery)
        grid_discharge_mwh = float(dispatched.schedule["discharge_grid_mwh"].sum())
        cell_discharge_mwh = (
            grid_discharge_mwh / battery_config.discharge_efficiency
        )
        state, end, allocations = complete_degradation_day(
            prepared,
            market_day,
            cell_discharge_mwh,
            degradation_config,
        )

        terminal_energy = float(dispatched.summary["terminal_energy_mwh"])
        stored = {
            cohort.cohort_id: terminal_energy * cohort.usable_energy_mwh / start.usable_energy_mwh
            for cohort in end.cohorts
        }
        capacities = {cohort.cohort_id: cohort.usable_energy_mwh for cohort in end.cohorts}
        closing_energy = sum(stored.values())
        cycle_loss = terminal_energy - closing_energy
        grid_charge = float(dispatched.summary["grid_charge_mwh"])
        conversion_loss = (
            grid_charge * (1 - battery_config.charge_efficiency)
            + cell_discharge_mwh - grid_discharge_mwh
        )
        schedule = dispatched.schedule
        self_discharge_loss = float((
            schedule["energy_start_mwh"]
            * (1 - (1 - battery_config.self_discharge_per_hour) ** schedule["duration_hours"])
        ).sum())
        balance_residual = (
            opening_energy + commissioning_energy + grid_charge - grid_discharge_mwh
            - retired_energy - calendar_loss - cycle_loss - conversion_loss
            - self_discharge_loss - closing_energy
        )
        if abs(balance_residual) > 1e-6 * max(1.0, start.usable_energy_mwh):
            raise DegradationDispatchInputError(
                f"{market_day} stored-energy ledger does not reconcile"
            )

        interval = dispatched.schedule.copy()
        interval["market_day"] = market_day
        interval["nominal_energy_mwh_start"] = start.nominal_energy_mwh
        interval["usable_energy_mwh_start"] = start.usable_energy_mwh
        interval["retained_capacity_fraction_start"] = (
            start.retained_capacity_fraction
        )
        interval["usable_charge_power_mw_start"] = start.usable_charge_power_mw
        interval["usable_discharge_power_mw_start"] = (
            start.usable_discharge_power_mw
        )
        interval["warranty_discharge_headroom_cell_mwh_start"] = (
            warranty_headroom_cell
        )
        interval["effective_max_daily_equivalent_cycles"] = dynamic_daily_cycles
        interval["augmentation_event_ids"] = "|".join(
            event.event_id for event in events
        )
        interval["retired_cohort_ids"] = "|".join(
            cohort_id for event in events for cohort_id in event.retired_cohort_ids
        )
        interval_outputs.append(interval)

        daily_outputs.append(
            {
                "market_day": market_day,
                "interval_count": int(len(interval)),
                "augmentation_event_ids": "|".join(
                    event.event_id for event in events
                ),
                "retired_cohort_ids": "|".join(
                    cohort_id
                    for event in events
                    for cohort_id in event.retired_cohort_ids
                ),
                "augmentation_energy_mwh": float(
                    sum(event.added_energy_mwh for event in events)
                ),
                "augmentation_charge_power_mw": float(
                    sum(event.added_charge_power_mw for event in events)
                ),
                "augmentation_discharge_power_mw": float(
                    sum(event.added_discharge_power_mw for event in events)
                ),
                "augmentation_cost_eur": float(
                    sum(event.cost_eur for event in events)
                ),
                "commissioning_energy_cost_eur": float(
                    sum(event.commissioning_energy_cost_eur for event in events)
                ),
                "opening_stored_energy_mwh": opening_energy,
                "retired_stored_energy_mwh": retired_energy,
                "commissioning_energy_mwh": commissioning_energy,
                "calendar_fade_energy_loss_mwh": calendar_loss,
                "initial_energy_mwh": initial_energy,
                "terminal_energy_mwh": terminal_energy,
                "cycle_fade_energy_loss_mwh": cycle_loss,
                "closing_stored_energy_mwh": closing_energy,
                "conversion_loss_mwh": conversion_loss,
                "self_discharge_loss_mwh": self_discharge_loss,
                "energy_balance_residual_mwh": balance_residual,
                "nominal_energy_mwh_start": start.nominal_energy_mwh,
                "usable_energy_mwh_start": start.usable_energy_mwh,
                "retained_capacity_fraction_start": (
                    start.retained_capacity_fraction
                ),
                "usable_charge_power_mw_start": start.usable_charge_power_mw,
                "usable_discharge_power_mw_start": (
                    start.usable_discharge_power_mw
                ),
                "grid_charge_mwh": float(
                    dispatched.schedule["charge_grid_mwh"].sum()
                ),
                "grid_discharge_mwh": grid_discharge_mwh,
                "cell_discharge_mwh": cell_discharge_mwh,
                "fleet_equivalent_full_cycles_increment": (
                    cell_discharge_mwh / start.nominal_energy_mwh
                ),
                "cohort_allocation_mwh": "|".join(
                    f"{cohort_id}:{value:.9f}"
                    for cohort_id, value in allocations.items()
                ),
                "warranty_discharge_headroom_cell_mwh_start": (
                    warranty_headroom_cell
                ),
                "effective_max_daily_equivalent_cycles": (
                    dynamic_daily_cycles
                ),
                "net_market_margin_eur": dispatched.summary[
                    "net_market_margin_eur"
                ],
                "market_cash_margin_eur": dispatched.summary["market_cash_margin_eur"],
                "gross_discharge_revenue_eur": dispatched.summary[
                    "gross_discharge_revenue_eur"
                ],
                "charging_energy_cost_eur": dispatched.summary[
                    "charging_energy_cost_eur"
                ],
                "fees_eur": (
                    dispatched.summary["buy_fees_eur"]
                    + dispatched.summary["sell_fees_eur"]
                ),
                "monetary_degradation_adder_eur": dispatched.summary[
                    "degradation_cost_eur"
                ],
                "usable_energy_mwh_end": end.usable_energy_mwh,
                "retained_capacity_fraction_end": (
                    end.retained_capacity_fraction
                ),
                "usable_charge_power_mw_end": end.usable_charge_power_mw,
                "usable_discharge_power_mw_end": (
                    end.usable_discharge_power_mw
                ),
                "cumulative_cell_discharge_mwh_end": (
                    end.cumulative_cell_discharge_mwh
                ),
                "warranty_capacity_breach_end": (
                    end.warranty_capacity_breach
                ),
                "warranty_throughput_exceeded_end": (
                    end.warranty_throughput_exceeded
                ),
                "warranty_breach_end": end.warranty_breach,
                "below_retirement_threshold_end": (
                    end.below_retirement_threshold
                ),
            }
        )

    interval_schedule = pd.concat(interval_outputs, ignore_index=True)
    daily_results = pd.DataFrame.from_records(daily_outputs)
    final_snapshot_day = daily_results["market_day"].iloc[-1]
    _, final_snapshot, _ = prepare_degradation_day(
        state, final_snapshot_day, degradation_config
    )
    cohort_states = degradation_cohort_table(final_snapshot)
    total_margin = float(daily_results["net_market_margin_eur"].sum())
    augmentation_cost = float(daily_results["augmentation_cost_eur"].sum())
    summary = {
        "result_label": DEGRADED_DISPATCH_LABEL,
        "result_basis_note": DEGRADED_DISPATCH_BASIS_NOTE,
        "market_day_count": int(len(daily_results)),
        "interval_count": int(len(interval_schedule)),
        "first_market_day": str(daily_results["market_day"].min()),
        "last_market_day": str(daily_results["market_day"].max()),
        "net_market_margin_eur": total_margin,
        "market_cash_margin_eur": float(daily_results["market_cash_margin_eur"].sum()),
        "dispatch_wear_penalty_eur": float(daily_results["monetary_degradation_adder_eur"].sum()),
        "commissioning_energy_cost_eur": float(
            daily_results["commissioning_energy_cost_eur"].sum()
        ),
        "energy_accounting_convention": "cohort_energy_ledger_v1",
        "initial_stored_energy_mwh": float(daily_results["opening_stored_energy_mwh"].iloc[0]),
        "final_stored_energy_mwh": float(daily_results["closing_stored_energy_mwh"].iloc[-1]),
        "energy_ledger_totals_mwh": {
            key: float(daily_results[key].sum())
            for key in ("commissioning_energy_mwh", "retired_stored_energy_mwh",
                        "calendar_fade_energy_loss_mwh", "cycle_fade_energy_loss_mwh",
                        "conversion_loss_mwh", "self_discharge_loss_mwh")
        },
        "maximum_energy_balance_residual_mwh": float(
            daily_results["energy_balance_residual_mwh"].abs().max()
        ),
        "augmentation_cost_eur": augmentation_cost,
        "grid_charge_mwh": float(daily_results["grid_charge_mwh"].sum()),
        "grid_discharge_mwh": float(daily_results["grid_discharge_mwh"].sum()),
        "cell_discharge_mwh": float(daily_results["cell_discharge_mwh"].sum()),
        "initial_nominal_energy_mwh": battery_config.energy_capacity_mwh,
        "final_nominal_energy_mwh": final_snapshot.nominal_energy_mwh,
        "final_usable_energy_mwh": final_snapshot.usable_energy_mwh,
        "final_retained_capacity_fraction": (
            final_snapshot.retained_capacity_fraction
        ),
        "final_usable_charge_power_mw": (
            final_snapshot.usable_charge_power_mw
        ),
        "final_usable_discharge_power_mw": (
            final_snapshot.usable_discharge_power_mw
        ),
        "applied_augmentation_event_ids": list(
            state.applied_augmentation_event_ids
        ),
        "warranty_capacity_breach": final_snapshot.warranty_capacity_breach,
        "warranty_throughput_exceeded": (
            final_snapshot.warranty_throughput_exceeded
        ),
        "warranty_breach": final_snapshot.warranty_breach,
        "below_retirement_threshold": (
            final_snapshot.below_retirement_threshold
        ),
        "daily_terminal_soc_policy": (
            "Carry stored energy between days; target the configured terminal SOC fraction "
            "of beginning-of-day usable capacity, then record energy made unavailable by fade"
        ),
        "stored_energy_policy": (
            "Energy allocated by usable cohort capacity. Fade makes the same fraction of "
            "stored energy unavailable; retirement removes its cohort's stored energy. "
            "Added capacity starts empty unless commissioning energy is declared; its "
            "separate cost is passed to finance"
        ),
        "capacity_timing_policy": (
            "Beginning-of-day degraded limits use calendar age and only prior "
            "realized throughput; current-day discharge updates end-of-day state"
        ),
        "throughput_allocation_policy": (
            "Cell discharge allocated to cohorts in proportion to "
            "beginning-of-day usable energy"
        ),
        "augmentation_cost_policy": (
            "Augmentation cost is recorded separately and is not subtracted from "
            "DAM market margin; it can be passed to the separate v0.6 unlevered "
            "project-finance workflow"
        ),
        "monetary_degradation_adder_policy": (
            "The per-MWh degradation adder is a non-cash dispatch wear penalty; "
            "market_cash_margin_eur excludes it, and finance deducts actual expenses once"
        ),
        "battery_config": battery_config.to_dict(),
        "degradation_config": degradation_config.to_dict(),
        "final_cohorts": [
            {
                **asdict(cohort),
                "commissioned_day": cohort.commissioned_day.isoformat(),
            }
            for cohort in final_snapshot.cohorts
        ],
    }
    return DegradationDispatchResult(
        interval_schedule=interval_schedule,
        daily_results=daily_results,
        cohort_states=cohort_states,
        summary=summary,
    )
