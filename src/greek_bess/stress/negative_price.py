"""Deterministic declared negative-price events for synthetic bootstrap paths.

Events are interval-aligned declarations, never sampled or inferred. Each event replaces the
price in its explicitly declared UTC window with one explicitly declared negative EUR/MWh
value on every path. This changes a named part of the price shape; it is neither a constant
level shift over the horizon nor a scaling of every within-day spread.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from ._paths import validate_bootstrap_paths

NEGATIVE_PRICE_EVENT_POLICY = (
    "A negative-price event is one or more whole market intervals selected by a declared "
    "inclusive UTC start and exclusive UTC end and replaced, on every bootstrap path, by a "
    "declared strictly negative price in EUR/MWh. Event timing and depth have no defaults and "
    "are never sampled, inferred, fitted, ranked or searched. An empty declared event list is "
    "the identity. Windows must align to interval boundaries, cover at least one interval and "
    "not overlap. Prices are never clipped or floored."
)


class NegativePriceEventInputError(ValueError):
    """Raised when declared negative-price events cannot be applied exactly."""


@dataclass(frozen=True)
class NegativePriceEvent:
    """One declared interval-aligned event with an absolute negative replacement price."""

    event_id: str
    start_utc: datetime
    end_utc: datetime
    price_eur_per_mwh: float

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise NegativePriceEventInputError("event_id must be a non-empty string")
        if self.event_id != self.event_id.strip():
            raise NegativePriceEventInputError("event_id must not have surrounding whitespace")
        for name in ("start_utc", "end_utc"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise NegativePriceEventInputError(f"{name} must be a datetime")
            if value.tzinfo is None or value.utcoffset() is None:
                raise NegativePriceEventInputError(
                    f"{name} must be timezone aware; UTC is the primary interval key"
                )
        if self.end_utc <= self.start_utc:
            raise NegativePriceEventInputError(
                f"Event {self.event_id}: end_utc must be later than start_utc (exclusive)"
            )
        if isinstance(self.price_eur_per_mwh, bool) or not isinstance(
            self.price_eur_per_mwh, (int, float)
        ):
            raise NegativePriceEventInputError("price_eur_per_mwh must be a finite number below 0")
        if not math.isfinite(float(self.price_eur_per_mwh)) or self.price_eur_per_mwh >= 0:
            raise NegativePriceEventInputError("price_eur_per_mwh must be a finite number below 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "start_utc": pd.Timestamp(self.start_utc).tz_convert("UTC").isoformat(),
            "end_utc": pd.Timestamp(self.end_utc).tz_convert("UTC").isoformat(),
            "price_eur_per_mwh": float(self.price_eur_per_mwh),
        }


@dataclass(frozen=True)
class NegativePriceEventConfig:
    """A transformation identifier and the complete declared event set, with no defaults."""

    transformation_id: str
    events: tuple[NegativePriceEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.transformation_id, str) or not self.transformation_id.strip():
            raise NegativePriceEventInputError("transformation_id must be a non-empty string")
        if self.transformation_id != self.transformation_id.strip():
            raise NegativePriceEventInputError(
                "transformation_id must not have surrounding whitespace"
            )
        if not isinstance(self.events, tuple):
            raise NegativePriceEventInputError("events must be supplied as a tuple")
        if not all(isinstance(event, NegativePriceEvent) for event in self.events):
            raise NegativePriceEventInputError("Every event must be a NegativePriceEvent")
        identifiers = [event.event_id for event in self.events]
        duplicated = sorted({item for item in identifiers if identifiers.count(item) > 1})
        if duplicated:
            raise NegativePriceEventInputError(
                f"Duplicate event_id values: {', '.join(duplicated)}"
            )
        ordered = sorted(self.events, key=lambda event: event.start_utc)
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if later.start_utc < earlier.end_utc:
                raise NegativePriceEventInputError(
                    f"Events {earlier.event_id} and {later.event_id} overlap; an interval may "
                    "have only one declared event price"
                )

    @classmethod
    def from_dict(cls, payload: object) -> NegativePriceEventConfig:
        """Parse a strict JSON-compatible declaration."""

        if not isinstance(payload, Mapping):
            raise NegativePriceEventInputError(
                "Negative-price event config must contain one object"
            )
        required = {"transformation_id", "events"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise NegativePriceEventInputError(
                f"Unknown negative-price event config fields: {', '.join(unknown)}"
            )
        if missing:
            raise NegativePriceEventInputError(
                f"Missing negative-price event config fields: {', '.join(missing)}"
            )
        entries = payload["events"]
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
            raise NegativePriceEventInputError("events must be a list; declare [] for identity")
        return cls(
            transformation_id=payload["transformation_id"],
            events=tuple(_event_from_dict(entry) for entry in entries),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transformation_id": self.transformation_id,
            "events": [event.to_dict() for event in self.events],
        }


@dataclass(frozen=True)
class NegativePriceEventResult:
    """Transformed paths, one-to-one interval provenance and method summary."""

    paths: pd.DataFrame
    provenance: pd.DataFrame
    summary: dict[str, object]


def apply_negative_price_events(
    bootstrap_paths: pd.DataFrame, config: NegativePriceEventConfig
) -> NegativePriceEventResult:
    """Apply exactly the declared event windows, without sampling occurrence or depth."""

    paths = validate_bootstrap_paths(bootstrap_paths, NegativePriceEventInputError)
    original = paths["price_eur_per_mwh"].astype(float)
    if original.isna().any() or not original.map(math.isfinite).all():
        raise NegativePriceEventInputError("Bootstrap path prices must all be present and finite")

    transformed = original.copy()
    event_ids = pd.Series([None] * len(paths), index=paths.index, dtype=object)
    declared_prices = pd.Series([float("nan")] * len(paths), index=paths.index)
    applied_counts: dict[str, int] = {}
    for event in config.events:
        start = pd.Timestamp(event.start_utc).tz_convert("UTC")
        end = pd.Timestamp(event.end_utc).tz_convert("UTC")
        _require_aligned_window(paths, event, start, end)
        covered = (paths["delivery_start_utc"] >= start) & (paths["delivery_start_utc"] < end)
        interval_count = int(paths.loc[covered, "delivery_start_utc"].nunique())
        if interval_count == 0:
            raise NegativePriceEventInputError(
                f"Event {event.event_id} covers no bootstrap interval; it is refused rather "
                "than ignored"
            )
        transformed.loc[covered] = float(event.price_eur_per_mwh)
        event_ids.loc[covered] = event.event_id
        declared_prices.loc[covered] = float(event.price_eur_per_mwh)
        applied_counts[event.event_id] = interval_count

    result = paths.copy()
    result["price_eur_per_mwh"] = transformed
    if config.events:
        result["source_version"] = (
            result["source_version"]
            .astype(str)
            .map(lambda value: f"{value}|negative_price_events:{config.transformation_id}")
        )
        result["quality_flags"] = result["quality_flags"].map(
            lambda flags: sorted(
                set(flags) | {"declared_negative_price_events", "synthetic_not_forecast"}
            )
        )

    provenance = pd.DataFrame(
        {
            "path_id": paths["path_id"],
            "delivery_start_utc": paths["delivery_start_utc"],
            "transformation_id": config.transformation_id,
            "method": "declared_interval_negative_price_replacement",
            "event_id": event_ids,
            "event_applied": event_ids.notna(),
            "declared_event_price_eur_per_mwh": declared_prices,
            "original_price_eur_per_mwh": original,
            "transformed_price_eur_per_mwh": transformed,
            "input_source": paths["source"],
            "input_source_version": paths["source_version"],
        }
    )
    summary: dict[str, object] = {
        "result_label": (
            "synthetic bootstrap paths with declared negative-price events; not forecasts, "
            "probabilities or investment evidence"
        ),
        "method": "deterministic replacement in explicitly declared interval windows",
        "distinction": (
            "changes only declared interval windows to absolute negative prices; it is not a "
            "horizon-wide additive level shift or a daily spread scaling"
        ),
        "policy": NEGATIVE_PRICE_EVENT_POLICY,
        "configuration": config.to_dict(),
        "path_count": int(paths["path_id"].nunique()),
        "interval_count": int(len(paths)),
        "provenance_row_count": int(len(provenance)),
        "declared_event_count": len(config.events),
        "applied_interval_count_by_event": applied_counts,
        "negative_interval_count_before": int((original < 0).sum()),
        "negative_interval_count_after": int((transformed < 0).sum()),
        "zero_interval_count_before": int((original == 0).sum()),
        "zero_interval_count_after": int((transformed == 0).sum()),
    }
    return NegativePriceEventResult(result, provenance, summary)


def _event_from_dict(payload: object) -> NegativePriceEvent:
    if not isinstance(payload, Mapping):
        raise NegativePriceEventInputError("Each negative-price event must be an object")
    required = {"event_id", "start_utc", "end_utc", "price_eur_per_mwh"}
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown:
        raise NegativePriceEventInputError(
            f"Unknown negative-price event fields: {', '.join(unknown)}"
        )
    if missing:
        raise NegativePriceEventInputError(
            f"Missing negative-price event fields: {', '.join(missing)}"
        )
    try:
        start = pd.Timestamp(payload["start_utc"]).to_pydatetime()
        end = pd.Timestamp(payload["end_utc"]).to_pydatetime()
    except (TypeError, ValueError) as exc:
        raise NegativePriceEventInputError(
            "start_utc and end_utc must be ISO-8601 datetimes"
        ) from exc
    return NegativePriceEvent(
        event_id=payload["event_id"],
        start_utc=start,
        end_utc=end,
        price_eur_per_mwh=payload["price_eur_per_mwh"],
    )


def _require_aligned_window(
    paths: pd.DataFrame,
    event: NegativePriceEvent,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> None:
    starts = pd.DatetimeIndex(paths["delivery_start_utc"].drop_duplicates())
    ends = pd.DatetimeIndex(paths["delivery_end_utc"].drop_duplicates())
    horizon_edges = set(starts) | set(ends)
    for label, boundary in (("start_utc", start), ("end_utc", end)):
        if boundary not in horizon_edges:
            containing = paths.loc[
                (paths["delivery_start_utc"] < boundary) & (paths["delivery_end_utc"] > boundary)
            ]
            if not containing.empty:
                row = containing.iloc[0]
                raise NegativePriceEventInputError(
                    f"Event {event.event_id}: {label} falls inside interval "
                    f"{row['delivery_start_utc'].isoformat()}.."
                    f"{row['delivery_end_utc'].isoformat()}; "
                    "partial intervals are refused rather than approximated"
                )
