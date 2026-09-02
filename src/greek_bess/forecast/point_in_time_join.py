"""Leakage-safe as-of join from revision-bearing features to price intervals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from ..data.availability_audit import effective_evidence_grade
from ..data.decision_cutoff import (
    GateClosureSchedule,
    effective_cutoff_utc,
    validate_decision_lead_minutes,
)
from ..data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    EVIDENCE_GRADES,
    ensure_point_in_time,
)
from ..data.quality import assess_quality
from ..data.schema import ensure_canonical

REALISED_PRICE_VARIABLES = frozenset(
    {"price_eur_per_mwh", "realised_price", "realized_price", "day_ahead_price"}
)
AUDIT_COLUMNS = (
    "market_day",
    "delivery_start_utc",
    "variable",
    "area",
    "cutoff_utc",
    "published_at_utc",
    "retrieved_at_utc",
    "source_document_id",
    "source_revision",
    "raw_sha256",
    "forecast_issue_time_utc",
    "lead_minutes",
    "evidence_grade",
    "resolution_relation",
    "superseded_after_cutoff",
)


class PointInTimeJoinError(ValueError):
    """Raised when inputs cannot support a leakage-safe point-in-time join."""


@dataclass(frozen=True)
class PointInTimeJoinResult:
    """The interval feature frame, provenance audit and day-level summary."""

    feature_frame: pd.DataFrame
    audit_table: pd.DataFrame
    summary: dict[str, Any]


def join_point_in_time_features(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    *,
    schedule: GateClosureSchedule,
    decision_lead_minutes: int,
    admitted_grades: tuple[str, ...] = ADMISSIBLE_EVIDENCE_GRADES,
    exploratory: bool = False,
) -> PointInTimeJoinResult:
    """Select the latest strictly pre-cutoff revision and map it by containment.

    A feature value is never filled. If any declared variable/area pair is unavailable for any
    interval, the whole delivery day is excluded and every feature cell for that day is null.
    """

    lead = validate_decision_lead_minutes(decision_lead_minutes)
    admitted = tuple(dict.fromkeys(admitted_grades))
    unknown = sorted(set(admitted) - set(EVIDENCE_GRADES))
    if unknown:
        raise PointInTimeJoinError(f"Unknown admitted evidence grades: {', '.join(unknown)}")
    if not admitted:
        raise PointInTimeJoinError("At least one evidence grade must be admitted")
    if ASSUMED in admitted and not exploratory:
        raise PointInTimeJoinError(
            "The assumed grade is quarantined; admitting it requires exploratory=True"
        )
    forbidden = sorted(
        set(admitted) - set(ADMISSIBLE_EVIDENCE_GRADES) - ({ASSUMED} if exploratory else set())
    )
    if forbidden:
        raise PointInTimeJoinError(f"Evidence grades cannot be admitted: {', '.join(forbidden)}")

    price_frame = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(price_frame)
    if not quality.is_valid:
        codes = ", ".join(issue.code for issue in quality.issues if issue.severity == "error")
        raise PointInTimeJoinError(f"Price history fails its quality gate: {codes}")
    feature_rows = ensure_point_in_time(features, allow_empty=False, require_publication_time=True)
    realised = sorted(set(feature_rows["variable"]) & REALISED_PRICE_VARIABLES)
    if realised:
        raise PointInTimeJoinError(
            f"Realised target variables are refused by name: {', '.join(realised)}"
        )

    pairs = sorted(set(zip(feature_rows["variable"], feature_rows["area"], strict=True)))
    names = _column_names(pairs)
    output = pd.DataFrame({"delivery_start_utc": price_frame["delivery_start_utc"]})
    for name in names.values():
        output[name] = float("nan")
    market_days = price_frame["delivery_start_market"].dt.date
    audit_rows: list[dict[str, Any]] = []
    day_records: list[dict[str, Any]] = []

    for delivery_day in sorted(set(market_days)):
        cutoff = effective_cutoff_utc(schedule, delivery_day, lead)
        price_indices = price_frame.index[market_days == delivery_day]
        pending: list[tuple[int, tuple[str, str], pd.Series, str, int]] = []
        reasons: list[dict[str, str]] = []
        for pair in pairs:
            variable, area = pair
            pair_rows = feature_rows[
                (feature_rows["variable"] == variable) & (feature_rows["area"] == area)
            ]
            overlaps_day = pair_rows[
                (
                    pair_rows["delivery_start_utc"]
                    < price_frame.loc[price_indices, "delivery_end_utc"].max()
                )
                & (
                    pair_rows["delivery_end_utc"]
                    > price_frame.loc[price_indices, "delivery_start_utc"].min()
                )
            ]
            early = overlaps_day[overlaps_day["published_at_utc"] < cutoff].copy()
            if early.empty:
                cause = "no_publication" if overlaps_day.empty else "all_publications_after_cutoff"
                reasons.append({"variable": variable, "area": area, "cause": cause})
                continue
            early["_effective_grade"] = early.apply(
                lambda row, day_cutoff=cutoff: effective_evidence_grade(
                    str(row["availability_evidence_grade"]),
                    row["published_at_utc"],
                    row["retrieved_at_utc"],
                    day_cutoff,
                ),
                axis=1,
            )
            usable = early[early["_effective_grade"].isin(admitted)].copy()
            if usable.empty:
                reasons.append({"variable": variable, "area": area, "cause": "grade_not_admitted"})
                continue
            usable["_revision_sort"] = usable["source_revision"].fillna("")
            usable = usable.sort_values(
                ["delivery_start_utc", "published_at_utc", "_revision_sort", "source_document_id"],
                kind="stable",
            ).drop_duplicates("delivery_start_utc", keep="last")
            later_count = int((overlaps_day["published_at_utc"] >= cutoff).sum())
            missing = False
            for price_index in price_indices:
                start = price_frame.at[price_index, "delivery_start_utc"]
                covering = usable[
                    (usable["delivery_start_utc"] <= start) & (usable["delivery_end_utc"] > start)
                ]
                if len(covering) != 1:
                    missing = True
                    break
                selected = covering.iloc[0]
                relation = _resolution_relation(selected, price_frame.loc[price_index])
                pending.append((price_index, pair, selected, relation, later_count))
            if missing:
                pending = [item for item in pending if item[1] != pair]
                reasons.append({"variable": variable, "area": area, "cause": "incomplete_day"})

        if reasons:
            status = "excluded"
        else:
            status = "complete"
            for price_index, pair, selected, relation, later_count in pending:
                output.at[price_index, names[pair]] = float(selected["value"])
                audit_rows.append(
                    _audit_row(
                        delivery_day,
                        price_frame.at[price_index, "delivery_start_utc"],
                        cutoff,
                        selected,
                        relation,
                        later_count,
                    )
                )
        day_records.append(
            {
                "market_day": delivery_day.isoformat(),
                "status": status,
                "reasons": reasons,
                "price_interval_count": len(price_indices),
            }
        )

    audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
    complete_days = sum(row["status"] == "complete" for row in day_records)
    grade_counts = (
        audit["evidence_grade"].value_counts().sort_index().to_dict() if not audit.empty else {}
    )
    leads = audit["lead_minutes"] if not audit.empty else pd.Series(dtype=float)
    summary: dict[str, Any] = {
        "result_label": (
            "Point-in-time feature join; synthetic validation only until declarations "
            "and data acceptance exist."
        ),
        "method": "strict_pre_cutoff_revision_as_of_join",
        "schedule_id": schedule.schedule_id,
        "decision_lead_minutes": lead,
        "admitted_grades": list(admitted),
        "is_exploratory": exploratory,
        "feature_columns": list(names.values()),
        "delivery_day_count": len(day_records),
        "complete_day_count": complete_days,
        "excluded_day_count": len(day_records) - complete_days,
        "delivery_days": day_records,
        "audit_row_count": len(audit),
        "evidence_grade_counts": grade_counts,
        "lead_minutes_min": None if leads.empty else float(leads.min()),
        "lead_minutes_median": None if leads.empty else float(leads.median()),
        "superseded_after_cutoff_count": int(
            audit.drop_duplicates(["market_day", "variable", "area"])[
                "superseded_after_cutoff"
            ].sum()
        )
        if not audit.empty
        else 0,
        "price_input_sha256": _frame_digest(price_frame),
        "feature_input_sha256": _frame_digest(feature_rows),
        "audit_sha256": _frame_digest(audit),
        "establishes_only_point_in_time_selection": True,
        "data_accepted": False,
    }
    return PointInTimeJoinResult(output, audit, summary)


def _column_names(pairs: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    variables = [variable for variable, _ in pairs]
    return {
        pair: pair[0] if variables.count(pair[0]) == 1 else f"{pair[0]}__{pair[1]}"
        for pair in pairs
    }


def _resolution_relation(feature: pd.Series, price: pd.Series) -> str:
    feature_minutes = int(feature["resolution_minutes"])
    price_minutes = int(round(float(price["duration_hours"]) * 60))
    if feature_minutes == price_minutes:
        return "equal"
    if feature_minutes > price_minutes:
        return "broadcast_coarser_feature"
    raise PointInTimeJoinError(
        "A finer feature than the price interval requires a declared aggregation rule"
    )


def _audit_row(
    delivery_day: date,
    start: pd.Timestamp,
    cutoff: pd.Timestamp,
    selected: pd.Series,
    relation: str,
    later_count: int,
) -> dict[str, Any]:
    published = selected["published_at_utc"]
    return {
        "market_day": delivery_day.isoformat(),
        "delivery_start_utc": start,
        "variable": selected["variable"],
        "area": selected["area"],
        "cutoff_utc": cutoff,
        "published_at_utc": published,
        "retrieved_at_utc": selected["retrieved_at_utc"],
        "source_document_id": selected["source_document_id"],
        "source_revision": selected["source_revision"],
        "raw_sha256": selected["raw_sha256"],
        "forecast_issue_time_utc": selected["forecast_issue_time_utc"],
        "lead_minutes": (cutoff - published).total_seconds() / 60,
        "evidence_grade": selected["_effective_grade"],
        "resolution_relation": relation,
        "superseded_after_cutoff": later_count,
    }


def _frame_digest(frame: pd.DataFrame) -> str:
    records = frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
    payload = json.dumps(records, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
