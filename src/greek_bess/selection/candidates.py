"""The declared candidate grid for the Stage 9 selection experiment.

A candidate is a name, a model family and the hyperparameter values that distinguish it from
its siblings. The grid is declared here, in a fixed order, for two reasons that are part of the
protocol rather than conveniences:

- **The declared order is the tie-break.** When two candidates score within tolerance of the
  best value, the one declared first wins. Fixing that order in source, before any price is
  read, is what makes a tie reproducible instead of dependent on dictionary ordering or on
  whichever candidate a sort happened to visit first.
- **The grid is the same for both objectives.** Stage 9 asks which of two selection rules picks
  better from one set of options. Offering the rules different options would answer a different
  question, so the grid is built once and both rules read it.

Every candidate differs from the others only in how it fits. The schedule, the feature table
and the seed come from one shared :class:`~greek_bess.forecast.ml.MLForecastConfig` and are
refused as overrides, so two candidates cannot silently differ in what they were allowed to
see. A candidate may vary the fitting cadence and training window alongside its model
hyperparameters, because those change how the model learns from the visible past rather than
how much of the past is visible.

The design of record is ``docs/value_based_selection_design.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical
from ..forecast.ml import (
    ML_MODELS,
    MLForecastConfig,
    MLForecastInputError,
    _walk_forward_predict,
    build_causal_feature_table,
)

#: Fields a candidate may not override. The first three fix the experiment's schedule and the
#: family under test, and a candidate that moved them would not be comparable with its
#: siblings. ``random_seed`` is excluded because a candidate that differed only by seed would
#: measure fitting noise and present it as a configuration choice. ``feature_window_days`` is
#: excluded so that every candidate reads a byte-identical feature table: it is a defensible
#: thing to tune, but tuning it here would mean the two selection rules were choosing between
#: options that differed in their inputs as well as their models, and the point of this
#: experiment is that the model is the only thing that varies.
PROTECTED_CONFIG_FIELDS = (
    "validation_start_day",
    "test_start_day",
    "models",
    "random_seed",
    "feature_window_days",
)

#: The columns a candidate forecast table carries beside one column per candidate.
FORECAST_INDEX_COLUMNS = (
    "delivery_start_utc",
    "delivery_start_market",
    "market_day",
    "market_slot_minutes",
    "slot_occurrence",
    "duration_hours",
    "source",
    "actual_price_eur_per_mwh",
    "split",
)


class SelectionCandidateError(ValueError):
    """Raised when a candidate grid is not a like-for-like set of options."""


@dataclass(frozen=True)
class SelectionCandidate:
    """One named forecast configuration offered to both selection rules."""

    name: str
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise SelectionCandidateError("A candidate requires a non-empty name")
        if self.model not in ML_MODELS:
            raise SelectionCandidateError(
                f"Unsupported candidate model {self.model!r}; expected one of {list(ML_MODELS)}"
            )
        known = set(MLForecastConfig.__dataclass_fields__)
        unknown = sorted(set(self.settings) - known)
        if unknown:
            raise SelectionCandidateError(
                f"Candidate {self.name!r} sets unknown configuration fields: {unknown}"
            )
        protected = sorted(set(self.settings) & set(PROTECTED_CONFIG_FIELDS))
        if protected:
            raise SelectionCandidateError(
                f"Candidate {self.name!r} may not override {protected}: the schedule, the "
                "family under test and the seed are shared by every candidate"
            )
        object.__setattr__(self, "settings", dict(self.settings))

    def config(self, base: MLForecastConfig) -> MLForecastConfig:
        """The shared schedule with this candidate's family and hyperparameters applied."""

        return replace(base, models=(self.model,), **dict(self.settings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "settings": dict(self.settings),
        }


#: The grid Stage 9 declares. Both families already in ``ML_MODELS`` are represented, and no
#: family is added: Stage 9 tests a selection rule, and adding models is not what it measures.
#: Three configurations per family span a regularization or capacity range wide enough that the
#: candidates are genuinely different options rather than restatements of one.
DECLARED_CANDIDATES: tuple[SelectionCandidate, ...] = (
    SelectionCandidate("ridge_alpha_1", "ridge", {"ridge_alpha": 1.0}),
    SelectionCandidate("ridge_alpha_10", "ridge", {"ridge_alpha": 10.0}),
    SelectionCandidate("ridge_alpha_100", "ridge", {"ridge_alpha": 100.0}),
    SelectionCandidate(
        "gradient_lr_005_leaf_15",
        "hist_gradient_boosting",
        {"gradient_learning_rate": 0.05, "gradient_max_leaf_nodes": 15},
    ),
    SelectionCandidate(
        "gradient_lr_010_leaf_31",
        "hist_gradient_boosting",
        {"gradient_learning_rate": 0.10, "gradient_max_leaf_nodes": 31},
    ),
    SelectionCandidate(
        "gradient_lr_020_leaf_7",
        "hist_gradient_boosting",
        {"gradient_learning_rate": 0.20, "gradient_max_leaf_nodes": 7},
    ),
)


def validate_candidates(
    candidates: Sequence[SelectionCandidate],
) -> tuple[SelectionCandidate, ...]:
    """Refuse a grid that could not support a like-for-like comparison."""

    if len(candidates) < 2:
        raise SelectionCandidateError(
            "A selection comparison requires at least two candidates; one candidate is not a "
            "choice, and both rules would select it"
        )
    names = [candidate.name for candidate in candidates]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise SelectionCandidateError(f"Candidate names must be unique; repeated: {duplicates}")
    reserved = sorted(set(names) & set(FORECAST_INDEX_COLUMNS))
    if reserved:
        raise SelectionCandidateError(
            f"Candidate names collide with forecast table columns: {reserved}"
        )
    return tuple(candidates)


def generate_candidate_forecasts(
    prices: pd.DataFrame,
    base_config: MLForecastConfig,
    candidates: Sequence[SelectionCandidate] = DECLARED_CANDIDATES,
) -> pd.DataFrame:
    """Predict every candidate walk-forward over the validation and evaluation windows.

    One feature table is built and shared by every candidate, so two candidates read
    byte-identical features and differ only in how they fit them. Every fit reads prior market
    days only: this is the existing ``_walk_forward_predict`` loop, called once per candidate
    with that candidate's configuration and nothing else changed.
    """

    grid = validate_candidates(candidates)
    data = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(data, require_complete_days=True)
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise MLForecastInputError(f"Price data failed ML quality checks: {errors}")

    # One table, built once, read by every candidate. ``feature_window_days`` is protected, so
    # there is exactly one window in the grid and no candidate can acquire different inputs.
    feature_table = build_causal_feature_table(
        data, rolling_window_days=base_config.feature_window_days
    )
    available_days = sorted(feature_table["market_day"].unique())
    validation_days, evaluation_days = _split_days(available_days, base_config)

    scored = feature_table.loc[
        feature_table["market_day"].ge(base_config.validation_start_day)
    ].copy()
    scored["split"] = np.where(
        scored["market_day"].lt(base_config.test_start_day), "validation", "evaluation"
    )
    target_days = [*validation_days, *evaluation_days]
    for candidate in grid:
        config = candidate.config(base_config)
        predictions, _ = _walk_forward_predict(
            feature_table, target_days, candidate.model, config
        )
        scored[candidate.name] = scored["delivery_start_utc"].map(predictions)

    columns = [*FORECAST_INDEX_COLUMNS, *(candidate.name for candidate in grid)]
    return scored.loc[:, columns].reset_index(drop=True)


def _split_days(
    available_days: Sequence[date], config: MLForecastConfig
) -> tuple[list[date], list[date]]:
    """The validation and evaluation calendars, refusing a schedule with an empty window."""

    if not available_days:
        raise MLForecastInputError("The price history contains no market days")
    validation_days = [
        day
        for day in available_days
        if config.validation_start_day <= day < config.test_start_day
    ]
    evaluation_days = [day for day in available_days if day >= config.test_start_day]
    if not validation_days:
        raise MLForecastInputError(
            "The validation window contains no market days, so nothing could select"
        )
    if not evaluation_days:
        raise MLForecastInputError(
            "The evaluation window contains no market days, so nothing could be scored"
        )
    return validation_days, evaluation_days
