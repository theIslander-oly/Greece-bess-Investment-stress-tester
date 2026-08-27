"""Deterministic seasonal block bootstrap for synthetic DAM price paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import CANONICAL_COLUMNS, ensure_canonical
from greek_bess.data.timezones import GREECE_TZ, UTC, market_day_starts

SUPPORTED_RESOLUTION_MINUTES = frozenset({15, 60})

SOURCE_ERA_POLICY = (
    "A source era is a maximal contiguous run of market days sharing one delivery "
    "resolution. The bootstrap samples from exactly one era. When a history contains more "
    "than one, the era must be declared with source_resolution_minutes, optionally narrowed "
    "by source_start_day and source_end_day; there is no default, because a silently chosen "
    "era would make the sampled regime an accident of the input rather than a decision."
)


class BootstrapInputError(ValueError):
    """Raised when bootstrap inputs cannot produce an auditable path."""


@dataclass(frozen=True)
class SourceEra:
    """One maximal contiguous run of market days at a single delivery resolution."""

    resolution_minutes: int
    first_day: date
    last_day: date
    market_day_count: int

    @property
    def label(self) -> str:
        return (
            f"{self.resolution_minutes}min {self.first_day.isoformat()}"
            f"..{self.last_day.isoformat()}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution_minutes": self.resolution_minutes,
            "first_day": self.first_day.isoformat(),
            "last_day": self.last_day.isoformat(),
            "market_day_count": self.market_day_count,
        }


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
    source_resolution_minutes: int | None = None
    source_start_day: date | None = None
    source_end_day: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.start_day, date) or not isinstance(self.end_day, date):
            raise BootstrapInputError("start_day and end_day must be date values")
        for name in ("source_start_day", "source_end_day"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, date):
                raise BootstrapInputError(f"{name} must be a date value when supplied")
        if (
            self.source_start_day is not None
            and self.source_end_day is not None
            and self.source_end_day <= self.source_start_day
        ):
            raise BootstrapInputError(
                "source_end_day must be later than source_start_day (exclusive)"
            )
        if self.source_resolution_minutes is not None and (
            isinstance(self.source_resolution_minutes, bool)
            or self.source_resolution_minutes not in SUPPORTED_RESOLUTION_MINUTES
        ):
            raise BootstrapInputError(
                "source_resolution_minutes must be one of "
                f"{sorted(SUPPORTED_RESOLUTION_MINUTES)} when supplied"
            )
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
        allowed = {
            "start_day",
            "end_day",
            "path_count",
            "block_days",
            "random_seed",
            "source_resolution_minutes",
            "source_start_day",
            "source_end_day",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise BootstrapInputError(f"Unknown bootstrap config fields: {', '.join(unknown)}")
        try:
            values = dict(payload)
            values["start_day"] = date.fromisoformat(str(values["start_day"]))
            values["end_day"] = date.fromisoformat(str(values["end_day"]))
            for name in ("source_start_day", "source_end_day"):
                if values.get(name) is not None:
                    values[name] = date.fromisoformat(str(values[name]))
            return cls(**values)
        except (KeyError, TypeError, ValueError) as exc:
            raise BootstrapInputError(f"Invalid bootstrap config: {exc}") from exc

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["start_day"] = self.start_day.isoformat()
        payload["end_day"] = self.end_day.isoformat()
        for name in ("source_start_day", "source_end_day"):
            value = getattr(self, name)
            payload[name] = None if value is None else value.isoformat()
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
    eras = detect_source_eras(history)
    era = select_source_era(eras, config)
    history, source_first_day, source_last_day = _restrict_to_era(history, era, config)
    resolution_minutes = era.resolution_minutes
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
                    "source_era_resolution_minutes": resolution_minutes,
                    "source_era_first_day": source_first_day.isoformat(),
                    "source_era_last_day": source_last_day.isoformat(),
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
        "source_era_policy": SOURCE_ERA_POLICY,
        "resolution_minutes": resolution_minutes,
        "available_source_eras": [available.to_dict() for available in eras],
        "available_source_era_count": len(eras),
        "selected_source_era": era.to_dict(),
        "source_era_declared": config.source_resolution_minutes is not None,
        "historical_first_day": history_days[0].isoformat(),
        "historical_last_day": history_days[-1].isoformat(),
        "sampled_source_market_day_count": len(history_days),
        "path_count": config.path_count,
        "interval_count_per_path": int((paths["path_id"] == 0).sum()),
        "sampled_block_count": len(provenance),
        "minimum_block_candidate_count": int(provenance["candidate_count"].min()),
        "median_block_candidate_count": float(provenance["candidate_count"].median()),
    }
    return BootstrapResult(paths=paths, provenance=provenance, summary=summary)


def _validated_history(frame: pd.DataFrame) -> pd.DataFrame:
    history = ensure_canonical(frame, allow_empty=False)
    report = assess_quality(history, require_complete_days=True)
    if not report.is_valid:
        errors = ", ".join(issue.code for issue in report.issues if issue.severity == "error")
        raise BootstrapInputError(f"Historical prices failed quality validation: {errors}")
    return history


def detect_source_eras(historical_prices: pd.DataFrame) -> list[SourceEra]:
    """Split a canonical history into maximal contiguous single-resolution runs.

    A resolution change or a gap in market days both end an era, because a block sampled
    across either would not be a contiguous run of one regime. This is a structural
    reading of the frame; the deterministic quality gate is applied separately by
    ``generate_seasonal_bootstrap_paths``, which in practice already refuses a
    non-contiguous history, so a real accepted history separates eras by resolution alone.
    """

    history = ensure_canonical(historical_prices, allow_empty=False)
    working = history.assign(market_day=history["delivery_start_market"].dt.date)
    per_day = working.groupby("market_day", sort=True)["duration_hours"].agg(["nunique", "first"])
    mixed = per_day.loc[per_day["nunique"] > 1]
    if not mixed.empty:
        raise BootstrapInputError(
            f"Market day {mixed.index[0]} mixes interval resolutions; the bootstrap "
            "requires one resolution per market day"
        )

    eras: list[SourceEra] = []
    current_days: list[date] = []
    current_minutes: int | None = None
    for market_day, duration_hours in per_day["first"].items():
        minutes = int(round(float(duration_hours) * 60))
        contiguous = bool(current_days) and market_day == current_days[-1] + timedelta(days=1)
        if current_minutes == minutes and contiguous:
            current_days.append(market_day)
            continue
        if current_days and current_minutes is not None:
            eras.append(_era(current_minutes, current_days))
        current_days = [market_day]
        current_minutes = minutes
    if current_days and current_minutes is not None:
        eras.append(_era(current_minutes, current_days))
    return eras


def _era(resolution_minutes: int, days: list[date]) -> SourceEra:
    return SourceEra(
        resolution_minutes=resolution_minutes,
        first_day=days[0],
        last_day=days[-1],
        market_day_count=len(days),
    )


def select_source_era(eras: list[SourceEra], config: BootstrapConfig) -> SourceEra:
    """Resolve exactly one era, requiring a declaration when the history holds several."""

    if not eras:
        raise BootstrapInputError("Historical prices contain no market days")

    declared = config.source_resolution_minutes
    if declared is None:
        if len(eras) == 1:
            return eras[0]
        available = "; ".join(era.label for era in eras)
        raise BootstrapInputError(
            "Historical prices contain more than one source era, so the sampling era must "
            "be declared with source_resolution_minutes rather than chosen implicitly. "
            f"Available eras: {available}"
        )

    matching = [era for era in eras if era.resolution_minutes == declared]
    if config.source_start_day is not None:
        matching = [era for era in matching if era.last_day >= config.source_start_day]
    if config.source_end_day is not None:
        matching = [era for era in matching if era.first_day < config.source_end_day]

    if not matching:
        available = "; ".join(era.label for era in eras) or "none"
        raise BootstrapInputError(
            f"No source era matches the declared selection ({declared} minutes"
            f"{_window_text(config)}). Available eras: {available}"
        )
    if len(matching) > 1:
        available = "; ".join(era.label for era in matching)
        raise BootstrapInputError(
            "The declared selection matches more than one source era; narrow it with "
            f"source_start_day and source_end_day. Matching eras: {available}"
        )
    return matching[0]


def _window_text(config: BootstrapConfig) -> str:
    if config.source_start_day is None and config.source_end_day is None:
        return ""
    start = "-inf" if config.source_start_day is None else config.source_start_day.isoformat()
    end = "+inf" if config.source_end_day is None else config.source_end_day.isoformat()
    return f", {start}..{end}"


def _restrict_to_era(
    history: pd.DataFrame, era: SourceEra, config: BootstrapConfig
) -> tuple[pd.DataFrame, date, date]:
    market_day = history["delivery_start_market"].dt.date
    first_day = era.first_day
    last_day = era.last_day
    if config.source_start_day is not None and config.source_start_day > first_day:
        first_day = config.source_start_day
    if config.source_end_day is not None:
        narrowed = config.source_end_day - timedelta(days=1)
        if narrowed < last_day:
            last_day = narrowed
    if last_day < first_day:
        raise BootstrapInputError(
            f"The declared source window leaves no market day inside era {era.label}"
        )
    selected = history.loc[market_day.between(first_day, last_day)].reset_index(drop=True)
    if selected.empty:
        raise BootstrapInputError(
            f"The declared source window leaves no market day inside era {era.label}"
        )
    return selected, first_day, last_day


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
