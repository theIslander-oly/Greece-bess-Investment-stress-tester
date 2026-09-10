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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .availability_audit import expected_feature_interval_count
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
    "observation_semantics_version",
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
    missing_receipts = [field for field in REQUIRED_RECEIPT_FIELDS if field not in summary]
    if missing_receipts:
        raise FeatureShardError(
            f"{summary_path} is missing retrieval receipt fields: "
            f"{', '.join(missing_receipts)}. A shard that cannot say when its messages arrived "
            "cannot contribute to the combined table's receipt window and must be rebuilt."
        )
    missing_identity = [field for field in IDENTITY_FIELDS if field not in summary]
    if missing_identity:
        raise FeatureShardError(
            f"{summary_path} is missing retrieval identity fields: "
            f"{', '.join(missing_identity)}. A shard without an explicit feature semantics "
            "and observation semantics identity predates the current value and receipt-time "
            "contracts and must be rebuilt."
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


#: Fields a shard summary must carry for its coverage to be reconcilable against what it holds.
#: ``per_delivery_day`` names the days it says it built and ``excluded_day_count`` how many it
#: says it left out; without both, a shard states a window and a row count and nothing that ties
#: the two together.
REQUIRED_COVERAGE_FIELDS = ("per_delivery_day", "excluded_day_count")


@dataclass(frozen=True)
class ShardReconciliation:
    """What one shard actually holds, checked against what its summary claims."""

    built_days: tuple[date, ...]
    excluded_days: tuple[date, ...]
    row_counts: dict[date, int]
    #: The native resolution each stored day declares, read from the rows rather than assumed.
    resolutions: dict[date, int]


def _summary_days(summary: Mapping[str, Any], field: str, key: str) -> list[date]:
    entries = summary.get(field)
    if not isinstance(entries, list):
        return []
    days: list[date] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = entry.get(key)
        if value is None:
            continue
        days.append(date.fromisoformat(str(value)))
    return days


def reconcile_shard(shard: FeatureShard, frame: pd.DataFrame) -> ShardReconciliation:
    """Check one shard's declared window, claimed days and stored rows against each other.

    Three things must agree before a shard can contribute to a combined table: the days its
    frame actually holds, the days its summary says it built, and the days its summary says it
    excluded. The declared window is the fourth, and built and excluded days must partition it
    exactly.

    Until now none of this was checked. A shard whose CSV lost a day still declared its original
    window, still listed the day among those it built and still reported zero exclusions, and the
    combiner repeated all three claims. Downstream that is indistinguishable from a provider that
    published nothing for the day — the one thing this project records by name and never infers.
    """

    missing_coverage = [field for field in REQUIRED_COVERAGE_FIELDS if field not in shard.summary]
    if missing_coverage:
        raise FeatureShardError(
            f"{shard.features} is missing coverage fields: {', '.join(missing_coverage)}. A "
            "shard states a window and a row count; without the days it built and the count it "
            "excluded, nothing ties the two together and it must be rebuilt."
        )

    declared = _declared_days(shard)
    stored = _stored_days(frame)
    claimed_built = sorted(set(_summary_days(shard.summary, "per_delivery_day", "delivery_day")))
    claimed_excluded = sorted(
        set(_summary_days(shard.summary, "excluded_days_by_cause", "market_day"))
    )

    _refuse_rows_outside_window(shard, stored, declared)
    _refuse_unclaimed_or_missing_days(shard, stored, claimed_built)
    _refuse_unpartitioned_window(shard, declared, claimed_built, claimed_excluded)
    _refuse_uncounted_exclusions(shard, claimed_built, claimed_excluded, declared)

    return ShardReconciliation(
        built_days=tuple(claimed_built),
        excluded_days=tuple(claimed_excluded),
        row_counts={day: int((frame["market_day"] == day).sum()) for day in stored},
        resolutions={day: _day_resolution(shard, frame, day) for day in stored},
    )


def _day_resolution(shard: FeatureShard, frame: pd.DataFrame, day: date) -> int:
    """Return the one native resolution a stored day declares, refusing more than one.

    The resolution is read from the rows rather than assumed to be hourly: what a day owes
    depends on it, and a day carrying two resolutions has no single answer.
    """

    declared = {int(value) for value in frame.loc[frame["market_day"] == day, "resolution_minutes"]}
    if len(declared) != 1:
        raise FeatureShardError(
            f"{shard.features} stores {day.isoformat()} at resolutions "
            f"{sorted(declared)}. One delivery day carries one native resolution; what the day "
            "owes cannot be established from two."
        )
    return declared.pop()


def _declared_days(shard: FeatureShard) -> list[date]:
    days: list[date] = []
    day = shard.start_day
    while day <= shard.end_day:
        days.append(day)
        day += timedelta(days=1)
    return days


def _stored_days(frame: pd.DataFrame) -> list[date]:
    if frame.empty:
        return []
    return sorted({value for value in frame["market_day"] if isinstance(value, date)})


def _refuse_rows_outside_window(
    shard: FeatureShard, stored: list[date], declared: list[date]
) -> None:
    outside = sorted(set(stored) - set(declared))
    if outside:
        raise FeatureShardError(
            f"{shard.features} holds rows for {_name_days(outside)}, outside the window it "
            f"declares ({shard.start_day.isoformat()}..{shard.end_day.isoformat()}). A shard's "
            "window is what the combiner tiles, so a row beyond it would enter the combined "
            "table without any shard accounting for it."
        )


def _refuse_unclaimed_or_missing_days(
    shard: FeatureShard, stored: list[date], claimed_built: list[date]
) -> None:
    stored_set, claimed_set = set(stored), set(claimed_built)
    absent = sorted(claimed_set - stored_set)
    if absent:
        raise FeatureShardError(
            f"{shard.features} records {_name_days(absent)} among the delivery days it built, "
            "but holds no row for them. A day that was built has rows; a day that was not is "
            "excluded by a named cause. A summary claiming both at once cannot be combined, "
            "because downstream the missing day is indistinguishable from a provider that "
            "published nothing."
        )
    unclaimed = sorted(stored_set - claimed_set)
    if unclaimed:
        raise FeatureShardError(
            f"{shard.features} holds rows for {_name_days(unclaimed)}, which its summary does "
            "not record among the delivery days it built. Every stored day is accounted for by "
            "the record of the retrieval that produced it, or the table states more than the "
            "retrieval established."
        )


def _refuse_unpartitioned_window(
    shard: FeatureShard,
    declared: list[date],
    claimed_built: list[date],
    claimed_excluded: list[date],
) -> None:
    # The listed exclusions are a capped sample, so the partition cannot be checked as a set:
    # a shard that hit its cap legitimately lists fewer days than it excluded, and demanding
    # that built and listed days cover the window would refuse a correct shard. The partition is
    # therefore established by the count arithmetic in `_refuse_uncounted_exclusions`, and what
    # is checked here is every claim the listed entries do make.
    overlap = sorted(set(claimed_built) & set(claimed_excluded))
    if overlap:
        raise FeatureShardError(
            f"{shard.features} records {_name_days(overlap)} as both built and excluded. A "
            "delivery day is one or the other."
        )
    beyond = sorted((set(claimed_built) | set(claimed_excluded)) - set(declared))
    if beyond:
        raise FeatureShardError(
            f"{shard.features} accounts for {_name_days(beyond)}, outside the window it "
            f"declares ({shard.start_day.isoformat()}..{shard.end_day.isoformat()})."
        )


def _refuse_uncounted_exclusions(
    shard: FeatureShard,
    claimed_built: list[date],
    claimed_excluded: list[date],
    declared: list[date],
) -> None:
    # The listed exclusions are capped, so the count is the authority and the list is a sample.
    # Reconciliation therefore checks the count against the window arithmetic rather than
    # against the length of the list, which would pass trivially on any shard that hit the cap.
    reported = shard.summary.get("excluded_day_count")
    if not isinstance(reported, int):
        raise FeatureShardError(
            f"{shard.features} does not report an integer excluded_day_count. The count is the "
            "authority on how many days were left out; the listed causes are a capped sample."
        )
    implied = len(declared) - len(claimed_built)
    if reported != implied:
        raise FeatureShardError(
            f"{shard.features} declares a {len(declared)}-day window and records "
            f"{len(claimed_built)} built days, which leaves {implied} unbuilt, but reports "
            f"excluded_day_count {reported}. Built days and days excluded by name must "
            "partition the declared window exactly; the counts must reconcile even when the "
            "listed causes are capped, or an excluded day is invisible in the aggregate."
        )
    if len(claimed_excluded) > reported:
        raise FeatureShardError(
            f"{shard.features} lists {len(claimed_excluded)} excluded days but reports only "
            f"{reported}."
        )


def _name_days(days: Sequence[date]) -> str:
    """Name up to four days, then say how many more there are."""

    shown = ", ".join(day.isoformat() for day in days[:4])
    return shown if len(days) <= 4 else f"{shown} and {len(days) - 4} more"


#: Instant fields every shard summary must carry for the combined summary to describe when the
#: table's values were observed. They are required rather than defaulted: a shard that cannot
#: say when its messages arrived cannot contribute to a receipt window, and silently recording
#: ``None`` would leave the combined table claiming a span it never established.
REQUIRED_RECEIPT_FIELDS = (
    "run_started_at_utc",
    "first_message_received_at_utc",
    "last_message_received_at_utc",
)


def _shard_receipt(shards: list[FeatureShard], field: str, *, latest: bool) -> str:
    """Return the earliest or latest of one receipt field across every shard."""

    instants = [pd.Timestamp(str(shard.summary[field])) for shard in shards]
    chosen = max(instants) if latest else min(instants)
    return str(chosen.isoformat())


def _refuse_contradictory_provenance(
    shards: Sequence[FeatureShard], records: Sequence[Mapping[str, Any]]
) -> None:
    """Refuse provenance that contradicts itself or the shards it claims to describe.

    Two records naming the same local path must agree on the digest of what was retrieved.
    Disagreement is not a duplicate to be de-duplicated: it says two different byte sequences
    were retrieved under one name, and nothing downstream could tell which one produced a row.

    The document count each shard reports must also match the records its manifest holds, so a
    manifest cannot be silently shorter than the retrieval it describes.
    """

    digests: dict[str, str] = {}
    for record in records:
        path = record.get("local_path")
        digest = record.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            raise FeatureShardError(
                "An official combination requires every retrieval record to name a local path "
                f"and a sha256; {record!r} does not."
            )
        seen = digests.setdefault(path, digest)
        if seen != digest:
            raise FeatureShardError(
                f"Two retrieval records name {path} with different digests ({seen} and "
                f"{digest}). That is two different byte sequences under one name, and no later "
                "stage could tell which of them produced a row."
            )

    for shard in shards:
        reported = shard.summary.get("document_count")
        if not isinstance(reported, int):
            raise FeatureShardError(
                f"{shard.features} does not report an integer document_count, so its manifest "
                "cannot be checked against the retrieval it describes."
            )
        manifest = shard.manifest or {}
        entries = manifest.get("files") or manifest.get("records") or []
        held = len([entry for entry in entries if isinstance(entry, dict)])
        if held != reported:
            raise FeatureShardError(
                f"{shard.features} reports {reported} retrieved documents but its manifest "
                f"holds {held}. A manifest shorter than the retrieval it describes leaves rows "
                "with no record of where they came from."
            )


def _refuse_incomplete_days(
    shards: Sequence[FeatureShard], reconciliations: Sequence[ShardReconciliation]
) -> None:
    """Refuse a built day that does not hold one row per variable per delivery interval.

    A day is built completely or not at all, so a built day carries the market day's own
    interval count for every requested variable — 23, 24 or 25 hours across a DST boundary,
    decided by the day and by the resolution its own rows declare rather than assumed. A short
    day here would reach the availability audit as thin coverage rather than as a day with a
    named cause, which is exactly the distinction this project refuses to blur.
    """

    for shard, reconciliation in zip(shards, reconciliations, strict=True):
        variables = shard.summary.get("variables")
        variable_count = len(variables) if isinstance(variables, list) else 0
        if not variable_count:
            raise FeatureShardError(
                f"{shard.features} records no variable list, so the rows a built day owes "
                "cannot be established."
            )
        for day, rows in sorted(reconciliation.row_counts.items()):
            resolution = reconciliation.resolutions[day]
            expected = expected_feature_interval_count(day, resolution)
            owed = expected * variable_count
            if rows != owed:
                raise FeatureShardError(
                    f"{shard.features} holds {rows} rows for {day.isoformat()} but that market "
                    f"day owes {owed}: {expected} intervals of {resolution} minutes for each of "
                    f"{variable_count} variables. A day is built completely or excluded by "
                    "name; a partial day would reach the availability audit as thin coverage "
                    "rather than as a day with a cause."
                )


def combine_feature_shards(
    shard_features: list[Path], *, created_at_utc: str, official: bool = False
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    """Combine shards that tile one window into one validated feature table.

    Returns the combined frame, the combined retrieval summary and the combined retrieval
    records. Raises :class:`FeatureShardError` unless the shards share one retrieval identity,
    cover every day of the window exactly once, and each hold exactly the days their own
    retrieval recorded.

    ``official`` additionally requires every shard to carry the retrieval manifest that traces
    its rows to the source messages they were built from. It is off by default because a
    synthetic fixture legitimately has no provenance to record, and on for anything that will
    support an acceptance document: a combined table offered as official evidence cannot rest on
    a slice whose messages nothing accounts for.
    """

    if not shard_features:
        raise FeatureShardError("At least one shard is required; there is nothing to combine.")
    shards = [read_feature_shard(path) for path in shard_features]
    _refuse_mixed_identity(shards)
    start_day, end_day = _refuse_untiled_window(shards)

    ordered = sorted(shards, key=lambda shard: shard.start_day)
    frames = [read_point_in_time_csv(shard.features) for shard in ordered]
    # Each shard is reconciled against what it actually holds before any of it is concatenated.
    # Tiling the declared windows proves the shards *claim* to cover the window once; it says
    # nothing about whether each one holds the days it claims.
    reconciliations = [
        reconcile_shard(shard, frame)
        for shard, frame in zip(ordered, frames, strict=True)
    ]
    _refuse_incomplete_days(ordered, reconciliations)
    combined = ensure_point_in_time(pd.concat(frames, ignore_index=True))

    records: list[dict[str, Any]] = []
    for shard in ordered:
        if shard.manifest is None:
            if official:
                raise FeatureShardError(
                    f"{shard.features} has no retrieval manifest beside it. An official "
                    "combination traces every row to the source messages it was built from, and "
                    "a slice whose messages nothing accounts for cannot support an acceptance "
                    "document."
                )
            continue
        entries = shard.manifest.get("files") or shard.manifest.get("records") or []
        if not isinstance(entries, list) or (official and not entries):
            raise FeatureShardError(
                f"{shard.features} has a retrieval manifest that records no source message. A "
                "shard that produced rows retrieved something to produce them from."
            )
        records.extend(entry for entry in entries if isinstance(entry, dict))
    if official:
        _refuse_contradictory_provenance(ordered, records)

    first = ordered[0].summary
    # The built-day count is now the reconciled one: every day counted here was proved to hold
    # rows in its shard and to be recorded as built by that shard's own retrieval.
    built_days = [day for reconciliation in reconciliations for day in reconciliation.built_days]

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
        "observation_semantics_version": first.get("observation_semantics_version"),
        "decoded_message_contract": first.get("decoded_message_contract"),
        "start_day": start_day.isoformat(),
        "end_day": end_day.isoformat(),
        # When the shards were put back together, which is not when any of them observed
        # anything. The receipt window below spans the shards' own message receipts, so a reader
        # can see when the combined table's earliest and latest values actually arrived.
        "combined_at_utc": created_at_utc,
        "first_message_received_at_utc": _shard_receipt(
            ordered, "first_message_received_at_utc", latest=False
        ),
        "last_message_received_at_utc": _shard_receipt(
            ordered, "last_message_received_at_utc", latest=True
        ),
        "built_day_count": len(built_days),
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
                "run_started_at_utc": shard.summary.get("run_started_at_utc"),
                "first_message_received_at_utc": shard.summary.get(
                    "first_message_received_at_utc"
                ),
                "last_message_received_at_utc": shard.summary.get(
                    "last_message_received_at_utc"
                ),
                "feature_row_count": shard.summary.get("feature_row_count"),
                "document_count": shard.summary.get("document_count"),
            }
            for shard in ordered
        ],
        "shard_count": len(ordered),
    }
    return combined, summary, records
