"""Transparent unlevered project-finance calculations for Greek DAM BESS studies.

The module consumes an explicit, continuous daily operating path. It never extrapolates,
repeats or fills missing market days. Taxes, subsidies and debt are intentionally absent.
"""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq

FINANCE_RESULT_LABEL = (
    "Unlevered pre-tax, pre-subsidy Greek DAM project-finance research calculation "
    "based on the supplied operating path; not a bankable forecast or financial advice."
)
OPERATING_MARGIN_CASES = (
    "perfect_foresight_upper_bound",
    # A day-by-day dispatch under an evolving degradation state. Optimal per day, but the total
    # is one policy's outcome rather than a ceiling, so it must not inherit the upper-bound
    # wording of the case above.
    "daily_policy_degraded_simulation",
    "historical_forecast_backtest",
    "user_supplied_scenario",
)
YEAR_DAYS = 365.25
TOLERANCE = 1e-9


class FinanceInputError(ValueError):
    """Raised when finance assumptions or operating results are invalid."""


@dataclass(frozen=True)
class FinanceConfig:
    """Explicit unlevered project-finance assumptions, all in nominal EUR."""

    project_start_day: date
    project_end_day: date
    operating_margin_case: str
    discount_rate_fraction: float
    battery_system_capex_eur: float
    power_conversion_system_capex_eur: float = 0.0
    grid_connection_capex_eur: float = 0.0
    development_and_construction_capex_eur: float = 0.0
    other_initial_capex_eur: float = 0.0
    market_margin_realization_fraction: float = 1.0
    fixed_opex_eur_per_year: float = 0.0
    insurance_eur_per_year: float = 0.0
    asset_management_eur_per_year: float = 0.0
    variable_opex_eur_per_mwh_discharged: float = 0.0
    opex_escalation_fraction_per_year: float = 0.0
    decommissioning_cost_eur: float = 0.0
    residual_value_eur: float = 0.0

    def __post_init__(self) -> None:
        start = _as_date(self.project_start_day, "project_start_day")
        end = _as_date(self.project_end_day, "project_end_day")
        object.__setattr__(self, "project_start_day", start)
        object.__setattr__(self, "project_end_day", end)
        if end < start:
            raise FinanceInputError("project_end_day cannot precede project_start_day")
        if self.operating_margin_case not in OPERATING_MARGIN_CASES:
            raise FinanceInputError(
                "operating_margin_case must be one of: "
                + ", ".join(OPERATING_MARGIN_CASES)
            )
        _require_rate("discount_rate_fraction", self.discount_rate_fraction)
        _require_rate(
            "opex_escalation_fraction_per_year",
            self.opex_escalation_fraction_per_year,
        )
        _require_fraction(
            "market_margin_realization_fraction",
            self.market_margin_realization_fraction,
        )
        for name in (
            "battery_system_capex_eur",
            "power_conversion_system_capex_eur",
            "grid_connection_capex_eur",
            "development_and_construction_capex_eur",
            "other_initial_capex_eur",
            "fixed_opex_eur_per_year",
            "insurance_eur_per_year",
            "asset_management_eur_per_year",
            "variable_opex_eur_per_mwh_discharged",
            "decommissioning_cost_eur",
            "residual_value_eur",
        ):
            _require_nonnegative(name, getattr(self, name))
        if self.total_initial_capex_eur <= TOLERANCE:
            raise FinanceInputError("Total initial CAPEX must be greater than zero")

    @property
    def total_initial_capex_eur(self) -> float:
        return float(
            self.battery_system_capex_eur
            + self.power_conversion_system_capex_eur
            + self.grid_connection_capex_eur
            + self.development_and_construction_capex_eur
            + self.other_initial_capex_eur
        )

    @property
    def total_fixed_opex_eur_per_year(self) -> float:
        return float(
            self.fixed_opex_eur_per_year
            + self.insurance_eur_per_year
            + self.asset_management_eur_per_year
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FinanceConfig:
        if not isinstance(payload, dict):
            raise FinanceInputError("Finance config JSON must contain one object")
        try:
            return cls(**payload)
        except TypeError as exc:
            raise FinanceInputError(f"Invalid finance configuration: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["project_start_day"] = self.project_start_day.isoformat()
        payload["project_end_day"] = self.project_end_day.isoformat()
        payload["total_initial_capex_eur"] = self.total_initial_capex_eur
        payload["total_fixed_opex_eur_per_year"] = (
            self.total_fixed_opex_eur_per_year
        )
        return payload


@dataclass(frozen=True)
class ProjectFinanceResult:
    daily_cash_flows: pd.DataFrame
    annual_cash_flows: pd.DataFrame
    summary: dict[str, Any]


def evaluate_project_finance(
    daily_operating_results: pd.DataFrame,
    config: FinanceConfig,
) -> ProjectFinanceResult:
    """Calculate unlevered project cash flows over an explicit daily operating path."""

    daily = _validate_daily_operating_results(daily_operating_results, config)
    daily["project_year"] = daily["market_day"].map(
        lambda value: _project_year(value, config.project_start_day)
    )
    daily["market_margin_input_eur"] = daily["market_cash_margin_eur"]
    positive_margin = daily["market_margin_input_eur"].clip(lower=0)
    negative_margin = daily["market_margin_input_eur"].clip(upper=0)
    daily["realized_market_margin_eur"] = (
        positive_margin * config.market_margin_realization_fraction + negative_margin
    )

    escalation = daily["project_year"].map(
        lambda year: (1.0 + config.opex_escalation_fraction_per_year)
        ** (int(year) - 1)
    )
    days_in_project_year = daily["project_year"].map(
        lambda year: _days_in_full_project_year(
            config.project_start_day, int(year)
        )
    )
    daily["fixed_opex_eur"] = (
        config.total_fixed_opex_eur_per_year
        * escalation
        / days_in_project_year
    )
    daily["variable_opex_eur"] = (
        daily["grid_discharge_mwh"]
        * config.variable_opex_eur_per_mwh_discharged
        * escalation
    )
    daily["decommissioning_cost_eur"] = 0.0
    daily["residual_value_eur"] = 0.0
    final_index = daily.index[-1]
    daily.loc[final_index, "decommissioning_cost_eur"] = (
        config.decommissioning_cost_eur
    )
    daily.loc[final_index, "residual_value_eur"] = config.residual_value_eur
    daily["operating_net_cash_flow_eur"] = (
        daily["realized_market_margin_eur"]
        - daily["fixed_opex_eur"]
        - daily["variable_opex_eur"]
        - daily["augmentation_cost_eur"]
        - daily["commissioning_energy_cost_eur"]
        - daily["decommissioning_cost_eur"]
        + daily["residual_value_eur"]
    )
    daily["years_from_project_start"] = daily["market_day"].map(
        lambda value: ((value - config.project_start_day).days + 1) / YEAR_DAYS
    )
    daily["discount_factor"] = (
        1.0 + config.discount_rate_fraction
    ) ** daily["years_from_project_start"]
    daily["discounted_operating_net_cash_flow_eur"] = (
        daily["operating_net_cash_flow_eur"] / daily["discount_factor"]
    )

    annual = _annual_cash_flows(daily, config)
    # NPV and IRR read one dated series, so they cannot describe different cash-flow timings.
    # The initial capex sits at the project start, t = 0, and every operating cash flow sits on
    # the day it occurs under the end-of-day convention documented on `_dated_cash_flows`.
    times, amounts = _dated_cash_flows(daily, config)
    npv = float(
        -config.total_initial_capex_eur
        + daily["discounted_operating_net_cash_flow_eur"].sum()
    )
    irr, irr_status = _project_irr(times, amounts)
    payback_day, payback_years = _payback(
        daily,
        config.total_initial_capex_eur,
        "operating_net_cash_flow_eur",
    )
    discounted_payback_day, discounted_payback_years = _payback(
        daily,
        config.total_initial_capex_eur,
        "discounted_operating_net_cash_flow_eur",
    )

    pv_positive_margin = float((positive_margin / daily["discount_factor"]).sum())
    pv_negative_margin = float((negative_margin / daily["discount_factor"]).sum())
    pv_non_margin = float(
        -config.total_initial_capex_eur
        + (
            (
                -daily["fixed_opex_eur"]
                - daily["variable_opex_eur"]
                - daily["augmentation_cost_eur"]
                - daily["commissioning_energy_cost_eur"]
                - daily["decommissioning_cost_eur"]
                + daily["residual_value_eur"]
            )
            / daily["discount_factor"]
        ).sum()
    )
    break_even_realization = (
        -(pv_non_margin + pv_negative_margin) / pv_positive_margin
        if pv_positive_margin > TOLERANCE
        else None
    )
    maximum_initial_capex = float(
        daily["discounted_operating_net_cash_flow_eur"].sum()
    )
    # One EUR/year of cash margin, earned uniformly at each modeled day end. This
    # uses the same 365.25-day basis and exact dates as NPV, including partial years.
    annual_margin_discount_factor = float((1.0 / daily["discount_factor"]).sum() / YEAR_DAYS)
    break_even_average_annual_margin = (
        -pv_non_margin / annual_margin_discount_factor
        if annual_margin_discount_factor > TOLERANCE
        else None
    )

    annualized_horizon_years = (
        len(daily) / YEAR_DAYS
        if len(daily) > 0
        else 0.0
    )
    summary = {
        "result_label": FINANCE_RESULT_LABEL,
        "operating_margin_case": config.operating_margin_case,
        "operating_margin_interpretation": _margin_interpretation(
            config.operating_margin_case
        ),
        "project_start_day": config.project_start_day.isoformat(),
        "project_end_day": config.project_end_day.isoformat(),
        "modeled_day_count": int(len(daily)),
        "project_year_count": int(daily["project_year"].nunique()),
        "modeled_horizon_years": annualized_horizon_years,
        "initial_capex_eur": config.total_initial_capex_eur,
        "market_margin_input_eur": float(daily["market_margin_input_eur"].sum()),
        "market_margin_realization_fraction": (
            config.market_margin_realization_fraction
        ),
        "realized_market_margin_eur": float(
            daily["realized_market_margin_eur"].sum()
        ),
        "fixed_opex_eur": float(daily["fixed_opex_eur"].sum()),
        "variable_opex_eur": float(daily["variable_opex_eur"].sum()),
        "augmentation_cost_eur": float(daily["augmentation_cost_eur"].sum()),
        "commissioning_energy_cost_eur": float(daily["commissioning_energy_cost_eur"].sum()),
        "dispatch_wear_penalty_eur": float(daily["monetary_degradation_adder_eur"].sum()),
        "accounting_convention": "cash_margin_v2",
        "market_margin_realization_policy": (
            "The realization fraction applies only to positive daily cash margins; "
            "negative cash margins remain payable in full"
        ),
        "wear_penalty_policy": (
            "Dispatch wear penalties are non-cash opportunity costs and are added back "
            "before finance. Actual throughput expenses belong in fees or variable OPEX"
        ),
        "decommissioning_cost_eur": config.decommissioning_cost_eur,
        "residual_value_eur": config.residual_value_eur,
        "undiscounted_project_cash_flow_eur": float(
            -config.total_initial_capex_eur
            + daily["operating_net_cash_flow_eur"].sum()
        ),
        "npv_eur": npv,
        "discount_rate_fraction": config.discount_rate_fraction,
        "irr_fraction": irr,
        "irr_status": irr_status,
        "simple_payback_day": payback_day.isoformat() if payback_day else None,
        "simple_payback_years": payback_years,
        "discounted_payback_day": (
            discounted_payback_day.isoformat() if discounted_payback_day else None
        ),
        "discounted_payback_years": discounted_payback_years,
        "maximum_initial_capex_for_zero_npv_eur": maximum_initial_capex,
        "break_even_market_margin_realization_fraction": break_even_realization,
        "break_even_realization_within_zero_to_one": bool(
            break_even_realization is not None
            and 0.0 <= break_even_realization <= 1.0
        ),
        "break_even_average_annual_market_margin_eur": (
            break_even_average_annual_margin
        ),
        "break_even_annual_margin_policy": (
            "Required realized cash margin, earned uniformly at annual_margin / 365.25 "
            "per modeled day, before fixed costs and without a further realization haircut; "
            "uses the same dates as NPV"
        ),
        "positive_npv_at_configured_discount_rate": bool(npv > 0.0),
        "cash_flow_timing_policy": (
            "Initial CAPEX at project start (time zero); operating cash flows at each "
            "market-day end; augmentation on its recorded market day; residual value "
            "and decommissioning cost at project end. NPV and IRR are both computed from "
            "this one dated series; the annual table is a summary and no monetary metric "
            "is derived from it"
        ),
        "missing_day_policy": (
            "The operating path must contain every calendar day from project start "
            "through project end; missing days are rejected and never treated as zero"
        ),
        "augmentation_cost_policy": (
            "Nominal augmentation costs are taken from the supplied daily operating "
            "results and are not escalated again"
        ),
        "exclusions": [
            "tax",
            "subsidies and state aid",
            "debt and financing fees",
            "working capital",
            "intraday, balancing and reserve revenues",
            "grid feasibility and bid acceptance",
        ],
        "finance_config": config.to_dict(),
    }
    return ProjectFinanceResult(
        daily_cash_flows=daily,
        annual_cash_flows=annual,
        summary=summary,
    )


def _validate_daily_operating_results(
    frame: pd.DataFrame,
    config: FinanceConfig,
) -> pd.DataFrame:
    required = {"market_day", "grid_discharge_mwh"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise FinanceInputError(
            "Daily operating results are missing required columns: "
            + ", ".join(missing)
        )
    if not {"net_market_margin_eur", "market_cash_margin_eur"} & set(frame.columns):
        raise FinanceInputError(
            "Daily results require market_cash_margin_eur or net_market_margin_eur"
        )
    optional = (
        "net_market_margin_eur", "market_cash_margin_eur", "monetary_degradation_adder_eur",
        "augmentation_cost_eur", "commissioning_energy_cost_eur",
    )
    columns = ["market_day", "grid_discharge_mwh", *[c for c in optional if c in frame]]
    daily = frame.loc[:, columns].copy()
    for column in ("augmentation_cost_eur", "commissioning_energy_cost_eur",
                   "monetary_degradation_adder_eur"):
        if column not in daily:
            daily[column] = 0.0
    daily["market_day"] = daily["market_day"].map(
        lambda value: _as_date(value, "market_day")
    )
    if daily["market_day"].duplicated().any():
        raise FinanceInputError("Daily operating results contain duplicate market days")
    if not daily["market_day"].is_monotonic_increasing:
        raise FinanceInputError("Daily operating results must be sorted by market_day")
    for column in daily.columns.drop("market_day"):
        daily[column] = pd.to_numeric(daily[column], errors="coerce")
        if daily[column].isna().any() or not np.isfinite(daily[column]).all():
            raise FinanceInputError(f"{column} must contain only finite numbers")
    if (daily["grid_discharge_mwh"] < -TOLERANCE).any():
        raise FinanceInputError("grid_discharge_mwh cannot be negative")
    for column in ("augmentation_cost_eur", "commissioning_energy_cost_eur",
                   "monetary_degradation_adder_eur"):
        if (daily[column] < -TOLERANCE).any():
            raise FinanceInputError(f"{column} cannot be negative")
    if "market_cash_margin_eur" not in daily:
        # Legacy net-only inputs declare cash margin. Legacy degradation CSVs also
        # carry the wear adder, which must be reversed before deducting actual CAPEX.
        daily["market_cash_margin_eur"] = (
            daily["net_market_margin_eur"] + daily["monetary_degradation_adder_eur"]
        )
    elif "net_market_margin_eur" in daily and not np.allclose(
        daily["market_cash_margin_eur"],
        daily["net_market_margin_eur"] + daily["monetary_degradation_adder_eur"],
        rtol=1e-10, atol=1e-7,
    ):
        raise FinanceInputError("Cash margin and net margin plus wear penalty do not reconcile")

    expected = [
        timestamp.date()
        for timestamp in pd.date_range(
            config.project_start_day, config.project_end_day, freq="D"
        )
    ]
    observed = daily["market_day"].tolist()
    if observed != expected:
        first = observed[0].isoformat() if observed else None
        last = observed[-1].isoformat() if observed else None
        raise FinanceInputError(
            "Daily operating results must exactly cover every calendar day from "
            f"{config.project_start_day} through {config.project_end_day}; observed "
            f"{first} through {last} with {len(observed)} rows, expected {len(expected)}"
        )
    return daily.reset_index(drop=True)


def _annual_cash_flows(
    daily: pd.DataFrame, config: FinanceConfig
) -> pd.DataFrame:
    value_columns = [
        "market_margin_input_eur",
        "realized_market_margin_eur",
        "fixed_opex_eur",
        "variable_opex_eur",
        "augmentation_cost_eur",
        "commissioning_energy_cost_eur",
        "decommissioning_cost_eur",
        "residual_value_eur",
        "operating_net_cash_flow_eur",
        "discounted_operating_net_cash_flow_eur",
    ]
    records: list[dict[str, Any]] = [
        {
            "project_year": 0,
            "period_start_day": config.project_start_day,
            "period_end_day": config.project_start_day,
            "day_count": 0,
            **{column: 0.0 for column in value_columns},
            "initial_capex_eur": config.total_initial_capex_eur,
            "net_cash_flow_eur": -config.total_initial_capex_eur,
            "discounted_net_cash_flow_eur": -config.total_initial_capex_eur,
            "years_from_project_start": 0.0,
        }
    ]
    for project_year, group in daily.groupby("project_year", sort=True):
        period_end = group["market_day"].iloc[-1]
        records.append(
            {
                "project_year": int(project_year),
                "period_start_day": group["market_day"].iloc[0],
                "period_end_day": period_end,
                "day_count": int(len(group)),
                **{column: float(group[column].sum()) for column in value_columns},
                "initial_capex_eur": 0.0,
                "net_cash_flow_eur": float(
                    group["operating_net_cash_flow_eur"].sum()
                ),
                "discounted_net_cash_flow_eur": float(
                    group["discounted_operating_net_cash_flow_eur"].sum()
                ),
                "years_from_project_start": (
                    (period_end - config.project_start_day).days + 1
                )
                / YEAR_DAYS,
            }
        )
    annual = pd.DataFrame.from_records(records)
    annual["cumulative_net_cash_flow_eur"] = annual["net_cash_flow_eur"].cumsum()
    annual["cumulative_discounted_net_cash_flow_eur"] = annual[
        "discounted_net_cash_flow_eur"
    ].cumsum()
    return annual


def _dated_cash_flows(
    daily: pd.DataFrame, config: FinanceConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Return the project's cash flows as (times in years, amounts in EUR), one entry per date.

    **End-of-day convention.** A day's operating cash flow is dated at the end of that day, so
    the first delivery day sits at 1 / 365.25 years from the project start rather than at zero.
    ``daily["years_from_project_start"]`` already carries exactly that, and it is reused here
    rather than recomputed: NPV discounts by it, so an IRR that solved against a second,
    separately derived set of instants could disagree with the NPV it is supposed to zero.

    The initial capex is dated at the project start itself, t = 0, where its discount factor is
    one. That is the only cash flow not attached to a delivery day.
    """

    times = np.concatenate(
        ([0.0], daily["years_from_project_start"].to_numpy(dtype=float))
    )
    amounts = np.concatenate(
        (
            [-float(config.total_initial_capex_eur)],
            daily["operating_net_cash_flow_eur"].to_numpy(dtype=float),
        )
    )
    return times, amounts


# Rates are searched in this finite numerical range; uniqueness is assessed on
# the whole mathematical domain r > -1, not just at sampled grid points.
IRR_SEARCH_LOW = -0.9999
IRR_SEARCH_HIGH = 1_000_000.0
IRR_SCAN_POINTS = 4096


def _irr_objective(rate: float, times: np.ndarray, amounts: np.ndarray) -> float:
    return float(np.sum(amounts / (1.0 + rate) ** times))


def _positive_rate_root_count(amounts: np.ndarray) -> int | None:
    """Certify zero or one root on r > 0 using cumulative cash balances.

    Summation by parts expresses discounted cash flow as the Laplace transform
    of the cumulative balance. A balance of one sign has no positive-rate zero.
    One crossing with a nonzero final balance of the opposite sign gives exactly
    one positive-rate zero (Norstrom). More crossings are inconclusive.
    This criterion makes no claim about negative rates.
    """
    balances = np.cumsum(amounts)
    material = balances[np.abs(balances) > TOLERANCE]
    if not len(material):
        return None
    changes = np.count_nonzero(np.sign(material[1:]) != np.sign(material[:-1]))
    if changes == 0:
        return 0
    if changes == 1 and abs(balances[-1]) > TOLERANCE:
        return 1
    return None


def _project_irr(times: np.ndarray, amounts: np.ndarray) -> tuple[float | None, str]:
    """Return a rate only with a uniqueness certificate, never from a scan alone.

    Reverse the dated cash flows to apply the positive-rate criterion to negative
    rates: multiplying NPV by a positive exponential preserves its zeros. Work in
    log(1+r), reversing time for negative values, to avoid overflow near -100%.
    Unresolved multiple-sign cash flows retain NPV but have no reported IRR.
    """
    mask = np.abs(amounts) > TOLERANCE
    times, amounts = times[mask], amounts[mask]
    if len(amounts) < 2 or np.all(amounts > 0) or np.all(amounts < 0):
        return None, "not_evaluable_no_sign_change"
    times = times - times[0]
    # Scaling changes neither roots nor the root-count certificates.
    amounts = amounts / np.max(np.abs(amounts))
    reversed_times = times[-1] - times[::-1]

    def objective(log_rate: float) -> float:
        if log_rate >= 0:
            return float(np.sum(amounts * np.exp(-times * log_rate)))
        return float(np.sum(amounts[::-1] * np.exp(reversed_times * log_rate)))

    sign_changes = np.count_nonzero(np.sign(amounts[1:]) != np.sign(amounts[:-1]))
    positive_count = _positive_rate_root_count(amounts)
    negative_count = _positive_rate_root_count(amounts[::-1])
    zero_root = abs(float(np.sum(amounts))) <= TOLERANCE
    if sign_changes == 1:
        certified_count: int | None = 1
    elif positive_count is not None and negative_count is not None:
        certified_count = positive_count + negative_count + int(zero_root)
    else:
        certified_count = None
    if certified_count is not None and certified_count > 1:
        return None, "not_evaluable_multiple_rates"
    if certified_count == 0:
        return None, "not_evaluable_no_root_in_search_range"

    low, high = float(np.log1p(IRR_SEARCH_LOW)), float(np.log1p(IRR_SEARCH_HIGH))
    if certified_count == 1:
        if zero_root:
            return 0.0, "calculated"
        if np.sign(objective(low)) == np.sign(objective(high)):
            return None, "not_evaluable_no_root_in_search_range"
        root = brentq(objective, low, high, xtol=1e-13)
        return float(np.expm1(root)), "calculated"

    # A scan can exhibit multiple roots, but cannot rule out close or tangent roots.
    # Expand the diagnostic scan until the first/last nonzero cash flow dominates
    # all remaining terms. This can reveal roots too close to -100% to express as
    # floating-point rates, which still defeat a claim of global uniqueness.
    positive_limit = max(1.0, np.log(np.sum(np.abs(amounts[1:])) / abs(amounts[0]))
                         / times[1] + 1.0)
    negative_limit = max(1.0, np.log(np.sum(np.abs(amounts[:-1])) / abs(amounts[-1]))
                         / reversed_times[1] + 1.0)
    grid = np.unique(np.concatenate((
        np.linspace(-negative_limit, 0.0, IRR_SCAN_POINTS // 2),
        np.linspace(0.0, positive_limit, IRR_SCAN_POINTS // 2),
    )))
    values = np.array([objective(value) for value in grid])
    crossings = int(np.count_nonzero(values[1:] * values[:-1] < 0))
    found = crossings + int(zero_root)
    if found > 1:
        return None, "not_evaluable_multiple_rates"
    return None, "not_evaluable_uniqueness_not_established"


def _payback(
    daily: pd.DataFrame,
    initial_capex_eur: float,
    cash_flow_column: str,
) -> tuple[date | None, float | None]:
    cumulative = -initial_capex_eur
    for record in daily[["market_day", cash_flow_column]].itertuples(index=False):
        cash_flow = float(getattr(record, cash_flow_column))
        previous = cumulative
        cumulative += cash_flow
        if cumulative >= -TOLERANCE:
            fraction = (
                min(1.0, max(0.0, -previous / cash_flow))
                if cash_flow > TOLERANCE
                else 1.0
            )
            elapsed_days = (record.market_day - daily["market_day"].iloc[0]).days
            return record.market_day, (elapsed_days + fraction) / YEAR_DAYS
    return None, None


def _project_year(day: date, start: date) -> int:
    candidate_year = day.year - start.year
    anniversary = _anniversary(start, start.year + candidate_year)
    completed = candidate_year if day >= anniversary else candidate_year - 1
    return completed + 1


def _days_in_full_project_year(start: date, project_year: int) -> int:
    period_start = _anniversary(start, start.year + project_year - 1)
    period_end_exclusive = _anniversary(start, start.year + project_year)
    return (period_end_exclusive - period_start).days


def _anniversary(start: date, year: int) -> date:
    day = min(start.day, calendar.monthrange(year, start.month)[1])
    return date(year, start.month, day)


def _margin_interpretation(case: str) -> str:
    if case == "perfect_foresight_upper_bound":
        return (
            "The supplied operating margins use future prices and remain a gross-margin "
            "upper bound; they are not expected or achievable investment revenue."
        )
    if case == "daily_policy_degraded_simulation":
        return (
            "The supplied operating margins are a day-by-day perfect-foresight simulation "
            "under an evolving degradation state. Each day is optimal under the limits it "
            "began with, but those limits depend on what earlier days discharged, so the total "
            "is what that daily policy achieved and not a lifetime optimum or an upper bound "
            "on achievable margin. They are not expected investment revenue."
        )
    if case == "historical_forecast_backtest":
        return (
            "The supplied operating margins are historical forecast-dispatch backtest "
            "results; they are research evidence, not a future revenue forecast."
        )
    return (
        "The supplied operating margins are a user-defined scenario and inherit all "
        "assumptions and limitations of that scenario."
    )


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise FinanceInputError(f"{name} must be an ISO date") from exc
    raise FinanceInputError(f"{name} must be a date or ISO date string")


def _require_nonnegative(name: str, value: float) -> None:
    if not np.isfinite(value) or value < 0:
        raise FinanceInputError(f"{name} must be finite and nonnegative")


def _require_fraction(name: str, value: float) -> None:
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise FinanceInputError(f"{name} must be finite and between 0 and 1")


def _require_rate(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= -1.0:
        raise FinanceInputError(f"{name} must be finite and greater than -1")
