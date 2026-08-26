"""Walk-forward forecast-planned battery dispatch settled at realized prices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..data.schema import ensure_canonical
from ..dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from ..forecast import (
    FORECAST_METHODS,
    calculate_forecast_metrics,
    generate_naive_forecasts,
)

FORECAST_BACKTEST_LABEL = (
    "Walk-forward forecast-planned Greek DAM dispatch settled at realized prices; "
    "research backtest, not expected investment revenue."
)


class ForecastDispatchInputError(ValueError):
    """Raised when forecast-dispatch assumptions cannot support a fair backtest."""


@dataclass(frozen=True)
class ForecastDispatchBacktestResult:
    interval_schedule: pd.DataFrame
    daily_results: pd.DataFrame
    summary: dict[str, Any]


def backtest_forecast_dispatch(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    *,
    method: str = "ensemble",
    rolling_window_days: int = 28,
    start_day: date | str | None = None,
) -> ForecastDispatchBacktestResult:
    """Plan each day on a causal forecast and settle against realized DAM prices.

    Each day starts at the configured initial SOC and must return to that same
    SOC. This makes forecast and perfect-foresight daily values comparable and
    prevents energy borrowing across independent daily solves.
    """

    if method not in FORECAST_METHODS:
        raise ForecastDispatchInputError(f"Unsupported forecast method: {method}")
    if not np.isclose(
        config.initial_soc_fraction, config.effective_terminal_soc_fraction
    ):
        raise ForecastDispatchInputError(
            "Daily forecast backtests require terminal_soc_fraction to equal "
            "initial_soc_fraction"
        )

    actual = ensure_canonical(prices, allow_empty=False)
    forecast_result = generate_naive_forecasts(
        actual,
        methods=[method],
        rolling_window_days=rolling_window_days,
        start_day=start_day,
    )
    forecast_table = forecast_result.forecasts
    complete_days: list[date] = []
    excluded_days: list[dict[str, Any]] = []
    missing_forecast_interval_count = 0
    for market_day, day in forecast_table.groupby("market_day", sort=True):
        missing_count = int(day[method].isna().sum())
        missing_forecast_interval_count += missing_count
        if missing_count == 0:
            complete_days.append(market_day)
        else:
            excluded_days.append(
                {
                    "market_day": str(market_day),
                    "interval_count": int(len(day)),
                    "missing_forecast_interval_count": missing_count,
                }
            )
    if not complete_days:
        raise ForecastDispatchInputError(
            f"No complete {method} forecast day is available; provide more history"
        )

    forecast_by_start = forecast_table.set_index("delivery_start_utc")
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

        forecast_margin = float(settled["forecast_net_market_margin_eur"].sum())
        realized_margin = float(settled["realized_net_market_margin_eur"].sum())
        perfect_margin = float(settled["perfect_foresight_net_market_margin_eur"].sum())
        actual_prices = settled["realized_price_eur_per_mwh"].to_numpy(dtype=float)
        forecast_prices = settled["forecast_price_eur_per_mwh"].to_numpy(dtype=float)
        error = forecast_prices - actual_prices
        daily_outputs.append(
            {
                "market_day": market_day,
                "interval_count": len(settled),
                "forecast_method": method,
                "forecast_mae_eur_per_mwh": float(np.mean(np.abs(error))),
                "forecast_rmse_eur_per_mwh": float(np.sqrt(np.mean(error**2))),
                "forecast_margin_eur": forecast_margin,
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
    eligible_forecasts = forecast_table.loc[
        forecast_table["market_day"].isin(complete_days)
    ]
    backtested_forecast_metrics = calculate_forecast_metrics(
        eligible_forecasts, methods=[method]
    )[method]
    evaluation_day_count = int(forecast_table["market_day"].nunique())
    evaluation_interval_count = int(len(forecast_table))
    realized_total = float(daily_results["realized_margin_eur"].sum())
    forecast_total = float(daily_results["forecast_margin_eur"].sum())
    perfect_total = float(daily_results["perfect_foresight_margin_eur"].sum())
    loss_days = int(daily_results["realized_margin_eur"].lt(0).sum())
    summary = {
        "result_label": FORECAST_BACKTEST_LABEL,
        "forecast_method": method,
        "rolling_window_days": rolling_window_days,
        "evaluation_day_count": evaluation_day_count,
        "evaluation_interval_count": evaluation_interval_count,
        "backtested_day_count": len(daily_results),
        "backtested_interval_count": len(interval_schedule),
        "backtested_day_fraction": len(daily_results) / evaluation_day_count,
        "backtested_interval_fraction": (
            len(interval_schedule) / evaluation_interval_count
        ),
        "excluded_incomplete_forecast_day_count": len(excluded_days),
        "excluded_incomplete_forecast_days": excluded_days,
        "missing_forecast_interval_count": missing_forecast_interval_count,
        "first_backtest_market_day": str(daily_results["market_day"].min()),
        "last_backtest_market_day": str(daily_results["market_day"].max()),
        "forecast_metrics": forecast_result.metrics[method],
        "backtested_forecast_metrics": backtested_forecast_metrics,
        "forecast_planned_margin_eur": forecast_total,
        "realized_margin_eur": realized_total,
        "perfect_foresight_margin_eur": perfect_total,
        "perfect_foresight_regret_eur": perfect_total - realized_total,
        "perfect_foresight_capture_ratio": (
            realized_total / perfect_total if perfect_total > 1e-9 else None
        ),
        "loss_making_day_count": loss_days,
        "loss_making_day_fraction": loss_days / len(daily_results),
        "grid_charge_mwh": float(interval_schedule["charge_grid_mwh"].sum()),
        "grid_discharge_mwh": float(interval_schedule["discharge_grid_mwh"].sum()),
        "equivalent_full_cycles": float(
            interval_schedule["discharge_grid_mwh"].sum()
            / config.energy_capacity_mwh
        ),
        "terminal_soc_policy": "Initial SOC restored at the end of every market day",
        "forecast_coverage_policy": (
            "Forecast metrics cover the full requested evaluation period; dispatch is "
            "run only for complete forecast days, and excluded days are listed"
        ),
        "market_acceptance_assumption": (
            "Price-taking planned quantities are fully accepted; bid acceptance and "
            "imbalance exposure are excluded"
        ),
    }
    return ForecastDispatchBacktestResult(
        interval_schedule=interval_schedule,
        daily_results=daily_results,
        summary=summary,
    )


def _settle_day(
    planned_schedule: pd.DataFrame,
    perfect_schedule: pd.DataFrame,
    realized_prices: np.ndarray,
    config: BatteryDispatchConfig,
    method: str,
) -> pd.DataFrame:
    if len(planned_schedule) != len(realized_prices) or len(perfect_schedule) != len(
        realized_prices
    ):
        raise ForecastDispatchInputError("Dispatch schedules and realized prices misalign")
    settled = planned_schedule.copy().rename(
        columns={
            "charging_energy_cost_eur": "forecast_charging_energy_cost_eur",
            "discharge_energy_revenue_eur": "forecast_discharge_energy_revenue_eur",
            "net_market_margin_eur": "forecast_net_market_margin_eur",
        }
    )
    forecast_prices = settled["price_eur_per_mwh"].to_numpy(dtype=float)
    charge_mwh = settled["charge_grid_mwh"].to_numpy(dtype=float)
    discharge_mwh = settled["discharge_grid_mwh"].to_numpy(dtype=float)
    realized_charge_cost = realized_prices * charge_mwh
    realized_discharge_revenue = realized_prices * discharge_mwh
    fees_and_degradation = (
        settled["buy_fee_eur"].to_numpy(dtype=float)
        + settled["sell_fee_eur"].to_numpy(dtype=float)
        + settled["degradation_cost_eur"].to_numpy(dtype=float)
    )

    settled["forecast_method"] = method
    settled["forecast_price_eur_per_mwh"] = forecast_prices
    settled["realized_price_eur_per_mwh"] = realized_prices
    settled["price_eur_per_mwh"] = realized_prices
    settled["realized_charging_energy_cost_eur"] = realized_charge_cost
    settled["realized_discharge_energy_revenue_eur"] = realized_discharge_revenue
    settled["realized_net_market_margin_eur"] = (
        realized_discharge_revenue - realized_charge_cost - fees_and_degradation
    )
    settled["perfect_foresight_charge_mw"] = perfect_schedule[
        "charge_mw"
    ].to_numpy(dtype=float)
    settled["perfect_foresight_discharge_mw"] = perfect_schedule[
        "discharge_mw"
    ].to_numpy(dtype=float)
    settled["perfect_foresight_net_market_margin_eur"] = perfect_schedule[
        "net_market_margin_eur"
    ].to_numpy(dtype=float)
    return settled
