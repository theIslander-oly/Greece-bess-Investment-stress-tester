"""Like-for-like held-out dispatch comparison for ML and naïve forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..data.schema import ensure_canonical
from ..dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from ..forecast import FORECAST_METHODS, calculate_forecast_metrics
from ..forecast.ml import MLForecastResult
from .forecast_dispatch import (
    ForecastDispatchBacktestResult,
    ForecastDispatchInputError,
    _settle_day,
)


ML_DISPATCH_BENCHMARK_LABEL = (
    "Held-out like-for-like Greek DAM ML forecast-dispatch benchmark settled at "
    "realized prices; research result, not expected investment revenue."
)


@dataclass(frozen=True)
class MLDispatchBenchmarkResult:
    selected_model_interval_schedule: pd.DataFrame
    daily_results: pd.DataFrame
    method_summaries: dict[str, dict[str, Any]]
    summary: dict[str, Any]


def backtest_ml_dispatch_benchmark(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    ml_result: MLForecastResult,
) -> MLDispatchBenchmarkResult:
    """Settle every model and baseline over identical complete held-out days."""

    forecasts = ml_result.forecasts.loc[
        ml_result.forecasts["split"].eq("test")
    ].copy()
    methods = [*FORECAST_METHODS, *ml_result.config.models]
    evaluation_days = sorted(forecasts["market_day"].unique())
    common_days: list[object] = []
    excluded_days: list[dict[str, Any]] = []
    for market_day, day in forecasts.groupby("market_day", sort=True):
        missing_by_method = {
            method: int(day[method].isna().sum())
            for method in methods
            if day[method].isna().any()
        }
        if missing_by_method:
            excluded_days.append(
                {
                    "market_day": str(market_day),
                    "interval_count": int(len(day)),
                    "missing_forecast_intervals_by_method": missing_by_method,
                }
            )
        else:
            common_days.append(market_day)
    if not common_days:
        raise ForecastDispatchInputError(
            "No held-out test day has complete forecasts for every comparison method"
        )

    common_forecasts = forecasts.loc[forecasts["market_day"].isin(common_days)]
    method_results: dict[str, ForecastDispatchBacktestResult] = {}
    daily_outputs: list[pd.DataFrame] = []
    for method in methods:
        result = _backtest_precomputed_forecast(
            prices,
            config,
            common_forecasts,
            method=method,
        )
        method_results[method] = result
        daily = result.daily_results.copy()
        daily.insert(0, "comparison_method", method)
        daily_outputs.append(daily)

    method_summaries = {
        method: result.summary for method, result in method_results.items()
    }
    perfect_values = [
        float(summary["perfect_foresight_margin_eur"])
        for summary in method_summaries.values()
    ]
    if not np.allclose(perfect_values, perfect_values[0], atol=1e-6, rtol=0):
        raise RuntimeError("Perfect-foresight comparator differs across methods")
    ranking_names = sorted(
        methods,
        key=lambda method: float(method_summaries[method]["realized_margin_eur"]),
        reverse=True,
    )
    dispatch_ranking = [
        {
            "rank": rank,
            "method": method,
            "realized_margin_eur": method_summaries[method]["realized_margin_eur"],
            "perfect_foresight_margin_eur": method_summaries[method][
                "perfect_foresight_margin_eur"
            ],
            "perfect_foresight_regret_eur": method_summaries[method][
                "perfect_foresight_regret_eur"
            ],
            "perfect_foresight_capture_ratio": method_summaries[method][
                "perfect_foresight_capture_ratio"
            ],
            "forecast_rmse_eur_per_mwh": method_summaries[method][
                "forecast_metrics"
            ]["rmse_eur_per_mwh"],
        }
        for rank, method in enumerate(ranking_names, start=1)
    ]
    selected = ml_result.summary["selected_model"]
    summary = {
        "result_label": ML_DISPATCH_BENCHMARK_LABEL,
        "selected_model": selected,
        "comparison_methods": methods,
        "comparison_policy": (
            "Every method is settled over the identical held-out test days on which "
            "all comparison forecasts are complete"
        ),
        "test_evaluation_day_count": len(evaluation_days),
        "test_evaluation_interval_count": int(len(forecasts)),
        "common_backtest_day_count": len(common_days),
        "common_backtest_interval_count": int(len(common_forecasts)),
        "common_backtest_day_fraction": len(common_days) / len(evaluation_days),
        "common_backtest_interval_fraction": len(common_forecasts) / len(forecasts),
        "excluded_incomplete_comparison_day_count": len(excluded_days),
        "excluded_incomplete_comparison_days": excluded_days,
        "perfect_foresight_margin_eur": perfect_values[0],
        "dispatch_ranking": dispatch_ranking,
        "method_summaries": method_summaries,
        "selected_model_summary": method_summaries[selected],
        "market_acceptance_assumption": (
            "Price-taking planned quantities are fully accepted; bid acceptance and "
            "imbalance exposure are excluded"
        ),
    }
    return MLDispatchBenchmarkResult(
        selected_model_interval_schedule=method_results[selected].interval_schedule,
        daily_results=pd.concat(daily_outputs, ignore_index=True),
        method_summaries=method_summaries,
        summary=summary,
    )


def _backtest_precomputed_forecast(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    forecasts: pd.DataFrame,
    *,
    method: str,
) -> ForecastDispatchBacktestResult:
    if not np.isclose(
        config.initial_soc_fraction, config.effective_terminal_soc_fraction
    ):
        raise ForecastDispatchInputError(
            "Daily forecast backtests require terminal_soc_fraction to equal "
            "initial_soc_fraction"
        )
    required = {"delivery_start_utc", "market_day", method}
    missing = sorted(required - set(forecasts.columns))
    if missing:
        raise ForecastDispatchInputError(
            f"Forecast table is missing required columns: {missing}"
        )
    table = forecasts.copy()
    table["delivery_start_utc"] = pd.to_datetime(
        table["delivery_start_utc"], utc=True, errors="coerce"
    )
    if table["delivery_start_utc"].isna().any():
        raise ForecastDispatchInputError("Forecast delivery timestamps are invalid")
    if table["delivery_start_utc"].duplicated().any():
        raise ForecastDispatchInputError("Forecast delivery timestamps must be unique")
    actual = ensure_canonical(prices, allow_empty=False)
    actual_by_start = actual.set_index("delivery_start_utc")
    unknown = ~table["delivery_start_utc"].isin(actual_by_start.index)
    if unknown.any():
        raise ForecastDispatchInputError(
            "Forecast table contains intervals absent from realized prices"
        )
    table["actual_price_eur_per_mwh"] = table["delivery_start_utc"].map(
        actual_by_start["price_eur_per_mwh"]
    )

    complete_days: list[object] = []
    excluded_days: list[dict[str, Any]] = []
    missing_count = 0
    for market_day, day in table.groupby("market_day", sort=True):
        day_missing = int(day[method].isna().sum())
        missing_count += day_missing
        if day_missing:
            excluded_days.append(
                {
                    "market_day": str(market_day),
                    "interval_count": int(len(day)),
                    "missing_forecast_interval_count": day_missing,
                }
            )
        else:
            complete_days.append(market_day)
    if not complete_days:
        raise ForecastDispatchInputError(f"No complete {method} forecast day is available")

    forecast_by_start = table.set_index("delivery_start_utc")
    actual_working = actual.copy()
    actual_working["market_day"] = actual_working["delivery_start_market"].dt.date
    interval_outputs: list[pd.DataFrame] = []
    daily_outputs: list[dict[str, Any]] = []
    for market_day in complete_days:
        actual_day = actual_working.loc[
            actual_working["market_day"].eq(market_day), actual.columns
        ].reset_index(drop=True)
        day_forecasts = forecast_by_start.loc[actual_day["delivery_start_utc"], method]
        predicted_day = actual_day.copy()
        predicted_day["price_eur_per_mwh"] = day_forecasts.to_numpy(dtype=float)
        planned = optimize_perfect_foresight(predicted_day, config)
        perfect = optimize_perfect_foresight(actual_day, config)
        settled = _settle_day(
            planned.schedule,
            perfect.schedule,
            actual_day["price_eur_per_mwh"].to_numpy(dtype=float),
            config,
            method,
        )
        interval_outputs.append(settled)
        actual_prices = settled["realized_price_eur_per_mwh"].to_numpy(dtype=float)
        forecast_prices = settled["forecast_price_eur_per_mwh"].to_numpy(dtype=float)
        error = forecast_prices - actual_prices
        realized_margin = float(settled["realized_net_market_margin_eur"].sum())
        perfect_margin = float(
            settled["perfect_foresight_net_market_margin_eur"].sum()
        )
        daily_outputs.append(
            {
                "market_day": market_day,
                "interval_count": len(settled),
                "forecast_method": method,
                "forecast_mae_eur_per_mwh": float(np.mean(np.abs(error))),
                "forecast_rmse_eur_per_mwh": float(np.sqrt(np.mean(error**2))),
                "forecast_margin_eur": float(
                    settled["forecast_net_market_margin_eur"].sum()
                ),
                "realized_margin_eur": realized_margin,
                "perfect_foresight_margin_eur": perfect_margin,
                "regret_eur": perfect_margin - realized_margin,
                "perfect_foresight_capture_ratio": (
                    realized_margin / perfect_margin if perfect_margin > 1e-9 else None
                ),
                "grid_charge_mwh": float(settled["charge_grid_mwh"].sum()),
                "grid_discharge_mwh": float(settled["discharge_grid_mwh"].sum()),
                "equivalent_full_cycles": float(
                    settled["discharge_grid_mwh"].sum()
                    / config.energy_capacity_mwh
                ),
            }
        )

    interval_schedule = pd.concat(interval_outputs, ignore_index=True)
    daily_results = pd.DataFrame.from_records(daily_outputs)
    full_metrics = calculate_forecast_metrics(table, methods=[method])[method]
    eligible = table.loc[table["market_day"].isin(complete_days)]
    backtested_metrics = calculate_forecast_metrics(eligible, methods=[method])[method]
    realized_total = float(daily_results["realized_margin_eur"].sum())
    perfect_total = float(daily_results["perfect_foresight_margin_eur"].sum())
    summary = {
        "forecast_method": method,
        "evaluation_day_count": int(table["market_day"].nunique()),
        "evaluation_interval_count": int(len(table)),
        "backtested_day_count": len(daily_results),
        "backtested_interval_count": len(interval_schedule),
        "excluded_incomplete_forecast_days": excluded_days,
        "missing_forecast_interval_count": missing_count,
        "forecast_metrics": full_metrics,
        "backtested_forecast_metrics": backtested_metrics,
        "forecast_planned_margin_eur": float(
            daily_results["forecast_margin_eur"].sum()
        ),
        "realized_margin_eur": realized_total,
        "perfect_foresight_margin_eur": perfect_total,
        "perfect_foresight_regret_eur": perfect_total - realized_total,
        "perfect_foresight_capture_ratio": (
            realized_total / perfect_total if perfect_total > 1e-9 else None
        ),
        "grid_charge_mwh": float(interval_schedule["charge_grid_mwh"].sum()),
        "grid_discharge_mwh": float(interval_schedule["discharge_grid_mwh"].sum()),
        "terminal_soc_policy": "Initial SOC restored at the end of every market day",
    }
    return ForecastDispatchBacktestResult(
        interval_schedule=interval_schedule,
        daily_results=daily_results,
        summary=summary,
    )
