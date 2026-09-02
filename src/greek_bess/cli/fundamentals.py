"""Point-in-time fundamentals retrieval and the availability audit.

Both commands take declarations the repository refuses to supply. ``fetch-fundamentals`` needs a
sampling geography; ``audit-feature-availability`` needs a decision-cutoff schedule and a
decision lead. Neither has a default, an environment fallback or an "obvious" value, and the
committed examples are refused by name so that copying one into a run cannot turn a placeholder
into evidence.

Every output is private. A retrieved GRIB2 message, a feature table and an audit CSV are
provider content or derived research output; they belong in an ignored path or a workflow
artifact, never in a commit.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ..data.availability_audit import audit_feature_availability
from ..data.gfs import (
    FIRST_HOURLY_DELIVERY_DAY,
    GFS_VARIABLES,
    NOAA_GFS_ATTRIBUTION,
    NOAA_GFS_SOURCE,
    NoaaGfsClient,
    NoaaGfsError,
    write_gfs_retrieval_manifest,
)
from ..data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    EVIDENCE_GRADES,
    feature_coverage,
    read_point_in_time_csv,
    write_point_in_time_csv,
)
from ..data.provenance import RetrievalRecord, utc_now_iso
from ._registry import Command
from ._support import (
    _read_decision_cutoff_schedule,
    _read_sampling_geography,
    _sibling_path,
    _write_json,
    _write_plain_csv,
)

#: The one source v0.9 admits. It is an argument rather than a constant so that the command
#: names what it retrieved in its own output, and so that adding a second source later is a
#: reviewed change to this tuple rather than an edit to a call site.
SUPPORTED_FETCH_SOURCES = (NOAA_GFS_SOURCE,)


def configure_fetch_fundamentals(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, choices=SUPPORTED_FETCH_SOURCES)
    parser.add_argument(
        "--variables",
        nargs="+",
        required=True,
        choices=sorted(GFS_VARIABLES),
        help="Feature variables to build; there is no default variable set",
    )
    parser.add_argument(
        "--geography",
        required=True,
        type=Path,
        help="Declared sampling geography JSON; see config/fundamentals_geography.example.json",
    )
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path, help="Point-in-time feature CSV")
    parser.add_argument("--manifest", type=Path, help="Retrieval manifest JSON")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="Optional directory for the retrieved GRIB2 messages; they stay outside Git",
    )
    parser.add_argument("--summary", type=Path, help="Retrieval summary JSON")


def run_fetch_fundamentals(args: argparse.Namespace) -> int:
    if args.end_day < args.start_day:
        raise NoaaGfsError("--end-day must not precede --start-day")
    geography = _read_sampling_geography(args.geography)
    client = NoaaGfsClient()
    retrieved_at = utc_now_iso()

    frames: list[pd.DataFrame] = []
    records: list[RetrievalRecord] = []
    per_day: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    day = args.start_day
    while day <= args.end_day:
        if day < FIRST_HOURLY_DELIVERY_DAY:
            excluded.append(
                {
                    "market_day": day.isoformat(),
                    "cause": "before_hourly_product_start",
                    "detail": (
                        f"The 0.25° product is 3-hourly before "
                        f"{FIRST_HOURLY_DELIVERY_DAY.isoformat()}; the day carries no hourly "
                        "feature and no coarser value is broadcast into one"
                    ),
                }
            )
            day += timedelta(days=1)
            continue
        built = client.build_delivery_day_features(
            day,
            geography=geography,
            variables=args.variables,
            raw_dir=args.raw_dir,
            retrieved_at_utc=retrieved_at,
        )
        frames.append(built.features)
        records.extend(built.records)
        per_day.append(built.summary)
        day += timedelta(days=1)

    if not frames:
        raise NoaaGfsError(
            f"No delivery day in {args.start_day.isoformat()}..{args.end_day.isoformat()} can "
            "carry an hourly feature, so the retrieval produced nothing. An empty feature table "
            "is refused rather than written, because downstream it is indistinguishable from a "
            "provider that published nothing"
        )

    features = pd.concat(frames, ignore_index=True)
    write_point_in_time_csv(features, args.output)
    manifest_path = args.manifest or _sibling_path(args.output, ".retrieval_manifest.json")
    write_gfs_retrieval_manifest(manifest_path, records, created_at_utc=retrieved_at)
    coverage = feature_coverage(features)
    coverage_path = _sibling_path(args.output, ".coverage.csv")
    _write_plain_csv(coverage, coverage_path)

    summary = {
        "result_label": (
            f"Point-in-time {args.source} feature retrieval; provenance and availability "
            "evidence only, not accepted for forecasting."
        ),
        "method": "point_in_time_feature_retrieval",
        "source": args.source,
        "variables": sorted(args.variables),
        "geography_id": geography.geography_id,
        "geography": geography.to_dict(),
        "start_day": args.start_day.isoformat(),
        "end_day": args.end_day.isoformat(),
        "retrieved_at_utc": retrieved_at,
        "built_day_count": len(per_day),
        "excluded_day_count": len(excluded),
        "excluded_days_by_cause": excluded[:100],
        "feature_row_count": int(len(features)),
        "document_count": len(records),
        "retrieved_byte_count": sum(int(record.size_bytes) for record in records),
        "attribution": NOAA_GFS_ATTRIBUTION,
        "availability_classification": "requires_point_in_time_acceptance",
        "per_delivery_day": per_day,
    }
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_json(summary, summary_path)
    print(json.dumps({key: summary[key] for key in (
        "result_label", "source", "variables", "start_day", "end_day", "built_day_count",
        "excluded_day_count", "feature_row_count", "document_count", "retrieved_byte_count",
    )}, indent=2))
    return 0


def configure_audit_feature_availability(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("features", type=Path, help="Point-in-time feature CSV")
    parser.add_argument(
        "--decision-cutoff",
        required=True,
        type=Path,
        help="Declared decision-cutoff schedule JSON; there is no default cutoff",
    )
    parser.add_argument(
        "--decision-lead-minutes",
        required=True,
        type=int,
        help="Declared decision lead in minutes; it has no default and may be 0",
    )
    parser.add_argument("--variables", nargs="+", required=True)
    parser.add_argument("--area", default="GR")
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path, help="Per-delivery-day verdict CSV")
    parser.add_argument("--observations", type=Path, help="Per-value evidence CSV")
    parser.add_argument("--summary", type=Path, help="Audit summary JSON")
    parser.add_argument(
        "--admit-assumed-grade",
        action="store_true",
        help=(
            "Admit the quarantined 'assumed' grade. The run is then exploratory, its days can "
            "never be counted as accepted, and nothing it produces may be recorded as accepted"
        ),
    )


def run_audit_feature_availability(args: argparse.Namespace) -> int:
    admitted = (
        (*ADMISSIBLE_EVIDENCE_GRADES, ASSUMED)
        if args.admit_assumed_grade
        else ADMISSIBLE_EVIDENCE_GRADES
    )
    features = read_point_in_time_csv(
        args.features, require_publication_time=not args.admit_assumed_grade
    )
    audit = audit_feature_availability(
        features,
        schedule=_read_decision_cutoff_schedule(args.decision_cutoff),
        decision_lead_minutes=args.decision_lead_minutes,
        variables=args.variables,
        area=args.area,
        start_day=args.start_day,
        end_day=args.end_day,
        admitted_grades=admitted,
    )
    observations_path = args.observations or _sibling_path(args.output, ".observations.csv")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(audit.delivery_days, args.output)
    _write_plain_csv(audit.observations, observations_path)
    _write_json(audit.summary, summary_path)
    print(json.dumps(audit.summary, indent=2))
    return 0 if audit.summary["availability_accepted"] else 2


COMMANDS: tuple[Command, ...] = (
    Command(
        name="fetch-fundamentals",
        help=(
            "Retrieve point-in-time exogenous features at a declared sampling geography, with "
            "the publication instant and byte digest behind every value"
        ),
        configure=configure_fetch_fundamentals,
        run=run_fetch_fundamentals,
    ),
    Command(
        name="audit-feature-availability",
        help=(
            "Audit a point-in-time feature table against a declared decision cutoff and lead, "
            "per delivery interval, without reading any value"
        ),
        configure=configure_audit_feature_availability,
        run=run_audit_feature_availability,
    ),
)

# Named so that a reader of this module sees the full grade vocabulary the audit reports under,
# without having to open the data layer to find out what an unfamiliar grade in a CSV means.
DOCUMENTED_EVIDENCE_GRADES = EVIDENCE_GRADES
