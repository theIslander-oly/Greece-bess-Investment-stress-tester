"""Stage 9: compare selecting a forecast by price error against selecting it by battery value.

``forecast/ml.py`` picks the model it reports by one rule — lowest validation RMSE — and says
so in its own summary. RMSE is a price-error objective, and this project's object is a battery,
which earns from the ordering and spread of prices inside a delivery day rather than from the
level of the price that was predicted. The two quantities are not the same, and this repository
has already recorded a case where they disagree: ``rolling_mean`` has a worse RMSE than
``ridge`` and captures more value.

This module runs the experiment that turns that observation into evidence. Both rules are
offered the same candidates, scored on the same validation days, under one battery
configuration; each picks one candidate; both picks are then settled on evaluation days that
neither rule was allowed to see.

The discipline around that, rather than the arithmetic, is what this module is for:

- **Selection cannot see the evaluation window.** The frozen record is built from validation
  quantities alone and hashed before any evaluation day is settled, and the evaluation step
  takes it as an immutable argument. A selection revised after seeing an evaluation number
  would not reproduce its own ``frozen_selection_sha256``.
- **Ties break deterministically and visibly.** Objective values are compared against the best
  with a declared absolute tolerance; every candidate inside it is tied, and the tied candidate
  declared first wins. The tie and its members are recorded, because a tie broken silently is a
  selection nobody can reproduce.
- **The comparison basis is asserted, not assumed.** One battery configuration plans and
  settles every candidate, and the perfect-foresight ceiling is asserted identical across
  candidates to a tolerance. The assertion is written into the summary as ``equivalent_basis``.
- **The headline difference is computed here.** A renderer must not subtract one reported
  margin from another; the difference is a result, and results are computed by the module that
  owns the basis.

Nothing here prefers an outcome. The signed difference is recorded whatever its sign, and the
retrospective best candidate is recorded as a diagnostic ceiling that no pre-committed rule
could be expected to reach.

The design of record is ``docs/value_based_selection_design.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd

from ..backtest.forecast_dispatch import ForecastDispatchInputError
from ..backtest.ml_dispatch import _backtest_precomputed_forecast
from ..dispatch import BatteryDispatchConfig
from ..forecast import calculate_forecast_metrics
from .candidates import (
    DECLARED_CANDIDATES,
    SelectionCandidate,
    validate_candidates,
)

VALUE_SELECTION_RESULT_LABEL = (
    "Held-out comparison of validation-RMSE against validation-settled-margin model selection, "
    "settled at realized Greek DAM prices; historical research result, not expected investment "
    "revenue."
)

#: The two objectives, each as a name, the column it scores and the direction that wins.
RMSE_OBJECTIVE = "validation_rmse"
MARGIN_OBJECTIVE = "validation_settled_margin"
SELECTION_OBJECTIVES = (RMSE_OBJECTIVE, MARGIN_OBJECTIVE)

#: Absolute tie tolerances, declared per objective because the two are measured in different
#: units. Anything inside the tolerance is a tie rather than a win, and ties resolve to the
#: candidate declared first.
RMSE_TIE_TOLERANCE_EUR_PER_MWH = 1e-9
MARGIN_TIE_TOLERANCE_EUR = 1e-6

#: Tolerance on the assertion that every candidate faced the same perfect-foresight ceiling.
#: It is the tolerance ``ml_dispatch`` and ``fundamentals_dispatch`` already apply to the same
#: assertion, and it is absolute: the ceiling is a sum of euro amounts from identical inputs,
#: so anything above solver noise is a defect rather than a rounding difference.
CEILING_TOLERANCE_EUR = 1e-6

#: Evidence classes a caller may declare for the evaluation window. A window this repository
#: has already inspected supports supplementary evidence only; a confirmatory claim needs a
#: window predeclared untouched, or a prospective one.
RETROSPECTIVE_EVIDENCE = "retrospective_supplementary"
PREDECLARED_EVIDENCE = "predeclared_untouched"
EVIDENCE_CLASSES = (RETROSPECTIVE_EVIDENCE, PREDECLARED_EVIDENCE)


class ValueSelectionInputError(ForecastDispatchInputError):
    """Raised when a selection comparison would not be like for like."""


@dataclass(frozen=True)
class ValueSelectionResult:
    """The scoreboard, the frozen selection, the settled evaluation and the summary."""

    validation_scoreboard: pd.DataFrame
    evaluation_scoreboard: pd.DataFrame
    frozen_selection: dict[str, Any]
    objective_results: dict[str, dict[str, Any]]
    summary: dict[str, Any]


def compare_selection_objectives(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    forecasts: pd.DataFrame,
    *,
    candidates: Sequence[SelectionCandidate] = DECLARED_CANDIDATES,
    evidence_class: str = RETROSPECTIVE_EVIDENCE,
) -> ValueSelectionResult:
    """Score every candidate on validation, freeze one pick per objective, then evaluate.

    ``forecasts`` is a candidate forecast table from
    :func:`~greek_bess.selection.candidates.generate_candidate_forecasts`: one column per
    candidate, and a ``split`` column separating ``validation`` from ``evaluation`` rows.
    """

    grid = validate_candidates(candidates)
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueSelectionInputError(
            f"Unknown evidence_class {evidence_class!r}; expected one of {list(EVIDENCE_CLASSES)}"
        )
    validation_rows, evaluation_rows = _split_rows(forecasts, grid)

    # Step 1 — score on validation days only. Nothing below this line has read an evaluation
    # price, and the scoreboard is the only input the selection rules are given.
    validation_scoreboard = _score_candidates(
        prices, config, validation_rows, grid, split="validation"
    )
    _assert_equivalent_basis(validation_scoreboard, split="validation")

    # Step 2 — select, and freeze. The digest is taken here, before any evaluation settlement.
    selections = {
        RMSE_OBJECTIVE: _select(
            validation_scoreboard,
            grid,
            column="rmse_eur_per_mwh",
            maximize=False,
            tolerance=RMSE_TIE_TOLERANCE_EUR_PER_MWH,
        ),
        MARGIN_OBJECTIVE: _select(
            validation_scoreboard,
            grid,
            column="realized_margin_eur",
            maximize=True,
            tolerance=MARGIN_TIE_TOLERANCE_EUR,
        ),
    }
    frozen_selection = _freeze(selections, validation_scoreboard, forecasts)

    # Step 3 — settle the evaluation window. Every candidate is settled, not only the two
    # selected, because the retrospective best candidate is a reported diagnostic. That is safe
    # only because the selection above is already frozen and hashed.
    evaluation_scoreboard = _score_candidates(
        prices, config, evaluation_rows, grid, split="evaluation"
    )
    _assert_equivalent_basis(evaluation_scoreboard, split="evaluation")

    objective_results = _evaluate_frozen_selection(
        frozen_selection, evaluation_scoreboard, config
    )
    summary = _summarize(
        frozen_selection=frozen_selection,
        objective_results=objective_results,
        validation_scoreboard=validation_scoreboard,
        evaluation_scoreboard=evaluation_scoreboard,
        grid=grid,
        config=config,
        evidence_class=evidence_class,
        forecast_digest=_forecast_digest(forecasts, grid),
    )
    return ValueSelectionResult(
        validation_scoreboard=validation_scoreboard,
        evaluation_scoreboard=evaluation_scoreboard,
        frozen_selection=frozen_selection,
        objective_results=objective_results,
        summary=summary,
    )


def _split_rows(
    forecasts: pd.DataFrame, grid: Sequence[SelectionCandidate]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The validation and evaluation rows, refusing a table that cannot support the comparison."""

    required = {"split", "market_day", "delivery_start_utc", "actual_price_eur_per_mwh"}
    missing = sorted(required - set(forecasts.columns))
    if missing:
        raise ValueSelectionInputError(
            f"Candidate forecast table is missing required columns: {missing}"
        )
    absent = sorted(
        candidate.name for candidate in grid if candidate.name not in forecasts.columns
    )
    if absent:
        raise ValueSelectionInputError(
            f"Candidate forecast table is missing candidate columns: {absent}"
        )
    unknown_splits = sorted(set(forecasts["split"].unique()) - {"validation", "evaluation"})
    if unknown_splits:
        raise ValueSelectionInputError(
            f"Candidate forecast table carries unknown splits: {unknown_splits}"
        )
    validation_rows = forecasts.loc[forecasts["split"].eq("validation")].copy()
    evaluation_rows = forecasts.loc[forecasts["split"].eq("evaluation")].copy()
    if validation_rows.empty:
        raise ValueSelectionInputError("The validation split is empty, so nothing could select")
    if evaluation_rows.empty:
        raise ValueSelectionInputError(
            "The evaluation split is empty, so nothing could be scored"
        )
    overlap = sorted(
        set(validation_rows["market_day"]) & set(evaluation_rows["market_day"])
    )
    if overlap:
        raise ValueSelectionInputError(
            f"Validation and evaluation windows share market days: {overlap[:5]}"
        )
    if max(validation_rows["market_day"]) >= min(evaluation_rows["market_day"]):
        raise ValueSelectionInputError(
            "Every validation day must precede every evaluation day; selection may not read "
            "days that follow the window it is frozen for"
        )
    return validation_rows, evaluation_rows


