"""Deterministic seasonal block bootstrap for synthetic DAM price paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import CANONICAL_COLUMNS, ensure_canonical
from greek_bess.data.timezones import GREECE_TZ, UTC, market_day_starts


class BootstrapInputError(ValueError):
    """Raised when bootstrap inputs cannot produce an auditable path."""


@dataclass(frozen=True)
class BootstrapConfig:
    """Explicit seasonal block-bootstrap assumptions.

    ``end_day`` is exclusive. Seasons are meteorological: winter (December-February),
    spring (March-May), summer (June-August), and autumn (September-November).
    """

    start_day: date
    end_day: date
    path_count: int = 1
    block_days: int = 7
    random_seed: int = 42

    def __post_init__(self) -> None:
        if not isinstance(self.start_day, date) or not isinstance(self.end_day, date):
            raise BootstrapInputError("start_day and end_day must be date values")
        for name, value in (
            ("path_count", self.path_count),
            ("block_days", self.block_days),
            ("random_seed", self.random_seed),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise BootstrapInputError(f"{name} must be an integer")
        if self.end_day <= self.start_day:
            raise BootstrapInputError("end_day must be later than start_day (exclusive)")
        if self.path_count < 1:
            raise BootstrapInputError("path_count must be at least 1")
        if self.block_days < 1:
            raise BootstrapInputError("block_days must be at least 1")
        if self.random_seed < 0:
            raise BootstrapInputError("random_seed must be non-negative")

    @classmethod
    def from_dict(cls, payload: object) -> BootstrapConfig:
        """Parse a strict JSON-compatible configuration object."""

        if not isinstance(payload, dict):
            raise BootstrapInputError("Bootstrap config JSON must contain one object")
        allowed = {"start_day", "end_day", "path_count", "block_days", "random_seed"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise BootstrapInputError(f"Unknown bootstrap config fields: {', '.join(unknown)}")
        try:
            values = dict(payload)
            values["start_day"] = date.fromisoformat(str(values["start_day"]))
            values["end_day"] = date.fromisoformat(str(values["end_day"]))
            return cls(**values)
        except (KeyError, TypeError, ValueError) as exc:
            raise BootstrapInputError(f"Invalid bootstrap config: {exc}") from exc

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["start_day"] = self.start_day.isoformat()
        payload["end_day"] = self.end_day.isoformat()
        return payload


@dataclass(frozen=True)
class BootstrapResult:
    """Generated synthetic intervals, sampled-block audit trail and assumptions."""

    paths: pd.DataFrame
    provenance: pd.DataFrame
    summary: dict[str, object]


def generate_seasonal_bootstrap_paths(
    historical_prices: pd.DataFrame, config: BootstrapConfig
) -> BootstrapResult:
    """Sample same-season, structure-compatible historical blocks with replacement.

    Prices are copied without adjustment. Target timestamps are constructed independently,
    so a sampled block is eligible only when its per-day interval counts exactly match the
    target block. This preserves 23/25-hour and 92/100-quarter-hour market days without filling.
    """

    history = _validated_history(historical_prices)
    resolution_minutes = int(round(float(history["duration_hours"].iloc[0]) * 60))
    by_day = {
        delivery_day: day.reset_index(drop=True)
        for delivery_day, day in history.assign(
            market_day=history["delivery_start_market"].dt.date
        ).groupby("market_day", sort=True)
    }
    history_days = sorted(by_day)
    rng = np.random.default_rng(config.random_seed)
    path_frames: list[pd.DataFrame] = []
    provenance_records: list[dict[str, object]] = []

    for path_id in range(config.path_count):
        target_day = config.start_day
        block_id = 0
        interval_frames: list[pd.DataFrame] = []
        while target_day < config.end_day:
            length = min(config.block_days, (config.end_day - target_day).days)
            target_days = [target_day + timedelta(days=offset) for offset in range(length)]
            target_counts = tuple(
                len(market_day_starts(day, resolution_minutes)) for day in target_days
            )
            candidates = _candidate_blocks(
                history_days, by_day, length, _season(target_day), target_counts
            )
            if not candidates:
                raise BootstrapInputError(
                    "No contiguous historical block matches target season and interval "
                    f"structure for {target_day.isoformat()} ({target_counts})"
                )
            sampled_index = int(rng.integers(len(candidates)))
            source_days = candidates[sampled_index]
            for target, source in zip(target_days, source_days, strict=True):
                interval_frames.append(
                    _map_day(
                        by_day[source],
                        target,
                        resolution_minutes,
                        path_id,
                        config.random_seed,
                    )
                )
            provenance_records.append(
                {
                    "path_id": path_id,
                    "block_id": block_id,
                    "target_start_day": target_days[0].isoformat(),
                    "target_end_day": target_days[-1].isoformat(),
                    "source_start_day": source_days[0].isoformat(),
                    "source_end_day": source_days[-1].isoformat(),
                    "season": _season(target_day),
                    "day_count": length,
                    "interval_count": sum(target_counts),
                    "candidate_count": len(candidates),
                    "sampled_candidate_index": sampled_index,
                }
            )
            target_day += timedelta(days=length)
            block_id += 1
        path_frames.append(pd.concat(interval_frames, ignore_index=True))

    paths = pd.concat(path_frames, ignore_index=True)
    provenance = pd.DataFrame.from_records(provenance_records)
    summary: dict[str, object] = {
        "result_label": (
            "synthetic seasonal block-bootstrap paths; not forecasts or investment evidence"
        ),
        "method": "meteorological-season block bootstrap with replacement",
        "configuration": config.to_dict(),
        "resolution_minutes": resolution_minutes,
        "historical_first_day": history_days[0].isoformat(),
        "historical_last_day": history_days[-1].isoformat(),
        "path_count": config.path_count,
        "interval_count_per_path": int((paths["path_id"] == 0).sum()),
        "sampled_block_count": len(provenance),
    }
    return BootstrapResult(paths=paths, provenance=provenance, summary=summary)


def _validated_history(frame: pd.DataFrame) -> pd.DataFrame:
    history = ensure_canonical(frame, allow_empty=False)
    report = assess_quality(history, require_complete_days=True)
    if not report.is_valid:
        errors = ", ".join(issue.code for issue in report.issues if issue.severity == "error")
        raise BootstrapInputError(f"Historical prices failed quality validation: {errors}")
    durations = history["duration_hours"].unique()
    if len(durations) != 1:
        raise BootstrapInputError("Historical prices must use one interval resolution")
    return history


def _candidate_blocks(
    history_days: list[date],
    by_day: dict[date, pd.DataFrame],
    length: int,
    season: str,
    target_counts: tuple[int, ...],
) -> list[list[date]]:
    candidates: list[list[date]] = []
    day_set = set(history_days)
    for start in history_days:
        block = [start + timedelta(days=offset) for offset in range(length)]
        if (
            _season(start) == season
            and all(day in day_set for day in block)
            and tuple(len(by_day[day]) for day in block) == target_counts
        ):
            candidates.append(block)
    return candidates


def _map_day(
    source: pd.DataFrame,
    target_day: date,
    resolution_minutes: int,
    path_id: int,
    seed: int,
) -> pd.DataFrame:
    starts_market = market_day_starts(target_day, resolution_minutes)
    starts_utc = starts_market.tz_convert(UTC)
    result = source.copy()
    result["delivery_start_utc"] = starts_utc
    result["delivery_end_utc"] = starts_utc + timedelta(minutes=resolution_minutes)
    result["delivery_start_market"] = starts_market
    result["delivery_start_greece"] = starts_utc.tz_convert(GREECE_TZ)
    result["source"] = "synthetic"
    result["source_version"] = f"seasonal_block_bootstrap_v1_seed_{seed}"
    result["quality_flags"] = result["quality_flags"].map(
        lambda flags: sorted(set(flags) | {"seasonal_block_bootstrap", "synthetic_not_forecast"})
    )
    result = ensure_canonical(result)
    result.insert(0, "path_id", path_id)
    return result.loc[:, ["path_id", *CANONICAL_COLUMNS]]


def _season(day: date) -> str:
    if day.month in (12, 1, 2):
        return "winter"
    if day.month in (3, 4, 5):
        return "spring"
    if day.month in (6, 7, 8):
        return "summer"
    return "autumn"
