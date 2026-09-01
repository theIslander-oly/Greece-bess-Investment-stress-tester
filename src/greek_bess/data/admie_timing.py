"""Pre-auction publication-timing acceptance for quarantined ADMIE forecast files.

**Retained but unused.** ADMIE load and RES forecasts were removed from scope on 2026-09-01 and
the 2026-08-26 quarantine was closed as never accepted: no ADMIE field ever entered forecasting,
and a passing audit would no longer admit one. This module is kept, tested and runnable so that a
future operator declaration could be tested without rebuilding it. The description below is of
what the audit does, not of a capability the project currently uses.

The 2026-08-26 decision kept ADMIE load and RES forecasts retrieved and timestamped but
unparsed until their publication sequence was proven to precede the target-day bid decision.
Retrieval manifests carry that quarantine as the ``requires_pre_auction_timing_validation``
label. This module turns the label into an executable audit: it reads retrieval manifests the
ADMIE client already writes, compares each file's publication time against a **declared**
day-ahead gate closure for every delivery day the file covers, and reports what the evidence
does and does not establish.

Three properties of the audit matter more than its arithmetic.

**The gate closure is declared, never assumed.** It has no default and no built-in constant.
A closure time is a market rule that can change across the 2020-2026 history, so a schedule is
one or more dated regimes, each naming the clock it is stated on and carrying a required
reference to the rule it came from. A delivery day earlier than the first regime is refused
rather than audited against a rule that was not in force.

**An asserted timestamp is weaker than a witnessed one.** ``file_published`` is provider
metadata read at retrieval time; it is what ADMIE says about the past, not an independent
observation of when the file became available. When the retrieval itself happened before the
gate closure of the delivery day in question, the catalog entry is a contemporaneous witness
that the file existed by then, and the audit records that separately. Evidence of the weaker
kind is reported as weaker, never quietly promoted.

**Timing acceptance is not format acceptance.** Proving a file was published in time says
nothing about its contents, its schema stability, or whether the published numbers are the
ones a bidder acted on. Passing this audit does not lift the quarantine on its own, and the
summary says so in its own output rather than only in documentation.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

ADMIE_TIMING_LABEL = (
    "Pre-auction publication-timing audit of quarantined ADMIE forecast files; data-acceptance "
    "evidence about publication timing only, not a file-format acceptance, a forecast or "
    "investment evidence."
)

ADMIE_TIMING_POLICY = (
    "An ADMIE forecast file is usable as a causal day-ahead feature for a delivery day only if "
    "it was published strictly before that day's declared gate closure. The gate closure is "
    "declared as one or more dated regimes with no default, each naming its clock and the "
    "market rule it comes from, because the rule can change across the audited history. A "
    "publication exactly at the closure instant counts as late. The latest revision published "
    "strictly before closure is the decision-time revision, and it is the only revision a "
    "backtest may read: a later revision of the same delivery day is post-decision "
    "information. A retrieval performed before the closure witnesses availability "
    "contemporaneously; a provider publication timestamp read afterwards only asserts it, and "
    "the two are reported separately. This audit establishes timing alone. It does not accept "
    "any file format, schema, or value, and it does not lift the forecast-feature quarantine."
)

TIMING_ESTABLISHES_NOT = (
    "the file format, column schema or units of any audited file",
    "that the published values are the values a bidder observed",
    "that any audited variable carries forecasting skill",
    "that a file absent from the audited manifests was never published",
)

WITNESSED_PRE_GATE = "witnessed_pre_gate"
ASSERTED_PRE_GATE = "asserted_pre_gate"
NO_PRE_GATE_PUBLICATION = "no_pre_gate_publication"
NO_RECORD = "no_record"

ACCEPTABLE_DAY_STATUSES = frozenset({WITNESSED_PRE_GATE, ASSERTED_PRE_GATE})

DECLARABLE_CLOSURE_TIMEZONES = frozenset({"Europe/Athens", "Europe/Brussels", "UTC"})

_REQUIRED_RECORD_FIELDS = (
    "source",
    "dataset",
    "source_url",
    "retrieved_at_utc",
    "sha256",
    "coverage_start",
    "coverage_end",
    "published_at_utc",
)


class AdmiePublicationTimingError(ValueError):
    """Raised when publication timing cannot be audited exactly as declared."""


@dataclass(frozen=True)
class GateClosureRegime:
    """One dated day-ahead gate-closure rule.

    ``closure_day_offset`` is counted in days from the delivery day and must not be positive:
    a closure on the delivery day itself or later would make the whole question moot. The
    ``reference`` is required so the rule behind an accepted day is on the record.
    """

    effective_from_delivery_day: date
    closure_day_offset: int
    closure_local_time: time
    closure_timezone: str
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.effective_from_delivery_day, date) or isinstance(
            self.effective_from_delivery_day, datetime
        ):
            raise AdmiePublicationTimingError(
                "effective_from_delivery_day must be a calendar date, not a timestamp"
            )
        if isinstance(self.closure_day_offset, bool) or not isinstance(
            self.closure_day_offset, int
        ):
            raise AdmiePublicationTimingError("closure_day_offset must be an integer")
        if self.closure_day_offset > 0:
            raise AdmiePublicationTimingError(
                "closure_day_offset must not be positive; a gate closing after the delivery "
                "day starts cannot bound a day-ahead decision"
            )
        if not isinstance(self.closure_local_time, time):
            raise AdmiePublicationTimingError("closure_local_time must be a time of day")
        if self.closure_local_time.tzinfo is not None:
            raise AdmiePublicationTimingError(
                "closure_local_time must be a naive time of day; declare its clock in "
                "closure_timezone"
            )
        if self.closure_timezone not in DECLARABLE_CLOSURE_TIMEZONES:
            allowed = ", ".join(sorted(DECLARABLE_CLOSURE_TIMEZONES))
            raise AdmiePublicationTimingError(
                f"closure_timezone must be one of: {allowed}"
            )
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise AdmiePublicationTimingError(
                "reference must name the market rule or publication the closure comes from"
            )

    def closure_utc(self, delivery_day: date) -> pd.Timestamp:
        """Return the closure instant in UTC for one delivery day."""

        naive = datetime.combine(
            delivery_day + timedelta(days=self.closure_day_offset), self.closure_local_time
        )
        try:
            localized = pd.Timestamp(naive).tz_localize(
                ZoneInfo(self.closure_timezone), nonexistent="raise", ambiguous="raise"
            )
        # pandas raises a pytz NonExistentTimeError/AmbiguousTimeError here, and pytz is a
        # transitive dependency this project does not import; the refusal is the same for
        # either, so the localization call is guarded rather than the exception class named.
        except Exception as exc:
            raise AdmiePublicationTimingError(
                f"Gate closure {self.closure_local_time.isoformat()} "
                f"{self.closure_timezone} does not exist exactly once on "
                f"{(delivery_day + timedelta(days=self.closure_day_offset)).isoformat()}; a "
                "daylight-saving transition makes the declared closure ambiguous and it is "
                "refused rather than guessed"
            ) from exc
        return localized.tz_convert("UTC")

    def to_dict(self) -> dict[str, Any]:
        return {
            "effective_from_delivery_day": self.effective_from_delivery_day.isoformat(),
            "closure_day_offset": int(self.closure_day_offset),
            "closure_local_time": self.closure_local_time.isoformat(),
            "closure_timezone": self.closure_timezone,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class GateClosureSchedule:
    """An ordered, dated sequence of declared gate-closure regimes."""

    schedule_id: str
    regimes: tuple[GateClosureRegime, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.schedule_id, str) or not self.schedule_id.strip():
            raise AdmiePublicationTimingError("schedule_id must be a non-empty string")
        if self.schedule_id != self.schedule_id.strip():
            raise AdmiePublicationTimingError("schedule_id must not have surrounding whitespace")
        if not isinstance(self.regimes, tuple) or not self.regimes:
            raise AdmiePublicationTimingError(
                "A gate-closure schedule must declare at least one regime; there is no default "
                "closure time"
            )
        for regime in self.regimes:
            if not isinstance(regime, GateClosureRegime):
                raise AdmiePublicationTimingError("Every regime must be a GateClosureRegime")
        days = [regime.effective_from_delivery_day for regime in self.regimes]
        if days != sorted(days):
            raise AdmiePublicationTimingError(
                "Gate-closure regimes must be declared in ascending effective_from_delivery_day "
                "order"
            )
        if len(set(days)) != len(days):
            raise AdmiePublicationTimingError(
                "Two gate-closure regimes share an effective_from_delivery_day; a delivery day "
                "would have two declared closures"
            )

    @classmethod
    def from_dict(cls, payload: object) -> GateClosureSchedule:
        if not isinstance(payload, Mapping):
            raise AdmiePublicationTimingError("Gate-closure schedule config must be one object")
        required = {"schedule_id", "regimes"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise AdmiePublicationTimingError(
                f"Unknown gate-closure schedule fields: {', '.join(unknown)}"
            )
        if missing:
            raise AdmiePublicationTimingError(
                f"Missing gate-closure schedule fields: {', '.join(missing)}"
            )
        declared = payload["regimes"]
        if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
            raise AdmiePublicationTimingError("regimes must be a non-empty list")
        return cls(
            schedule_id=str(payload["schedule_id"]),
            regimes=tuple(_regime_from_dict(entry) for entry in declared),
        )

    def regime_for(self, delivery_day: date) -> GateClosureRegime:
        selected: GateClosureRegime | None = None
        for regime in self.regimes:
            if regime.effective_from_delivery_day <= delivery_day:
                selected = regime
        if selected is None:
            raise AdmiePublicationTimingError(
                f"Delivery day {delivery_day.isoformat()} precedes the first declared "
                f"gate-closure regime ({self.regimes[0].effective_from_delivery_day.isoformat()}); "
                "a day is not audited against a rule that was not declared for it"
            )
        return selected

    def closure_utc(self, delivery_day: date) -> pd.Timestamp:
        return self.regime_for(delivery_day).closure_utc(delivery_day)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "regimes": [regime.to_dict() for regime in self.regimes],
        }


@dataclass(frozen=True)
class PublicationTimingAudit:
    """Per-observation evidence, per-delivery-day verdicts and the run summary."""

    observations: pd.DataFrame
    delivery_days: pd.DataFrame
    summary: dict[str, Any]


def read_retrieval_manifests(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Read one or more ADMIE retrieval manifests into a de-duplicated record list.

    The same file legitimately appears in two manifests when a window is retrieved twice. An
    identical record is kept once. Two disagreements are refused rather than resolved: the same
    URL carrying two different digests is a file the provider replaced in place, and the same
    URL carrying two different publication timestamps is a restated publication time. Either
    would change a verdict, and silently keeping the first copy read would hide it.
    """

    by_url: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or not isinstance(payload.get("records"), Sequence):
            raise AdmiePublicationTimingError(
                f"{path}: a retrieval manifest must be an object with a 'records' list"
            )
        for entry in payload["records"]:
            if not isinstance(entry, Mapping):
                raise AdmiePublicationTimingError(f"{path}: every manifest record must be object")
            record = dict(entry)
            url = str(record.get("source_url", ""))
            incumbent = by_url.get(url)
            if incumbent is None:
                by_url[url] = record
                ordered.append(record)
                continue
            if incumbent.get("sha256") != record.get("sha256"):
                raise AdmiePublicationTimingError(
                    f"ADMIE URL {url} carries two different sha256 digests across the supplied "
                    "manifests; the published file was replaced in place and the audit refuses "
                    "to choose between them"
                )
            if incumbent.get("published_at_utc") != record.get("published_at_utc"):
                raise AdmiePublicationTimingError(
                    f"ADMIE URL {url} carries two different publication timestamps across the "
                    f"supplied manifests ({incumbent.get('published_at_utc')} and "
                    f"{record.get('published_at_utc')}); a restated publication time can change "
                    "a verdict and is refused rather than resolved"
                )
    return ordered


