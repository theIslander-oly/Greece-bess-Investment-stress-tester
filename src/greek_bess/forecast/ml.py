"""Leakage-safe walk-forward ML benchmarks for Greek DAM prices."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical
from .naive import FORECAST_METHODS, calculate_forecast_metrics, generate_naive_forecasts

ML_MODELS = ("ridge", "hist_gradient_boosting")
ML_FORECAST_LABEL = (
    "Leakage-safe walk-forward Greek DAM ML benchmark; research forecast, not "
    "expected investment revenue."
)

FEATURE_PROVENANCE: dict[str, str] = {
    "slot_sin": "Known day-ahead from the target market-clock delivery slot",
    "slot_cos": "Known day-ahead from the target market-clock delivery slot",
    "weekday_sin": "Known day-ahead from the target market calendar",
    "weekday_cos": "Known day-ahead from the target market calendar",
    "year_day_sin": "Known day-ahead from the target market calendar",
    "year_day_cos": "Known day-ahead from the target market calendar",
    "is_weekend": "Known day-ahead from the target market calendar",
    "slot_occurrence": "Known from the published DST-aware target interval structure",
    "daily_persistence": "Realized price from the matching prior market-day slot only",
    "weekly_persistence": "Realized price from the matching slot seven days earlier only",
    "rolling_mean": "Matching-slot mean from prior days inside the configured window",
    "ensemble": "Mean of available causal naïve forecasts for the target interval",
    "price_lag_2d": "Realized price from the matching slot two market days earlier only",
    "rolling_mean_7d": "Matching-slot mean from the preceding seven calendar days only",
    "rolling_std_7d": "Matching-slot standard deviation from preceding seven days only",
    "rolling_min_7d": "Matching-slot minimum from the preceding seven days only",
    "rolling_max_7d": "Matching-slot maximum from the preceding seven days only",
}
FEATURE_COLUMNS = tuple(FEATURE_PROVENANCE)


class MLForecastInputError(ValueError):
    """Raised when ML split or walk-forward assumptions are invalid."""


@dataclass(frozen=True)
class MLForecastConfig:
    """Time-split and deterministic model assumptions for an ML benchmark."""

    validation_start_day: date
    test_start_day: date
    models: tuple[str, ...] = ML_MODELS
    feature_window_days: int = 28
    refit_frequency_days: int = 7
    min_training_days: int = 28
    training_window_days: int | None = None
    ridge_alpha: float = 10.0
    gradient_learning_rate: float = 0.05
    gradient_max_iter: int = 150
    gradient_max_leaf_nodes: int = 15
    gradient_l2_regularization: float = 1.0
    random_seed: int = 42

    def __post_init__(self) -> None:
        for name in ("validation_start_day", "test_start_day"):
            value = getattr(self, name)
            if not isinstance(value, date):
                raise MLForecastInputError(f"{name} must be a date")
        if self.validation_start_day >= self.test_start_day:
            raise MLForecastInputError(
                "validation_start_day must be earlier than test_start_day"
            )
        selected = tuple(dict.fromkeys(self.models))
        if not selected:
            raise MLForecastInputError("At least one ML model is required")
        unsupported = sorted(set(selected) - set(ML_MODELS))
        if unsupported:
            raise MLForecastInputError(f"Unsupported ML models: {unsupported}")
        object.__setattr__(self, "models", selected)
        for name in (
            "feature_window_days",
            "refit_frequency_days",
            "min_training_days",
            "gradient_max_iter",
            "gradient_max_leaf_nodes",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 1:
                raise MLForecastInputError(f"{name} must be a positive integer")
        if self.training_window_days is not None:
            if not isinstance(self.training_window_days, int) or self.training_window_days < 1:
                raise MLForecastInputError(
                    "training_window_days must be a positive integer or null"
                )
            if self.training_window_days < self.min_training_days:
                raise MLForecastInputError(
                    "training_window_days cannot be below min_training_days"
                )
        for name in (
            "ridge_alpha",
            "gradient_learning_rate",
            "gradient_l2_regularization",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0:
                raise MLForecastInputError(f"{name} must be finite and nonnegative")
        if self.gradient_learning_rate == 0:
            raise MLForecastInputError("gradient_learning_rate must be greater than zero")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_start_day"] = str(self.validation_start_day)
        payload["test_start_day"] = str(self.test_start_day)
        payload["models"] = list(self.models)
        return payload


@dataclass(frozen=True)
class MLForecastResult:
    forecasts: pd.DataFrame
    feature_table: pd.DataFrame
    summary: dict[str, Any]
    config: MLForecastConfig


def generate_ml_forecasts(
    prices: pd.DataFrame,
    config: MLForecastConfig,
) -> MLForecastResult:
    """Fit deterministic models walk-forward and evaluate validation/test periods."""

    data = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(data, require_complete_days=True)
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise MLForecastInputError(f"Price data failed ML quality checks: {errors}")

    feature_table = build_causal_feature_table(
        data, rolling_window_days=config.feature_window_days
    )
    available_days = sorted(feature_table["market_day"].unique())
    if not available_days or available_days[-1] < config.test_start_day:
        raise MLForecastInputError("No held-out test days are available")
    validation_days = [
        day
        for day in available_days
        if config.validation_start_day <= day < config.test_start_day
    ]
    test_days = [day for day in available_days if day >= config.test_start_day]
    if not validation_days:
        raise MLForecastInputError("Validation period contains no market days")
    if not test_days:
        raise MLForecastInputError("Test period contains no market days")

    evaluation = feature_table.loc[
        feature_table["market_day"].ge(config.validation_start_day)
    ].copy()
    evaluation["split"] = np.where(
        evaluation["market_day"].lt(config.test_start_day), "validation", "test"
    )
    refit_logs: dict[str, list[dict[str, Any]]] = {}
    target_days = validation_days + test_days
    for model_name in config.models:
        predictions, refit_log = _walk_forward_predict(
            feature_table, target_days, model_name, config
        )
        evaluation[model_name] = evaluation["delivery_start_utc"].map(predictions)
        refit_logs[model_name] = refit_log

    comparison_methods = [*FORECAST_METHODS, *config.models]
    metrics: dict[str, dict[str, dict[str, object]]] = {}
    for split in ("validation", "test"):
        split_table = evaluation.loc[evaluation["split"].eq(split)]
        metrics[split] = calculate_forecast_metrics(
            split_table, methods=comparison_methods
        )

    selected_model = min(
        config.models,
        key=lambda name: float(metrics["validation"][name]["rmse_eur_per_mwh"]),
    )
    output_columns = [
        "delivery_start_utc",
        "delivery_start_market",
        "market_day",
        "market_slot_minutes",
        "slot_occurrence",
        "duration_hours",
        "source",
        "actual_price_eur_per_mwh",
        "split",
        *FORECAST_METHODS,
        *config.models,
    ]
    forecasts = evaluation.loc[:, output_columns].reset_index(drop=True)
    summary = {
        "result_label": ML_FORECAST_LABEL,
        "models": list(config.models),
        "baseline_methods": list(FORECAST_METHODS),
        "selected_model": selected_model,
        "model_selection_policy": "Lowest validation RMSE; test metrics are not used for selection",
        "validation_start_day": str(config.validation_start_day),
        "test_start_day": str(config.test_start_day),
        "training_start_day": str(min(available_days)),
        "last_test_day": str(max(test_days)),
        "validation_day_count": len(validation_days),
        "test_day_count": len(test_days),
        "validation_interval_count": int(evaluation["split"].eq("validation").sum()),
        "test_interval_count": int(evaluation["split"].eq("test").sum()),
        "metrics": metrics,
        "validation_ranking": _metric_ranking(metrics["validation"]),
        "test_ranking": _metric_ranking(metrics["test"]),
        "feature_columns": list(FEATURE_COLUMNS),
        "feature_provenance": FEATURE_PROVENANCE,
        "refit_logs": refit_logs,
        "config": config.to_dict(),
        "scikit_learn_version": sklearn.__version__,
        "data_policy": (
            "All price-derived features use prior market days only; target-day prices "
            "are labels and never model inputs"
        ),
    }
    return MLForecastResult(
        forecasts=forecasts,
        feature_table=feature_table,
        summary=summary,
        config=config,
    )


def build_causal_feature_table(
    prices: pd.DataFrame,
    *,
    rolling_window_days: int = 28,
) -> pd.DataFrame:
    """Build calendar and price-history features using only prior market days."""

    if not isinstance(rolling_window_days, int) or rolling_window_days < 1:
        raise MLForecastInputError("rolling_window_days must be a positive integer")
    naive = generate_naive_forecasts(
        prices,
        methods=FORECAST_METHODS,
        rolling_window_days=rolling_window_days,
    ).forecasts
    table = naive.copy()
    market_time = table["delivery_start_market"]
    slot_fraction = table["market_slot_minutes"].to_numpy(dtype=float) / 1440
    weekday = market_time.dt.dayofweek.to_numpy(dtype=float)
    year_day = market_time.dt.dayofyear.to_numpy(dtype=float)
    table["slot_sin"] = np.sin(2 * np.pi * slot_fraction)
    table["slot_cos"] = np.cos(2 * np.pi * slot_fraction)
    table["weekday_sin"] = np.sin(2 * np.pi * weekday / 7)
    table["weekday_cos"] = np.cos(2 * np.pi * weekday / 7)
    table["year_day_sin"] = np.sin(2 * np.pi * year_day / 365.25)
    table["year_day_cos"] = np.cos(2 * np.pi * year_day / 365.25)
    table["is_weekend"] = (weekday >= 5).astype(float)

    price_lookup: dict[tuple[date, int, int], float] = {}
    slot_history: dict[int, list[tuple[date, float]]] = {}
    lag_2d: list[float] = []
    rolling_mean_7d: list[float] = []
    rolling_std_7d: list[float] = []
    rolling_min_7d: list[float] = []
    rolling_max_7d: list[float] = []
    for market_day, day_frame in table.groupby("market_day", sort=True):
        for row in day_frame.itertuples(index=False):
            slot = int(row.market_slot_minutes)
            occurrence = int(row.slot_occurrence)
            lag_2d.append(
                _prior_value(
                    price_lookup, market_day - timedelta(days=2), slot, occurrence
                )
            )
            values = [
                value
                for history_day, value in slot_history.get(slot, [])
                if 0 < (market_day - history_day).days <= 7
            ]
            rolling_mean_7d.append(float(np.mean(values)) if values else np.nan)
            rolling_std_7d.append(
                float(np.std(values, ddof=0)) if len(values) >= 2 else np.nan
            )
            rolling_min_7d.append(float(np.min(values)) if values else np.nan)
            rolling_max_7d.append(float(np.max(values)) if values else np.nan)
        for row in day_frame.itertuples(index=False):
            slot = int(row.market_slot_minutes)
            occurrence = int(row.slot_occurrence)
            actual = float(row.actual_price_eur_per_mwh)
            price_lookup[(market_day, slot, occurrence)] = actual
            slot_history.setdefault(slot, []).append((market_day, actual))

    table["price_lag_2d"] = lag_2d
    table["rolling_mean_7d"] = rolling_mean_7d
    table["rolling_std_7d"] = rolling_std_7d
    table["rolling_min_7d"] = rolling_min_7d
    table["rolling_max_7d"] = rolling_max_7d
    return table


def _walk_forward_predict(
    feature_table: pd.DataFrame,
    target_days: list[date],
    model_name: str,
    config: MLForecastConfig,
) -> tuple[pd.Series, list[dict[str, Any]]]:
    predictions: dict[pd.Timestamp, float] = {}
    refit_log: list[dict[str, Any]] = []
    fitted_model: Any = None
    last_refit_day: date | None = None

    for target_day in target_days:
        refit_required = (
            fitted_model is None
            or last_refit_day is None
            or target_day == config.test_start_day
            or (target_day - last_refit_day).days >= config.refit_frequency_days
        )
        if refit_required:
            training = feature_table.loc[feature_table["market_day"].lt(target_day)]
            if config.training_window_days is not None:
                window_start = target_day - timedelta(days=config.training_window_days)
                training = training.loc[training["market_day"].ge(window_start)]
            training_day_count = int(training["market_day"].nunique())
            if training_day_count < config.min_training_days:
                raise MLForecastInputError(
                    f"{model_name} needs at least {config.min_training_days} training "
                    f"days before {target_day}; found {training_day_count}"
                )
            fitted_model = _make_model(model_name, config)
            fitted_model.fit(
                training.loc[:, FEATURE_COLUMNS],
                training["actual_price_eur_per_mwh"].to_numpy(dtype=float),
            )
            last_refit_day = target_day
            refit_log.append(
                {
                    "forecast_start_day": str(target_day),
                    "training_start_day": str(training["market_day"].min()),
                    "training_end_day": str(training["market_day"].max()),
                    "training_day_count": training_day_count,
                    "training_interval_count": int(len(training)),
                }
            )

        target = feature_table.loc[feature_table["market_day"].eq(target_day)]
        predicted = fitted_model.predict(target.loc[:, FEATURE_COLUMNS])
        predictions.update(
            zip(target["delivery_start_utc"], predicted.astype(float), strict=True)
        )

    return pd.Series(predictions, dtype=float), refit_log


def _make_model(model_name: str, config: MLForecastConfig) -> Any:
    if model_name == "ridge":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            Ridge(alpha=config.ridge_alpha),
        )
    if model_name == "hist_gradient_boosting":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            HistGradientBoostingRegressor(
                learning_rate=config.gradient_learning_rate,
                max_iter=config.gradient_max_iter,
                max_leaf_nodes=config.gradient_max_leaf_nodes,
                l2_regularization=config.gradient_l2_regularization,
                random_state=config.random_seed,
            ),
        )
    raise MLForecastInputError(f"Unsupported ML model: {model_name}")


def _prior_value(
    lookup: dict[tuple[date, int, int], float],
    prior_day: date,
    slot: int,
    occurrence: int,
) -> float:
    value = lookup.get((prior_day, slot, occurrence))
    if value is None:
        value = lookup.get((prior_day, slot, 0))
    return float(value) if value is not None else np.nan


def _metric_ranking(metrics: dict[str, dict[str, object]]) -> list[dict[str, Any]]:
    ranked = sorted(
        metrics,
        key=lambda name: (
            metrics[name]["rmse_eur_per_mwh"] is None,
            float(metrics[name]["rmse_eur_per_mwh"] or np.inf),
        ),
    )
    return [
        {
            "rank": rank,
            "method": name,
            "rmse_eur_per_mwh": metrics[name]["rmse_eur_per_mwh"],
            "mae_eur_per_mwh": metrics[name]["mae_eur_per_mwh"],
            "coverage_fraction": metrics[name]["coverage_fraction"],
        }
        for rank, name in enumerate(ranked, start=1)
    ]