def _score_candidates(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    rows: pd.DataFrame,
    grid: Sequence[SelectionCandidate],
    *,
    split: str,
) -> pd.DataFrame:
    """Settle every candidate over one window and record value and error side by side."""

    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(grid):
        if rows[candidate.name].isna().any():
            missing = int(rows[candidate.name].isna().sum())
            raise ValueSelectionInputError(
                f"Candidate {candidate.name!r} has {missing} missing {split} forecast "
                "intervals; excluding them would give candidates different calendars"
            )
        settled = _backtest_precomputed_forecast(
            prices, config, rows, method=candidate.name
        )
        summary = settled.summary
        metrics = calculate_forecast_metrics(rows, methods=[candidate.name])[candidate.name]
        realized = float(summary["realized_margin_eur"])
        perfect = float(summary["perfect_foresight_margin_eur"])
        discharge = float(summary["grid_discharge_mwh"])
        records.append(
            {
                "declared_index": index,
                "candidate": candidate.name,
                "model": candidate.model,
                "split": split,
                "day_count": int(summary["backtested_day_count"]),
                "interval_count": int(summary["backtested_interval_count"]),
                "rmse_eur_per_mwh": float(cast(Any, metrics["rmse_eur_per_mwh"])),
                "mae_eur_per_mwh": float(cast(Any, metrics["mae_eur_per_mwh"])),
                "realized_margin_eur": realized,
                "market_cash_margin_eur": float(summary["market_cash_margin_eur"]),
                "perfect_foresight_margin_eur": perfect,
                "perfect_foresight_regret_eur": perfect - realized,
                "perfect_foresight_capture_ratio": (
                    realized / perfect if perfect > 1e-9 else None
                ),
                "grid_charge_mwh": float(summary["grid_charge_mwh"]),
                "grid_discharge_mwh": discharge,
                "equivalent_full_cycles": discharge / config.energy_capacity_mwh,
            }
        )
    return pd.DataFrame.from_records(records)


