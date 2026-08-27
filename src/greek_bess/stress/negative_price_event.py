"""Deterministic additive negative-price events for synthetic bootstrap paths."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from .price_level import PriceLevelShockInputError, _validated_paths


class NegativePriceEventInputError(ValueError):
    """Raised when negative-price-event assumptions or paths are invalid."""


@dataclass(frozen=True)
class NegativePriceEventWindow:
    """One explicit half-open UTC event window."""

    event_id: str
    start_utc: pd.Timestamp
    end_utc: pd.Timestamp

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise NegativePriceEventInputError("event_id must be a non-empty string")
        if self.event_id != self.event_id.strip():
            raise NegativePriceEventInputError("event_id must not have surrounding whitespace")
        for name, value in (("start_utc", self.start_utc), ("end_utc", self.end_utc)):
            if not isinstance(value, pd.Timestamp) or value.tz is None:
                raise NegativePriceEventInputError(f"{name} must be timezone-aware")
            if str(value.tz) != "UTC":
                raise NegativePriceEventInputError(f"{name} must be expressed in UTC")
        if self.end_utc <= self.start_utc:
            raise NegativePriceEventInputError("event end_utc must be later than start_utc")

    @classmethod
    def from_dict(cls, payload: object) -> NegativePriceEventWindow:
        if not isinstance(payload, dict):
            raise NegativePriceEventInputError("Each event must be an object")
        required = {"event_id", "start_utc", "end_utc"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown or missing:
            detail = f"unknown={unknown}, missing={missing}"
            raise NegativePriceEventInputError(f"Invalid event fields: {detail}")
        try:
            start = pd.Timestamp(payload["start_utc"])
            end = pd.Timestamp(payload["end_utc"])
        except (TypeError, ValueError) as exc:
            raise NegativePriceEventInputError(f"Invalid event timestamp: {exc}") from exc
        event_id = payload["event_id"]
        if not isinstance(event_id, str):
            raise NegativePriceEventInputError("event_id must be a non-empty string")
        return cls(event_id, start, end)

    def to_dict(self) -> dict[str, str]:
        return {
            "event_id": self.event_id,
            "start_utc": self.start_utc.isoformat(),
            "end_utc": self.end_utc.isoformat(),
        }


@dataclass(frozen=True)
class NegativePriceEventConfig:
    """Explicit deterministic assumptions for additive negative-price events."""

    transformation_id: str
    shift_eur_per_mwh: float
    events: tuple[NegativePriceEventWindow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.transformation_id, str) or not self.transformation_id.strip():
            raise NegativePriceEventInputError("transformation_id must be a non-empty string")
        if self.transformation_id != self.transformation_id.strip():
            raise NegativePriceEventInputError(
                "transformation_id must not have surrounding whitespace"
            )
        if isinstance(self.shift_eur_per_mwh, bool) or not isinstance(
            self.shift_eur_per_mwh, (int, float)
        ):
            raise NegativePriceEventInputError("shift_eur_per_mwh must be a finite negative number")
        if not math.isfinite(float(self.shift_eur_per_mwh)) or self.shift_eur_per_mwh >= 0:
            raise NegativePriceEventInputError("shift_eur_per_mwh must be a finite negative number")
        if not isinstance(self.events, tuple) or not self.events:
            raise NegativePriceEventInputError("events must be a non-empty array")
        if not all(isinstance(event, NegativePriceEventWindow) for event in self.events):
            raise NegativePriceEventInputError("events must contain event window objects")
        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise NegativePriceEventInputError("event_id values must be unique")
        ordered = sorted(self.events, key=lambda event: event.start_utc)
        if any(
            left.end_utc > right.start_utc
            for left, right in zip(ordered, ordered[1:], strict=False)
        ):
            raise NegativePriceEventInputError("Event windows must not overlap")

    @classmethod
    def from_dict(cls, payload: object) -> NegativePriceEventConfig:
        """Parse a strict JSON-compatible configuration object."""

        if not isinstance(payload, dict):
            raise NegativePriceEventInputError("Negative-price-event config must be one object")
        required = {"transformation_id", "shift_eur_per_mwh", "events"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown or missing:
            detail = f"unknown={unknown}, missing={missing}"
            raise NegativePriceEventInputError(f"Invalid config fields: {detail}")
        events_payload = payload["events"]
        if not isinstance(events_payload, list):
            raise NegativePriceEventInputError("events must be a non-empty array")
        events = tuple(NegativePriceEventWindow.from_dict(item) for item in events_payload)
        try:
            shift = float(payload["shift_eur_per_mwh"])
        except (TypeError, ValueError) as exc:
            raise NegativePriceEventInputError(
                "shift_eur_per_mwh must be a finite negative number"
            ) from exc
        transformation_id = payload["transformation_id"]
        if not isinstance(transformation_id, str):
            raise NegativePriceEventInputError("transformation_id must be a non-empty string")
        return cls(transformation_id, shift, events)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        return payload


@dataclass(frozen=True)
class NegativePriceEventResult:
    """Transformed paths, interval provenance and explicit summary."""

    paths: pd.DataFrame
    provenance: pd.DataFrame
    summary: dict[str, object]


def apply_negative_price_events(
    bootstrap_paths: pd.DataFrame, config: NegativePriceEventConfig
) -> NegativePriceEventResult:
    """Apply configured additive shifts only within exact half-open UTC windows."""

    try:
        paths = _validated_paths(bootstrap_paths)
    except PriceLevelShockInputError as exc:
        raise NegativePriceEventInputError(str(exc)) from exc
    result = paths.copy()
    original = paths["price_eur_per_mwh"].astype(float)
    event_ids = pd.Series(pd.NA, index=result.index, dtype="string")

    for event in config.events:
        mask = (result["delivery_start_utc"] >= event.start_utc) & (
            result["delivery_end_utc"] <= event.end_utc
        )
        selected = result.loc[mask]
        if selected.empty:
            raise NegativePriceEventInputError(f"Event {event.event_id} selects no intervals")
        keys_by_path = [
            set(path["delivery_start_utc"])
            for _, path in selected.groupby("path_id", sort=True)
        ]
        if len(keys_by_path) != result["path_id"].nunique() or any(
            keys != keys_by_path[0] for keys in keys_by_path[1:]
        ):
            raise NegativePriceEventInputError(
                f"Event {event.event_id} must select identical intervals in every path"
            )
        if keys_by_path[0] != set(
            pd.date_range(
                event.start_utc,
                event.end_utc,
                freq=_resolution(result),
                inclusive="left",
            )
        ):
            raise NegativePriceEventInputError(
                f"Event {event.event_id} boundaries must align with complete path intervals"
            )
        event_ids.loc[mask] = event.event_id

    applied = event_ids.notna()
    result.loc[applied, "price_eur_per_mwh"] = (
        original.loc[applied] + float(config.shift_eur_per_mwh)
    )
    if not (result.loc[applied, "price_eur_per_mwh"] < 0).all():
        raise NegativePriceEventInputError(
            "Configured shift must make every selected event interval negative"
        )
    result.loc[applied, "source_version"] = result.loc[applied, "source_version"].map(
        lambda value: f"{value}|negative_event:{config.transformation_id}"
    )
    result.loc[applied, "quality_flags"] = result.loc[applied, "quality_flags"].map(
        lambda flags: sorted(set(flags) | {"negative_price_event", "synthetic_not_forecast"})
    )
    provenance = pd.DataFrame(
        {
            "path_id": result["path_id"],
            "delivery_start_utc": result["delivery_start_utc"],
            "transformation_id": config.transformation_id,
            "event_id": event_ids,
            "event_applied": applied,
            "shift_eur_per_mwh": float(config.shift_eur_per_mwh),
            "original_price_eur_per_mwh": original,
            "shocked_price_eur_per_mwh": result["price_eur_per_mwh"],
            "input_source": paths["source"],
            "input_source_version": paths["source_version"],
        }
    )
    summary: dict[str, object] = {
        "result_label": (
            "synthetic negative-price-event paths; not forecasts or investment evidence"
        ),
        "method": "additive shifts in explicit half-open UTC event windows",
        "configuration": config.to_dict(),
        "path_count": int(result["path_id"].nunique()),
        "interval_count": len(result),
        "event_count": len(config.events),
        "shocked_interval_count": int(applied.sum()),
    }
    return NegativePriceEventResult(result, provenance, summary)


def _resolution(paths: pd.DataFrame) -> pd.Timedelta:
    minutes = int(round(float(paths["duration_hours"].iloc[0]) * 60))
    return pd.Timedelta(minutes * 60, unit="s")
