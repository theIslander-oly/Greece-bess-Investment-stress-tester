"""Per-delivery-year decomposition of an accepted Greek DAM replay.

Aggregate 2020-2026 figures conceal regime dependence: the 2022 gas crisis, the
2020 COVID trough and the 2025-2026 negative-price surge are averaged into one
number. This module splits an already-accepted replay into delivery years so the
regimes are visible, without adding a model, a market or a transformation.

Nothing here is a forecast, a probability, a percentile, a loss metric or a
ranking of future years. Annual perfect-foresight figures remain labelled
gross-margin upper bounds; annual forecast figures remain backtest outcomes on a
selected historical period.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..data.schema import ensure_canonical
from ..data.timezones import MARKET_TZ

ANNUAL_DECOMPOSITION_LABEL = (
    "Per-delivery-year decomposition of a historical Greek DAM replay. Annual "
    "perfect-foresight figures are labelled gross-margin upper bounds and annual "
    "forecast figures are historical backtest outcomes; neither is expected revenue, "
    "a forecast for any year, or an investment conclusion."
)

DELIVERY_YEAR_POLICY = (
    "A delivery year is the calendar year of the interval's CET/CEST market-day start, "
    "which is the sense in which the Greek DAM has delivery years, and the same "
    "convention the committed custody records use. Grouping by UTC year instead moves "
    "the interval beginning 31 December 23:00Z into the earlier year, which is why a "
    "UTC-grouped 2020 count can exceed a market-clock 2020 count by one interval."
)

NORMALIZATION_POLICY = (
    "Per-market-day figures are within-period averages over the market days actually "
    "present. No annual figure is annualized, extrapolated, scaled to a full year or "
    "compared across years of unequal coverage without its day count."
)

LIKE_FOR_LIKE_POLICY = (
    "Each method's own-days annual ceiling covers only the days that method backtested, "
    "so ceilings differ between methods. The common-day table restricts every method to "
    "the days all methods backtested, where the ceiling must be identical."
)

SCHEDULE_REQUIRED_COLUMNS = (
    "delivery_start_utc",
    "price_eur_per_mwh",
    "charge_grid_mwh",
    "discharge_grid_mwh",
    "charging_energy_cost_eur",
    "discharge_energy_revenue_eur",
    "buy_fee_eur",
    "sell_fee_eur",
    "degradation_cost_eur",
    "net_market_margin_eur",
)

DAILY_REQUIRED_COLUMNS = (
    "market_day",
    "interval_count",
    "forecast_mae_eur_per_mwh",
    "forecast_rmse_eur_per_mwh",
    "forecast_margin_eur",
    "realized_margin_eur",
    "perfect_foresight_margin_eur",
    "regret_eur",
    "grid_charge_mwh",
    "grid_discharge_mwh",
)

_PRICE_MATCH_TOLERANCE = 1e-9


class AnnualDecompositionError(ValueError):
    """Raised when a replay cannot be decomposed into comparable delivery years."""


@dataclass(frozen=True)
class AnnualReplayDecomposition:
    """Per-year market context, ceiling, forecast capture and like-for-like tables."""

    annual_overview: pd.DataFrame
    annual_forecast: pd.DataFrame
    annual_common_day: pd.DataFrame
    summary: dict[str, Any]


def decompose_annual_replay(
    prices: pd.DataFrame,
    *,
    perfect_foresight_schedule: pd.DataFrame | None = None,
    daily_results_by_method: Mapping[str, pd.DataFrame] | None = None,
    energy_capacity_mwh: float | None = None,
) -> AnnualReplayDecomposition:
    """Split an accepted replay into delivery years on the CET/CEST market clock.

    `prices` is the accepted canonical history the replay was run over. It defines
    the delivery years, the market days available in each, and the coverage against
    which every partial year is labelled.

    `perfect_foresight_schedule` is an interval schedule from
    `optimize_perfect_foresight`, in either the full-horizon or the daily-composed
    mode. Its prices must equal the accepted history interval by interval, which is
    what proves the schedule was solved on this history rather than another one.

    `daily_results_by_method` maps a forecast method name to the `daily_results`
    table of `backtest_forecast_dispatch` for that method.

    `energy_capacity_mwh` is required only for equivalent-full-cycle columns, which
    are omitted when it is not supplied.
    """

    accepted = ensure_canonical(prices, allow_empty=False)
    if energy_capacity_mwh is not None and energy_capacity_mwh <= 0:
        raise AnnualDecompositionError("energy_capacity_mwh must be positive when supplied")

    duplicated = accepted["delivery_start_utc"].duplicated()
    if duplicated.any():
        first = accepted.loc[duplicated, "delivery_start_utc"].iloc[0]
        raise AnnualDecompositionError(
            f"The accepted history repeats {int(duplicated.sum())} canonical delivery "
            f"intervals, beginning {first}; a decomposition of a duplicated history would "
            "double-count its own totals"
        )

    accepted = accepted.copy()
    accepted["delivery_year"] = accepted["delivery_start_market"].dt.year
    accepted["market_day"] = accepted["delivery_start_market"].dt.date

    overview = _annual_market_context(accepted)
    delivery_years = [int(year) for year in overview["delivery_year"]]
    market_days_by_year = dict(
        zip(delivery_years, (int(count) for count in overview["market_day_count"]), strict=True)
    )

    ceiling_summary: dict[str, Any] = {}
    if perfect_foresight_schedule is not None:
        ceiling = _annual_perfect_foresight(
            perfect_foresight_schedule, accepted, energy_capacity_mwh
        )
        overview = overview.merge(ceiling, on="delivery_year", how="left")
        ceiling_summary = _ceiling_reconciliation(perfect_foresight_schedule, ceiling)

    methods = sorted(daily_results_by_method or {})
    validated_daily = {
        method: _validate_daily_results(
            method, (daily_results_by_method or {})[method], accepted
        )
        for method in methods
    }

    annual_forecast = _annual_forecast(validated_daily, delivery_years, market_days_by_year)
    annual_common_day, common_days = _annual_common_day(validated_daily, delivery_years)

    summary: dict[str, Any] = {
        "result_label": ANNUAL_DECOMPOSITION_LABEL,
        "delivery_year_policy": DELIVERY_YEAR_POLICY,
        "normalization_policy": NORMALIZATION_POLICY,
        "like_for_like_policy": LIKE_FOR_LIKE_POLICY,
        "delivery_years": delivery_years,
        "partial_delivery_years": [
            int(year)
            for year, partial in zip(
                overview["delivery_year"], overview["is_partial_year"], strict=True
            )
            if bool(partial)
        ],
        "first_market_day": str(accepted["market_day"].min()),
        "last_market_day": str(accepted["market_day"].max()),
        "market_day_count": int(accepted["market_day"].nunique()),
        "interval_count": int(len(accepted)),
        "missing_price_interval_count": int(accepted["price_eur_per_mwh"].isna().sum()),
        "forecast_methods": methods,
        **ceiling_summary,
        **_common_day_summary(annual_common_day, common_days, methods),
    }
    return AnnualReplayDecomposition(
        annual_overview=overview,
        annual_forecast=annual_forecast,
        annual_common_day=annual_common_day,
        summary=summary,
    )


def _annual_market_context(accepted: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in accepted.groupby("delivery_year", sort=True):
        price = group["price_eur_per_mwh"]
        by_day = group.groupby("market_day")["price_eur_per_mwh"]
        daily_range = by_day.max() - by_day.min()
        calendar_day_count = 366 if calendar.isleap(int(year)) else 365
        market_day_count = int(group["market_day"].nunique())
        rows.append(
            {
                "delivery_year": int(year),
                "first_market_day": str(group["market_day"].min()),
                "last_market_day": str(group["market_day"].max()),
                "market_day_count": market_day_count,
                "calendar_day_count": calendar_day_count,
                "market_day_coverage_fraction": market_day_count / calendar_day_count,
                "is_partial_year": market_day_count < calendar_day_count,
                "interval_count": int(len(group)),
                "hourly_interval_count": int((group["duration_hours"] == 1.0).sum()),
                "quarter_hour_interval_count": int((group["duration_hours"] == 0.25).sum()),
                "delivered_hours": float(group["duration_hours"].sum()),
                "missing_price_interval_count": int(price.isna().sum()),
                "negative_price_interval_count": int((price < 0).sum()),
                "zero_price_interval_count": int((price == 0).sum()),
                "mean_price_eur_per_mwh": _optional_float(price.mean()),
                "minimum_price_eur_per_mwh": _optional_float(price.min()),
                "maximum_price_eur_per_mwh": _optional_float(price.max()),
                "mean_daily_price_range_eur_per_mwh": _optional_float(daily_range.mean()),
            }
        )
    return pd.DataFrame.from_records(rows)


def _annual_perfect_foresight(
    schedule: pd.DataFrame,
    accepted: pd.DataFrame,
    energy_capacity_mwh: float | None,
) -> pd.DataFrame:
    validated = _validate_schedule(schedule, accepted)
    rows: list[dict[str, Any]] = []
    for year, group in validated.groupby("delivery_year", sort=True):
        charge_mwh = float(group["charge_grid_mwh"].sum())
        discharge_mwh = float(group["discharge_grid_mwh"].sum())
        charge_cost = float(group["charging_energy_cost_eur"].sum())
        discharge_revenue = float(group["discharge_energy_revenue_eur"].sum())
        margin = float(group["net_market_margin_eur"].sum())
        dispatch_day_count = int(group["market_day"].nunique())
        row: dict[str, Any] = {
            "delivery_year": int(year),
            "dispatch_interval_count": int(len(group)),
            "dispatch_market_day_count": dispatch_day_count,
            "perfect_foresight_gross_discharge_revenue_eur": discharge_revenue,
            "perfect_foresight_charging_energy_cost_eur": charge_cost,
            "perfect_foresight_fees_eur": float(
                group["buy_fee_eur"].sum() + group["sell_fee_eur"].sum()
            ),
            "perfect_foresight_degradation_cost_eur": float(
                group["degradation_cost_eur"].sum()
            ),
            "perfect_foresight_net_market_margin_eur": margin,
            "perfect_foresight_net_market_margin_eur_per_market_day": (
                margin / dispatch_day_count if dispatch_day_count else None
            ),
            "perfect_foresight_grid_charge_mwh": charge_mwh,
            "perfect_foresight_grid_discharge_mwh": discharge_mwh,
            "perfect_foresight_average_charge_price_eur_per_mwh": (
                charge_cost / charge_mwh if charge_mwh > 1e-9 else None
            ),
            "perfect_foresight_average_discharge_price_eur_per_mwh": (
                discharge_revenue / discharge_mwh if discharge_mwh > 1e-9 else None
            ),
        }
        if energy_capacity_mwh is not None:
            row["perfect_foresight_equivalent_full_cycles"] = discharge_mwh / energy_capacity_mwh
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def _validate_schedule(schedule: pd.DataFrame, accepted: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in SCHEDULE_REQUIRED_COLUMNS if column not in schedule.columns]
    if missing:
        raise AnnualDecompositionError(
            f"Perfect-foresight schedule is missing columns: {', '.join(missing)}"
        )
    if schedule.empty:
        raise AnnualDecompositionError("Perfect-foresight schedule is empty")

    working = schedule.loc[:, list(SCHEDULE_REQUIRED_COLUMNS)].copy()
    working["delivery_start_utc"] = pd.to_datetime(working["delivery_start_utc"], utc=True)
    if working["delivery_start_utc"].duplicated().any():
        raise AnnualDecompositionError(
            "Perfect-foresight schedule repeats a canonical delivery interval"
        )

    accepted_prices = accepted.set_index("delivery_start_utc")["price_eur_per_mwh"]
    unknown = working.loc[~working["delivery_start_utc"].isin(accepted_prices.index)]
    if not unknown.empty:
        raise AnnualDecompositionError(
            f"Perfect-foresight schedule holds {len(unknown)} intervals absent from the "
            "accepted history; the schedule was not solved on this history"
        )

    aligned = accepted_prices.loc[working["delivery_start_utc"]].to_numpy(dtype=float)
    scheduled = working["price_eur_per_mwh"].to_numpy(dtype=float)
    differing = ~np.isclose(
        aligned, scheduled, rtol=0.0, atol=_PRICE_MATCH_TOLERANCE, equal_nan=True
    )
    if differing.any():
        raise AnnualDecompositionError(
            f"Perfect-foresight schedule settles {int(differing.sum())} intervals at a price "
            "the accepted history does not publish; the schedule was not solved on this history"
        )

    market_start = working["delivery_start_utc"].dt.tz_convert(MARKET_TZ)
    working["delivery_year"] = market_start.dt.year
    working["market_day"] = market_start.dt.date
    return working


def _ceiling_reconciliation(
    schedule: pd.DataFrame, ceiling: pd.DataFrame
) -> dict[str, Any]:
    total = float(schedule["net_market_margin_eur"].sum())
    annual_total = float(ceiling["perfect_foresight_net_market_margin_eur"].sum())
    return {
        "perfect_foresight_net_market_margin_eur": total,
        "perfect_foresight_annual_margin_sum_eur": annual_total,
        "perfect_foresight_margin_reconciliation_residual_eur": annual_total - total,
        "perfect_foresight_dispatch_interval_count": int(len(schedule)),
    }


def _validate_daily_results(
    method: str, daily: pd.DataFrame, accepted: pd.DataFrame
) -> pd.DataFrame:
    missing = [column for column in DAILY_REQUIRED_COLUMNS if column not in daily.columns]
    if missing:
        raise AnnualDecompositionError(
            f"Daily results for {method} are missing columns: {', '.join(missing)}"
        )
    if daily.empty:
        raise AnnualDecompositionError(f"Daily results for {method} are empty")

    working = daily.copy()
    working["market_day"] = _as_market_days(working["market_day"], method)
    if working["market_day"].duplicated().any():
        raise AnnualDecompositionError(f"Daily results for {method} repeat a market day")

    accepted_days = set(accepted["market_day"].unique())
    unknown = sorted(set(working["market_day"]) - accepted_days)
    if unknown:
        raise AnnualDecompositionError(
            f"Daily results for {method} cover {len(unknown)} market days absent from the "
            f"accepted history, beginning {unknown[0]}; they describe a different history"
        )
    working["delivery_year"] = working["market_day"].map(lambda day: day.year)
    return working


def _as_market_days(values: pd.Series, method: str) -> pd.Series:
    try:
        parsed = pd.to_datetime(values, errors="raise")
    except (ValueError, TypeError) as exc:
        raise AnnualDecompositionError(
            f"Daily results for {method} carry an unparseable market day: {exc}"
        ) from exc
    return parsed.dt.date


def _annual_forecast(
    validated_daily: Mapping[str, pd.DataFrame],
    delivery_years: list[int],
    market_days_by_year: Mapping[int, int],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for method in sorted(validated_daily):
        daily = validated_daily[method]
        for year in delivery_years:
            group = daily.loc[daily["delivery_year"] == year]
            available_days = market_days_by_year[year]
            row = {
                "delivery_year": year,
                "forecast_method": method,
                "available_market_day_count": available_days,
                "backtested_market_day_count": int(len(group)),
                "not_backtested_market_day_count": available_days - int(len(group)),
                "backtested_day_coverage_fraction": (
                    len(group) / available_days if available_days else None
                ),
            }
            row.update(_forecast_year_metrics(group))
            rows.append(row)
    if not rows:
        return pd.DataFrame(
            columns=[
                "delivery_year",
                "forecast_method",
                "available_market_day_count",
                "backtested_market_day_count",
                "not_backtested_market_day_count",
                "backtested_day_coverage_fraction",
            ]
        )
    return pd.DataFrame.from_records(rows)


def _forecast_year_metrics(group: pd.DataFrame) -> dict[str, Any]:
    if group.empty:
        return {
            "backtested_interval_count": 0,
            "forecast_mae_eur_per_mwh": None,
            "forecast_rmse_eur_per_mwh": None,
            "forecast_planned_margin_eur": None,
            "realized_margin_eur": None,
            "perfect_foresight_margin_eur": None,
            "perfect_foresight_regret_eur": None,
            "perfect_foresight_capture_ratio": None,
            "realized_margin_eur_per_market_day": None,
            "loss_making_day_count": 0,
            "loss_making_day_fraction": None,
            "grid_charge_mwh": None,
            "grid_discharge_mwh": None,
        }
    intervals = group["interval_count"].to_numpy(dtype=float)
    interval_total = float(intervals.sum())
    realized = float(group["realized_margin_eur"].sum())
    ceiling = float(group["perfect_foresight_margin_eur"].sum())
    loss_days = int((group["realized_margin_eur"] < 0).sum())
    mae = group["forecast_mae_eur_per_mwh"].to_numpy(dtype=float)
    rmse = group["forecast_rmse_eur_per_mwh"].to_numpy(dtype=float)
    return {
        "backtested_interval_count": int(interval_total),
        "forecast_mae_eur_per_mwh": float((mae * intervals).sum() / interval_total),
        "forecast_rmse_eur_per_mwh": float(
            np.sqrt((rmse**2 * intervals).sum() / interval_total)
        ),
        "forecast_planned_margin_eur": float(group["forecast_margin_eur"].sum()),
        "realized_margin_eur": realized,
        "perfect_foresight_margin_eur": ceiling,
        "perfect_foresight_regret_eur": float(group["regret_eur"].sum()),
        "perfect_foresight_capture_ratio": (realized / ceiling if ceiling > 1e-9 else None),
        "realized_margin_eur_per_market_day": realized / len(group),
        "loss_making_day_count": loss_days,
        "loss_making_day_fraction": loss_days / len(group),
        "grid_charge_mwh": float(group["grid_charge_mwh"].sum()),
        "grid_discharge_mwh": float(group["grid_discharge_mwh"].sum()),
    }


def _annual_common_day(
    validated_daily: Mapping[str, pd.DataFrame], delivery_years: list[int]
) -> tuple[pd.DataFrame, set[date]]:
    methods = sorted(validated_daily)
    if not methods:
        return pd.DataFrame(columns=["delivery_year", "forecast_method"]), set()

    common_days: set[date] = set(validated_daily[methods[0]]["market_day"])
    for method in methods[1:]:
        common_days &= set(validated_daily[method]["market_day"])

    rows: list[dict[str, Any]] = []
    for year in delivery_years:
        year_days = {day for day in common_days if day.year == year}
        ceilings: list[float] = []
        year_rows: list[dict[str, Any]] = []
        for method in methods:
            daily = validated_daily[method]
            group = daily.loc[daily["market_day"].isin(year_days)]
            metrics = _forecast_year_metrics(group)
            if metrics["perfect_foresight_margin_eur"] is not None:
                ceilings.append(float(metrics["perfect_foresight_margin_eur"]))
            year_rows.append(
                {
                    "delivery_year": year,
                    "forecast_method": method,
                    "common_market_day_count": len(year_days),
                    **{
                        key: metrics[key]
                        for key in (
                            "backtested_interval_count",
                            "forecast_mae_eur_per_mwh",
                            "forecast_rmse_eur_per_mwh",
                            "realized_margin_eur",
                            "perfect_foresight_margin_eur",
                            "perfect_foresight_regret_eur",
                            "perfect_foresight_capture_ratio",
                            "realized_margin_eur_per_market_day",
                            "loss_making_day_count",
                        )
                    },
                }
            )
        spread = max(ceilings) - min(ceilings) if ceilings else None
        for row in year_rows:
            row["perfect_foresight_margin_spread_eur"] = spread
        rows.extend(year_rows)
    return pd.DataFrame.from_records(rows), common_days


def _common_day_summary(
    annual_common_day: pd.DataFrame, common_days: set[date], methods: list[str]
) -> dict[str, Any]:
    if not methods:
        return {}
    spreads = annual_common_day["perfect_foresight_margin_spread_eur"].dropna()
    return {
        "common_market_day_count": len(common_days),
        "common_day_ceiling_spread_by_year": {
            str(int(year)): _optional_float(value)
            for year, value in annual_common_day.groupby("delivery_year")[
                "perfect_foresight_margin_spread_eur"
            ].first().items()
        },
        "maximum_common_day_ceiling_spread_eur": (
            float(spreads.max()) if not spreads.empty else None
        ),
    }


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
