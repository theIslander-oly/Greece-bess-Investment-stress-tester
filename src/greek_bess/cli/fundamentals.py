"""The point-in-time fundamentals surfaces: retrieval, audit, join, ablation and settlement.

Every command here takes declarations the repository refuses to supply. ``fetch-fundamentals``
needs a sampling geography; the audit, the join and the two benchmarks need a decision-cutoff
schedule and a decision lead; the forecast benchmark needs its price-regime bands; the dispatch
comparison needs the arms it is settling. None has a default, an environment fallback or an
"obvious" value, and the committed examples are refused by name so that copying one into a run
cannot turn a placeholder into evidence.

The five commands form one chain, and each refuses to be run out of order rather than filling
in what an earlier stage did not produce: retrieval writes every revision, the audit judges
availability without reading a value, the join selects the decision-time revision and digests
the frame, the forecast ablation refuses any input whose digest and declarations differ from
the join's, and the dispatch comparison settles exactly the days that ablation recorded.

``fetch-fundamentals`` excludes a delivery day by name and continues when the source condition
is a fact about that day — the 3-hourly era before the hourly product, an object the archive says
it does not hold, or a ``.idx`` sidecar that indexes a different publication. It stops on
everything else, including any request the archive did not answer, because an unanswered request
is not evidence that the provider published nothing and a window is not silently shortened on it.

Every output is private. A retrieved GRIB2 message, a feature table, an audit CSV and a settled
schedule are provider content or derived research output; they belong in an ignored path or a
workflow artifact, never in a commit.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ..backtest.fundamentals_dispatch import backtest_fundamentals_dispatch
from ..data.availability_audit import audit_feature_availability
from ..data.feature_shards import combine_feature_shards
from ..data.gfs import (
    FIRST_HOURLY_DELIVERY_DAY,
    GFS_FEATURE_SEMANTICS_VERSION,
    GFS_OBSERVATION_SEMANTICS_VERSION,
    GFS_VARIABLES,
    NOAA_GFS_ATTRIBUTION,
    NOAA_GFS_SOURCE,
    SOURCE_CONDITION_CAUSES,
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
from ..forecast.fundamentals import (
    FundamentalsBenchmarkConfig,
    generate_fundamentals_benchmark,
)
from ..forecast.point_in_time_join import join_point_in_time_features
from ._registry import Command
from ._support import (
    _add_ml_arguments,
    _ml_config_from_args,
    _read_battery_config,
    _read_canonical_csv,
    _read_decision_cutoff_schedule,
    _read_sampling_geography,
    _sibling_path,
    _write_dispatch_csv,
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


def _extreme_instant(
    per_day: Sequence[Mapping[str, object]], field: str, *, latest: bool
) -> str:
    """Return the earliest or latest of one instant field across every built delivery day.

    The instants are compared as timestamps rather than as strings: they are all UTC and all
    ISO-8601, but they need not carry the same number of fractional digits, and an ordering that
    happens to work on today's formatting is not something an evidence field should rely on.
    """

    instants = [pd.Timestamp(str(day[field])) for day in per_day]
    chosen = max(instants) if latest else min(instants)
    return chosen.isoformat()


def run_fetch_fundamentals(args: argparse.Namespace) -> int:
    if args.end_day < args.start_day:
        raise NoaaGfsError("--end-day must not precede --start-day")
    geography = _read_sampling_geography(args.geography)
    client = NoaaGfsClient()
    run_started_at = utc_now_iso()

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
        try:
            built = client.build_delivery_day_features(
                day,
                geography=geography,
                variables=args.variables,
                raw_dir=args.raw_dir,
                run_started_at_utc=run_started_at,
            )
        except NoaaGfsError as exc:
            # A source condition is a fact about one delivery day, and the refusals that raise it
            # already say the day "is excluded by name". Until now the exception propagated out
            # of this loop and killed the whole window instead, so one unpublished object cost
            # every other day retrieved beside it. Only the two named source conditions are
            # excluded here: every other refusal is about how a value would be built, and a run
            # that quietly dropped those days would record an integrity defect of this client as
            # a provider non-publication. Absence itself is a classified answer from the store,
            # never an unanswered request — see `greek_bess.data.http`.
            if exc.cause not in SOURCE_CONDITION_CAUSES:
                raise
            excluded.append(
                {"market_day": day.isoformat(), "cause": exc.cause, "detail": str(exc)}
            )
            day += timedelta(days=1)
            continue
        frames.append(built.features)
        records.extend(built.records)
        per_day.append(built.summary)
        day += timedelta(days=1)

    if not frames:
        raise NoaaGfsError(
            f"No delivery day in {args.start_day.isoformat()}..{args.end_day.isoformat()} "
            "produced an hourly feature, so the retrieval produced nothing. An empty feature "
            "table is refused rather than written, because downstream it is indistinguishable "
            "from a provider that published nothing. Excluded by cause: "
            f"{json.dumps(_exclusion_counts(excluded), sort_keys=True)}"
        )

    features = pd.concat(frames, ignore_index=True)
    write_point_in_time_csv(features, args.output)
    manifest_path = args.manifest or _sibling_path(args.output, ".retrieval_manifest.json")
    write_gfs_retrieval_manifest(manifest_path, records, created_at_utc=run_started_at)
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
        "feature_semantics_version": GFS_FEATURE_SEMANTICS_VERSION,
        "observation_semantics_version": GFS_OBSERVATION_SEMANTICS_VERSION,
        "decoded_message_contract": per_day[0]["decoded_message_contract"],
        "start_day": args.start_day.isoformat(),
        "end_day": args.end_day.isoformat(),
        # When the run began, and when its earliest and latest message actually arrived. These
        # are three different instants and only the receipts are evidence of observation; a run
        # that started before a cutoff may have kept receiving messages well after it.
        "run_started_at_utc": run_started_at,
        "first_message_received_at_utc": _extreme_instant(
            per_day, "first_message_received_at_utc", latest=False
        ),
        "last_message_received_at_utc": _extreme_instant(
            per_day, "last_message_received_at_utc", latest=True
        ),
        "built_day_count": len(per_day),
        "excluded_day_count": len(excluded),
        # The list is capped so a long window cannot turn a summary into a day-by-day log; the
        # counts are not, so no exclusion is ever invisible in the aggregate.
        "excluded_day_count_by_cause": _exclusion_counts(excluded),
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
        "excluded_day_count", "excluded_day_count_by_cause", "feature_row_count",
        "document_count", "retrieved_byte_count",
    )}, indent=2))
    return 0


def _exclusion_counts(excluded: Sequence[Mapping[str, object]]) -> dict[str, int]:
    """Return how many delivery days each named cause excluded."""

    return dict(Counter(str(entry["cause"]) for entry in excluded))


def configure_combine_feature_tables(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "shards",
        nargs="+",
        type=Path,
        help=(
            "Point-in-time feature CSVs retrieved by fetch-fundamentals, each beside its own "
            "summary; they must tile one window, covering every delivery day exactly once"
        ),
    )
    parser.add_argument("--output", required=True, type=Path, help="Combined feature CSV")
    parser.add_argument("--manifest", type=Path, help="Combined retrieval manifest JSON")
    parser.add_argument("--summary", type=Path, help="Combined retrieval summary JSON")
    parser.add_argument(
        "--official",
        action="store_true",
        help=(
            "Require every shard to carry the retrieval manifest tracing its rows to the source "
            "messages they were built from. Use for any combination that will support an "
            "acceptance document"
        ),
    )


def run_combine_feature_tables(args: argparse.Namespace) -> int:
    created_at = utc_now_iso()
    features, summary, records = combine_feature_shards(
        list(args.shards), created_at_utc=created_at, official=args.official
    )
    write_point_in_time_csv(features, args.output)

    manifest_path = args.manifest or _sibling_path(args.output, ".retrieval_manifest.json")
    _write_json(
        {
            "schema_version": 1,
            "created_at_utc": created_at,
            "files": records,
        },
        manifest_path,
    )
    coverage = feature_coverage(features)
    _write_plain_csv(coverage, _sibling_path(args.output, ".coverage.csv"))

    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_json(summary, summary_path)
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "result_label",
                    "source",
                    "variables",
                    "start_day",
                    "end_day",
                    "shard_count",
                    "built_day_count",
                    "feature_row_count",
                    "document_count",
                )
            },
            indent=2,
        )
    )
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


def configure_build_point_in_time_features(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV defining delivery intervals")
    parser.add_argument("features", type=Path, help="Point-in-time feature CSV with all revisions")
    parser.add_argument("--decision-cutoff", required=True, type=Path)
    parser.add_argument("--decision-lead-minutes", required=True, type=int)
    parser.add_argument(
        "--admitted-grades", nargs="+", required=True, choices=EVIDENCE_GRADES,
        help="Evidence grades admitted by this run; there is no default",
    )
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--output", required=True, type=Path, help="Joined interval feature CSV")
    parser.add_argument("--audit", type=Path, help="Per-value revision-selection audit CSV")
    parser.add_argument("--summary", type=Path, help="Join summary JSON")


def run_build_point_in_time_features(args: argparse.Namespace) -> int:
    result = join_point_in_time_features(
        _read_canonical_csv(args.prices),
        read_point_in_time_csv(args.features),
        schedule=_read_decision_cutoff_schedule(args.decision_cutoff),
        decision_lead_minutes=args.decision_lead_minutes,
        admitted_grades=tuple(args.admitted_grades),
        exploratory=args.exploratory,
    )
    audit_path = args.audit or _sibling_path(args.output, ".audit.csv")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(result.feature_frame, args.output)
    _write_plain_csv(result.audit_table, audit_path)
    _write_json(result.summary, summary_path)
    print(json.dumps(result.summary, indent=2))
    return 0 if result.summary["excluded_day_count"] == 0 else 2


def configure_benchmark_fundamentals_forecast(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV of realized prices")
    parser.add_argument(
        "--features", required=True, type=Path,
        help="Interval feature frame written by build-point-in-time-features",
    )
    parser.add_argument(
        "--feature-summary", type=Path,
        help="Join summary JSON; defaults beside the feature frame",
    )
    parser.add_argument(
        "--feature-set-sha256", required=True,
        help=(
            "The feature-set digest this benchmark claims to run on. It is declared rather "
            "than adopted so that a result names one accepted feature table"
        ),
    )
    parser.add_argument("--decision-cutoff", required=True, type=Path)
    parser.add_argument("--decision-lead-minutes", required=True, type=int)
    parser.add_argument(
        "--admitted-grades", nargs="+", required=True, choices=EVIDENCE_GRADES,
        help="Evidence grades this benchmark admits; they must equal the join's own",
    )
    parser.add_argument(
        "--price-regime-bands", nargs="+", required=True, type=float,
        help=(
            "Ascending upper edges of the reported price-regime slices, in EUR/MWh. There is "
            "no default: which price levels are worth separating is a judgment"
        ),
    )
    _add_ml_arguments(parser)
    parser.add_argument("--output", required=True, type=Path, help="Two-arm forecast CSV")
    parser.add_argument("--summary", type=Path, help="Benchmark JSON; defaults beside the CSV")


def run_benchmark_fundamentals_forecast(args: argparse.Namespace) -> int:
    summary_source = args.feature_summary or args.features.with_suffix(".summary.json")
    join_summary = json.loads(summary_source.read_text(encoding="utf-8"))
    schedule = _read_decision_cutoff_schedule(args.decision_cutoff)
    config = FundamentalsBenchmarkConfig(
        ml=_ml_config_from_args(args),
        feature_set_sha256=args.feature_set_sha256,
        decision_cutoff_schedule_id=schedule.schedule_id,
        decision_lead_minutes=args.decision_lead_minutes,
        evidence_grades_admitted=tuple(args.admitted_grades),
        price_regime_bands=tuple(args.price_regime_bands),
    )
    result = generate_fundamentals_benchmark(
        _read_canonical_csv(args.prices),
        # Round-trip precision for the same reason the feature reader uses it: this frame
        # is checked against the digest the join recorded, and a digest has no tolerance.
        pd.read_csv(args.features, float_precision="round_trip"),
        join_summary,
        config,
    )
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(result.forecasts, args.output)
    _write_json(result.summary, summary_path)
    print(json.dumps(result.summary, indent=2))
    return 0


def configure_benchmark_fundamentals_dispatch(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV of realized prices")
    parser.add_argument("--config", required=True, type=Path, help="Battery JSON")
    parser.add_argument(
        "--forecasts", required=True, type=Path,
        help="Two-arm forecast CSV written by benchmark-fundamentals-forecast",
    )
    parser.add_argument(
        "--forecast-summary", type=Path,
        help="Forecast benchmark summary JSON; defaults beside the forecast CSV",
    )
    parser.add_argument(
        "--methods", nargs="+", required=True,
        help=(
            "The arms to settle. There is no default set: a comparison states which arms it "
            "settled, and every challenger must be named beside its own control"
        ),
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Settled interval dispatch CSV, one block per comparison method",
    )
    parser.add_argument("--daily-output", type=Path, help="Daily CSV; defaults beside --output")
    parser.add_argument(
        "--paired-differences", type=Path,
        help="Paired daily difference CSV; defaults beside --output",
    )
    parser.add_argument("--summary", type=Path, help="Comparison JSON; defaults beside --output")


def run_benchmark_fundamentals_dispatch(args: argparse.Namespace) -> int:
    summary_source = args.forecast_summary or args.forecasts.with_suffix(".summary.json")
    benchmark_summary = json.loads(summary_source.read_text(encoding="utf-8"))
    result = backtest_fundamentals_dispatch(
        _read_canonical_csv(args.prices),
        _read_battery_config(args.config),
        pd.read_csv(args.forecasts),
        benchmark_summary,
        methods=args.methods,
    )
    daily_path = args.daily_output or _sibling_path(args.output, ".daily.csv")
    paired_path = args.paired_differences or _sibling_path(args.output, ".paired.csv")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_dispatch_csv(result.interval_schedules, args.output)
    _write_plain_csv(result.daily_results, daily_path)
    _write_plain_csv(result.paired_differences, paired_path)
    _write_json(result.summary, summary_path)
    print(json.dumps(result.summary, indent=2))
    return 0


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
        name="build-point-in-time-features",
        help=(
            "Select strictly pre-cutoff feature revisions, emit one value per price interval, "
            "and record a provenance audit without filling excluded days"
        ),
        configure=configure_build_point_in_time_features,
        run=run_build_point_in_time_features,
    ),
    Command(
        name="benchmark-fundamentals-forecast",
        help=(
            "Run the price-history control and the fundamentals challenger over identical "
            "days, models, hyperparameters and refit cadence, selecting on validation only"
        ),
        configure=configure_benchmark_fundamentals_forecast,
        run=run_benchmark_fundamentals_forecast,
    ),
    Command(
        name="benchmark-fundamentals-dispatch",
        help=(
            "Settle every named ablation arm over the identical held-out common days, under "
            "one battery and one realized price series, and record the incremental margin"
        ),
        configure=configure_benchmark_fundamentals_dispatch,
        run=run_benchmark_fundamentals_dispatch,
    ),
    Command(
        name="combine-feature-tables",
        help=(
            "Combine point-in-time feature shards that tile one window into one table, "
            "refusing any overlap, gap or mixed retrieval identity"
        ),
        configure=configure_combine_feature_tables,
        run=run_combine_feature_tables,
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