def audit_admie_publication_timing(
    records: Sequence[Mapping[str, Any]],
    *,
    schedule: GateClosureSchedule,
    filetypes: Sequence[str],
    start_day: date,
    end_day: date,
) -> PublicationTimingAudit:
    """Audit declared gate-closure compliance for named ADMIE filetypes over a day window.

    Every requested filetype is audited over every delivery day in ``[start_day, end_day]``.
    A day with no covering record is reported as a gap, never assumed compliant, and every
    audited day carries the closure instant and the regime that produced it.
    """

    requested = _validate_filetypes(filetypes)
    if end_day < start_day:
        raise AdmiePublicationTimingError("end_day must not precede start_day")
    audited_days = [
        start_day + timedelta(days=offset) for offset in range((end_day - start_day).days + 1)
    ]
    closures = {day: schedule.closure_utc(day) for day in audited_days}

    observation_rows: list[dict[str, Any]] = []
    ignored_record_count = 0
    for record in records:
        parsed = _parse_record(record)
        if parsed["filetype"] not in requested:
            ignored_record_count += 1
            continue
        covered = [
            day
            for day in audited_days
            if parsed["coverage_start"] <= day <= parsed["coverage_end"]
        ]
        if not covered:
            ignored_record_count += 1
            continue
        for day in covered:
            observation_rows.append(_observation(parsed, day, closures[day], schedule))

    observations = _observation_frame(observation_rows)
    delivery_days = _delivery_day_frame(observations, requested, audited_days, closures, schedule)
    summary = _summary(
        observations=observations,
        delivery_days=delivery_days,
        schedule=schedule,
        requested=requested,
        start_day=start_day,
        end_day=end_day,
        ignored_record_count=ignored_record_count,
    )
    return PublicationTimingAudit(
        observations=observations, delivery_days=delivery_days, summary=summary
    )


