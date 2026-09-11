"""Per-strategy tables, the study summary and the reconciliations that guard them.

A study's headline is a table of strategies, not a single number, and this module is where
that is enforced. Two things it deliberately does not produce:

- **No ceiling across strategies.** Once the strategies have aged differently there is no one
  physical state a perfect-foresight bound could be conditional on, so the per-day ceiling
  under a strategy's own state stays in that strategy's daily table and is never summed into a
  study-level figure (design §5.2, `METHODOLOGY.md` §5.1).
- **No annualised or extrapolated figure.** The window is the horizon; finance reports over
  exactly the declared days and nothing is scaled to a year or a project life.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..degradation import DEGRADATION_MODEL_LABEL
from .config import IntegratedStudyConfig, IntegratedStudyInputError
from .runner import IntegratedStudyRun, StrategyRun

#: What every integrated study result is, and what it is not. The declared study label is
#: appended to this sentence rather than replacing it, so a study cannot be recorded under a
#: description that drops the standing negatives.
INTEGRATED_STUDY_LABEL = (
    "Integrated Greek DAM study: one policy's settled outcome over a declared historical "
    "window, with each strategy ageing under its own realized throughput and illustrative "
    "cost assumptions. Not expected revenue, not a forecast, not investment evidence, and "
    "not a lifetime optimum or an upper bound."
)

#: Why the aggregate is a simulation rather than a bound, in one recordable sentence, for the
#: same reason `backtest/degradation_dispatch.py` records one: a reader who sees only the
#: total needs the reason attached to it.
INTEGRATED_STUDY_BASIS_NOTE = (
    "Each market day is planned on the information that strategy was allowed to read and "
    "settled at realized prices, under the limits that strategy begins the day with. Those "
    "limits depend on what that strategy discharged earlier, so a strategy's total is what "
    "its own policy achieved and not a ceiling over policies. After the first day the "
    "strategies hold different physical states, so no single perfect-foresight ceiling is "
    "conditional on all of them and none is reported."
)

#: The reconciliation tolerance for a per-day energy or cost identity, in absolute units. It
#: is looser than float equality because the dispatch schedule is a solver result and tighter
#: than anything that could hide a mis-stated cost.
RECONCILIATION_TOLERANCE = 1e-6


@dataclass(frozen=True)
class IntegratedStudyResult:
    """One study: its per-day rows, its per-strategy summary, its cash flows and its result."""

    daily_results: pd.DataFrame
    strategy_summaries: pd.DataFrame
    cash_flows: pd.DataFrame
    summary: dict[str, Any]


def assemble_integrated_study(run: IntegratedStudyRun) -> IntegratedStudyResult:
    """Turn one completed run into the tables and the recorded result."""

    config = run.config
    daily = pd.concat(
        [strategy_run.daily_results for strategy_run in run.strategy_runs],
        ignore_index=True,
    )
    cash_flows = pd.concat(
        [
            strategy_run.finance.daily_cash_flows.assign(
                strategy_id=strategy_run.spec.strategy_id
            )
            for strategy_run in run.strategy_runs
        ],
        ignore_index=True,
    )
    cash_flows = cash_flows.loc[
        :, ["strategy_id", *[c for c in cash_flows.columns if c != "strategy_id"]]
    ]
    summaries = [
        _strategy_summary(config, strategy_run) for strategy_run in run.strategy_runs
    ]
    strategy_summaries = pd.DataFrame.from_records(summaries)
    _refuse_shared_state(config, strategy_summaries)

    summary: dict[str, Any] = {
        "result_label": f"{INTEGRATED_STUDY_LABEL} {config.result_label.strip()}",
        "result_basis_note": INTEGRATED_STUDY_BASIS_NOTE,
        "study_id": config.study_id,
        "price_source": config.price_source,
        "window_start_day": config.window_start_day.isoformat(),
        "window_end_day": config.window_end_day.isoformat(),
        "window_day_count": len(config.window_days),
        "strategy_count": len(run.strategy_runs),
        "strategy_ids": [
            strategy_run.spec.strategy_id for strategy_run in run.strategy_runs
        ],
        "strategies": summaries,
        "coverage": run.coverage,
        "declared_finance_operating_margin_case": (
            config.finance.operating_margin_case
        ),
        "study_configuration": config.to_dict(),
        "degradation_model_label": DEGRADATION_MODEL_LABEL,
        "shared_ceiling_reported": False,
        "ceiling_policy": (
            "A perfect-foresight ceiling is conditional on a physical state. The strategies "
            "hold different states from the second day onward, so a per-day ceiling is "
            "recorded under each strategy's own state and no ceiling is reported across them"
        ),
        "finance_horizon_policy": (
            "Finance covers exactly the declared window and nothing is annualised, "
            "extrapolated to a project life, or repeated"
        ),
        "operating_margin_case_policy": (
            "The finance operating-margin case describes the operating path, so it is "
            "derived from each strategy's planner rather than shared; the declared case is "
            "recorded beside the derived ones"
        ),
        "state_isolation_policy": (
            "Every strategy holds its own degradation state, advanced only by its own "
            "settled throughput; declaration order reaches no strategy's result"
        ),
        "terminal_soc_policy": (
            "Configured initial SOC restored at every market-day end, for every strategy"
        ),
        "market_acceptance_assumption": (
            "Price-taking planned quantities are fully accepted; bid acceptance and "
            "imbalance exposure are excluded"
        ),
        "monetary_degradation_adder_policy": (
            "The per-MWh monetary adder is a non-cash dispatch wear penalty. It steers the "
            "plan and is deducted in net_market_margin_eur, but market_cash_margin_eur "
            "excludes it and finance reads that. Augmentation capital cost and declared "
            "commissioning energy are separate cash flows the finance model applies once"
        ),
        "stored_energy_policy": (
            "Each strategy carries its own stored energy between days, allocated by usable "
            "cohort capacity. Fade makes the same proportion unavailable and retirement "
            "removes its cohort's energy; capacity added by an augmentation starts empty "
            "unless the event declares commissioning energy, whose cost finance pays once"
        ),
    }
    return IntegratedStudyResult(
        daily_results=daily,
        strategy_summaries=strategy_summaries,
        cash_flows=cash_flows,
        summary=summary,
    )


def _strategy_summary(
    config: IntegratedStudyConfig, strategy_run: StrategyRun
) -> dict[str, Any]:
    daily = strategy_run.daily_results
    finance = strategy_run.finance.summary
    final = strategy_run.final_snapshot
    _reconcile(config, strategy_run)
    return {
        "strategy_id": strategy_run.spec.strategy_id,
        "planner": strategy_run.spec.planner,
        "decision_information": strategy_run.spec.decision_information,
        "operating_margin_case": strategy_run.spec.operating_margin_case,
        "market_day_count": int(len(daily)),
        "net_market_margin_eur": float(daily["net_market_margin_eur"].sum()),
        "market_cash_margin_eur": float(daily["market_cash_margin_eur"].sum()),
        "planned_margin_eur": float(daily["planned_margin_eur"].sum()),
        "grid_charge_mwh": float(daily["grid_charge_mwh"].sum()),
        "grid_discharge_mwh": float(daily["grid_discharge_mwh"].sum()),
        "cell_discharge_mwh": float(daily["cell_discharge_mwh"].sum()),
        "buy_fees_eur": float(daily["buy_fees_eur"].sum()),
        "sell_fees_eur": float(daily["sell_fees_eur"].sum()),
        "monetary_degradation_adder_eur": float(
            daily["monetary_degradation_adder_eur"].sum()
        ),
        "augmentation_cost_eur": float(daily["augmentation_cost_eur"].sum()),
        "commissioning_energy_cost_eur": float(
            daily["commissioning_energy_cost_eur"].sum()
        ),
        "commissioning_energy_mwh": float(daily["commissioning_energy_mwh"].sum()),
        "opening_stored_energy_mwh": float(daily["opening_stored_energy_mwh"].iloc[0]),
        "closing_stored_energy_mwh": float(daily["closing_stored_energy_mwh"].iloc[-1]),
        "maximum_energy_balance_residual_mwh": float(
            daily["energy_balance_residual_mwh"].abs().max()
        ),
        "loss_making_day_count": int(daily["market_cash_margin_eur"].lt(0).sum()),
        "planned_price_mae_eur_per_mwh": _optional_mean(
            daily["planned_price_mae_eur_per_mwh"]
        ),
        "planned_price_rmse_eur_per_mwh": _optional_mean(
            daily["planned_price_rmse_eur_per_mwh"]
        ),
        "initial_usable_energy_mwh": float(daily["usable_energy_mwh_start"].iloc[0]),
        "final_usable_energy_mwh": final.usable_energy_mwh,
        "final_nominal_energy_mwh": final.nominal_energy_mwh,
        "final_retained_capacity_fraction": final.retained_capacity_fraction,
        "final_cumulative_cell_discharge_mwh": final.cumulative_cell_discharge_mwh,
        "equivalent_full_cycles": float(
            daily["cell_discharge_mwh"].sum() / config.battery.energy_capacity_mwh
        ),
        "warranty_capacity_breach": final.warranty_capacity_breach,
        "warranty_throughput_exceeded": final.warranty_throughput_exceeded,
        "below_retirement_threshold": final.below_retirement_threshold,
        "applied_augmentation_event_ids": list(
            strategy_run.final_state.applied_augmentation_event_ids
        ),
        "npv_eur": finance["npv_eur"],
        "irr_fraction": finance["irr_fraction"],
        "irr_status": finance["irr_status"],
        "initial_capex_eur": finance["initial_capex_eur"],
        "realized_market_margin_eur": finance["realized_market_margin_eur"],
        "undiscounted_project_cash_flow_eur": finance[
            "undiscounted_project_cash_flow_eur"
        ],
        "finance_result_label": finance["result_label"],
    }


def _reconcile(config: IntegratedStudyConfig, strategy_run: StrategyRun) -> None:
    """Check the identities the design requires before a figure is allowed out.

    Each is an identity the composition must satisfy by construction, so a failure here is a
    defect in the join rather than an unusual input. They are checked on every run instead of
    only in tests, because the join is the thing this unit adds and nothing downstream could
    detect a broken one from the numbers alone.
    """

    daily = strategy_run.daily_results
    strategy_id = strategy_run.spec.strategy_id

    # A day an augmentation lands on opens below the configured fraction by construction:
    # added capacity is empty unless the event declares commissioning energy. Every other day
    # must open exactly where the previous one closed, scaled by that day's usable capacity.
    carried_day = daily["augmentation_event_ids"].eq("")
    energy_start_error = (
        daily["initial_energy_mwh"] - daily["configured_initial_energy_mwh"]
    ).abs().where(carried_day, 0.0)
    energy_end_error = (
        daily["terminal_energy_mwh"] - daily["configured_terminal_energy_mwh"]
    ).abs()
    for name, error in (
        ("initial", energy_start_error),
        ("terminal", energy_end_error),
    ):
        worst = float(error.max())
        if worst > RECONCILIATION_TOLERANCE:
            raise IntegratedStudyInputError(
                f"Strategy {strategy_id} does not reconcile its {name} stored energy against "
                f"the configured SOC on at least one day (worst deviation {worst:.9f} MWh)"
            )

    adder = config.battery.degradation_cost_eur_per_mwh_discharged
    expected_adder = daily["grid_discharge_mwh"] * adder
    worst_adder = float((daily["monetary_degradation_adder_eur"] - expected_adder).abs().max())
    if worst_adder > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} records a monetary degradation adder that does not "
            f"reconcile against the configured rate (worst deviation EUR {worst_adder:.9f})"
        )

    expected_fees = (
        daily["grid_charge_mwh"] * config.battery.buy_fee_eur_per_mwh
        + daily["grid_discharge_mwh"] * config.battery.sell_fee_eur_per_mwh
    )
    worst_fees = float(
        ((daily["buy_fees_eur"] + daily["sell_fees_eur"]) - expected_fees).abs().max()
    )
    if worst_fees > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} records fees that do not reconcile against the "
            f"configured rates (worst deviation EUR {worst_fees:.9f})"
        )

    expected_margin = (
        daily["discharge_energy_revenue_eur"]
        - daily["charging_energy_cost_eur"]
        - daily["buy_fees_eur"]
        - daily["sell_fees_eur"]
        - daily["monetary_degradation_adder_eur"]
    )
    worst_margin = float((daily["net_market_margin_eur"] - expected_margin).abs().max())
    if worst_margin > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} records a settled margin that does not reconcile "
            f"against its own components (worst deviation EUR {worst_margin:.9f})"
        )

    expected_cash_margin = (
        daily["discharge_energy_revenue_eur"]
        - daily["charging_energy_cost_eur"]
        - daily["buy_fees_eur"]
        - daily["sell_fees_eur"]
    )
    worst_cash = float((daily["market_cash_margin_eur"] - expected_cash_margin).abs().max())
    if worst_cash > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} records a cash margin that does not reconcile against "
            f"its own components (worst deviation EUR {worst_cash:.9f})"
        )

    # The wear adder is a dispatch signal. Finance must receive the cash margin without it,
    # or the study pays a shadow price in euro it never owed.
    cash_total = float(daily["market_cash_margin_eur"].sum())
    finance_cash = float(
        strategy_run.finance.daily_cash_flows["market_margin_input_eur"].sum()
    )
    if abs(cash_total - finance_cash) > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} settled EUR {cash_total:.2f} of cash margin but finance "
            f"read EUR {finance_cash:.2f}"
        )

    augmentation_total = float(daily["augmentation_cost_eur"].sum())
    finance_augmentation = float(
        strategy_run.finance.daily_cash_flows["augmentation_cost_eur"].sum()
    )
    if abs(augmentation_total - finance_augmentation) > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} passes EUR {augmentation_total:.2f} of augmentation "
            f"cost to finance but finance applied EUR {finance_augmentation:.2f}"
        )

    commissioning_total = float(daily["commissioning_energy_cost_eur"].sum())
    finance_commissioning = float(
        strategy_run.finance.daily_cash_flows["commissioning_energy_cost_eur"].sum()
    )
    if abs(commissioning_total - finance_commissioning) > RECONCILIATION_TOLERANCE:
        raise IntegratedStudyInputError(
            f"Strategy {strategy_id} passes EUR {commissioning_total:.2f} of commissioning "
            f"energy cost to finance but finance applied EUR {finance_commissioning:.2f}"
        )


def _refuse_shared_state(
    config: IntegratedStudyConfig, strategy_summaries: pd.DataFrame
) -> None:
    """Refuse a result in which strategies with different throughput aged identically.

    Sharing one degradation state across the strategy loop is the defect this study is most
    likely to acquire, and it produces entirely plausible numbers. The symptom it cannot hide
    is this one: different cell discharge, identical end-of-window capacity.

    The check is scoped to a configuration whose cycle fade is non-zero, because that is the
    only configuration in which throughput is supposed to move capacity at all. Under the
    declared zero-fade reproduction (design §7 check 2) identical capacities are the correct
    answer, and a check that refused them would refuse the one run that proves the composition
    did not change the existing arithmetic.
    """

    if len(strategy_summaries) < 2:
        return
    if config.degradation.cycle_fade_fraction_per_equivalent_cycle <= 0.0:
        return
    throughput = strategy_summaries["cell_discharge_mwh"].round(6)
    capacity = strategy_summaries["final_usable_energy_mwh"].round(9)
    if throughput.nunique() > 1 and capacity.nunique() == 1:
        raise IntegratedStudyInputError(
            "Strategies with different cell throughput reached identical end-of-window "
            "usable energy. Each strategy must own its degradation state; a shared state is "
            "the one defect here that still produces plausible figures"
        )


def _optional_mean(column: pd.Series) -> float | None:
    values = pd.to_numeric(column, errors="coerce").dropna()
    return float(values.mean()) if not values.empty else None
