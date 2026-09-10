"""The v0.9 fundamentals ablation: identical models, identical days, one extra feature set.

The question this module answers is narrow on purpose. Arm A is the accepted price-history
benchmark: the two existing model families on ``FEATURE_COLUMNS``. Arm B is the same two
families, the same fixed hyperparameters, the same seed, the same refit cadence and the same
walk-forward loop, with the accepted point-in-time feature columns appended. Nothing else
differs, so a difference in the result can only come from the information.

Three rules do most of the work here, and each exists because its absence would produce a
believable wrong number:

- **The feature set is identified, not described.** A benchmark declares the digest of the
  joined feature frame it fits on, and the join records the same digest. A mismatch is refused
  rather than reconciled, so a result can always be traced to one accepted feature table.
- **A missing feature excludes its day; it is never imputed.** The pipeline's imputer exists
  for the price-lag warm-up gaps and must not reach an exogenous column, so the walk-forward
  loop is told which columns must be complete wherever it reads them.
- **Both arms are judged on the same delivery days.** The evaluation set is the intersection
  of days complete for every baseline, for arm A and for arm B, and arm A is re-measured on
  that reduced calendar. A difference that came from a different calendar would not be an
  ablation result.

Nothing here selects on test metrics, and nothing here is a forecast of future value. The
summary records what was measured on one held-out period under one declared cutoff.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

import numpy as np
import pandas as pd
import sklearn

from ..data.decision_cutoff import validate_decision_lead_minutes
from ..data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    EVIDENCE_GRADES,
    VARIABLE_UNITS,
)
from .ml import (
    FEATURE_COLUMNS,
    FEATURE_PROVENANCE,
    MLForecastConfig,
    _walk_forward_predict,
    build_causal_feature_table,
)
from .naive import FORECAST_METHODS, calculate_forecast_metrics
from .point_in_time_join import frame_digest

#: Arm B's model names are arm A's with this suffix. The names are columns in the recorded
#: forecast table and keys in the recorded metrics, so they are part of the contract.
FUNDAMENTALS_ARM_SUFFIX = "_fundamentals"

#: The matched control's model names are the baseline's with this suffix. It trains on exactly
#: the rows the weather challenger is eligible for and reads only the price columns, so the
#: challenger-minus-matched-control difference is attributable to the weather columns alone.
MATCHED_CONTROL_SUFFIX = "_matched"

FUNDAMENTALS_FORECAST_BENCHMARK_LABEL = (
    "Leakage-safe walk-forward Greek DAM fundamentals ablation on one held-out period; "
    "research benchmark of price error, not expected investment revenue."
)

#: Appended to the label whenever a gate in the design's Section 19 downgrades the run.
EXPLORATORY_LABEL_SUFFIX = (
    " Exploratory: accepted-feature coverage does not support a general conclusion."
)

#: One sentence per exogenous variable, in the style of :data:`FEATURE_PROVENANCE`. A column
#: whose variable is absent here is refused: an unexplained model input is exactly what the
#: point-in-time contract exists to prevent. Keyed by variable, because a joined column is
#: either the variable name or ``variable__area`` when one variable carries several areas.
FUNDAMENTALS_FEATURE_PROVENANCE: dict[str, str] = {
    "dswrf_surface": (
        "Surface downward shortwave radiation at the declared sampling geography, from the "
        "decision-time forecast vintage published strictly before the declared cutoff, "
        "de-averaged from its bucket; evidence graded per delivery interval"
    ),
    "wind_speed_10m": (
        "Ten-metre wind speed at the declared sampling geography, from the decision-time "
        "forecast vintage published strictly before the declared cutoff, instantaneous at the "
        "forecast step; evidence graded per delivery interval"
    ),
    "temperature_2m": (
        "Two-metre temperature at the declared sampling geography, from the decision-time "
        "forecast vintage published strictly before the declared cutoff, instantaneous at the "
        "forecast step; evidence graded per delivery interval"
    ),
}

#: Meteorological seasons, as three whole calendar months. Winter is named for the year its
#: January falls in and begins in the December before it.
METEOROLOGICAL_SEASONS: dict[str, tuple[int, ...]] = {
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJA": (6, 7, 8),
    "SON": (9, 10, 11),
}

_QUARTER_HOUR_MINUTES = 15


class FundamentalsBenchmarkError(ValueError):
    """Raised when an ablation cannot be run exactly as declared."""


@dataclass(frozen=True)
class FundamentalsBenchmarkConfig:
    """Everything the ablation must declare rather than infer.

    The four point-in-time declarations are carried here as *assertions about the feature
    frame*, not as new choices: the benchmark refuses to run unless they equal what the join
    recorded. Declaring them twice is the point — a benchmark that silently adopted whatever
    cutoff its input happened to be built under could not be read without its input.
    """

    ml: MLForecastConfig
    feature_set_sha256: str
    decision_cutoff_schedule_id: str
    decision_lead_minutes: int
    evidence_grades_admitted: tuple[str, ...]
    price_regime_bands: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.ml, MLForecastConfig):
            raise FundamentalsBenchmarkError("ml must be an MLForecastConfig")
        digest = str(self.feature_set_sha256).strip().lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise FundamentalsBenchmarkError(
                "feature_set_sha256 must be a 64-character hexadecimal digest"
            )
        object.__setattr__(self, "feature_set_sha256", digest)
        schedule_id = str(self.decision_cutoff_schedule_id).strip()
        if not schedule_id:
            raise FundamentalsBenchmarkError("decision_cutoff_schedule_id must be declared")
        object.__setattr__(self, "decision_cutoff_schedule_id", schedule_id)
        object.__setattr__(
            self,
            "decision_lead_minutes",
            validate_decision_lead_minutes(self.decision_lead_minutes),
        )
        grades = tuple(dict.fromkeys(self.evidence_grades_admitted))
        if not grades:
            raise FundamentalsBenchmarkError("At least one evidence grade must be admitted")
        unknown = sorted(set(grades) - set(EVIDENCE_GRADES))
        if unknown:
            raise FundamentalsBenchmarkError(
                f"Unknown admitted evidence grades: {', '.join(unknown)}"
            )
        object.__setattr__(self, "evidence_grades_admitted", grades)
        bands = tuple(float(band) for band in self.price_regime_bands)
        if not bands:
            raise FundamentalsBenchmarkError(
                "price_regime_bands must be declared; the slice has no default because the "
                "bands are a judgment about which price levels are worth separating"
            )
        if any(not np.isfinite(band) for band in bands):
            raise FundamentalsBenchmarkError("price_regime_bands must all be finite")
        if any(later <= earlier for earlier, later in zip(bands, bands[1:], strict=False)):
            raise FundamentalsBenchmarkError(
                "price_regime_bands must be strictly ascending upper edges"
            )
        object.__setattr__(self, "price_regime_bands", bands)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ml": self.ml.to_dict(),
            "feature_set_sha256": self.feature_set_sha256,
            "decision_cutoff_schedule_id": self.decision_cutoff_schedule_id,
            "decision_lead_minutes": self.decision_lead_minutes,
            "evidence_grades_admitted": list(self.evidence_grades_admitted),
            "price_regime_bands": list(self.price_regime_bands),
        }


@dataclass(frozen=True)
class FundamentalsBenchmarkResult:
    """The two-arm forecast table and the summary that says what it establishes."""

    forecasts: pd.DataFrame
    summary: dict[str, Any]
    config: FundamentalsBenchmarkConfig


def generate_fundamentals_benchmark(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    join_summary: Mapping[str, Any],
    config: FundamentalsBenchmarkConfig,
) -> FundamentalsBenchmarkResult:
    """Run arm A and arm B over identical days and record both, with no test-set selection."""

    feature_columns = _validate_feature_inputs(features, join_summary, config)
    base = build_causal_feature_table(
        prices, rolling_window_days=config.ml.feature_window_days
    )
    table = _merge_features(base, features, feature_columns)

    available_days = sorted(table["market_day"].unique())
    if not available_days or available_days[-1] < config.ml.test_start_day:
        raise FundamentalsBenchmarkError("No held-out test days are available")
    validation_days = [
        day
        for day in available_days
        if config.ml.validation_start_day <= day < config.ml.test_start_day
    ]
    test_days = [day for day in available_days if day >= config.ml.test_start_day]
    if not validation_days:
        raise FundamentalsBenchmarkError("Validation period contains no market days")
    if not test_days:
        raise FundamentalsBenchmarkError("Test period contains no market days")
    target_days = validation_days + test_days

    feature_complete_days = _feature_complete_days(table, feature_columns)
    challenger_table = table.loc[table["market_day"].isin(feature_complete_days)]
    training_rows_dropped = int(len(table) - len(challenger_table))

    control_models = list(config.ml.models)
    matched_control_models = [f"{name}{MATCHED_CONTROL_SUFFIX}" for name in control_models]
    challenger_models = [f"{name}{FUNDAMENTALS_ARM_SUFFIX}" for name in control_models]
    evaluation = table.loc[table["market_day"].ge(config.ml.validation_start_day)].copy()
    evaluation["split"] = np.where(
        evaluation["market_day"].lt(config.ml.test_start_day), "validation", "test"
    )
    refit_logs: dict[str, list[dict[str, Any]]] = {}
    for model_name in control_models:
        control, control_log = _walk_forward_predict(
            table, target_days, model_name, config.ml, feature_columns=FEATURE_COLUMNS
        )
        evaluation[model_name] = evaluation["delivery_start_utc"].map(control)
        refit_logs[model_name] = control_log

        # The matched control: the challenger's training rows, the baseline's feature columns.
        # Without it, a challenger-minus-baseline difference confounds two changes at once —
        # the weather columns, and the training coverage lost by requiring them complete.
        matched_name = f"{model_name}{MATCHED_CONTROL_SUFFIX}"
        matched, matched_log = _walk_forward_predict(
            challenger_table,
            target_days,
            model_name,
            config.ml,
            feature_columns=FEATURE_COLUMNS,
        )
        evaluation[matched_name] = evaluation["delivery_start_utc"].map(matched)
        refit_logs[matched_name] = matched_log

        challenger_name = f"{model_name}{FUNDAMENTALS_ARM_SUFFIX}"
        challenger, challenger_log = _walk_forward_predict(
            challenger_table,
            target_days,
            model_name,
            config.ml,
            feature_columns=(*FEATURE_COLUMNS, *feature_columns),
            require_non_null=feature_columns,
        )
        evaluation[challenger_name] = evaluation["delivery_start_utc"].map(challenger)
        refit_logs[challenger_name] = challenger_log

    _refuse_unmatched_training(refit_logs, matched_control_models, challenger_models)

    methods = [*FORECAST_METHODS, *control_models, *matched_control_models, *challenger_models]
    common_days, excluded_days = _common_days(
        evaluation, methods, feature_complete_days, join_summary
    )
    if not common_days:
        raise FundamentalsBenchmarkError(
            "No evaluation day is complete for every baseline and both ablation arms"
        )
    evaluation["is_common_day"] = evaluation["market_day"].isin(common_days)
    common = evaluation.loc[evaluation["is_common_day"]]

    metrics = {
        split: calculate_forecast_metrics(
            common.loc[common["split"].eq(split)], methods=methods
        )
        for split in ("validation", "test")
    }
    control_metrics_all_days = {
        split: calculate_forecast_metrics(
            evaluation.loc[evaluation["split"].eq(split)],
            methods=[*FORECAST_METHODS, *control_models],
        )
        for split in ("validation", "test")
    }
    selected_control = _select_on_validation(metrics["validation"], control_models)
    selected_matched_control = _select_on_validation(
        metrics["validation"], matched_control_models
    )
    selected_challenger = _select_on_validation(metrics["validation"], challenger_models)

    common_test = common.loc[common["split"].eq("test")]
    quarter_hour_test_days = sorted(
        {
            day
            for day, frame in common_test.groupby("market_day", sort=True)
            if _resolution_minutes(frame) == _QUARTER_HOUR_MINUTES
        }
    )
    complete_seasons = _complete_meteorological_seasons(quarter_hour_test_days)
    exploratory_causes: list[str] = []
    if bool(join_summary.get("is_exploratory")):
        exploratory_causes.append("feature_join_recorded_exploratory")
    if ASSUMED in config.evidence_grades_admitted:
        exploratory_causes.append("quarantined_assumed_grade_admitted")
    if not complete_seasons:
        exploratory_causes.append("no_complete_meteorological_season_of_quarter_hour_test_days")
    is_exploratory = bool(exploratory_causes)

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
        "is_common_day",
        *methods,
    ]
    forecasts = evaluation.loc[:, output_columns].reset_index(drop=True)
    summary: dict[str, Any] = {
        "result_label": FUNDAMENTALS_FORECAST_BENCHMARK_LABEL
        + (EXPLORATORY_LABEL_SUFFIX if is_exploratory else ""),
        "ablation_arms": {
            "baselines": {
                "methods": list(FORECAST_METHODS),
                "feature_columns": [],
                "description": "Causal naïve forecasts from price history only",
            },
            "full_history_baseline": {
                "methods": control_models,
                "feature_columns": list(FEATURE_COLUMNS),
                "training_rows": "every day in the causal feature table",
                "description": (
                    "Calendar and price-history features only, trained on the full history. "
                    "Retained as a separately named baseline; its comparison with the matched "
                    "control measures the effect of reduced training coverage, not the value "
                    "of weather"
                ),
            },
            "matched_control": {
                "methods": matched_control_models,
                "feature_columns": list(FEATURE_COLUMNS),
                "training_rows": "exactly the days the challenger is eligible for",
                "description": (
                    "Calendar and price-history features only, trained on exactly the "
                    "challenger's eligible rows. This is the comparator that isolates the "
                    "weather columns: against it, only the feature columns differ"
                ),
            },
            "challenger": {
                "methods": challenger_models,
                "feature_columns": [*FEATURE_COLUMNS, *feature_columns],
                "training_rows": "exactly the days with complete accepted features",
                "description": (
                    "The baseline features plus the accepted point-in-time exogenous columns; "
                    "identical models, hyperparameters, seed, cadence and days"
                ),
            },
            "attribution": (
                "challenger minus matched_control is attributable to the weather columns; "
                "matched_control minus full_history_baseline is attributable to training "
                "coverage. The challenger-minus-baseline difference confounds the two and is "
                "not reported as a weather effect"
            ),
        },
        "feature_set_sha256": config.feature_set_sha256,
        "fundamentals_feature_columns": list(feature_columns),
        "fundamentals_feature_provenance": _provenance(feature_columns),
        "price_history_feature_provenance": FEATURE_PROVENANCE,
        "decision_cutoff_schedule_id": config.decision_cutoff_schedule_id,
        "decision_lead_minutes": config.decision_lead_minutes,
        "evidence_grades_admitted": list(config.evidence_grades_admitted),
        "common_day_count": len(common_days),
        "common_interval_count": int(len(common)),
        "common_validation_day_count": int(
            common.loc[common["split"].eq("validation"), "market_day"].nunique()
        ),
        "common_test_day_count": int(common_test["market_day"].nunique()),
        "first_common_day": str(min(common_days)),
        "last_common_day": str(max(common_days)),
        "evaluation_day_count": len(validation_days) + len(test_days),
        "excluded_days_by_cause": _cause_counts(excluded_days),
        "excluded_days": excluded_days,
        "challenger_training_intervals_dropped": training_rows_dropped,
        "metrics": metrics,
        "control_metrics_on_all_evaluation_days": control_metrics_all_days,
        "metrics_by_slice": _slice_metrics(common_test, methods, config.price_regime_bands),
        "sliced_split": "test",
        "price_regime_bands": list(config.price_regime_bands),
        "selected_control": selected_control,
        "selected_matched_control": selected_matched_control,
        "selected_challenger": selected_challenger,
        "model_selection_policy": (
            "Lowest validation RMSE on the common days; test metrics are not used for "
            "selection, and the feature set, split and cutoff are never revised after a test "
            "run"
        ),
        "validation_start_day": str(config.ml.validation_start_day),
        "test_start_day": str(config.ml.test_start_day),
        "training_start_day": str(min(available_days)),
        "last_test_day": str(max(test_days)),
        "quarter_hour_common_test_day_count": len(quarter_hour_test_days),
        "complete_meteorological_seasons_in_common_test_days": complete_seasons,
        "is_exploratory": is_exploratory,
        "exploratory_causes": exploratory_causes,
        "refit_logs": refit_logs,
        "config": config.to_dict(),
        "scikit_learn_version": sklearn.__version__,
        "establishes_only_price_error": True,
        "is_probabilistic": False,
        "is_forecast": False,
        "is_investment_evidence": False,
        "data_policy": (
            "Price-derived features use prior market days only; every exogenous value was "
            "published strictly before the declared decision cutoff for its delivery day; a "
            "delivery day missing any accepted feature is excluded from every arm and is "
            "never imputed"
        ),
    }
    return FundamentalsBenchmarkResult(
        forecasts=forecasts, summary=summary, config=config
    )


def _validate_feature_inputs(
    features: pd.DataFrame,
    join_summary: Mapping[str, Any],
    config: FundamentalsBenchmarkConfig,
) -> tuple[str, ...]:
    """Refuse any input the benchmark could otherwise silently reinterpret."""

    if not isinstance(join_summary, Mapping):
        raise FundamentalsBenchmarkError("The feature summary must be an object")
    recorded_digest = join_summary.get("feature_set_sha256")
    if not recorded_digest:
        raise FundamentalsBenchmarkError(
            "The feature summary declares no feature_set_sha256; a benchmark may not name a "
            "feature set its input does not identify"
        )
    if "delivery_start_utc" not in features.columns:
        raise FundamentalsBenchmarkError("Feature frame is missing delivery_start_utc")
    actual_digest = frame_digest(features)
    if actual_digest != str(recorded_digest):
        raise FundamentalsBenchmarkError(
            f"Feature frame digest {actual_digest} does not match the {recorded_digest} its "
            "summary records; the frame and the summary describe different feature sets"
        )
    if config.feature_set_sha256 != actual_digest:
        raise FundamentalsBenchmarkError(
            f"The benchmark declares feature set {config.feature_set_sha256}, but the frame "
            f"supplied is {actual_digest}"
        )
    for field, recorded_key in (
        ("decision_cutoff_schedule_id", "schedule_id"),
        ("decision_lead_minutes", "decision_lead_minutes"),
    ):
        declared = getattr(config, field)
        recorded = join_summary.get(recorded_key)
        if recorded != declared:
            raise FundamentalsBenchmarkError(
                f"The benchmark declares {field}={declared!r}, but the feature set was built "
                f"under {recorded!r}"
            )
    recorded_grades = tuple(join_summary.get("admitted_grades") or ())
    if recorded_grades != config.evidence_grades_admitted:
        raise FundamentalsBenchmarkError(
            f"The benchmark admits evidence grades {list(config.evidence_grades_admitted)}, "
            f"but the feature set was built admitting {list(recorded_grades)}"
        )
    if ASSUMED in config.evidence_grades_admitted and not join_summary.get("is_exploratory"):
        raise FundamentalsBenchmarkError(
            "The quarantined assumed grade is admitted but the feature set is not recorded "
            "as exploratory"
        )
    forbidden = sorted(
        set(config.evidence_grades_admitted) - set(ADMISSIBLE_EVIDENCE_GRADES) - {ASSUMED}
    )
    if forbidden:
        raise FundamentalsBenchmarkError(
            f"Evidence grades cannot be admitted: {', '.join(forbidden)}"
        )

    recorded_columns = tuple(join_summary.get("feature_columns") or ())
    frame_columns = tuple(name for name in features.columns if name != "delivery_start_utc")
    if recorded_columns != frame_columns:
        raise FundamentalsBenchmarkError(
            f"Feature frame carries columns {list(frame_columns)} but its summary records "
            f"{list(recorded_columns)}"
        )
    if not frame_columns:
        raise FundamentalsBenchmarkError("The feature frame carries no feature columns")
    collisions = sorted(set(frame_columns) & set(FEATURE_COLUMNS))
    if collisions:
        raise FundamentalsBenchmarkError(
            f"Exogenous columns collide with price-history features: {', '.join(collisions)}"
        )
    unexplained = sorted(
        name for name in frame_columns if _variable_of(name) not in FUNDAMENTALS_FEATURE_PROVENANCE
    )
    if unexplained:
        raise FundamentalsBenchmarkError(
            f"No recorded provenance for feature columns: {', '.join(unexplained)}"
        )
    return frame_columns


def _merge_features(
    base: pd.DataFrame, features: pd.DataFrame, feature_columns: tuple[str, ...]
) -> pd.DataFrame:
    """Attach the joined feature columns to the causal price-feature table by interval."""

    keyed = features.loc[:, ["delivery_start_utc", *feature_columns]].copy()
    keyed["delivery_start_utc"] = pd.to_datetime(keyed["delivery_start_utc"], utc=True)
    if keyed["delivery_start_utc"].duplicated().any():
        raise FundamentalsBenchmarkError(
            "The feature frame carries more than one row for a delivery interval"
        )
    if set(keyed["delivery_start_utc"]) != set(base["delivery_start_utc"]):
        raise FundamentalsBenchmarkError(
            "The feature frame and the price history cover different delivery intervals; a "
            "benchmark may not join a feature set built from other prices"
        )
    merged = base.merge(keyed, on="delivery_start_utc", how="left", validate="one_to_one")
    for name in feature_columns:
        merged[name] = pd.to_numeric(merged[name], errors="coerce")
    return merged


def _feature_complete_days(
    table: pd.DataFrame, feature_columns: tuple[str, ...]
) -> list[date]:
    """Return the days on which every exogenous column is present for every interval."""

    present = table.loc[:, list(feature_columns)].notna().all(axis=1)
    complete: list[date] = []
    for market_day, day_rows in present.groupby(table["market_day"], sort=True):
        if bool(day_rows.all()):
            complete.append(cast(date, market_day))
        elif bool(day_rows.any()):
            raise FundamentalsBenchmarkError(
                f"Delivery day {market_day} carries features for some intervals and not "
                "others; the join excludes a day whole or not at all"
            )
    return complete


def _common_days(
    evaluation: pd.DataFrame,
    methods: Sequence[str],
    feature_complete_days: Sequence[date],
    join_summary: Mapping[str, Any],
) -> tuple[list[date], list[dict[str, Any]]]:
    """Intersect the days every baseline and both arms can be measured on."""

    feature_causes = _feature_exclusion_causes(join_summary)
    complete = set(feature_complete_days)
    common: list[date] = []
    excluded: list[dict[str, Any]] = []
    for market_day, day in evaluation.groupby("market_day", sort=True):
        missing = {
            method: int(day[method].isna().sum())
            for method in methods
            if bool(day[method].isna().any())
        }
        if market_day not in complete:
            excluded.append(
                {
                    "market_day": str(market_day),
                    "split": str(day["split"].iloc[0]),
                    "interval_count": int(len(day)),
                    "cause": feature_causes.get(
                        cast(date, market_day), "feature_unavailable"
                    ),
                    "missing_forecast_intervals_by_method": missing,
                }
            )
        elif missing:
            excluded.append(
                {
                    "market_day": str(market_day),
                    "split": str(day["split"].iloc[0]),
                    "interval_count": int(len(day)),
                    "cause": "incomplete_forecast_coverage",
                    "missing_forecast_intervals_by_method": missing,
                }
            )
        else:
            common.append(cast(date, market_day))
    return common, excluded


def _feature_exclusion_causes(join_summary: Mapping[str, Any]) -> dict[date, str]:
    """Carry the join's own named cause per excluded day rather than restating it."""

    causes: dict[date, str] = {}
    for record in join_summary.get("delivery_days") or ():
        if not isinstance(record, Mapping) or record.get("status") == "complete":
            continue
        try:
            market_day = date.fromisoformat(str(record.get("market_day")))
        except ValueError:
            continue
        reasons = record.get("reasons") or ()
        named = sorted(
            {
                str(reason.get("cause"))
                for reason in reasons
                if isinstance(reason, Mapping) and reason.get("cause")
            }
        )
        causes[market_day] = (
            "feature_" + "_and_".join(named) if named else "feature_unavailable"
        )
    return causes


