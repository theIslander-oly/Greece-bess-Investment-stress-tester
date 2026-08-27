"""Independent deterministic dispatch across validated synthetic bootstrap paths."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import ensure_canonical
from greek_bess.dispatch import BatteryDispatchConfig, optimize_perfect_foresight


class BootstrapDispatchInputError(ValueError):
    """Raised when bootstrap paths are not equivalent, complete synthetic paths."""


@dataclass(frozen=True)
class BootstrapDispatchResult:
    """Interval schedules, one operational summary per path, and common assumptions."""

    interval_results: pd.DataFrame
    path_summaries: pd.DataFrame
    summary: dict[str, Any]


def dispatch_bootstrap_paths(
    paths: pd.DataFrame,
    config: BatteryDispatchConfig,
    *,
    availability: float | Sequence[float] | pd.Series = 1.0,
) -> BootstrapDispatchResult:
    """Optimize every path independently under one battery and availability profile.

    This is a collection of perfect-foresight gross-margin upper bounds on synthetic paths,
    not a forecast, probability model, or estimate of expected revenue.
    """

    validated, path_ids = _validate_paths(paths)
    intervals_per_path = len(validated) // len(path_ids)
    availability_values = _common_availability(availability, intervals_per_path)
    schedules: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []

    for path_id in path_ids:
        path = validated.loc[validated["path_id"] == path_id].drop(columns="path_id")
        result = optimize_perfect_foresight(path, config, availability=availability_values)
        schedule = result.schedule.copy()
        schedule.insert(0, "path_id", path_id)
        schedules.append(schedule)
        summaries.append({"path_id": path_id, **result.summary})

    interval_results = pd.concat(schedules, ignore_index=True)
    path_summaries = pd.DataFrame.from_records(summaries)
    return BootstrapDispatchResult(
        interval_results=interval_results,
        path_summaries=path_summaries,
        summary={
            "result_label": (
                "independent perfect-foresight gross-margin upper bounds on synthetic "
                "seasonal bootstrap paths; not forecasts, probabilities, expected revenue, "
                "or investment evidence"
            ),
            "method": "independent deterministic dispatch per bootstrap path",
            "path_count": len(path_ids),
            "interval_count_per_path": intervals_per_path,
            "battery_configuration": config.to_dict(),
            "availability_assumption": (
                {"type": "constant", "fraction": float(availability_values[0])}
                if np.all(availability_values == availability_values[0])
                else {"type": "common_interval_profile", "interval_count": intervals_per_path}
            ),
            "input_source": "synthetic seasonal bootstrap paths",
            "is_forecast": False,
            "is_investment_evidence": False,
        },
    )


def _validate_paths(paths: pd.DataFrame) -> tuple[pd.DataFrame, list[int]]:
    if "path_id" not in paths:
        raise BootstrapDispatchInputError("Missing bootstrap path columns: path_id")
    if paths.empty:
        raise BootstrapDispatchInputError("Bootstrap paths must not be empty")
    path_values = pd.to_numeric(paths["path_id"], errors="coerce")
    if path_values.isna().any() or (path_values % 1 != 0).any() or (path_values < 0).any():
        raise BootstrapDispatchInputError("path_id values must be non-negative integers")
    frame = paths.copy()
    frame["path_id"] = path_values.astype(int)
    if frame.duplicated(["path_id", "delivery_start_utc"]).any():
        raise BootstrapDispatchInputError("Duplicate path_id/canonical UTC interval keys")

    path_ids = sorted(frame["path_id"].unique().tolist())
    reference_keys: pd.DatetimeIndex | None = None
    validated: list[pd.DataFrame] = []
    for path_id in path_ids:
        raw = frame.loc[frame["path_id"] == path_id]
        canonical = ensure_canonical(raw.drop(columns="path_id"), allow_empty=False)
        report = assess_quality(canonical, require_complete_days=True)
        if not report.is_valid:
            errors = ", ".join(i.code for i in report.issues if i.severity == "error")
            raise BootstrapDispatchInputError(f"Path {path_id} failed quality validation: {errors}")
        if (
            not (canonical["source"] == "synthetic").all()
            or not canonical["quality_flags"]
            .map(lambda flags: "synthetic_not_forecast" in flags)
            .all()
        ):
            raise BootstrapDispatchInputError(
                f"Path {path_id} must retain synthetic/non-forecast provenance labels"
            )
        keys = pd.DatetimeIndex(canonical["delivery_start_utc"])
        if reference_keys is None:
            reference_keys = keys
        elif not keys.equals(reference_keys):
            raise BootstrapDispatchInputError(
                f"Path {path_id} has inconsistent canonical interval identity"
            )
        canonical.insert(0, "path_id", path_id)
        validated.append(canonical)
    return pd.concat(validated, ignore_index=True), path_ids


def _common_availability(
    availability: float | Sequence[float] | pd.Series, interval_count: int
) -> np.ndarray:
    if np.isscalar(availability):
        values = np.full(interval_count, float(cast(Any, availability)))
    else:
        values = np.asarray(availability, dtype=float)
        if values.ndim != 1 or len(values) != interval_count:
            raise BootstrapDispatchInputError(
                f"availability must be one common profile of exactly {interval_count} values"
            )
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise BootstrapDispatchInputError("availability values must be finite and between 0 and 1")
    return values
