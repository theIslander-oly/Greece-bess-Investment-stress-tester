"""Deterministic availability and outage paths for synthetic bootstrap paths.

An outage here is **declared, never sampled**. A drawn outage would be a probability
statement, and this project excludes probability estimates without an independently validated
calibration: nothing in the replayed history calibrates a forced-outage rate for a Greek
merchant battery that has not operated yet. A schedule is therefore a judgmental scenario in
the same sense as a compression factor — a statement of what to examine, not a claim about
what will happen.

A schedule is a baseline available fraction plus zero or more declared windows, each with its
own available fraction. The baseline has no default: availability is one of the assumptions
`AGENTS.md` requires to be explicit, and a silent 1.0 would make full availability an accident
of the input rather than a decision.

The profile is common to every path in a run. Paths share one canonical interval identity, so
one schedule maps onto all of them, and every path is dispatched under the same physical
condition. What differs between paths is the sampled price, which is the point.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from ._paths import validate_bootstrap_paths

AVAILABILITY_POLICY = (
    "An availability schedule is a declared baseline fraction plus zero or more declared "
    "outage windows, each with its own available fraction in [0, 1]. Timing, duration and "
    "depth are judgmental scenario inputs, never sampled: an outage drawn from a rate would "
    "be a probability statement, and no calibrated forced-outage rate exists for a Greek "
    "merchant battery that has not operated. The baseline fraction has no default. Windows "
    "must not overlap each other, must overlap the dispatched horizon, and must begin and end "
    "on interval boundaries, so the schedule that is applied is the schedule that was "
    "declared. A window is applied whole to every interval it covers; no within-interval "
    "proration is invented."
)


class AvailabilityInputError(ValueError):
    """Raised when an availability schedule cannot be applied audibly and safely."""


@dataclass(frozen=True)
class OutageWindow:
    """One declared window of reduced or zero availability.

    ``end_utc`` is exclusive. ``available_fraction`` of 0.0 is a full outage and any value
    below the schedule's baseline is a derate; both are declared rather than inferred.
    """

    outage_id: str
    start_utc: datetime
    end_utc: datetime
    available_fraction: float

    def __post_init__(self) -> None:
        if not isinstance(self.outage_id, str) or not self.outage_id.strip():
            raise AvailabilityInputError("outage_id must be a non-empty string")
        if self.outage_id != self.outage_id.strip():
            raise AvailabilityInputError("outage_id must not have surrounding whitespace")
        for name in ("start_utc", "end_utc"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise AvailabilityInputError(f"{name} must be a datetime")
            if value.tzinfo is None or value.utcoffset() is None:
                raise AvailabilityInputError(
                    f"{name} must be timezone aware; UTC is the primary interval key"
                )
        if self.end_utc <= self.start_utc:
            raise AvailabilityInputError(
                f"Outage {self.outage_id}: end_utc must be later than start_utc (exclusive)"
            )
        _require_fraction(f"Outage {self.outage_id}: available_fraction", self.available_fraction)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outage_id": self.outage_id,
            "start_utc": pd.Timestamp(self.start_utc).tz_convert("UTC").isoformat(),
            "end_utc": pd.Timestamp(self.end_utc).tz_convert("UTC").isoformat(),
            "available_fraction": float(self.available_fraction),
        }


@dataclass(frozen=True)
class AvailabilityScheduleConfig:
    """A named availability schedule: a declared baseline and declared outage windows."""

    schedule_id: str
    baseline_available_fraction: float
    windows: tuple[OutageWindow, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.schedule_id, str) or not self.schedule_id.strip():
            raise AvailabilityInputError("schedule_id must be a non-empty string")
        if self.schedule_id != self.schedule_id.strip():
            raise AvailabilityInputError("schedule_id must not have surrounding whitespace")
        _require_fraction("baseline_available_fraction", self.baseline_available_fraction)
        if not isinstance(self.windows, tuple):
            raise AvailabilityInputError("windows must be supplied as a tuple of OutageWindow")
        for window in self.windows:
            if not isinstance(window, OutageWindow):
                raise AvailabilityInputError("Every window must be an OutageWindow")
        identifiers = [window.outage_id for window in self.windows]
        duplicated = sorted({name for name in identifiers if identifiers.count(name) > 1})
        if duplicated:
            raise AvailabilityInputError(
                f"Duplicate outage_id values: {', '.join(duplicated)}"
            )
        ordered = sorted(self.windows, key=lambda window: window.start_utc)
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if later.start_utc < earlier.end_utc:
                raise AvailabilityInputError(
                    f"Outage windows {earlier.outage_id} and {later.outage_id} overlap; "
                    "an interval covered by two windows has no declared available fraction"
                )

    @classmethod
    def from_dict(cls, payload: object) -> AvailabilityScheduleConfig:
        """Parse a strict JSON-compatible configuration object."""

        if not isinstance(payload, Mapping):
            raise AvailabilityInputError("Availability schedule config must contain one object")
        required = {"schedule_id", "baseline_available_fraction", "windows"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise AvailabilityInputError(
                f"Unknown availability schedule fields: {', '.join(unknown)}"
            )
        if missing:
            raise AvailabilityInputError(
                f"Missing availability schedule fields: {', '.join(missing)}"
            )
        declared = payload["windows"]
        if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
            raise AvailabilityInputError("windows must be a list; declare [] for no outage")
        return cls(
            schedule_id=payload["schedule_id"],
            baseline_available_fraction=payload["baseline_available_fraction"],
            windows=tuple(_window_from_dict(entry) for entry in declared),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "baseline_available_fraction": float(self.baseline_available_fraction),
            "windows": [window.to_dict() for window in self.windows],
        }


@dataclass(frozen=True)
class AvailabilityProfile:
    """One interval-aligned availability profile, its audit trail and its declaration.

    ``values`` is the per-interval fraction in canonical UTC order, ready to pass to
    ``dispatch_bootstrap_paths``. ``declaration`` is the compact record a downstream dispatch
    summary carries, so a margin can be traced back to the schedule that produced it.
    """

    values: np.ndarray
    interval_keys: pd.DatetimeIndex
    provenance: pd.DataFrame
    summary: dict[str, Any]
    declaration: dict[str, Any]


def build_availability_profile(
    bootstrap_paths: pd.DataFrame, config: AvailabilityScheduleConfig
) -> AvailabilityProfile:
    """Map a declared availability schedule onto the paths' canonical interval identity.

    The transformation has no random component: identical paths and configuration produce an
    identical profile, provenance and summary. Prices are not read, so zero and negative
    prices pass through untouched.
    """

    paths = validate_bootstrap_paths(bootstrap_paths, AvailabilityInputError)
    starts, ends, durations = _common_interval_identity(paths)

    values = np.full(len(starts), float(config.baseline_available_fraction))
    applied = np.full(len(starts), "", dtype=object)
    applied_counts: dict[str, int] = {}
    for window in config.windows:
        start = pd.Timestamp(window.start_utc).tz_convert("UTC")
        end = pd.Timestamp(window.end_utc).tz_convert("UTC")
        _refuse_misaligned_boundaries(window, start, end, starts, ends)
        covered = (starts < end) & (ends > start)
        count = int(covered.sum())
        if count == 0:
            raise AvailabilityInputError(
                f"Outage {window.outage_id} ({start.isoformat()}..{end.isoformat()}) covers no "
                "dispatched interval; a declared window that applies to nothing is refused "
                "rather than ignored"
            )
        values[covered] = float(window.available_fraction)
        applied[covered] = window.outage_id
        applied_counts[window.outage_id] = count

    provenance = pd.DataFrame(
        {
            "delivery_start_utc": starts,
            "delivery_end_utc": ends,
            "duration_hours": durations,
            "schedule_id": config.schedule_id,
            "baseline_available_fraction": float(config.baseline_available_fraction),
            "outage_id": pd.Series(applied).replace("", None),
            "available_fraction": values,
        }
    )
    summary = _summary(config, values, durations, applied_counts)
    declaration = _declaration(config, values, durations, applied_counts)
    return AvailabilityProfile(
        values=values,
        interval_keys=pd.DatetimeIndex(starts),
        provenance=provenance,
        summary=summary,
        declaration=declaration,
    )


def _common_interval_identity(
    paths: pd.DataFrame,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex, np.ndarray]:
    """Return the one interval identity every path shares, or refuse."""

    reference: pd.DataFrame | None = None
    for path_id, path in paths.groupby("path_id", sort=True):
        ordered = path.sort_values("delivery_start_utc").reset_index(drop=True)
        if reference is None:
            reference = ordered
            continue
        if not pd.DatetimeIndex(ordered["delivery_start_utc"]).equals(
            pd.DatetimeIndex(reference["delivery_start_utc"])
        ):
            raise AvailabilityInputError(
                f"Path {path_id} has a different canonical interval identity; one availability "
                "schedule must map onto every path of a run"
            )
    if reference is None:  # pragma: no cover - validate_bootstrap_paths refuses empty input.
        raise AvailabilityInputError("Bootstrap paths must not be empty")
    return (
        pd.DatetimeIndex(reference["delivery_start_utc"]),
        pd.DatetimeIndex(reference["delivery_end_utc"]),
        reference["duration_hours"].to_numpy(dtype=float),
    )


def _refuse_misaligned_boundaries(
    window: OutageWindow,
    start: pd.Timestamp,
    end: pd.Timestamp,
    starts: pd.DatetimeIndex,
    ends: pd.DatetimeIndex,
) -> None:
    """Refuse a boundary that falls strictly inside an interval.

    Prorating a partly covered interval would invent a within-interval schedule the caller
    never declared, and silently rounding it would apply an outage other than the one stated.
    Refusing names the interval so the declaration can be corrected.
    """

    for label, boundary in (("start_utc", start), ("end_utc", end)):
        split = (starts < boundary) & (ends > boundary)
        if bool(split.any()):
            index = int(np.flatnonzero(np.asarray(split))[0])
            raise AvailabilityInputError(
                f"Outage {window.outage_id}: {label} {boundary.isoformat()} falls inside "
                f"delivery interval {starts[index].isoformat()}..{ends[index].isoformat()}. "
                "Declare a boundary on an interval edge; a partly covered interval is not "
                "prorated, because that would apply a schedule that was never declared"
            )


def _summary(
    config: AvailabilityScheduleConfig,
    values: np.ndarray,
    durations: np.ndarray,
    applied_counts: Mapping[str, int],
) -> dict[str, Any]:
    baseline = float(config.baseline_available_fraction)
    derated = values < baseline
    unavailable = values == 0.0
    return {
        "result_label": (
            "declared availability profile for synthetic bootstrap paths; a judgmental "
            "scenario, not a forecast, a probability or an outage rate"
        ),
        "method": "declared baseline availability with declared outage windows",
        "policy": AVAILABILITY_POLICY,
        "configuration": config.to_dict(),
        "interval_count": int(len(values)),
        "horizon_hours": float(durations.sum()),
        "declared_window_count": len(config.windows),
        "derated_interval_count": int(derated.sum()),
        "derated_hours": float(durations[derated].sum()),
        "fully_unavailable_interval_count": int(unavailable.sum()),
        "fully_unavailable_hours": float(durations[unavailable].sum()),
        "minimum_available_fraction": float(values.min()),
        "maximum_available_fraction": float(values.max()),
        "applied_interval_count_by_outage": dict(applied_counts),
        "is_forecast": False,
        "is_probabilistic": False,
    }


def _declaration(
    config: AvailabilityScheduleConfig,
    values: np.ndarray,
    durations: np.ndarray,
    applied_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Return the compact record a dispatch summary carries downstream.

    Key names here travel into the scenario-ensemble summary, which refuses any key reading as
    a probability, an expectation or a ranking, so they are deliberately plain.
    """

    baseline = float(config.baseline_available_fraction)
    derated = values < baseline
    return {
        "type": "declared_schedule",
        "schedule_id": config.schedule_id,
        "baseline_available_fraction": baseline,
        "declared_window_count": len(config.windows),
        "derated_interval_count": int(derated.sum()),
        "derated_hours": float(durations[derated].sum()),
        "minimum_available_fraction": float(values.min()),
        "windows": [
            {**window.to_dict(), "applied_interval_count": applied_counts[window.outage_id]}
            for window in config.windows
        ],
    }


