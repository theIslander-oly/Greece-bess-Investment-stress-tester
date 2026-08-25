"""Strictly causal naïve forecasts for Greek DAM price baselines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import sqrt

import numpy as np
import pandas as pd

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical


FORECAST_METHODS = (
    "daily_persistence",
    "weekly_persistence",
    "rolling_mean",
    "ensemble",
)


class ForecastInputError(ValueError):
    """Raised when data or forecast assumptions are invalid."""


@dataclass(frozen=True)
class ForecastResult:
    forecasts: pd.DataFrame
    metrics: dict[str, dict[str, object]]
    methods: tuple[str, ...]
    rolling_window_days: int


def generate_naive_forecasts(
    prices: pd.DataFrame,
    *,
    methods: tuple[str, ...] | list[str] = FORECAST_METHODS,
    rolling_window_days: int = 28,
    start_day: date | str | None = None,
) -> ForecastResult:
    """Generate walk-forward baselines using observations from prior days only.

    Forecasts for every interval of a target day are calculated before any
    realized value from that target day is added to history.
    """

    selected_methods = _validate_methods(methods)
    if not isinstance(rolling_window_days, int) or rolling_window_days < 1:
        raise ForecastInputError("rolling_window_days must be a positive integer")
    parsed_start = _parse_start_day(start_day)

    data = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(data, require_complete_days=True)
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise ForecastInputError(f"Price data failed forecast quality checks: {errors}")

    working = data.copy()
    working["market_day"] = working["delivery_start_market"].dt.date
    working["market_slot_minutes"] = (
        working["delivery_start_market"].dt.hour * 60
        + working["delivery_start_market"].dt.minute
    )
    working["slot_occurrence"] = working.groupby(
        ["market_day", "market_slot_minutes"], sort=False
    ).cumcount()

    price_lookup: dict[tuple[date, int, int], float] = {}
    slot_history: dict[int, list[tuple[date, float]]] = {}
    records: list[dict[str, object]] = []

    for market_day, day_frame in working.groupby("market_day", sort=True):
        day_records: list[dict[str, object]] = []
        for row in day_frame.itertuples(index=False):
            slot = int(row.market_slot_minutes)
            occurrence = int(row.slot_occurrence)
            daily = _lookup_prior(
                price_lookup, market_day - timedelta(days=1), slot, occurrence
            )
            weekly = _lookup_prior(
                price_lookup, market_day - timedelta(days=7), slot, occurrence
            )
            rolling_values = [
                value
                for history_day, value in slot_history.get(slot, [])
                if 0 < (market_day - history_day).days <= rolling_window_days
            ]
            rolling = float(np.mean(rolling_values)) if rolling_values else np.nan
            ensemble_values = [
                value for value in (daily, weekly, rolling) if np.isfinite(value)
            ]
            ensemble = (
                float(np.mean(ensemble_values)) if ensemble_values else np.nan
            )
            day_records.append(
                {
                    "delivery_start_utc": row.delivery_start_utc,
                    "delivery_start_market": row.delivery_start_market,
                    "market_day": market_day,
                    "market_slot_minutes": slot,
                    "slot_occurrence": occurrence,
                    "duration_hours": float(row.duration_hours),
                    "source": row.source,
                    "actual_price_eur_per_mwh": float(row.price_eur_per_mwh),
                    "daily_persistence": daily,
                    "weekly_persistence": weekly,
                    "rolling_mean": rolling,
                    "ensemble": ensemble,
                }
            )

        if parsed_start is None or market_day >= parsed_start:
            records.extend(day_records)

        # Update only after all forecasts for this day are fixed. This is the
        # central no-leakage guarantee for day-ahead evaluation.
        for row in day_frame.itertuples(index=False):
            slot = int(row.market_slot_minutes)
            occurrence = int(row.slot_occurrence)
            price = float(row.price_eur_per_mwh)
            price_lookup[(market_day, slot, occurrence)] = price
            slot_history.setdefault(slot, []).append((market_day, price))

    forecasts = pd.DataFrame.from_records(records)
    if forecasts.empty:
        raise ForecastInputError("No forecast intervals remain after start_day")
    output_columns = [
        "delivery_start_utc",
        "delivery_start_market",
        "market_day",
        "market_slot_minutes",
        "slot_occurrence",
        "duration_hours",
        "source",
        "actual_price_eur_per_mwh",
        *selected_methods,
    ]
    forecasts = forecasts.loc[:, output_columns].reset_index(drop=True)
    metrics = calculate_forecast_metrics(forecasts, methods=selected_methods)
    return ForecastResult(
        forecasts=forecasts,
        metrics=metrics,
        methods=selected_methods,
        rolling_window_days=rolling_window_days,
    )


def calculate_forecast_metrics(
    forecasts: pd.DataFrame,
    *,
    methods: tuple[str, ...] | list[str] = FORECAST_METHODS,
) -> dict[str, dict[str, object]]:
    """Calculate signed-price-safe error and negative-price metrics."""

    selected_methods = tuple(dict.fromkeys(methods))
    if not selected_methods:
        raise ForecastInputError("At least one forecast method is required")
    if "actual_price_eur_per_mwh" not in forecasts:
        raise ForecastInputError("Forecast table is missing actual_price_eur_per_mwh")
    actual_all = pd.to_numeric(
        forecasts["actual_price_eur_per_mwh"], errors="coerce"
    )
    metrics: dict[str, dict[str, object]] = {}
    total_count = len(forecasts)

    for method in selected_methods:
        if method not in forecasts:
            raise ForecastInputError(f"Forecast table is missing method column {method}")
        predicted_all = pd.to_numeric(forecasts[method], errors="coerce")
        valid = actual_all.notna() & predicted_all.notna()
        actual = actual_all.loc[valid].to_numpy(dtype=float)
        predicted = predicted_all.loc[valid].to_numpy(dtype=float)
        count = len(actual)
        if count == 0:
            metrics[method] = {
                "observation_count": 0,
                "coverage_fraction": 0.0,
                "mae_eur_per_mwh": None,
                "rmse_eur_per_mwh": None,
                "mean_error_eur_per_mwh": None,
                "median_absolute_error_eur_per_mwh": None,
                "wape": None,
                "correlation": None,
                "negative_price_precision": None,
                "negative_price_recall": None,
            }
            continue

        error = predicted - actual
        absolute_error = np.abs(error)
        denominator = float(np.abs(actual).sum())
        actual_negative = actual < 0
        predicted_negative = predicted < 0
        true_negative_calls = int((actual_negative & predicted_negative).sum())
        negative_calls = int(predicted_negative.sum())
        actual_negative_count = int(actual_negative.sum())
        correlation = None
        if count > 1 and np.std(actual) > 0 and np.std(predicted) > 0:
            correlation = float(np.corrcoef(actual, predicted)[0, 1])
        metrics[method] = {
            "observation_count": count,
            "coverage_fraction": count / total_count if total_count else 0.0,
            "mae_eur_per_mwh": float(absolute_error.mean()),
            "rmse_eur_per_mwh": sqrt(float(np.mean(error**2))),
            "mean_error_eur_per_mwh": float(error.mean()),
            "median_absolute_error_eur_per_mwh": float(np.median(absolute_error)),
            "wape": float(absolute_error.sum() / denominator) if denominator else None,
            "correlation": correlation,
            "negative_price_precision": (
                true_negative_calls / negative_calls if negative_calls else None
            ),
            "negative_price_recall": (
                true_negative_calls / actual_negative_count
                if actual_negative_count
                else None
            ),
        }
    return metrics


def _lookup_prior(
    lookup: dict[tuple[date, int, int], float],
    prior_day: date,
    slot: int,
    occurrence: int,
) -> float:
    exact = lookup.get((prior_day, slot, occurrence))
    if exact is not None:
        return exact
    # A fall-back DST day has two occurrences of one wall-clock slot. A normal
    # prior day has one, so the second target occurrence uses its rank-zero peer.
    fallback = lookup.get((prior_day, slot, 0))
    return float(fallback) if fallback is not None else np.nan


def _validate_methods(methods: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(methods))
    if not selected:
        raise ForecastInputError("At least one forecast method is required")
    unsupported = sorted(set(selected) - set(FORECAST_METHODS))
    if unsupported:
        raise ForecastInputError(f"Unsupported forecast methods: {unsupported}")
    return selected


def _parse_start_day(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ForecastInputError("start_day must use YYYY-MM-DD") from exc