def _cause_counts(excluded_days: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in excluded_days:
        cause = str(record["cause"])
        counts[cause] = counts.get(cause, 0) + 1
    return dict(sorted(counts.items()))


def _refuse_unmatched_training(
    refit_logs: dict[str, list[dict[str, Any]]],
    matched_control_models: Sequence[str],
    challenger_models: Sequence[str],
) -> None:
    """Refuse unless each matched pair refit on identical rows with identical targets.

    The matched control exists so that one comparison varies only the feature columns. That is
    a claim about which rows each arm was fitted on, and a claim is worth no more than its
    check: the two arms record a digest of their training row identities and of their targets
    at every refit, and this refuses the run unless every pair agrees on both.

    Without it, a later change to how either arm selects rows would silently reintroduce the
    confound the matched control was added to remove, and the recorded comparison would go on
    describing itself as attributable to weather.
    """

    for matched_name, challenger_name in zip(
        matched_control_models, challenger_models, strict=True
    ):
        matched_log = refit_logs[matched_name]
        challenger_log = refit_logs[challenger_name]
        if len(matched_log) != len(challenger_log):
            raise FundamentalsBenchmarkError(
                f"{matched_name} refit {len(matched_log)} times and {challenger_name} "
                f"{len(challenger_log)} times; a matched pair refits on the same cadence"
            )
        for matched_entry, challenger_entry in zip(
            matched_log, challenger_log, strict=True
        ):
            day = matched_entry["forecast_start_day"]
            for field in ("training_row_digest", "training_target_digest"):
                if matched_entry[field] != challenger_entry[field]:
                    raise FundamentalsBenchmarkError(
                        f"{matched_name} and {challenger_name} disagree on {field} at the "
                        f"refit for {day}. A matched pair must differ only in the feature "
                        "columns it reads; differing training rows would make the comparison "
                        "a measurement of training coverage rather than of the weather columns"
                    )


def _select_on_validation(
    validation_metrics: Mapping[str, Mapping[str, Any]], models: Sequence[str]
) -> str:
    """Pick within an arm on validation RMSE alone, exactly as the accepted benchmark does."""

    def rmse(name: str) -> float:
        value = validation_metrics[name]["rmse_eur_per_mwh"]
        return float("inf") if value is None else float(cast(Any, value))

    return min(models, key=rmse)


def _resolution_minutes(day: pd.DataFrame) -> int | None:
    minutes = {int(round(float(hours) * 60)) for hours in day["duration_hours"]}
    return minutes.pop() if len(minutes) == 1 else None


def _complete_meteorological_seasons(days: Sequence[date]) -> list[str]:
    """Name every meteorological season the given days cover in full.

    Gate G4 asks for "one full meteorological season of quarter-hour delivery days" before a
    result may be labelled anything but exploratory. A season is counted only when *every* one
    of its calendar days is present: a threshold below that would be a judgmental default, and
    the project's convention is to err toward the exploratory label rather than invent one.
    """

    present = set(days)
    if not present:
        return []
    complete: list[str] = []
    candidates = {
        (day.year + 1 if day.month == 12 else day.year, name)
        for day in present
        for name, months in METEOROLOGICAL_SEASONS.items()
        if day.month in months
    }
    for year, name in sorted(candidates):
        if present.issuperset(_season_days(year, name)):
            complete.append(f"{year}-{name}")
    return complete


def _season_days(year: int, name: str) -> set[date]:
    days: set[date] = set()
    for month in METEOROLOGICAL_SEASONS[name]:
        month_year = year - 1 if name == "DJF" and month == 12 else year
        length = calendar.monthrange(month_year, month)[1]
        days.update(date(month_year, month, day) for day in range(1, length + 1))
    return days


def _slice_metrics(
    common_test: pd.DataFrame, methods: Sequence[str], bands: Sequence[float]
) -> dict[str, dict[str, dict[str, dict[str, object]]]]:
    """Report the same metrics on the declared slices of the held-out common days.

    The slices exist because one aggregate number cannot say where a difference sat. None of
    them selects anything: they are reported after the fact, on the test split, and the model
    choice was already made on validation.
    """

    if common_test.empty:
        return {}
    sliced = common_test.copy()
    sliced["_delivery_year"] = [str(day.year) for day in sliced["market_day"]]
    sliced["_interval_of_day"] = [
        f"{int(minutes) // 60:02d}:{int(minutes) % 60:02d}"
        for minutes in sliced["market_slot_minutes"]
    ]
    sliced["_resolution_era"] = [
        _era_name(int(round(float(hours) * 60))) for hours in sliced["duration_hours"]
    ]
    sliced["_price_regime"] = _regime_labels(
        sliced["actual_price_eur_per_mwh"].to_numpy(dtype=float), bands
    )
    return {
        slice_name: {
            str(key): calculate_forecast_metrics(group, methods=list(methods))
            for key, group in sliced.groupby(column, sort=True)
        }
        for slice_name, column in (
            ("delivery_year", "_delivery_year"),
            ("interval_of_day", "_interval_of_day"),
            ("price_regime", "_price_regime"),
            ("resolution_era", "_resolution_era"),
        )
    }


def _era_name(minutes: int) -> str:
    if minutes == 60:
        return "hourly"
    if minutes == _QUARTER_HOUR_MINUTES:
        return "quarter_hour"
    return f"{minutes}_minute"


def _regime_labels(values: np.ndarray, bands: Sequence[float]) -> list[str]:
    edges = list(bands)
    names = [f"<= {edges[0]:g}"]
    names.extend(f"({lower:g}, {upper:g}]" for lower, upper in zip(edges, edges[1:], strict=False))
    names.append(f"> {edges[-1]:g}")
    positions = np.searchsorted(np.asarray(edges, dtype=float), values, side="left")
    return [names[int(position)] for position in positions]


def _provenance(feature_columns: Sequence[str]) -> dict[str, str]:
    return {
        name: FUNDAMENTALS_FEATURE_PROVENANCE[_variable_of(name)] for name in feature_columns
    }


def _variable_of(column: str) -> str:
    """A joined column is the variable name, or ``variable__area`` when areas disambiguate."""

    return column.split("__", 1)[0]


#: Named so a reader of this module sees the closed variable registry the provenance map must
#: cover, without opening the data layer to find out whether a variable is missing a sentence.
DOCUMENTED_FEATURE_VARIABLES = tuple(sorted(VARIABLE_UNITS))
