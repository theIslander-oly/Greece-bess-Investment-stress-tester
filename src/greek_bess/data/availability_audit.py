"""Point-in-time availability audit: could a bidder have had every feature value in time?

The ADMIE publication-timing audit asked that question of *files*. This asks it of *values*, per
delivery interval, and it is the gate a feature table must pass before any model may read it.
The difference matters for the chosen source: a forecast cycle publishes one object per forecast
step, upload order is not monotone in step, and one step being on time says nothing about
another. A day-level verdict built from the earliest or the latest object would be wrong in both
directions, so every delivery interval of every audited day is checked on its own evidence.

Three rules govern the verdicts.

**The comparison is strict, against a declared cutoff.** A value is available for delivery day D
only if its publication instant is strictly before ``closure_utc(D) - decision_lead_minutes``. A
publication exactly at the cutoff is late. Both quantities are operator declarations with no
default, and this module has no fallback for either.

**A grade is derived, and it may fall but never rise.** A stored row records what the retrieval
established: ``provider_declared`` when a provider instant is attached to the datum,
``witnessed`` when the datum was observed contemporaneously, ``assumed`` when availability was
inferred from a rule rather than from the datum. The effective grade for a delivery day is
computed here from the row's own two instants against that day's cutoff — and a row stored as
``assumed`` stays ``assumed`` whatever its timestamps say, because the inference is the weakness,
not the arithmetic.

The two instants mean different things and neither substitutes for the other.
``published_at_utc`` is the provider's: when the source object was made available, read from the
object itself. ``retrieved_at_utc`` is this project's: when the datum was *successfully
received* here, and for a derived value the latest receipt among its inputs. It is deliberately
not the instant a retrieval run began. A run that starts an hour before a cutoff and is still
receiving messages an hour after it observed some of its values late; a run-start stamp would
report every one of them as witnessed. That is the one grade in this scheme that cannot be
reconstructed afterwards, so nobody reading the table later could have checked it.

**A day is complete or it is excluded by name.** Partial coverage is a status with a cause, never
a day with fewer intervals. Nothing is forward-filled and no interval is inferred from a
neighbouring one.

This audit establishes availability. It accepts no value, no unit and no forecasting skill, and
it does not on its own admit the source to a benchmark: the data-acceptance document of the v0.9
design's section 7 does that, and it comes later.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from .decision_cutoff import (
    DecisionCutoffError,
    GateClosureSchedule,
    effective_cutoff_utc,
    validate_decision_lead_minutes,
)
from .point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    EVIDENCE_GRADES,
    PROVIDER_DECLARED,
    UNAVAILABLE,
    WITNESSED,
    ensure_point_in_time,
)
from .timezones import MARKET_TZ

AVAILABILITY_LABEL = (
    "Point-in-time availability audit of one exogenous feature source against a declared "
    "decision cutoff; data-acceptance evidence about availability only, not a value acceptance, "
    "a forecast or investment evidence."
)

AVAILABILITY_POLICY = (
    "A feature value is usable for a delivery day only if it was published strictly before that "
    "day's declared decision cutoff, which is the declared gate closure minus the declared "
    "decision lead. Both are operator declarations with no default. A publication exactly at "
    "the cutoff is late. Availability is established per delivery interval, because a forecast "
    "cycle publishes one object per step and upload order is not monotone in step. Evidence is "
    "graded: a value this project observed before the cutoff is witnessed, a value whose "
    "provider-attached publication instant places it before the cutoff is provider-declared, "
    "and the two are reported separately and never merged. Availability inferred from a "
    "regulatory deadline or a nominal latency rather than from the datum is assumed, and is "
    "quarantined rather than admitted. A day whose every interval is not covered by an admitted "
    "value is excluded by named cause; no interval is filled, interpolated or inferred from a "
    "neighbour."
)

AVAILABILITY_ESTABLISHES_NOT = (
    "that any audited value is correct, or that its unit is as declared",
    "that any audited variable carries forecasting skill",
    "that a delivery day absent from the audited table was never published for",
    "that the declared cutoff matches the market rule the operator cited",
)

#: Day statuses. The first two are acceptable; the rest each name why a day is not.
WITNESSED_BEFORE_CUTOFF = "witnessed_before_cutoff"
PROVIDER_DECLARED_BEFORE_CUTOFF = "provider_declared_before_cutoff"
INCOMPLETE_BEFORE_CUTOFF = "incomplete_before_cutoff"
ALL_PUBLICATIONS_AFTER_CUTOFF = "all_publications_after_cutoff"
GRADE_NOT_ADMITTED = "grade_not_admitted"
NO_PUBLICATION = "no_publication"
#: A day covered only because the exploratory flag admitted the quarantined grade. It is a
#: status of its own and is deliberately *not* acceptable: design section 4.4 says an assumed
#: grade is usable only in a labelled exploratory run that is never recorded as accepted, and
#: the cheapest way to keep that true is to make such a day unable to reach an accepted count.
ASSUMED_GRADE_EXPLORATORY = "assumed_grade_admitted_exploratory"

ACCEPTABLE_FEATURE_DAY_STATUSES = frozenset(
    {WITNESSED_BEFORE_CUTOFF, PROVIDER_DECLARED_BEFORE_CUTOFF}
)


class FeatureAvailabilityError(DecisionCutoffError):
    """Raised when feature availability cannot be audited exactly as declared."""


@dataclass(frozen=True)
class FeatureAvailabilityAudit:
    """Per-value evidence, per-delivery-day verdicts and the run summary."""

    observations: pd.DataFrame
    delivery_days: pd.DataFrame
    summary: dict[str, Any]


def effective_evidence_grade(
    stored_grade: str,
    published_at_utc: pd.Timestamp | None,
    retrieved_at_utc: pd.Timestamp,
    cutoff_utc: pd.Timestamp,
) -> str:
    """Return the grade one row earns for one delivery day's cutoff.

    Design section 4.4 defines ``witnessed`` and ``provider_declared`` by the row's own two
    instants, so both are computed here rather than trusted from storage. The one thing storage
    decides is quarantine: a row stored as :data:`ASSUMED` cannot earn an admissible grade, no
    matter how early its timestamps are, because what is weak about it is that the instant was
    inferred rather than observed.
    """

    if stored_grade not in EVIDENCE_GRADES:
        raise FeatureAvailabilityError(f"Unknown stored evidence grade {stored_grade!r}")
    if stored_grade == ASSUMED:
        return ASSUMED
    if published_at_utc is None or pd.isna(published_at_utc):
        return UNAVAILABLE
    if published_at_utc >= cutoff_utc:
        return UNAVAILABLE
    if retrieved_at_utc < cutoff_utc:
        return WITNESSED
    return PROVIDER_DECLARED


def expected_feature_interval_count(delivery_day: date, resolution_minutes: int) -> int:
    """Return how many intervals of one native resolution a CET/CEST market day holds.

    Built from the market day's own length, so a 23-hour and a 25-hour day answer for
    themselves. A resolution that does not tile the day exactly is refused rather than rounded:
    a daily feature cannot describe a 23-hour day without a declared aggregation rule.
    """

    start = pd.Timestamp(delivery_day).tz_localize(MARKET_TZ)
    end = pd.Timestamp(delivery_day + timedelta(days=1)).tz_localize(MARKET_TZ)
    minutes = int((end - start).total_seconds() // 60)
    if resolution_minutes <= 0 or minutes % resolution_minutes:
        raise FeatureAvailabilityError(
            f"A {resolution_minutes}-minute feature does not tile the {minutes}-minute market "
            f"day {delivery_day.isoformat()}; a partial interval would need a declared "
            "aggregation rule and none is declared"
        )
    return minutes // resolution_minutes


def audit_feature_availability(
    features: pd.DataFrame,
    *,
    schedule: GateClosureSchedule,
    decision_lead_minutes: int,
    variables: Sequence[str],
    area: str,
    start_day: date,
    end_day: date,
    admitted_grades: Sequence[str] = ADMISSIBLE_EVIDENCE_GRADES,
) -> FeatureAvailabilityAudit:
    """Audit every named variable over every delivery day in ``[start_day, end_day]``."""

    if end_day < start_day:
        raise FeatureAvailabilityError("end_day must not precede start_day")
    lead = validate_decision_lead_minutes(decision_lead_minutes)
    requested = _validate_variables(variables)
    admitted = _validate_admitted_grades(admitted_grades)
    # Admitting the quarantined grade is what makes a run exploratory, and it is also the only
    # circumstance in which a row without a publication instant may be read at all. Deriving one
    # from the other means a caller cannot accidentally read a quarantine table into an accepted
    # audit, or admit the grade without the table that carries it.
    table = ensure_point_in_time(features, require_publication_time=ASSUMED not in admitted)

    audited_days = [
        start_day + timedelta(days=offset) for offset in range((end_day - start_day).days + 1)
    ]
    cutoffs = {day: effective_cutoff_utc(schedule, day, lead) for day in audited_days}

    scoped = table.loc[table["area"] == area] if not table.empty else table
    observation_rows: list[dict[str, Any]] = []
    day_rows: list[dict[str, Any]] = []
    for variable in requested:
        for day in audited_days:
            cutoff = cutoffs[day]
            rows = (
                scoped.loc[(scoped["variable"] == variable) & (scoped["market_day"] == day)]
                if not scoped.empty
                else scoped
            )
            observations = [
                _observation(row, variable=variable, area=area, day=day, cutoff=cutoff,
                             schedule=schedule)
                for _, row in rows.iterrows()
            ]
            observation_rows.extend(observations)
            day_rows.append(
                _delivery_day(
                    observations,
                    variable=variable,
                    area=area,
                    day=day,
                    cutoff=cutoff,
                    schedule=schedule,
                    admitted=admitted,
                    resolutions=sorted({int(value) for value in rows["resolution_minutes"]})
                    if not rows.empty
                    else [],
                )
            )

    observations_frame = _observation_frame(observation_rows)
    delivery_days = _delivery_day_frame(day_rows)
    summary = _summary(
        observations=observations_frame,
        delivery_days=delivery_days,
        schedule=schedule,
        lead=lead,
        requested=requested,
        area=area,
        start_day=start_day,
        end_day=end_day,
        admitted=admitted,
    )
    return FeatureAvailabilityAudit(
        observations=observations_frame, delivery_days=delivery_days, summary=summary
    )


_OBSERVATION_COLUMNS = (
    "variable",
    "area",
    "market_day",
    "delivery_start_utc",
    "decision_cutoff_utc",
    "decision_cutoff_schedule_id",
    "decision_cutoff_regime_from",
    "decision_cutoff_reference",
    "source_document_id",
    "source_revision",
    "raw_sha256",
    "published_at_utc",
    "retrieved_at_utc",
    "publication_lead_minutes",
    "retrieval_lead_minutes",
    "stored_evidence_grade",
    "effective_evidence_grade",
    "availability_evidence_detail",
)

_DELIVERY_DAY_COLUMNS = (
    "variable",
    "area",
    "market_day",
    "decision_cutoff_utc",
    "decision_cutoff_schedule_id",
    "decision_cutoff_regime_from",
    "day_status",
    "expected_interval_count",
    "covered_interval_count",
    "observation_count",
    "witnessed_interval_count",
    "provider_declared_interval_count",
    "assumed_interval_count",
    "quarantined_observation_count",
    "superseded_after_cutoff_count",
    "min_decision_time_lead_minutes",
    "median_decision_time_lead_minutes",
)


def _validate_variables(variables: Sequence[str]) -> tuple[str, ...]:
    if isinstance(variables, (str, bytes)) or not isinstance(variables, Sequence):
        raise FeatureAvailabilityError("variables must be a list of feature variable names")
    requested = [str(name) for name in variables]
    if not requested:
        raise FeatureAvailabilityError(
            "At least one variable must be named; the audit has no default variable set"
        )
    duplicated = sorted({name for name in requested if requested.count(name) > 1})
    if duplicated:
        raise FeatureAvailabilityError(f"Duplicate variables requested: {', '.join(duplicated)}")
    return tuple(requested)


def _validate_admitted_grades(grades: Sequence[str]) -> tuple[str, ...]:
    admitted = tuple(str(grade) for grade in grades)
    if not admitted:
        raise FeatureAvailabilityError("At least one evidence grade must be admitted")
    unknown = sorted(set(admitted) - set(EVIDENCE_GRADES))
    if unknown:
        raise FeatureAvailabilityError(f"Unknown evidence grades: {', '.join(unknown)}")
    if UNAVAILABLE in admitted:
        raise FeatureAvailabilityError(
            f"{UNAVAILABLE!r} is the absence of evidence and cannot be admitted"
        )
    return admitted


def _observation(
    row: Mapping[str, Any],
    *,
    variable: str,
    area: str,
    day: date,
    cutoff: pd.Timestamp,
    schedule: GateClosureSchedule,
) -> dict[str, Any]:
    regime = schedule.regime_for(day)
    published = row["published_at_utc"]
    retrieved = row["retrieved_at_utc"]
    effective = effective_evidence_grade(
        str(row["availability_evidence_grade"]), published, retrieved, cutoff
    )
    return {
        "variable": variable,
        "area": area,
        "market_day": day.isoformat(),
        "delivery_start_utc": row["delivery_start_utc"].isoformat(),
        "decision_cutoff_utc": cutoff.isoformat(),
        "decision_cutoff_schedule_id": schedule.schedule_id,
        "decision_cutoff_regime_from": regime.effective_from_delivery_day.isoformat(),
        "decision_cutoff_reference": regime.reference,
        "source_document_id": str(row["source_document_id"]),
        "source_revision": row["source_revision"],
        "raw_sha256": str(row["raw_sha256"]),
        "published_at_utc": None if pd.isna(published) else published.isoformat(),
        "retrieved_at_utc": retrieved.isoformat(),
        "publication_lead_minutes": (
            None if pd.isna(published) else (cutoff - published).total_seconds() / 60.0
        ),
        "retrieval_lead_minutes": (cutoff - retrieved).total_seconds() / 60.0,
        "stored_evidence_grade": str(row["availability_evidence_grade"]),
        "effective_evidence_grade": effective,
        "availability_evidence_detail": row["availability_evidence_detail"],
    }


def _delivery_day(
    observations: Sequence[Mapping[str, Any]],
    *,
    variable: str,
    area: str,
    day: date,
    cutoff: pd.Timestamp,
    schedule: GateClosureSchedule,
    admitted: Sequence[str],
    resolutions: Sequence[int],
) -> dict[str, Any]:
    regime = schedule.regime_for(day)
    base: dict[str, Any] = {
        "variable": variable,
        "area": area,
        "market_day": day.isoformat(),
        "decision_cutoff_utc": cutoff.isoformat(),
        "decision_cutoff_schedule_id": schedule.schedule_id,
        "decision_cutoff_regime_from": regime.effective_from_delivery_day.isoformat(),
        "observation_count": len(observations),
    }
    if len(set(resolutions)) > 1:
        raise FeatureAvailabilityError(
            f"{variable} carries resolutions {sorted(set(resolutions))} on {day.isoformat()}; a "
            "day whose feature changes resolution part-way through cannot be audited as one day"
        )
    expected = (
        expected_feature_interval_count(day, resolutions[0]) if resolutions else None
    )

    admitted_rows = [
        observation
        for observation in observations
        if observation["effective_evidence_grade"] in admitted
    ]
    superseded = sum(
        1
        for observation in observations
        if observation["publication_lead_minutes"] is not None
        and observation["publication_lead_minutes"] <= 0.0
    )
    quarantined = sum(
        1 for observation in observations if observation["effective_evidence_grade"] == ASSUMED
    )

    # The decision-time value for an interval is the latest one published strictly before the
    # cutoff; a revision and then the document identity break a tie. Sorting ascending and
    # keeping the last write per interval selects it. The publication instant is compared as a
    # timestamp rather than as its ISO text, so the ordering does not depend on every producer
    # formatting sub-second precision the same way.
    decision_by_interval: dict[str, Mapping[str, Any]] = {}
    for observation in sorted(admitted_rows, key=_decision_sort_key):
        decision_by_interval[str(observation["delivery_start_utc"])] = observation

    covered = len(decision_by_interval)
    witnessed = sum(
        1
        for observation in decision_by_interval.values()
        if observation["effective_evidence_grade"] == WITNESSED
    )
    provider = sum(
        1
        for observation in decision_by_interval.values()
        if observation["effective_evidence_grade"] == PROVIDER_DECLARED
    )
    assumed_intervals = sum(
        1
        for observation in decision_by_interval.values()
        if observation["effective_evidence_grade"] == ASSUMED
    )
    leads = sorted(
        float(observation["publication_lead_minutes"])
        for observation in decision_by_interval.values()
        if observation["publication_lead_minutes"] is not None
    )

    if not observations:
        status = NO_PUBLICATION
    elif not admitted_rows and not any(
        observation["publication_lead_minutes"] is not None
        and observation["publication_lead_minutes"] > 0.0
        for observation in observations
    ):
        status = ALL_PUBLICATIONS_AFTER_CUTOFF
    elif not admitted_rows:
        status = GRADE_NOT_ADMITTED
    elif expected is None or covered < expected:
        status = INCOMPLETE_BEFORE_CUTOFF
    elif assumed_intervals:
        status = ASSUMED_GRADE_EXPLORATORY
    elif witnessed == covered:
        status = WITNESSED_BEFORE_CUTOFF
    else:
        status = PROVIDER_DECLARED_BEFORE_CUTOFF

    return {
        **base,
        "day_status": status,
        "expected_interval_count": expected,
        "covered_interval_count": covered,
        "witnessed_interval_count": witnessed,
        "provider_declared_interval_count": provider,
        "assumed_interval_count": assumed_intervals,
        "quarantined_observation_count": quarantined,
        "superseded_after_cutoff_count": superseded,
        "min_decision_time_lead_minutes": leads[0] if leads else None,
        "median_decision_time_lead_minutes": (
            float(pd.Series(leads).median()) if leads else None
        ),
    }


def _decision_sort_key(observation: Mapping[str, Any]) -> tuple[pd.Timestamp, str, str]:
    published = observation["published_at_utc"]
    return (
        pd.Timestamp.min.tz_localize("UTC")
        if published is None
        else pd.Timestamp(str(published)),
        str(observation["source_revision"]),
        str(observation["source_document_id"]),
    )


def _observation_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=list(_OBSERVATION_COLUMNS))
    if frame.empty:
        return frame
    return frame.sort_values(
        ["variable", "area", "market_day", "delivery_start_utc", "published_at_utc",
         "source_document_id"],
        kind="stable",
    ).reset_index(drop=True)


def _delivery_day_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=list(_DELIVERY_DAY_COLUMNS))
    if frame.empty:
        return frame
    for column in ("expected_interval_count", "covered_interval_count"):
        frame[column] = frame[column].astype("Int64")
    return frame.sort_values(["variable", "area", "market_day"], kind="stable").reset_index(
        drop=True
    )


def _summary(
    *,
    observations: pd.DataFrame,
    delivery_days: pd.DataFrame,
    schedule: GateClosureSchedule,
    lead: int,
    requested: tuple[str, ...],
    area: str,
    start_day: date,
    end_day: date,
    admitted: tuple[str, ...],
) -> dict[str, Any]:
    per_variable: dict[str, Any] = {}
    for variable in requested:
        rows = delivery_days.loc[delivery_days["variable"] == variable]
        accepted = rows["day_status"].isin(ACCEPTABLE_FEATURE_DAY_STATUSES)
        leads = rows.loc[accepted, "min_decision_time_lead_minutes"].dropna().astype(float)
        per_variable[variable] = {
            "audited_day_count": int(len(rows)),
            "day_status_counts": {
                str(name): int(count)
                for name, count in rows["day_status"].value_counts().sort_index().items()
            },
            "accepted_day_count": int(accepted.sum()),
            "witnessed_day_count": int(
                (rows["day_status"] == WITNESSED_BEFORE_CUTOFF).sum()
            ),
            "min_decision_time_lead_minutes": float(leads.min()) if len(leads) else None,
            "median_decision_time_lead_minutes": (
                float(leads.median()) if len(leads) else None
            ),
            "days_with_publications_after_cutoff": int(
                (rows["superseded_after_cutoff_count"] > 0).sum()
            ),
            "unaccepted_delivery_days": [
                {"market_day": str(row["market_day"]), "cause": str(row["day_status"])}
                for _, row in rows.loc[~accepted].iterrows()
            ][:100],
        }

    unaccepted = delivery_days.loc[
        ~delivery_days["day_status"].isin(ACCEPTABLE_FEATURE_DAY_STATUSES)
    ]
    accepted_days = delivery_days.loc[
        delivery_days["day_status"].isin(ACCEPTABLE_FEATURE_DAY_STATUSES)
    ]
    is_accepted = bool(len(delivery_days) > 0 and unaccepted.empty)
    fully_witnessed = bool(
        is_accepted and (delivery_days["day_status"] == WITNESSED_BEFORE_CUTOFF).all()
    )
    return {
        "result_label": AVAILABILITY_LABEL,
        "method": "point_in_time_availability_audit",
        "policy": AVAILABILITY_POLICY,
        "decision_cutoff_schedule_id": schedule.schedule_id,
        "decision_cutoff_schedule": schedule.to_dict(),
        "decision_lead_minutes": int(lead),
        "audited_variables": list(requested),
        "audited_area": area,
        "audit_start_day": start_day.isoformat(),
        "audit_end_day": end_day.isoformat(),
        "audited_delivery_day_count": int(len(set(delivery_days["market_day"]))),
        "observation_count": int(len(observations)),
        "evidence_grades_admitted": list(admitted),
        "is_exploratory": bool(ASSUMED in admitted),
        "quarantined_observation_count": int(
            delivery_days["quarantined_observation_count"].sum()
        ) if not delivery_days.empty else 0,
        "day_status_counts": {
            str(name): int(count)
            for name, count in delivery_days["day_status"].value_counts().sort_index().items()
        } if not delivery_days.empty else {},
        "per_variable": per_variable,
        "availability_accepted": is_accepted,
        "availability_accepted_with_contemporaneous_witness": fully_witnessed,
        "witnessed_day_count": int(
            (delivery_days["day_status"] == WITNESSED_BEFORE_CUTOFF).sum()
        ) if not delivery_days.empty else 0,
        "accepted_day_count": int(len(accepted_days)),
        "evidence_basis": (
            "contemporaneous_retrieval_witness"
            if fully_witnessed
            else "provider_declared_publication_instants"
        ),
        "finding_count": int(len(unaccepted)),
        "findings": [
            {
                "code": str(row["day_status"]),
                "variable": str(row["variable"]),
                "area": str(row["area"]),
                "market_day": str(row["market_day"]),
                "decision_cutoff_utc": str(row["decision_cutoff_utc"]),
            }
            for _, row in unaccepted.iterrows()
        ][:100],
        "establishes_only_availability": True,
        "does_not_establish": list(AVAILABILITY_ESTABLISHES_NOT),
        "quarantine_lifted": False,
    }