def _regime_from_dict(payload: object) -> GateClosureRegime:
    if not isinstance(payload, Mapping):
        raise AdmiePublicationTimingError("Every gate-closure regime must be an object")
    required = {
        "effective_from_delivery_day",
        "closure_day_offset",
        "closure_local_time",
        "closure_timezone",
        "reference",
    }
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown:
        raise AdmiePublicationTimingError(
            f"Unknown gate-closure regime fields: {', '.join(unknown)}"
        )
    if missing:
        raise AdmiePublicationTimingError(
            f"Missing gate-closure regime fields: {', '.join(missing)}"
        )
    try:
        effective_from = date.fromisoformat(str(payload["effective_from_delivery_day"]))
        closure_time = time.fromisoformat(str(payload["closure_local_time"]))
    except ValueError as exc:
        raise AdmiePublicationTimingError(
            "effective_from_delivery_day must be an ISO date and closure_local_time an ISO time"
        ) from exc
    offset = payload["closure_day_offset"]
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise AdmiePublicationTimingError("closure_day_offset must be an integer")
    return GateClosureRegime(
        effective_from_delivery_day=effective_from,
        closure_day_offset=offset,
        closure_local_time=closure_time,
        closure_timezone=str(payload["closure_timezone"]),
        reference=str(payload["reference"]),
    )


