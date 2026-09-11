"""The per-day loop that connects forecasting, ageing, settlement and cash flows.

This module implements section 4 of `docs/integrated_study_design.md` and nothing else. It
computes no new arithmetic: every step is an existing contract, called in the one order that
makes the join safe.

The two properties it exists to hold are worth naming where they are implemented rather than
only in the design:

**Each strategy owns its ageing state.** A single `DegradationState` shared across a strategy
loop is the obvious way to write this loop and produces entirely plausible numbers, in which a
cautious strategy silently pays for an aggressive one's throughput. States are therefore held
in a per-strategy mapping, advanced only by that strategy's own settled discharge, and the
declaration order of the strategies cannot reach any of them.

**No day may read its own outcome.** A planner other than `perfect_foresight` sees only prices
from days strictly before the delivery day, which the causal forecast generator already
guarantees; prices after the declared window are discarded before a forecast is generated at
all, so a longer history cannot enter through the window's last days.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical
from ..degradation import (
    DegradationSnapshot,
    DegradationState,
    complete_degradation_day,
    initialize_degradation_state,
    prepare_degradation_day,
    warranty_discharge_headroom_mwh,
)
from ..dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from ..finance import ProjectFinanceResult, evaluate_project_finance
from ..forecast import generate_naive_forecasts
from .config import (
    IntegratedStudyConfig,
    IntegratedStudyInputError,
    StrategySpec,
)

TOLERANCE = 1e-9


@dataclass(frozen=True)
class StrategyRun:
    """One strategy's complete pass over the declared window."""

    spec: StrategySpec
    daily_results: pd.DataFrame
    finance: ProjectFinanceResult
    final_state: DegradationState
    final_snapshot: DegradationSnapshot


@dataclass(frozen=True)
class IntegratedStudyRun:
    """Every strategy's pass over one declared window, before results are assembled."""

    config: IntegratedStudyConfig
    strategy_runs: tuple[StrategyRun, ...]
    coverage: dict[str, Any]


def run_integrated_study(
    prices: pd.DataFrame, config: IntegratedStudyConfig
) -> IntegratedStudyRun:
    """Run every declared strategy over the declared window, or refuse to run at all."""

    data, coverage = _window_prices(prices, config)
    forecasts = _window_forecasts(data, config)
    day_frames = _day_frames(data, config)

    states = {
        strategy.strategy_id: initialize_degradation_state(
            nominal_energy_mwh=config.battery.energy_capacity_mwh,
            nominal_charge_power_mw=config.battery.charge_power_mw,
            nominal_discharge_power_mw=config.battery.discharge_power_mw,
            config=config.degradation,
        )
        for strategy in config.strategies
    }
    rows: dict[str, list[dict[str, Any]]] = {
        strategy.strategy_id: [] for strategy in config.strategies
    }

    for market_day in config.window_days:
        actual_day = day_frames[market_day]
        realized_prices = actual_day["price_eur_per_mwh"].to_numpy(dtype=float)
        for strategy in config.strategies:
            state = states[strategy.strategy_id]
            prepared, start, events = prepare_degradation_day(
                state, market_day, config.degradation
            )
            _refuse_exhausted_state(strategy, market_day, start)
            day_battery, allowed_cycles = _beginning_of_day_battery(
                config.battery, config.degradation, start
            )

            if strategy.reads_realized_delivery_day_prices:
                planned = optimize_perfect_foresight(actual_day, day_battery)
                ceiling = planned
                planned_prices = realized_prices
            else:
                planned_day = actual_day.copy()
                planned_prices = (
                    forecasts.loc[actual_day["delivery_start_utc"], strategy.planner]
                    .to_numpy(dtype=float)
                )
                planned_day["price_eur_per_mwh"] = planned_prices
                planned = optimize_perfect_foresight(planned_day, day_battery)
                ceiling = optimize_perfect_foresight(actual_day, day_battery)

            settled = _settle(planned.schedule, realized_prices, config.battery)
            cell_discharge_mwh = (
                settled.grid_discharge_mwh / config.battery.discharge_efficiency
            )
            states[strategy.strategy_id], end, _ = complete_degradation_day(
                prepared, market_day, cell_discharge_mwh, config.degradation
            )
            rows[strategy.strategy_id].append(
                _daily_row(
                    strategy=strategy,
                    market_day=market_day,
                    interval_count=len(actual_day),
                    settled=settled,
                    planned=planned,
                    ceiling=ceiling,
                    planned_prices=planned_prices,
                    realized_prices=realized_prices,
                    cell_discharge_mwh=cell_discharge_mwh,
                    start=start,
                    end=end,
                    events=events,
                    allowed_cycles=allowed_cycles,
                    battery=day_battery,
                )
            )

    strategy_runs: list[StrategyRun] = []
    for strategy in config.strategies:
        daily = pd.DataFrame.from_records(rows[strategy.strategy_id])
        finance = evaluate_project_finance(
            daily.loc[
                :,
                [
                    "market_day",
                    "net_market_margin_eur",
                    "grid_discharge_mwh",
                    "augmentation_cost_eur",
                ],
            ],
            replace(config.finance, operating_margin_case=strategy.operating_margin_case),
        )
        _, final_snapshot, _ = prepare_degradation_day(
            states[strategy.strategy_id], config.window_end_day, config.degradation
        )
        strategy_runs.append(
            StrategyRun(
                spec=strategy,
                daily_results=daily,
                finance=finance,
                final_state=states[strategy.strategy_id],
                final_snapshot=final_snapshot,
            )
        )
    return IntegratedStudyRun(
        config=config, strategy_runs=tuple(strategy_runs), coverage=coverage
    )


