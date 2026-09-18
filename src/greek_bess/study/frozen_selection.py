"""Replay accepted Stage 9 forecast bytes without refitting or selecting again."""

from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..selection.candidates import SelectionCandidate, validate_candidates
from ..selection.experiment import (
    MARGIN_OBJECTIVE,
    RETROSPECTIVE_EVIDENCE,
    RMSE_OBJECTIVE,
    _validate_realized_price_identity,
)
from .config import FROZEN_SELECTION_PLANNERS, IntegratedStudyConfig, IntegratedStudyInputError


def read_frozen_selection(
    directory: Path,
    prices: pd.DataFrame,
    config: IntegratedStudyConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Verify an independently pinned bundle and return exactly its selected forecasts.

    The acceptance record, not a hash by itself, supplies evidence of causal construction.
    Byte identity cannot certify that an arbitrary caller created forecasts without leakage.
    """

    try:
        return _read(directory, prices, config)
    except IntegratedStudyInputError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise IntegratedStudyInputError(f"Invalid frozen selection evidence: {exc}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegratedStudyInputError(message)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read(
    directory: Path,
    prices: pd.DataFrame,
    config: IntegratedStudyConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = directory.resolve()
    index_bytes = (root / "evidence_index.json").read_bytes()
    pin = config.selection_evidence_index_sha256
    _require(_digest(index_bytes) == pin, "Selection evidence index digest mismatch")
    index = json.loads(index_bytes)
    _require(
        index["evidence_class"] == RETROSPECTIVE_EVIDENCE,
        "Frozen replay requires retrospective supplementary evidence",
    )
    files = index["files_sha256"]
    _require(isinstance(files, dict), "Selection evidence file index must be an object")
    _require(
        {"forecasts.csv", "selection.summary.json"} <= set(files),
        "Selection evidence omits required files",
    )
    contents: dict[str, bytes] = {}
    for name, expected in files.items():
        _require(
            isinstance(name, str) and not Path(name).is_absolute(),
            "Selection evidence paths must be relative",
        )
        path = (root / name).resolve()
        _require(
            path.is_relative_to(root) and path != root,
            "Selection evidence path escapes its directory",
        )
        _require(
            isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
            "Selection evidence contains an invalid file digest",
        )
        content = path.read_bytes()
        _require(_digest(content) == expected, f"Selection evidence file digest mismatch: {name}")
        contents[name] = content

    payload = json.loads(contents["selection.summary.json"])
    summary = payload["summary"]
    frozen = dict(payload["frozen_selection"])
    seal = frozen.pop("frozen_selection_sha256")
    computed = _digest(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    )
    _require(
        computed == seal == summary["frozen_selection_sha256"] == index["frozen_selection_sha256"],
        "Broken frozen selection seal",
    )
    _require(
        summary["evidence_class"] == index["evidence_class"], "Selection evidence classes disagree"
    )
    for split in ("validation", "evaluation"):
        for field in ("first_day", "last_day", "day_count"):
            key = f"{split}_{field}"
            _require(summary[key] == frozen[key], f"Frozen selection disagrees on {key}")
    _require(
        frozen["evaluation_first_day"] == config.window_start_day.isoformat()
        and frozen["evaluation_last_day"] == config.window_end_day.isoformat()
        and frozen["evaluation_day_count"] == len(config.window_days),
        "Study window must equal the frozen evaluation window",
    )
    _require(
        frozen["validation_last_day"] < frozen["evaluation_first_day"],
        "Frozen selection validation must precede evaluation",
    )

    table = pd.read_csv(io.BytesIO(contents["forecasts.csv"]), float_precision="round_trip")
    required = {
        "delivery_start_utc",
        "market_day",
        "duration_hours",
        "split",
        "source",
        "actual_price_eur_per_mwh",
    }
    _require(required <= set(table), "Frozen forecast table omits required columns")
    _require(
        all(pd.Timestamp(value).tzinfo is not None for value in table.delivery_start_utc),
        "Frozen forecast interval keys must be timezone-aware",
    )
    table["delivery_start_utc"] = pd.to_datetime(table.delivery_start_utc, utc=True)
    _validate_realized_price_identity(prices, table)
    actual = prices.set_index("delivery_start_utc").loc[table.delivery_start_utc]
    days = actual.delivery_start_market.dt.date.map(str).to_numpy()
    _require(
        np.array_equal(table.market_day.to_numpy(), days),
        "Frozen forecast market days disagree with canonical prices",
    )
    durations = pd.to_numeric(table.duration_hours, errors="coerce").to_numpy(dtype=float)
    _require(
        bool(np.isfinite(durations).all())
        and bool(np.allclose(durations, actual.duration_hours, rtol=0, atol=1e-12)),
        "Frozen forecast durations disagree with canonical prices",
    )
    synthetic = table.source.eq("synthetic")
    _require(
        bool(synthetic.all()) if config.price_source == "synthetic" else not bool(synthetic.any()),
        "Frozen forecast price source disagrees with study",
    )
    _require(
        np.array_equal(table.source.to_numpy(), actual.source.to_numpy()),
        "Frozen forecast sources disagree with canonical prices",
    )
    _require(
        set(table.split.unique()) == {"validation", "evaluation"},
        "Frozen forecast table must contain validation and evaluation only",
    )
    canonical_days = prices.delivery_start_market.dt.date.map(str)
    for split in ("validation", "evaluation"):
        rows = table.loc[table.split.eq(split)]
        first, last = frozen[f"{split}_first_day"], frozen[f"{split}_last_day"]
        expected_days = set(pd.date_range(first, last).strftime("%Y-%m-%d"))
        _require(
            len(expected_days) == frozen[f"{split}_day_count"]
            and set(rows.market_day) == expected_days,
            f"Frozen {split} calendar is incomplete or inconsistent",
        )
        expected_keys = prices.loc[canonical_days.isin(expected_days), "delivery_start_utc"]
        _require(
            set(rows.delivery_start_utc) == set(expected_keys),
            f"Frozen {split} interval coverage differs from canonical prices",
        )

    grid = validate_candidates(tuple(SelectionCandidate(**item) for item in summary["candidates"]))
    _require(
        all(candidate.name in table for candidate in grid),
        "Frozen forecast table is missing candidate columns",
    )
    # Legacy selection digests used the producer OS's default CSV line terminator.
    # File bytes have already matched the independent pin. Reconstruct only these two
    # known serializations; do not change precision, values, order or the recorded digest.
    semantic = summary["candidate_forecast_sha256"]
    _require(
        semantic == index["candidate_forecast_sha256"], "Candidate forecast digest records disagree"
    )
    columns = ["delivery_start_utc", "split", *(candidate.name for candidate in grid)]
    ordered = table.loc[:, columns].sort_values("delivery_start_utc")
    matching_endings = [
        label
        for label, ending in (("LF", "\n"), ("CRLF", "\r\n"))
        if _digest(
            ordered.to_csv(index=False, float_format="%.10f", lineterminator=ending).encode("utf-8")
        )
        == semantic
    ]
    _require(len(matching_endings) == 1, "Candidate forecast semantic digest mismatch")
    evaluation = table.loc[table.split.eq("evaluation")].set_index("delivery_start_utc")
    selected: dict[str, str] = {}
    result = pd.DataFrame(index=evaluation.index)
    for planner, objective, summary_key in zip(
        FROZEN_SELECTION_PLANNERS,
        (RMSE_OBJECTIVE, MARGIN_OBJECTIVE),
        ("selected_by_validation_rmse", "selected_by_validation_settled_margin"),
        strict=True,
    ):
        choice = frozen["selections"][objective]
        candidate = choice["selected_candidate"]
        _require(
            candidate in {item.name for item in grid} and candidate == summary[summary_key],
            "Frozen selected candidate disagrees with summary or grid",
        )
        position = choice["selected_declared_index"]
        _require(
            isinstance(position, int)
            and not isinstance(position, bool)
            and 0 <= position < len(grid),
            "Invalid frozen candidate index",
        )
        chosen = grid[position]
        _require(
            chosen.name == candidate and chosen.model == choice["selected_model"],
            "Frozen candidate index or model disagrees with grid",
        )
        values = pd.to_numeric(evaluation[candidate], errors="coerce").to_numpy(dtype=float)
        _require(bool(np.isfinite(values).all()), "Selected frozen forecasts must be finite")
        result[planner] = values
        selected[planner] = candidate
    provenance = {
        "evidence_index_sha256": pin,
        "source_run_id": index["workflow_run_id"],
        "source_commit": index["source_commit"],
        "frozen_selection_sha256": seal,
        "candidate_forecast_sha256": semantic,
        "candidate_digest_line_ending": matching_endings[0],
        "forecast_file_sha256": files["forecasts.csv"],
        "selected_candidates": selected,
        "evidence_class": index["evidence_class"],
        "replay_policy": "Replay accepted candidate forecasts; no refit or reselection",
        "causality_basis": (
            "Inherited from independently accepted source evidence, not from hashes alone"
        ),
    }
    return result.sort_index(), provenance