def _validate_filetypes(filetypes: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(filetypes, Sequence) or isinstance(filetypes, (str, bytes)):
        raise AdmiePublicationTimingError("filetypes must be a list of ADMIE filetype names")
    cleaned = [str(name) for name in filetypes]
    if not cleaned:
        raise AdmiePublicationTimingError(
            "At least one ADMIE filetype must be named; the audit has no default filetype set"
        )
    for name in cleaned:
        if not name or name != name.strip():
            raise AdmiePublicationTimingError("Every filetype must be a non-empty trimmed name")
    duplicated = sorted({name for name in cleaned if cleaned.count(name) > 1})
    if duplicated:
        raise AdmiePublicationTimingError(
            f"Duplicate filetypes requested: {', '.join(duplicated)}"
        )
    return tuple(cleaned)


def _parse_record(record: Mapping[str, Any]) -> dict[str, Any]:
    missing = sorted(name for name in _REQUIRED_RECORD_FIELDS if record.get(name) is None)
    if missing:
        raise AdmiePublicationTimingError(
            f"ADMIE retrieval record is missing required fields: {', '.join(missing)}"
        )
    if str(record["source"]) != "admie":
        raise AdmiePublicationTimingError(
            f"Record for {record['source_url']} is not an ADMIE record (source="
            f"{record['source']!r}); this audit reads ADMIE retrieval manifests only"
        )
    published = _aware_timestamp(record["published_at_utc"], "published_at_utc")
    retrieved = _aware_timestamp(record["retrieved_at_utc"], "retrieved_at_utc")
    if published > retrieved:
        raise AdmiePublicationTimingError(
            f"{record['source_url']}: published_at_utc {published.isoformat()} is later than "
            f"retrieved_at_utc {retrieved.isoformat()}; a file cannot be retrieved before it "
            "was published"
        )
    try:
        coverage_start = date.fromisoformat(str(record["coverage_start"]))
        coverage_end = date.fromisoformat(str(record["coverage_end"]))
    except ValueError as exc:
        raise AdmiePublicationTimingError(
            f"{record['source_url']}: coverage_start and coverage_end must be ISO dates"
        ) from exc
    if coverage_end < coverage_start:
        raise AdmiePublicationTimingError(
            f"{record['source_url']}: coverage_end precedes coverage_start"
        )
    revision = record.get("revision")
    if revision is not None and (isinstance(revision, bool) or not isinstance(revision, int)):
        raise AdmiePublicationTimingError(
            f"{record['source_url']}: revision must be an integer or absent"
        )
    return {
        "filetype": str(record["dataset"]),
        "source_url": str(record["source_url"]),
        "sha256": str(record["sha256"]),
        "size_bytes": record.get("size_bytes"),
        "revision": revision,
        "published_at_source": record.get("published_at_source"),
        "published_at_utc": published,
        "retrieved_at_utc": retrieved,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "availability_classification": str(
            record.get("availability_classification", "not_assessed")
        ),
    }


def _aware_timestamp(value: object, field: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(str(value))
    except ValueError as exc:
        raise AdmiePublicationTimingError(f"{field} must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None:
        raise AdmiePublicationTimingError(
            f"{field} must be timezone aware; a naive publication time cannot be compared with "
            "a gate closure"
        )
    return timestamp.tz_convert("UTC")


def _observation(
    parsed: Mapping[str, Any],
    delivery_day: date,
    closure: pd.Timestamp,
    schedule: GateClosureSchedule,
) -> dict[str, Any]:
    regime = schedule.regime_for(delivery_day)
    published: pd.Timestamp = parsed["published_at_utc"]
    retrieved: pd.Timestamp = parsed["retrieved_at_utc"]
    before_gate = bool(published < closure)
    witnessed = bool(before_gate and retrieved < closure)
    return {
        "filetype": parsed["filetype"],
        "delivery_day": delivery_day.isoformat(),
        "gate_closure_utc": closure.isoformat(),
        "gate_closure_schedule_id": schedule.schedule_id,
        "gate_closure_regime_from": regime.effective_from_delivery_day.isoformat(),
        "gate_closure_reference": regime.reference,
        "source_url": parsed["source_url"],
        "revision": parsed["revision"],
        "published_at_source": parsed["published_at_source"],
        "published_at_utc": published.isoformat(),
        "retrieved_at_utc": retrieved.isoformat(),
        "publication_lead_minutes": (closure - published).total_seconds() / 60.0,
        "retrieval_lead_minutes": (closure - retrieved).total_seconds() / 60.0,
        "publication_status": (
            "published_before_gate_closure" if before_gate else "published_after_gate_closure"
        ),
        "evidence_strength": (
            "witnessed_at_retrieval" if witnessed else "asserted_by_publisher"
        ),
        "coverage_start": parsed["coverage_start"].isoformat(),
        "coverage_end": parsed["coverage_end"].isoformat(),
        "sha256": parsed["sha256"],
        "size_bytes": parsed["size_bytes"],
        "availability_classification": parsed["availability_classification"],
    }


_OBSERVATION_COLUMNS = (
    "filetype",
    "delivery_day",
    "gate_closure_utc",
    "gate_closure_schedule_id",
    "gate_closure_regime_from",
    "gate_closure_reference",
    "source_url",
    "revision",
    "published_at_source",
    "published_at_utc",
    "retrieved_at_utc",
    "publication_lead_minutes",
    "retrieval_lead_minutes",
    "publication_status",
    "evidence_strength",
    "coverage_start",
    "coverage_end",
    "sha256",
    "size_bytes",
    "availability_classification",
)

_DELIVERY_DAY_COLUMNS = (
    "filetype",
    "delivery_day",
    "gate_closure_utc",
    "gate_closure_schedule_id",
    "gate_closure_regime_from",
    "day_status",
    "record_count",
    "pre_gate_record_count",
    "post_gate_record_count",
    "witnessed_pre_gate_record_count",
    "superseded_after_gate_closure_count",
    "decision_time_source_url",
    "decision_time_revision",
    "decision_time_published_at_utc",
    "decision_time_lead_minutes",
    "decision_time_evidence_strength",
)


def _observation_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=list(_OBSERVATION_COLUMNS))
    if frame.empty:
        return frame
    frame["revision"] = frame["revision"].astype("Int64")
    return frame.sort_values(
        ["filetype", "delivery_day", "published_at_utc", "source_url"]
    ).reset_index(drop=True)


def _delivery_day_frame(
    observations: pd.DataFrame,
    requested: tuple[str, ...],
    audited_days: list[date],
    closures: Mapping[date, pd.Timestamp],
    schedule: GateClosureSchedule,
) -> pd.DataFrame:
    grouped: dict[tuple[str, str], pd.DataFrame] = {}
    if not observations.empty:
        for key, group in observations.groupby(["filetype", "delivery_day"], sort=True):
            grouped[(str(key[0]), str(key[1]))] = group

    rows: list[dict[str, Any]] = []
    for filetype in requested:
        for day in audited_days:
            key = (filetype, day.isoformat())
            group = grouped.get(key)
            regime = schedule.regime_for(day)
            base = {
                "filetype": filetype,
                "delivery_day": day.isoformat(),
                "gate_closure_utc": closures[day].isoformat(),
                "gate_closure_schedule_id": schedule.schedule_id,
                "gate_closure_regime_from": regime.effective_from_delivery_day.isoformat(),
            }
            if group is None or group.empty:
                rows.append(
                    {
                        **base,
                        "day_status": NO_RECORD,
                        "record_count": 0,
                        "pre_gate_record_count": 0,
                        "post_gate_record_count": 0,
                        "witnessed_pre_gate_record_count": 0,
                        "superseded_after_gate_closure_count": 0,
                        "decision_time_source_url": None,
                        "decision_time_revision": None,
                        "decision_time_published_at_utc": None,
                        "decision_time_lead_minutes": None,
                        "decision_time_evidence_strength": None,
                    }
                )
                continue
            pre_gate = group.loc[group["publication_status"] == "published_before_gate_closure"]
            post_gate = group.loc[group["publication_status"] == "published_after_gate_closure"]
            witnessed = pre_gate.loc[pre_gate["evidence_strength"] == "witnessed_at_retrieval"]
            if pre_gate.empty:
                rows.append(
                    {
                        **base,
                        "day_status": NO_PRE_GATE_PUBLICATION,
                        "record_count": int(len(group)),
                        "pre_gate_record_count": 0,
                        "post_gate_record_count": int(len(post_gate)),
                        "witnessed_pre_gate_record_count": 0,
                        # Nothing was superseded: there was no decision-time revision to
                        # supersede. The post-gate publications are counted in their own column.
                        "superseded_after_gate_closure_count": 0,
                        "decision_time_source_url": None,
                        "decision_time_revision": None,
                        "decision_time_published_at_utc": None,
                        "decision_time_lead_minutes": None,
                        "decision_time_evidence_strength": None,
                    }
                )
                continue
            decision = pre_gate.sort_values(
                ["published_at_utc", "revision", "source_url"]
            ).iloc[-1]
            rows.append(
                {
                    **base,
                    "day_status": (
                        WITNESSED_PRE_GATE if not witnessed.empty else ASSERTED_PRE_GATE
                    ),
                    "record_count": int(len(group)),
                    "pre_gate_record_count": int(len(pre_gate)),
                    "post_gate_record_count": int(len(post_gate)),
                    "witnessed_pre_gate_record_count": int(len(witnessed)),
                    "superseded_after_gate_closure_count": int(len(post_gate)),
                    "decision_time_source_url": decision["source_url"],
                    "decision_time_revision": decision["revision"],
                    "decision_time_published_at_utc": decision["published_at_utc"],
                    "decision_time_lead_minutes": float(decision["publication_lead_minutes"]),
                    "decision_time_evidence_strength": decision["evidence_strength"],
                }
            )
    frame = pd.DataFrame(rows, columns=list(_DELIVERY_DAY_COLUMNS))
    # An ADMIE revision is an integer. Written beside the missing values of a day that has no
    # decision-time revision it would otherwise be exported as 1.0 rather than 1.
    frame["decision_time_revision"] = frame["decision_time_revision"].astype("Int64")
    return frame


def _summary(
    *,
    observations: pd.DataFrame,
    delivery_days: pd.DataFrame,
    schedule: GateClosureSchedule,
    requested: tuple[str, ...],
    start_day: date,
    end_day: date,
    ignored_record_count: int,
) -> dict[str, Any]:
    status_counts = delivery_days["day_status"].value_counts().to_dict()
    per_filetype: dict[str, Any] = {}
    for filetype in requested:
        rows = delivery_days.loc[delivery_days["filetype"] == filetype]
        accepted = rows["day_status"].isin(ACCEPTABLE_DAY_STATUSES)
        leads = rows.loc[accepted, "decision_time_lead_minutes"].astype(float)
        per_filetype[filetype] = {
            "audited_day_count": int(len(rows)),
            "day_status_counts": {
                str(name): int(count)
                for name, count in rows["day_status"].value_counts().sort_index().items()
            },
            "accepted_day_count": int(accepted.sum()),
            "witnessed_day_count": int((rows["day_status"] == WITNESSED_PRE_GATE).sum()),
            "min_decision_time_lead_minutes": float(leads.min()) if len(leads) else None,
            "median_decision_time_lead_minutes": float(leads.median()) if len(leads) else None,
            "days_with_post_gate_revisions": int(
                (rows["superseded_after_gate_closure_count"] > 0).sum()
            ),
            "unaccepted_delivery_days": [
                str(day)
                for day in rows.loc[~accepted, "delivery_day"].tolist()[:25]
            ],
        }

    unaccepted = delivery_days.loc[~delivery_days["day_status"].isin(ACCEPTABLE_DAY_STATUSES)]
    findings = [
        {
            "code": str(row["day_status"]),
            "filetype": str(row["filetype"]),
            "delivery_day": str(row["delivery_day"]),
            "gate_closure_utc": str(row["gate_closure_utc"]),
        }
        for _, row in unaccepted.iterrows()
    ]
    is_accepted = bool(len(delivery_days) > 0 and unaccepted.empty)
    fully_witnessed = bool(
        is_accepted and (delivery_days["day_status"] == WITNESSED_PRE_GATE).all()
    )
    return {
        "result_label": ADMIE_TIMING_LABEL,
        "method": "admie_publication_timing_audit",
        "policy": ADMIE_TIMING_POLICY,
        "gate_closure_schedule": schedule.to_dict(),
        "audited_filetypes": list(requested),
        "audit_start_day": start_day.isoformat(),
        "audit_end_day": end_day.isoformat(),
        "audited_delivery_day_count": int(len(set(delivery_days["delivery_day"]))),
        "observation_count": int(len(observations)),
        "ignored_record_count": int(ignored_record_count),
        "day_status_counts": {
            str(name): int(count) for name, count in sorted(status_counts.items())
        },
        "per_filetype": per_filetype,
        "timing_accepted": is_accepted,
        "timing_accepted_with_contemporaneous_witness": fully_witnessed,
        "evidence_basis": (
            "contemporaneous_retrieval_witness"
            if fully_witnessed
            else "publisher_asserted_timestamps"
        ),
        "finding_count": int(len(findings)),
        "findings": findings[:100],
        "establishes_only_publication_timing": True,
        "does_not_establish": list(TIMING_ESTABLISHES_NOT),
        "quarantine_lifted": False,
    }
