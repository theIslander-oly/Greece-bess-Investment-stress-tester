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
    def from_dict(cls, payload: dict[str, Any]) -> "FinanceConfig":
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
    daily["market_margin_input_eur"] = daily["net_market_margin_eur"]
    daily["realized_market_margin_eur"] = (
        daily["market_margin_input_eur"]
        * config.market_margin_realization_fraction
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
    npv = float(
        -config.total_initial_capex_eur
        + daily["discounted_operating_net_cash_flow_eur"].sum()
    )
    irr, irr_status = _project_irr(annual)
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

    pv_input_market_margin = float(
        (daily["market_margin_input_eur"] / daily["discount_factor"]).sum()
    )
    pv_non_margin = float(
        -config.total_initial_capex_eur
        + (
            (
                -daily["fixed_opex_eur"]
                - daily["variable_opex_eur"]
                - daily["augmentation_cost_eur"]
                - daily["decommissioning_cost_eur"]
                + daily["residual_value_eur"]
            )
            / daily["discount_factor"]
        ).sum()
    )
    break_even_realization = (
        -pv_non_margin / pv_input_market_margin
        if pv_input_market_margin > TOLERANCE
        else None
    )
    maximum_initial_capex = float(
        daily["discounted_operating_net_cash_flow_eur"].sum()
    )
    annual_margin_discount_factor = float(
        sum(
            1.0 / (1.0 + config.discount_rate_fraction) ** years
            for years in annual.loc[
                annual["project_year"] > 0, "years_from_project_start"
            ]
        )
    )
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
        "positive_npv_at_configured_discount_rate": bool(npv > 0.0),
        "cash_flow_timing_policy": (
            "Initial CAPEX at project start (time zero); operating cash flows at each "
            "market-day end; augmentation on its recorded market day; residual value "
            "and decommissioning cost at project end"
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
    required = {"market_day", "net_market_margin_eur", "grid_discharge_mwh"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise FinanceInputError(
            "Daily operating results are missing required columns: "
            + ", ".join(missing)
        )
    columns = ["market_day", "net_market_margin_eur", "grid_discharge_mwh"]
    if "augmentation_cost_eur" in frame.columns:
        columns.append("augmentation_cost_eur")
    daily = frame.loc[:, columns].copy()
    if "augmentation_cost_eur" not in daily:
        daily["augmentation_cost_eur"] = 0.0
    daily["market_day"] = daily["market_day"].map(
        lambda value: _as_date(value, "market_day")
    )
    if daily["market_day"].duplicated().any():
        raise FinanceInputError("Daily operating results contain duplicate market days")
    if not daily["market_day"].is_monotonic_increasing:
        raise FinanceInputError("Daily operating results must be sorted by market_day")
    for column in (
        "net_market_margin_eur",
        "grid_discharge_mwh",
        "augmentation_cost_eur",
    ):
        daily[column] = pd.to_numeric(daily[column], errors="coerce")
        if daily[column].isna().any() or not np.isfinite(daily[column]).all():
            raise FinanceInputError(f"{column} must contain only finite numbers")
    if (daily["grid_discharge_mwh"] < -TOLERANCE).any():
        raise FinanceInputError("grid_discharge_mwh cannot be negative")
    if (daily["augmentation_cost_eur"] < -TOLERANCE).any():
        raise FinanceInputError("augmentation_cost_eur cannot be negative")

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


def _project_irr(annual: pd.DataFrame) -> tuple[float | None, str]:
    cash_flows = annual["net_cash_flow_eur"].to_numpy(dtype=float)
    times = annual["years_from_project_start"].to_numpy(dtype=float)
    signs = np.sign(cash_flows[np.abs(cash_flows) > TOLERANCE])
    sign_changes = int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0
    if sign_changes == 0:
        return None, "not_evaluable_no_sign_change"
    if sign_changes > 1:
        return None, "not_evaluable_multiple_sign_changes"

    def objective(rate: float) -> float:
        return float(np.sum(cash_flows / (1.0 + rate) ** times))

    low = -0.9999
    low_value = objective(low)
    for high in (1.0, 10.0, 100.0, 1_000.0, 1_000_000.0):
        high_value = objective(high)
        if np.sign(low_value) != np.sign(high_value):
            return float(brentq(objective, low, high, xtol=1e-12)), "calculated"
    return None, "not_evaluable_no_root_in_search_range"


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