def _assert_equivalent_basis(scoreboard: pd.DataFrame, *, split: str) -> None:
    """Every candidate must have faced the same ceiling on the same days."""

    ceilings = scoreboard["perfect_foresight_margin_eur"].to_numpy(dtype=float)
    spread = float(np.max(ceilings) - np.min(ceilings))
    if spread > CEILING_TOLERANCE_EUR:
        raise ValueSelectionInputError(
            f"Candidates faced different perfect-foresight ceilings on the {split} window "
            f"(spread EUR {spread:.6f}); the comparison would not be like for like"
        )
    day_counts = set(scoreboard["day_count"].tolist())
    if len(day_counts) > 1:
        raise ValueSelectionInputError(
            f"Candidates were settled over different {split} day counts: {sorted(day_counts)}"
        )


def _select(
    scoreboard: pd.DataFrame,
    grid: Sequence[SelectionCandidate],
    *,
    column: str,
    maximize: bool,
    tolerance: float,
) -> dict[str, Any]:
    """Pick one candidate, breaking ties by declared order and recording that it happened."""

    values = scoreboard[column].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueSelectionInputError(
            f"Selection column {column!r} carries a non-finite value; a candidate that cannot "
            "be scored cannot be chosen against"
        )
    best = float(np.max(values)) if maximize else float(np.min(values))
    within = np.abs(values - best) <= tolerance
    tied = scoreboard.loc[within].sort_values("declared_index")
    winner = tied.iloc[0]
    return {
        "objective": MARGIN_OBJECTIVE if maximize else RMSE_OBJECTIVE,
        "objective_column": column,
        "direction": "maximize" if maximize else "minimize",
        "tie_tolerance": tolerance,
        "selected_candidate": str(winner["candidate"]),
        "selected_model": str(winner["model"]),
        "selected_declared_index": int(winner["declared_index"]),
        "objective_value": float(winner[column]),
        "tie_occurred": bool(len(tied) > 1),
        "tied_candidates": [str(name) for name in tied["candidate"]],
        "tie_break_rule": "Lowest declared index among candidates within the tolerance",
        "candidate_values": {
            str(row["candidate"]): float(row[column])
            for _, row in scoreboard.sort_values("declared_index").iterrows()
        },
    }


