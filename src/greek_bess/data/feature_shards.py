"""Combining independently retrieved point-in-time feature shards into one table.

The v0.9 retrieval is one HTTPS round trip per forecast step per delivery day, and the source
spike's own numbers make the cost of the declared window concrete: the first dispatched run
measured 72 seconds per delivery day, so the 2,006 declared days need roughly forty hours of
continuous retrieval against a job that may run for four. The window cannot be shortened —
it is pre-registered — and the retrieval client must not be made concurrent on the way to an
accepted artifact, because changing how an evidence path talks to the provider is a change to
the evidence. What is left is to retrieve disjoint slices of the same window separately and
put them back together.

That is only sound because a delivery day is retrieved independently of every other: the
client reads each day's own forecast cycle and derives nothing from a neighbour. This module
holds the invariant that makes the recombination checkable rather than assumed — the shards
must **tile** the window, covering every day once and no day twice — and refuses anything
else instead of picking a winner. Two retrievals of one day are two revisions of the same
observation, and choosing between them is a decision the point-in-time join makes under a
declared cutoff, never a decision a concatenation makes silently.

Nothing here retrieves, grades, accepts or values anything. It reassembles bytes that were
already retrieved and re-runs the same schema validation the retrieval ran.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .point_in_time import ensure_point_in_time, read_point_in_time_csv


class FeatureShardError(ValueError):
    """A set of shards cannot be combined into one feature table."""


#: Summary fields that identify what a shard retrieved rather than how much of it. Two shards
#: that disagree on any of these did not retrieve slices of one window, and combining them
#: would produce a table whose rows mean different things without saying so.
IDENTITY_FIELDS = (
    "method",
    "source",
    "variables",
    "geography_id",
    "geography",
    "feature_semantics_version",
    "decoded_message_contract",
)


@dataclass(frozen=True)
class FeatureShard:
    """One retrieved slice of the declared window, with the summary that identifies it."""

    features: Path
    summary: dict[str, Any]
    manifest: dict[str, Any] | None

    @property
    def start_day(self) -> date:
        return date.fromisoformat(str(self.summary["start_day"]))

    @property
    def end_day(self) -> date:
        return date.fromisoformat(str(self.summary["end_day"]))

    @property
    def identity(self) -> tuple[Any, ...]:
        return tuple(
            json.dumps(self.summary.get(field), sort_keys=True) for field in IDENTITY_FIELDS
        )


def read_feature_shard(features: Path) -> FeatureShard:
    """Read one shard's summary and retrieval manifest from the paths the retrieval writes."""

    summary_path = features.with_suffix(".summary.json")
    if not summary_path.is_file():
        raise FeatureShardError(
            f"{features} has no retrieval summary at {summary_path}. A shard is combined on the "
            "evidence of what it retrieved, not on the presence of a CSV beside it."
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise FeatureShardError(f"{summary_path} does not hold a retrieval summary object")
    missing_identity = [field for field in IDENTITY_FIELDS if field not in summary]
    if missing_identity:
        raise FeatureShardError(
            f"{summary_path} is missing retrieval identity fields: "
            f"{', '.join(missing_identity)}. A shard without an explicit feature semantics "
            "identity predates the current value contract and must be rebuilt."
        )

    manifest: dict[str, Any] | None = None
    for candidate in (
        features.with_name(features.stem + ".retrieval_manifest.json"),
        features.with_name("retrieval_manifest.json"),
    ):
        if candidate.is_file():
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest = loaded
            break
    return FeatureShard(features=features, summary=summary, manifest=manifest)


def _refuse_mixed_identity(shards: list[FeatureShard]) -> None:
    first = shards[0]
    for shard in shards[1:]:
        if shard.identity != first.identity:
            differing = [
                field
                for field in IDENTITY_FIELDS
                if json.dumps(shard.summary.get(field), sort_keys=True)
                != json.dumps(first.summary.get(field), sort_keys=True)
            ]
            raise FeatureShardError(
                f"{shard.features} and {first.features} disagree on {', '.join(differing)}. "
                "Shards of one window are retrieved under one source, one variable set and one "
                "declared geography; combining tables that do not share them would give one "
                "column two meanings without saying so."
            )


def _refuse_untiled_window(shards: list[FeatureShard]) -> tuple[date, date]:
    ordered = sorted(shards, key=lambda shard: (shard.start_day, shard.end_day))
    for shard in ordered:
        if shard.end_day < shard.start_day:
            raise FeatureShardError(
                f"{shard.features} declares the window "
                f"{shard.start_day.isoformat()}..{shard.end_day.isoformat()}, which ends before "
                "it starts."
            )
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        if later.start_day <= earlier.end_day:
            raise FeatureShardError(
                f"{earlier.features} covers {earlier.start_day.isoformat()}.."
                f"{earlier.end_day.isoformat()} and {later.features} covers "
                f"{later.start_day.isoformat()}..{later.end_day.isoformat()}; they overlap. Two "
                "retrievals of one delivery day are two revisions of the same observation, and "
                "choosing between them is the point-in-time join's decision under a declared "
                "cutoff, not a concatenation's."
            )
        if later.start_day != earlier.end_day + timedelta(days=1):
            missing_from = earlier.end_day + timedelta(days=1)
            missing_to = later.start_day - timedelta(days=1)
            raise FeatureShardError(
                f"No shard covers {missing_from.isoformat()}..{missing_to.isoformat()}. The "
                "shards must tile the declared window: a silently short window would be "
                "indistinguishable downstream from a provider that published nothing."
            )
    return ordered[0].start_day, ordered[-1].end_day


def combine_feature_shards(
    shard_features: list[Path], *, created_at_utc: str
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    """Combine shards that tile one window into one validated feature table.

    Returns the combined frame, the combined retrieval summary and the combined retrieval
    records. Raises :class:`FeatureShardError` unless the shards share one retrieval identity
    and cover every day of the window exactly once.
    """

    if not shard_features:
        raise FeatureShardError("At least one shard is required; there is nothing to combine.")
    shards = [read_feature_shard(path) for path in shard_features]
    _refuse_mixed_identity(shards)
    start_day, end_day = _refuse_untiled_window(shards)

    ordered = sorted(shards, key=lambda shard: shard.start_day)
    frames = [read_point_in_time_csv(shard.features) for shard in ordered]
    combined = ensure_point_in_time(pd.concat(frames, ignore_index=True))

    records: list[dict[str, Any]] = []
    for shard in ordered:
        if shard.manifest is None:
            continue
        entries = shard.manifest.get("files") or shard.manifest.get("records") or []
        if isinstance(entries, list):
            records.extend(entry for entry in entries if isinstance(entry, dict))

    first = ordered[0].summary
    # A shard caps the day-by-day list it writes but not its counts, so the combined counts are
    # summed from the shards' own totals rather than from the capped lists. Recounting the lists
    # would silently under-report exclusions on any shard that hit the cap, and an under-reported
    # exclusion is a delivery day missing from the window with nothing saying so.
    excluded: list[dict[str, Any]] = []
    excluded_count = 0
    cause_counts: Counter[str] = Counter()
    for shard in ordered:
        shard_excluded = shard.summary.get("excluded_days_by_cause")
        listed = (
            [item for item in shard_excluded if isinstance(item, dict)]
            if isinstance(shard_excluded, list)
            else []
        )
        excluded.extend(listed)
        shard_count = shard.summary.get("excluded_day_count")
        excluded_count += int(shard_count) if isinstance(shard_count, int) else len(listed)
        shard_causes = shard.summary.get("excluded_day_count_by_cause")
        if isinstance(shard_causes, dict):
            for cause, count in shard_causes.items():
                cause_counts[str(cause)] += int(count)
        else:
            cause_counts.update(str(item.get("cause")) for item in listed)

    per_day: list[dict[str, Any]] = []
    for shard in ordered:
        shard_days = shard.summary.get("per_delivery_day")
        if isinstance(shard_days, list):
            per_day.extend(item for item in shard_days if isinstance(item, dict))

    summary: dict[str, Any] = {
        "result_label": first.get("result_label"),
        "method": first.get("method"),
        "source": first.get("source"),
        "variables": first.get("variables"),
        "geography_id": first.get("geography_id"),
        "geography": first.get("geography"),
        "feature_semantics_version": first.get("feature_semantics_version"),
        "decoded_message_contract": first.get("decoded_message_contract"),
        "start_day": start_day.isoformat(),
        "end_day": end_day.isoformat(),
        "retrieved_at_utc": created_at_utc,
        "built_day_count": len(per_day),
        "excluded_day_count": excluded_count,
        "excluded_day_count_by_cause": dict(cause_counts),
        "excluded_days_by_cause": excluded[:100],
        "feature_row_count": int(len(combined)),
        "document_count": len(records),
        "retrieved_byte_count": sum(
            int(entry.get("size_bytes") or 0) for entry in records
        ),
        "attribution": first.get("attribution"),
        "availability_classification": "requires_point_in_time_acceptance",
        "per_delivery_day": per_day,
        # The recombination is itself evidence: which slices were retrieved, when, and by what
        # run. A reader who doubts the table can re-retrieve any one slice on its own.
        "combined_from_shards": [
            {
                "features": shard.features.name,
                "start_day": shard.start_day.isoformat(),
                "end_day": shard.end_day.isoformat(),
                "retrieved_at_utc": shard.summary.get("retrieved_at_utc"),
                "feature_row_count": shard.summary.get("feature_row_count"),
                "document_count": shard.summary.get("document_count"),
            }
            for shard in ordered
        ],
        "shard_count": len(ordered),
    }
    return combined, summary, records