def _window_from_dict(payload: object) -> OutageWindow:
    if not isinstance(payload, Mapping):
        raise AvailabilityInputError("Every outage window must be one object")
    required = {"outage_id", "start_utc", "end_utc", "available_fraction"}
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown:
        raise AvailabilityInputError(f"Unknown outage window fields: {', '.join(unknown)}")
    if missing:
        raise AvailabilityInputError(f"Missing outage window fields: {', '.join(missing)}")
    return OutageWindow(
        outage_id=payload["outage_id"],
        start_utc=_timestamp(payload["start_utc"], "start_utc"),
        end_utc=_timestamp(payload["end_utc"], "end_utc"),
        available_fraction=payload["available_fraction"],
    )


def _timestamp(value: object, name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise AvailabilityInputError(f"{name} must be an ISO 8601 timestamp string")
    try:
        parsed = pd.Timestamp(value)
    except ValueError as exc:
        raise AvailabilityInputError(f"{name} is not a valid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise AvailabilityInputError(
            f"{name} must state a timezone offset; UTC is the primary interval key"
        )
    result: datetime = parsed.to_pydatetime()
    return result


def _require_fraction(label: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AvailabilityInputError(f"{label} must be a number between 0 and 1")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise AvailabilityInputError(f"{label} must be a finite number between 0 and 1")