def _window_prices(
    prices: pd.DataFrame, config: IntegratedStudyConfig
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return history up to the window's last day, refusing any gap inside the window.

    Days after the window are dropped before anything reads them, and the count is recorded:
    a study that silently used a longer history would make its own causality claim
    unverifiable. Days before the window are kept, because a causal forecast for the window's
    first day has to come from somewhere.
    """

    data = ensure_canonical(prices, allow_empty=False)
    working = data.copy()
    working["market_day"] = working["delivery_start_market"].dt.date
    after_window = working["market_day"].gt(config.window_end_day)
    discarded_days = int(working.loc[after_window, "market_day"].nunique())
    discarded_intervals = int(after_window.sum())
    retained = working.loc[~after_window].reset_index(drop=True)
    if retained.empty:
        raise IntegratedStudyInputError(
            "No supplied delivery day falls on or before "
            f"{config.window_end_day.isoformat()}"
        )

    # The window check runs before the quality gate so that an absent delivery day is named
    # as the missing day it is. The gate would also refuse it, but as a non-contiguous
    # horizon somewhere in the history, which tells a reader nothing about which day to
    # supply. A day that is present but incomplete stays the gate's finding.
    observed = set(retained["market_day"])
    missing = [day for day in config.window_days if day not in observed]
    if missing:
        raise IntegratedStudyInputError(
            f"The declared window {config.window_start_day.isoformat()}.."
            f"{config.window_end_day.isoformat()} is missing official prices for "
            f"{len(missing)} delivery day(s), first {missing[0].isoformat()}. The study "
            "refuses a gap rather than bridging it: no day is filled, imputed or treated as "
            "a no-trade day. Declare a narrower continuous window"
        )

    quality = assess_quality(
        data, require_complete_days=config.battery.require_complete_market_days
    )
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise IntegratedStudyInputError(
            f"Price data failed integrated-study quality checks: {errors}"
        )

    history_days = sorted({day for day in observed if day < config.window_start_day})
    coverage: dict[str, Any] = {
        "declared_window_day_count": len(config.window_days),
        "built_day_count": len(config.window_days),
        "excluded_day_count": 0,
        "excluded_days_by_cause": {},
        "prior_history_day_count": len(history_days),
        "first_prior_history_day": (
            history_days[0].isoformat() if history_days else None
        ),
        "discarded_post_window_day_count": discarded_days,
        "discarded_post_window_interval_count": discarded_intervals,
        "coverage_policy": (
            "Built days and excluded days partition the declared window exactly. Every "
            "excluded day fails the run: exclusion is a diagnostic, not an outcome"
        ),
    }
    return retained.loc[:, data.columns].reset_index(drop=True), coverage


def _window_forecasts(
    data: pd.DataFrame, config: IntegratedStudyConfig
) -> pd.DataFrame:
    """Generate every declared naive forecast, refusing a window day any of them cannot cover."""

    methods = config.forecast_methods
    if not methods:
        return pd.DataFrame()
    result = generate_naive_forecasts(
        data,
        methods=list(methods),
        rolling_window_days=config.rolling_window_days,
    )
    table = result.forecasts
    window = table.loc[table["market_day"].isin(set(config.window_days))]
    for method in methods:
        incomplete = sorted(
            {
                day
                for day, missing in window.groupby("market_day", sort=True)[method]
                .apply(lambda column: bool(column.isna().any()))
                .items()
                if missing
            }
        )
        if incomplete:
            raise IntegratedStudyInputError(
                f"The {method} forecast is incomplete on {len(incomplete)} declared window "
                f"day(s), first {incomplete[0].isoformat()}. Every compared strategy must "
                "have a complete forecast for every day of the window; supply more price "
                "history before the window, or declare a narrower window"
            )
    return window.set_index("delivery_start_utc")


def _day_frames(
    data: pd.DataFrame, config: IntegratedStudyConfig
) -> dict[date, pd.DataFrame]:
    working = data.copy()
    working["market_day"] = working["delivery_start_market"].dt.date
    window = set(config.window_days)
    frames: dict[date, pd.DataFrame] = {}
    for market_day, day in working.groupby("market_day", sort=True):
        if market_day in window:
            frames[market_day] = day.loc[:, data.columns].reset_index(drop=True)
    return frames


def _refuse_exhausted_state(
    strategy: StrategySpec, market_day: date, start: DegradationSnapshot
) -> None:
    if start.usable_energy_mwh <= TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy.strategy_id} begins {market_day.isoformat()} with no usable "
            "energy under the declared degradation assumptions"
        )
    if (
        start.usable_charge_power_mw <= TOLERANCE
        or start.usable_discharge_power_mw <= TOLERANCE
    ):
        raise IntegratedStudyInputError(
            f"Strategy {strategy.strategy_id} begins {market_day.isoformat()} with no usable "
            "power under the declared degradation assumptions"
        )


def _beginning_of_day_battery(
    battery: BatteryDispatchConfig,
    degradation: Any,
    start: DegradationSnapshot,
) -> tuple[BatteryDispatchConfig, float | None]:
    """Build the day's dispatch limits from the state the strategy begins the day with.

    This is the same derivation `simulate_degradation_dispatch` applies, kept identical on
    purpose: the study must reproduce the existing backtests when fade is zero, and a second
    way of turning a snapshot into a battery would be a second thing to keep in step.
    """

    warranty_headroom_cell = warranty_discharge_headroom_mwh(start, degradation)
    allowed_grid_discharge = np.inf
    if battery.max_daily_equivalent_cycles is not None:
        allowed_grid_discharge = (
            battery.max_daily_equivalent_cycles * start.usable_energy_mwh
        )
    if (
        degradation.enforce_warranty_throughput_limit
        and warranty_headroom_cell is not None
    ):
        allowed_grid_discharge = min(
            allowed_grid_discharge,
            warranty_headroom_cell * battery.discharge_efficiency,
        )
    allowed_cycles = (
        None
        if np.isinf(allowed_grid_discharge)
        else max(0.0, allowed_grid_discharge / start.usable_energy_mwh)
    )
    day_battery = replace(
        battery,
        charge_power_mw=start.usable_charge_power_mw,
        discharge_power_mw=start.usable_discharge_power_mw,
        energy_capacity_mwh=start.usable_energy_mwh,
        max_daily_equivalent_cycles=allowed_cycles,
    )
    return day_battery, allowed_cycles


@dataclass(frozen=True)
class _Settlement:
    grid_charge_mwh: float
    grid_discharge_mwh: float
    charging_energy_cost_eur: float
    discharge_energy_revenue_eur: float
    buy_fees_eur: float
    sell_fees_eur: float
    monetary_degradation_adder_eur: float
    net_market_margin_eur: float


def _settle(
    planned_schedule: pd.DataFrame,
    realized_prices: np.ndarray,
    battery: BatteryDispatchConfig,
) -> _Settlement:
    """Value planned quantities at the prices that actually occurred.

    The separation is the existing one from `backtest/forecast_dispatch.py`: quantities come
    from the plan, prices come from the market, and fees and the monetary degradation adder
    are properties of the quantities rather than of the price that was expected.
    """

    if len(planned_schedule) != len(realized_prices):
        raise IntegratedStudyInputError(
            "The planned schedule and the realized prices have different lengths"
        )
    charge_mwh = planned_schedule["charge_grid_mwh"].to_numpy(dtype=float)
    discharge_mwh = planned_schedule["discharge_grid_mwh"].to_numpy(dtype=float)
    charge_cost = float(np.sum(realized_prices * charge_mwh))
    discharge_revenue = float(np.sum(realized_prices * discharge_mwh))
    buy_fees = float(planned_schedule["buy_fee_eur"].sum())
    sell_fees = float(planned_schedule["sell_fee_eur"].sum())
    adder = float(planned_schedule["degradation_cost_eur"].sum())
    return _Settlement(
        grid_charge_mwh=float(np.sum(charge_mwh)),
        grid_discharge_mwh=float(np.sum(discharge_mwh)),
        charging_energy_cost_eur=charge_cost,
        discharge_energy_revenue_eur=discharge_revenue,
        buy_fees_eur=buy_fees,
        sell_fees_eur=sell_fees,
        monetary_degradation_adder_eur=adder,
        net_market_margin_eur=(
            discharge_revenue - charge_cost - buy_fees - sell_fees - adder
        ),
    )


def _daily_row(
    *,
    strategy: StrategySpec,
    market_day: date,
    interval_count: int,
    settled: _Settlement,
    planned: Any,
    ceiling: Any,
    planned_prices: np.ndarray,
    realized_prices: np.ndarray,
    cell_discharge_mwh: float,
    start: DegradationSnapshot,
    end: DegradationSnapshot,
    events: tuple[Any, ...],
    allowed_cycles: float | None,
    battery: BatteryDispatchConfig,
) -> dict[str, Any]:
    error = planned_prices - realized_prices
    is_perfect_foresight = strategy.reads_realized_delivery_day_prices
    day_ceiling = float(ceiling.summary["net_market_margin_eur"])
    return {
        "strategy_id": strategy.strategy_id,
        "market_day": market_day,
        "planner": strategy.planner,
        "decision_information": strategy.decision_information,
        "interval_count": interval_count,
        "planned_margin_eur": float(planned.summary["net_market_margin_eur"]),
        "net_market_margin_eur": settled.net_market_margin_eur,
        "day_ceiling_under_own_state_eur": day_ceiling,
        "day_regret_under_own_state_eur": day_ceiling - settled.net_market_margin_eur,
        # A planner that reads realized prices makes no price error, which is not the same
        # statement as an error of zero; the cell stays empty rather than claiming perfect
        # accuracy. `float("nan")` keeps the column numeric so a strategy that records no
        # error and one that records an error still concatenate as one dtype.
        "planned_price_mae_eur_per_mwh": (
            float("nan") if is_perfect_foresight else float(np.mean(np.abs(error)))
        ),
        "planned_price_rmse_eur_per_mwh": (
            float("nan") if is_perfect_foresight else float(np.sqrt(np.mean(error**2)))
        ),
        "grid_charge_mwh": settled.grid_charge_mwh,
        "grid_discharge_mwh": settled.grid_discharge_mwh,
        "cell_discharge_mwh": cell_discharge_mwh,
        "charging_energy_cost_eur": settled.charging_energy_cost_eur,
        "discharge_energy_revenue_eur": settled.discharge_energy_revenue_eur,
        "buy_fees_eur": settled.buy_fees_eur,
        "sell_fees_eur": settled.sell_fees_eur,
        "monetary_degradation_adder_eur": settled.monetary_degradation_adder_eur,
        "augmentation_cost_eur": float(sum(event.cost_eur for event in events)),
        "augmentation_event_ids": "|".join(event.event_id for event in events),
        "usable_energy_mwh_start": start.usable_energy_mwh,
        "usable_charge_power_mw_start": start.usable_charge_power_mw,
        "usable_discharge_power_mw_start": start.usable_discharge_power_mw,
        "retained_capacity_fraction_start": start.retained_capacity_fraction,
        "effective_max_daily_equivalent_cycles": allowed_cycles,
        "initial_energy_mwh": float(planned.summary["initial_energy_mwh"]),
        "terminal_energy_mwh": float(planned.summary["terminal_energy_mwh"]),
        "configured_initial_energy_mwh": (
            battery.initial_soc_fraction * battery.energy_capacity_mwh
        ),
        "configured_terminal_energy_mwh": (
            battery.effective_terminal_soc_fraction * battery.energy_capacity_mwh
        ),
        "usable_energy_mwh_end": end.usable_energy_mwh,
        "retained_capacity_fraction_end": end.retained_capacity_fraction,
        "cumulative_cell_discharge_mwh_end": end.cumulative_cell_discharge_mwh,
        "warranty_capacity_breach_end": end.warranty_capacity_breach,
        "warranty_throughput_exceeded_end": end.warranty_throughput_exceeded,
        "below_retirement_threshold_end": end.below_retirement_threshold,
    }