def _freeze(
    selections: Mapping[str, dict[str, Any]],
    validation_scoreboard: pd.DataFrame,
    forecasts: pd.DataFrame,
) -> dict[str, Any]:
    """Seal the selection before any evaluation day is settled, and hash what was sealed."""

    days_by_split = {
        split: sorted(
            str(day)
            for day in forecasts.loc[forecasts["split"].eq(split), "market_day"].unique()
        )
        for split in ("validation", "evaluation")
    }
    validation_days = days_by_split["validation"]
    evaluation_days = days_by_split["evaluation"]
    record: dict[str, Any] = {
        "selection_policy": (
            "One selection per objective, made on validation days only and frozen before the "
            "evaluation window is settled. Outcome-dependent switching is prohibited."
        ),
        "selections": {
            objective: {
                key: selection[key]
                for key in (
                    "objective",
                    "objective_column",
                    "direction",
                    "tie_tolerance",
                    "selected_candidate",
                    "selected_model",
                    "selected_declared_index",
                    "objective_value",
                    "tie_occurred",
                    "tied_candidates",
                    "tie_break_rule",
                )
            }
            for objective, selection in selections.items()
        },
        "validation_day_count": len(validation_days),
        "validation_first_day": validation_days[0],
        "validation_last_day": validation_days[-1],
        "evaluation_day_count": len(evaluation_days),
        "evaluation_first_day": evaluation_days[0],
        "evaluation_last_day": evaluation_days[-1],
        "validation_scoreboard_digest": _frame_digest(validation_scoreboard),
    }
    record["frozen_selection_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return record


def _evaluate_frozen_selection(
    frozen_selection: Mapping[str, Any],
    evaluation_scoreboard: pd.DataFrame,
    config: BatteryDispatchConfig,
) -> dict[str, dict[str, Any]]:
    """Read each frozen pick's evaluation row. The selection is an input here, never an output."""

    indexed = evaluation_scoreboard.set_index("candidate")
    best_row = evaluation_scoreboard.loc[
        evaluation_scoreboard["realized_margin_eur"].idxmax()
    ]
    results: dict[str, dict[str, Any]] = {}
    for objective, selection in frozen_selection["selections"].items():
        name = str(selection["selected_candidate"])
        if name not in indexed.index:
            raise ValueSelectionInputError(
                f"Frozen selection names candidate {name!r}, which the evaluation window does "
                "not score; the frozen record and the evaluation disagree"
            )
        row = indexed.loc[name]
        realized = float(row["realized_margin_eur"])
        results[objective] = {
            "objective": objective,
            "selected_candidate": name,
            "selected_model": str(row["model"]),
            "validation_objective_value": float(selection["objective_value"]),
            "evaluation_day_count": int(row["day_count"]),
            "evaluation_interval_count": int(row["interval_count"]),
            "realized_margin_eur": realized,
            "market_cash_margin_eur": float(row["market_cash_margin_eur"]),
            "perfect_foresight_margin_eur": float(row["perfect_foresight_margin_eur"]),
            "perfect_foresight_regret_eur": float(row["perfect_foresight_regret_eur"]),
            "perfect_foresight_capture_ratio": (
                None
                if pd.isna(row["perfect_foresight_capture_ratio"])
                else float(row["perfect_foresight_capture_ratio"])
            ),
            "retrospective_best_candidate": str(best_row["candidate"]),
            "retrospective_best_margin_eur": float(best_row["realized_margin_eur"]),
            "retrospective_best_regret_eur": float(best_row["realized_margin_eur"]) - realized,
            "rmse_eur_per_mwh": float(row["rmse_eur_per_mwh"]),
            "mae_eur_per_mwh": float(row["mae_eur_per_mwh"]),
            "grid_charge_mwh": float(row["grid_charge_mwh"]),
            "grid_discharge_mwh": float(row["grid_discharge_mwh"]),
            "equivalent_full_cycles": float(row["equivalent_full_cycles"]),
            "charge_power_mw": config.charge_power_mw,
            "discharge_power_mw": config.discharge_power_mw,
            "energy_capacity_mwh": config.energy_capacity_mwh,
        }
    return results


def _summarize(
    *,
    frozen_selection: Mapping[str, Any],
    objective_results: Mapping[str, dict[str, Any]],
    validation_scoreboard: pd.DataFrame,
    evaluation_scoreboard: pd.DataFrame,
    grid: Sequence[SelectionCandidate],
    config: BatteryDispatchConfig,
    evidence_class: str,
    forecast_digest: str,
) -> dict[str, Any]:
    """The headline difference and the context a reader needs to judge it."""

    by_rmse = objective_results[RMSE_OBJECTIVE]
    by_margin = objective_results[MARGIN_OBJECTIVE]
    difference = float(by_margin["realized_margin_eur"]) - float(by_rmse["realized_margin_eur"])
    same_candidate = by_margin["selected_candidate"] == by_rmse["selected_candidate"]
    return {
        "result_label": VALUE_SELECTION_RESULT_LABEL,
        "evidence_class": evidence_class,
        "evidence_note": (
            "An already inspected historical window supports supplementary evidence only. A "
            "confirmatory claim requires a newly predeclared untouched or prospective window."
        ),
        "objectives": list(SELECTION_OBJECTIVES),
        "candidate_count": len(grid),
        "candidates": [candidate.to_dict() for candidate in grid],
        "frozen_selection_sha256": frozen_selection["frozen_selection_sha256"],
        "selected_by_validation_rmse": by_rmse["selected_candidate"],
        "selected_by_validation_settled_margin": by_margin["selected_candidate"],
        "objectives_agree": same_candidate,
        "margin_minus_rmse_selection_eur": difference,
        "margin_selection_favoured": difference > 0,
        "headline_note": (
            "The signed difference is evaluation margin under margin-selection minus "
            "evaluation margin under RMSE-selection. It is one window, not a distribution, and "
            "this repository does not convert it into a probability."
        )
        if not same_candidate
        else (
            "Both objectives selected the same candidate on this window, so the difference is "
            "zero by construction and this window distinguishes nothing between the two rules."
        ),
        "equivalent_basis": {
            "battery_configuration": "One configuration plans and settles every candidate",
            "perfect_foresight_ceiling": (
                f"Asserted identical across candidates within EUR {CEILING_TOLERANCE_EUR}"
            ),
            "charge_power_mw": config.charge_power_mw,
            "discharge_power_mw": config.discharge_power_mw,
            "energy_capacity_mwh": config.energy_capacity_mwh,
            "terminal_soc_policy": "Initial SOC restored at the end of every market day",
        },
        "validation_day_count": frozen_selection["validation_day_count"],
        "validation_first_day": frozen_selection["validation_first_day"],
        "validation_last_day": frozen_selection["validation_last_day"],
        "evaluation_day_count": frozen_selection["evaluation_day_count"],
        "evaluation_first_day": frozen_selection["evaluation_first_day"],
        "evaluation_last_day": frozen_selection["evaluation_last_day"],
        "objective_results": dict(objective_results),
        "candidate_forecast_sha256": forecast_digest,
        "validation_scoreboard_digest": frozen_selection["validation_scoreboard_digest"],
        "evaluation_scoreboard_digest": _frame_digest(evaluation_scoreboard),
        "retrospective_best_note": (
            "The retrospective best candidate is chosen with knowledge of the evaluation "
            "outcome. It is a diagnostic ceiling, not a policy, and no selection rule can be "
            "expected to reach it."
        ),
        "selection_policy": frozen_selection["selection_policy"],
    }


def _forecast_digest(forecasts: pd.DataFrame, grid: Sequence[SelectionCandidate]) -> str:
    """A digest of the forecasts every figure here came from.

    The summary describes the candidates but cannot see the schedule and feature configuration
    that produced their predictions, so it names the table instead: two runs reporting the same
    digest read identical forecasts, and two reporting different digests are not comparable
    however alike their candidate lists look.
    """

    columns = ["delivery_start_utc", "split", *(candidate.name for candidate in grid)]
    ordered = forecasts.loc[:, columns].sort_values("delivery_start_utc")
    return hashlib.sha256(
        ordered.to_csv(index=False, float_format="%.10f").encode("utf-8")
    ).hexdigest()


def _frame_digest(frame: pd.DataFrame) -> str:
    """A stable digest of a scoreboard, so a recorded result names the numbers it came from."""

    ordered = frame.sort_values("declared_index").reset_index(drop=True)
    return hashlib.sha256(
        ordered.to_csv(index=False, float_format="%.10f").encode("utf-8")
    ).hexdigest()
