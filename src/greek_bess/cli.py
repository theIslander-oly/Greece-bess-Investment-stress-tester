"""Command-line entry points for market data and battery dispatch."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .analysis import AnnualDecompositionError, decompose_annual_replay
from .backtest import (
    backtest_forecast_dispatch,
    backtest_ml_dispatch_benchmark,
    simulate_degradation_dispatch,
)
from .data.admie import AdmieClient, AdmieError, select_latest_admie_revisions
from .data.admie_timing import (
    AdmiePublicationTimingError,
    GateClosureSchedule,
    audit_admie_publication_timing,
    read_retrieval_manifests,
)
from .data.custody import (
    CustodyError,
    build_custody_record,
    read_custody_record,
    verify_custody_record,
)
from .data.entsoe import EntsoeClient, EntsoeError
from .data.henex import HenexParseError, parse_henex_results
from .data.henex_archive import (
    HenexArchiveError,
    download_henex_annual_archives,
    find_henex_result_workbooks,
    normalize_henex_workbooks,
)
from .data.henex_daily import HenexDailyClient, HenexDailyError
from .data.http import OfficialDataDownloadError
from .data.quality import QualityReport, assess_quality, compare_sources
from .data.schema import concat_canonical, ensure_canonical, read_canonical_csv
from .data.synthetic import generate_synthetic_prices
from .data.timezones import GREECE_TZ, MARKET_TZ
from .degradation import DegradationConfig
from .dispatch import (
    BatteryDispatchConfig,
    DispatchInputError,
    DispatchSolveError,
    optimize_daily_perfect_foresight,
    optimize_perfect_foresight,
)
from .finance import FinanceConfig, evaluate_project_finance
from .forecast import (
    FORECAST_METHODS,
    ML_MODELS,
    MLForecastConfig,
    generate_ml_forecasts,
    generate_naive_forecasts,
)
from .reporting import (
    RESULT_KINDS,
    ReportContractError,
    build_run_manifest,
    read_run_manifest,
    write_run_manifest,
)
from .stress import (
    AvailabilityInputError,
    AvailabilityScheduleConfig,
    BootstrapConfig,
    BootstrapDispatchInputError,
    BootstrapInputError,
    NegativePriceEventConfig,
    PriceLevelShockConfig,
    PriceLevelShockInputError,
    ScenarioEnsembleInputError,
    ScenarioRun,
    SpreadCompressionConfig,
    apply_negative_price_events,
    apply_price_level_shock,
    apply_spread_compression,
    build_availability_profile,
    dispatch_bootstrap_paths,
    generate_seasonal_bootstrap_paths,
    report_scenario_ensemble,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greek-bess",
        description="Ingest and validate Greek Day-Ahead Market prices.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    synthetic = subparsers.add_parser(
        "generate-synthetic", help="Create labelled non-official demo prices"
    )
    synthetic.add_argument("--start-day", required=True, type=date.fromisoformat)
    synthetic.add_argument("--end-day", required=True, type=date.fromisoformat)
    synthetic.add_argument("--resolution-minutes", type=int, choices=(15, 60), default=60)
    synthetic.add_argument("--seed", type=int, default=42)
    synthetic.add_argument("--negative-price-share", type=float, default=0.02)
    synthetic.add_argument("--output", required=True, type=Path)

    henex = subparsers.add_parser(
        "parse-henex", help="Import a user-obtained HEnEx DAM results workbook"
    )
    henex.add_argument("workbook", type=Path)
    henex.add_argument("--output", required=True, type=Path)
    henex.add_argument("--allow-partial-days", action="store_true")

    henex_archives = subparsers.add_parser(
        "fetch-henex-archives",
        help="Download and normalize verified HEnEx annual DAM result archives",
    )
    henex_archives.add_argument("--start-year", required=True, type=int)
    henex_archives.add_argument("--end-year", required=True, type=int)
    henex_archives.add_argument("--raw-dir", type=Path, default=Path("data/raw/henex"))
    henex_archives.add_argument("--manifest", type=Path)
    henex_archives.add_argument("--output", required=True, type=Path)
    henex_archives.add_argument("--allow-partial-days", action="store_true")

    henex_directory = subparsers.add_parser(
        "normalize-henex-directory",
        help="Normalize all privately obtained HEnEx DAM result workbooks below a directory",
    )
    henex_directory.add_argument("directory", type=Path)
    henex_directory.add_argument("--output", required=True, type=Path)
    henex_directory.add_argument("--allow-partial-days", action="store_true")

    henex_daily = subparsers.add_parser(
        "fetch-henex-daily",
        help="Incrementally discover and normalize unarchived HEnEx daily DAM results",
    )
    henex_daily.add_argument("--start-day", required=True, type=date.fromisoformat)
    henex_daily.add_argument("--end-day", required=True, type=date.fromisoformat)
    henex_daily.add_argument("--max-catalog-pages", type=int, default=100)
    henex_daily.add_argument("--raw-dir", type=Path, default=Path("data/raw/henex"))
    henex_daily.add_argument("--manifest", type=Path)
    henex_daily.add_argument("--output", required=True, type=Path)
    henex_daily.add_argument("--allow-partial-days", action="store_true")

    entsoe = subparsers.add_parser(
        "fetch-entsoe", help="Fetch official Greek DAM prices using a personal token"
    )
    entsoe.add_argument(
        "--start", required=True, help="Timezone-aware start, e.g. 2026-01-01T00:00Z"
    )
    entsoe.add_argument("--end", required=True, help="Timezone-aware exclusive end")
    entsoe.add_argument("--chunk-days", type=int, default=31)
    entsoe.add_argument("--timeout-seconds", type=int, default=60)
    entsoe.add_argument("--max-attempts", type=int, default=5)
    entsoe.add_argument("--retry-backoff-seconds", type=float, default=10.0)
    entsoe.add_argument("--raw-cache-dir", type=Path, default=Path("data/raw/entsoe"))
    entsoe.add_argument("--output", required=True, type=Path)
    entsoe.add_argument("--allow-partial-days", action="store_true")

    admie_types = subparsers.add_parser(
        "list-admie-filetypes", help="Save the current public ADMIE filetype catalog"
    )
    admie_types.add_argument("--output", required=True, type=Path)

    admie_files = subparsers.add_parser(
        "fetch-admie-files",
        help="Discover and download official ADMIE files with publication-time provenance",
    )
    admie_files.add_argument("--filetypes", nargs="+", required=True)
    admie_files.add_argument("--start-day", required=True, type=date.fromisoformat)
    admie_files.add_argument("--end-day", required=True, type=date.fromisoformat)
    admie_files.add_argument("--raw-dir", type=Path, default=Path("data/raw/admie"))
    admie_files.add_argument("--manifest", type=Path)
    admie_files.add_argument("--all-revisions", action="store_true")

    admie_timing = subparsers.add_parser(
        "audit-admie-publication-timing",
        help=(
            "Audit ADMIE retrieval manifests against a declared day-ahead gate closure, "
            "without parsing any file"
        ),
    )
    admie_timing.add_argument(
        "manifests", nargs="+", type=Path, help="ADMIE retrieval manifest JSON files"
    )
    admie_timing.add_argument(
        "--gate-closure",
        required=True,
        type=Path,
        help="Declared gate-closure schedule JSON; there is no default closure time",
    )
    admie_timing.add_argument("--filetypes", nargs="+", required=True)
    admie_timing.add_argument("--start-day", required=True, type=date.fromisoformat)
    admie_timing.add_argument("--end-day", required=True, type=date.fromisoformat)
    admie_timing.add_argument(
        "--output", required=True, type=Path, help="Per-delivery-day verdict CSV"
    )
    admie_timing.add_argument("--observations", type=Path, help="Per-observation evidence CSV")
    admie_timing.add_argument("--summary", type=Path, help="Audit summary JSON")

    manifest_cmd = subparsers.add_parser(
        "record-run-manifest",
        help="Record a result summary under the versioned run-manifest contract",
    )
    manifest_cmd.add_argument("summary", type=Path, help="Summary JSON a result command wrote")
    manifest_cmd.add_argument(
        "--result-kind", required=True, choices=sorted(RESULT_KINDS), help="Declared result kind"
    )
    manifest_cmd.add_argument("--manifest-id", required=True, help="Identifier for this run")
    manifest_cmd.add_argument(
        "--produced-by", required=True, help="Command or API call that produced the summary"
    )
    manifest_cmd.add_argument(
        "--declared-inputs", type=Path, help="JSON object naming the run's declared inputs"
    )
    manifest_cmd.add_argument("--output", required=True, type=Path, help="Run manifest JSON")

    verify_manifest = subparsers.add_parser(
        "verify-run-manifest",
        help="Read a run manifest and refuse an unknown schema version or result kind",
    )
    verify_manifest.add_argument("manifest", type=Path)

    merge = subparsers.add_parser(
        "merge-canonical",
        help="Merge normalized CSV files from one official source into a single history",
    )
    merge.add_argument("inputs", nargs="+", type=Path)
    merge.add_argument("--allow-partial-days", action="store_true")
    merge.add_argument("--output", required=True, type=Path)

    compare = subparsers.add_parser(
        "compare-sources", help="Compare two normalized official-source CSV files"
    )
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--tolerance", type=float, default=1e-6)
    compare.add_argument("--output", required=True, type=Path)

    optimize = subparsers.add_parser(
        "optimize-perfect-foresight",
        help="Optimize a labelled DAM gross-margin upper bound",
    )
    optimize.add_argument("prices", type=Path, help="Canonical price CSV")
    optimize.add_argument("--config", required=True, type=Path, help="Battery JSON")
    optimize.add_argument("--availability", type=float, default=1.0)
    optimize.add_argument(
        "--daily-solves",
        action="store_true",
        help=(
            "Solve every market day independently and compose the schedules, the "
            "convention the forecast backtests are measured against, instead of one "
            "solve over the whole horizon"
        ),
    )
    optimize.add_argument("--output", required=True, type=Path, help="Dispatch CSV")
    optimize.add_argument("--summary", type=Path, help="Summary JSON; defaults beside dispatch CSV")

    forecast = subparsers.add_parser(
        "forecast-naive",
        help="Generate leakage-safe walk-forward price forecast baselines",
    )
    forecast.add_argument("prices", type=Path, help="Canonical price CSV")
    forecast.add_argument(
        "--methods",
        nargs="+",
        choices=FORECAST_METHODS,
        default=list(FORECAST_METHODS),
    )
    forecast.add_argument("--rolling-window-days", type=int, default=28)
    forecast.add_argument("--start-day", type=date.fromisoformat)
    forecast.add_argument("--output", required=True, type=Path, help="Forecast CSV")
    forecast.add_argument("--metrics", type=Path, help="Metrics JSON; defaults beside forecast CSV")

    ml_forecast = subparsers.add_parser(
        "forecast-ml",
        help="Run leakage-safe walk-forward ML and naïve forecast benchmarks",
    )
    ml_forecast.add_argument("prices", type=Path, help="Canonical price CSV")
    _add_ml_arguments(ml_forecast)
    ml_forecast.add_argument(
        "--output", required=True, type=Path, help="Validation/test forecast CSV"
    )
    ml_forecast.add_argument(
        "--summary", type=Path, help="Benchmark JSON; defaults beside forecast CSV"
    )

    backtest = subparsers.add_parser(
        "backtest-forecast-dispatch",
        help="Plan dispatch on forecasts and settle against realized prices",
    )
    backtest.add_argument("prices", type=Path, help="Canonical price CSV")
    backtest.add_argument("--config", required=True, type=Path, help="Battery JSON")
    backtest.add_argument("--method", choices=FORECAST_METHODS, default="ensemble")
    backtest.add_argument("--rolling-window-days", type=int, default=28)
    backtest.add_argument("--start-day", type=date.fromisoformat)
    backtest.add_argument("--output", required=True, type=Path, help="Interval CSV")
    backtest.add_argument(
        "--daily-output", type=Path, help="Daily CSV; defaults beside interval CSV"
    )
    backtest.add_argument("--summary", type=Path, help="Summary JSON; defaults beside interval CSV")

    ml_backtest = subparsers.add_parser(
        "backtest-ml-dispatch",
        help="Compare ML and naïve forecast dispatch over identical held-out test days",
    )
    ml_backtest.add_argument("prices", type=Path, help="Canonical price CSV")
    ml_backtest.add_argument("--config", required=True, type=Path, help="Battery JSON")
    _add_ml_arguments(ml_backtest)
    ml_backtest.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Selected-model held-out interval dispatch CSV",
    )
    ml_backtest.add_argument("--forecasts-output", type=Path)
    ml_backtest.add_argument("--daily-output", type=Path)
    ml_backtest.add_argument("--forecast-summary", type=Path)
    ml_backtest.add_argument("--summary", type=Path)

    degradation = subparsers.add_parser(
        "simulate-degradation-dispatch",
        help=(
            "Run daily perfect-foresight dispatch with evolving capacity, "
            "warranty screening and augmentation"
        ),
    )
    degradation.add_argument("prices", type=Path, help="Canonical price CSV")
    degradation.add_argument("--config", required=True, type=Path, help="Battery dispatch JSON")
    degradation.add_argument(
        "--degradation-config",
        required=True,
        type=Path,
        help="Degradation and augmentation JSON",
    )
    degradation.add_argument("--output", required=True, type=Path, help="Interval dispatch CSV")
    degradation.add_argument("--daily-output", type=Path)
    degradation.add_argument("--cohort-output", type=Path)
    degradation.add_argument("--summary", type=Path)

    finance = subparsers.add_parser(
        "evaluate-project-finance",
        help=(
            "Calculate unlevered pre-tax project cash flows, NPV, IRR, payback "
            "and break-even outputs from a complete daily operating path"
        ),
    )
    finance.add_argument(
        "daily_results",
        type=Path,
        help="Daily dispatch results with margin, discharge and augmentation columns",
    )
    finance.add_argument(
        "--finance-config", required=True, type=Path, help="Finance assumptions JSON"
    )
    finance.add_argument("--output", required=True, type=Path, help="Annual cash-flow CSV")
    finance.add_argument("--daily-output", type=Path)
    finance.add_argument("--summary", type=Path)

    bootstrap = subparsers.add_parser(
        "generate-bootstrap-paths",
        help="Generate labelled synthetic seasonal block-bootstrap price paths",
    )
    bootstrap.add_argument("prices", type=Path, help="Canonical historical price CSV")
    bootstrap.add_argument("--config", required=True, type=Path, help="Bootstrap assumptions JSON")
    bootstrap.add_argument("--output", required=True, type=Path, help="Synthetic paths CSV")
    bootstrap.add_argument("--provenance", type=Path, help="Sampled-block provenance CSV")
    bootstrap.add_argument("--summary", type=Path, help="Method and configuration JSON")

    bootstrap_dispatch = subparsers.add_parser(
        "dispatch-bootstrap-paths",
        help="Dispatch each validated synthetic bootstrap path independently",
    )
    bootstrap_dispatch.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    bootstrap_dispatch.add_argument("--config", required=True, type=Path, help="Battery JSON")
    bootstrap_dispatch.add_argument(
        "--availability",
        type=float,
        default=None,
        help="Constant available fraction applied to every interval of every path",
    )
    bootstrap_dispatch.add_argument(
        "--availability-schedule",
        type=Path,
        help=(
            "Declared availability schedule JSON: a baseline fraction with no default plus "
            "declared outage windows. Mutually exclusive with --availability"
        ),
    )
    bootstrap_dispatch.add_argument(
        "--availability-provenance",
        type=Path,
        help="Per-interval availability provenance CSV; defaults beside output",
    )
    bootstrap_dispatch.add_argument(
        "--output", required=True, type=Path, help="Interval dispatch CSV"
    )
    bootstrap_dispatch.add_argument("--path-summary", type=Path, help="Path summaries CSV")
    bootstrap_dispatch.add_argument("--summary", type=Path, help="Method summary JSON")

    shock = subparsers.add_parser(
        "apply-price-level-shock",
        help="Apply a labelled additive price-level shock to synthetic bootstrap paths",
    )
    shock.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    shock.add_argument(
        "--config", required=True, type=Path, help="Price-level shock assumptions JSON"
    )
    shock.add_argument("--output", required=True, type=Path, help="Shocked paths CSV")
    shock.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    shock.add_argument("--summary", type=Path, help="Method and configuration JSON")

    compression = subparsers.add_parser(
        "compress-spread",
        help="Compress within-day spread of synthetic bootstrap paths about a daily reference",
    )
    compression.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    compression.add_argument(
        "--config", required=True, type=Path, help="Spread compression assumptions JSON"
    )
    compression.add_argument("--output", required=True, type=Path, help="Compressed paths CSV")
    compression.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    compression.add_argument("--summary", type=Path, help="Method and configuration JSON")

    negative_events = subparsers.add_parser(
        "apply-negative-price-events",
        help="Apply explicitly declared negative-price event windows to synthetic bootstrap paths",
    )
    negative_events.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    negative_events.add_argument(
        "--config", required=True, type=Path, help="Declared negative-price events JSON"
    )
    negative_events.add_argument("--output", required=True, type=Path, help="Transformed paths CSV")
    negative_events.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    negative_events.add_argument("--summary", type=Path, help="Method and configuration JSON")

    ensemble = subparsers.add_parser(
        "report-scenario-ensemble",
        help=(
            "Report the non-probabilistic range of margins across named, already-dispatched "
            "scenarios"
        ),
    )
    ensemble.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help=(
            "Scenario manifest JSON. Every scenario is named explicitly; there is no default "
            "scenario set and no implicit baseline"
        ),
    )
    ensemble.add_argument("--output", required=True, type=Path, help="Per-path range CSV")
    ensemble.add_argument(
        "--margins",
        type=Path,
        help="Per-scenario, per-path margin CSV with provenance; defaults beside output",
    )
    ensemble.add_argument(
        "--summary", type=Path, help="Method summary JSON; defaults beside output"
    )

    annual = subparsers.add_parser(
        "decompose-annual-replay",
        help="Split an accepted replay into delivery years on the CET/CEST market clock",
    )
    annual.add_argument("prices", type=Path, help="Accepted canonical price CSV")
    annual.add_argument(
        "--perfect-foresight-schedule",
        type=Path,
        help="Interval dispatch CSV from optimize-perfect-foresight over the same history",
    )
    annual.add_argument(
        "--daily-results",
        action="extend",
        nargs="+",
        default=[],
        metavar="METHOD=PATH",
        help=(
            "Daily CSV from backtest-forecast-dispatch, as METHOD=PATH. Repeat the flag "
            "or pass several pairs to it; both accumulate"
        ),
    )
    annual.add_argument(
        "--energy-capacity-mwh",
        type=float,
        help="Battery energy capacity; required only for equivalent-full-cycle columns",
    )
    annual.add_argument("--output", required=True, type=Path, help="Per-year overview CSV")
    annual.add_argument(
        "--forecast-output", type=Path, help="Per-year, per-method CSV; defaults beside output"
    )
    annual.add_argument(
        "--common-day-output",
        type=Path,
        help="Per-year like-for-like CSV; defaults beside output",
    )
    annual.add_argument("--summary", type=Path, help="Summary JSON; defaults beside output")

    record_custody = subparsers.add_parser(
        "record-custody",
        help="Fingerprint an accepted official artifact without recording any price",
    )
    record_custody.add_argument(
        "directory", type=Path, help="Directory holding the extracted artifact"
    )
    record_custody.add_argument("--artifact-name", required=True)
    record_custody.add_argument("--source-run-id", required=True)
    record_custody.add_argument("--source-workflow")
    record_custody.add_argument(
        "--published-digest",
        help="SHA-256 the provider publishes for the artifact archive, when it exposes one",
    )
    record_custody.add_argument("--output", required=True, type=Path, help="Custody record JSON")

    verify_custody = subparsers.add_parser(
        "verify-custody",
        help="Verify a stored copy against a committed custody record",
    )
    verify_custody.add_argument(
        "directory", type=Path, help="Directory holding the copy under verification"
    )
    verify_custody.add_argument("--record", required=True, type=Path)
    verify_custody.add_argument("--report", type=Path, help="Verification result JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate-synthetic":
            frame = generate_synthetic_prices(
                args.start_day,
                args.end_day,
                resolution_minutes=args.resolution_minutes,
                seed=args.seed,
                negative_price_share=args.negative_price_share,
            )
            report = assess_quality(frame)
        elif args.command == "parse-henex":
            frame = parse_henex_results(args.workbook)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "fetch-henex-archives":
            if args.end_year < args.start_year:
                raise ValueError("end-year must not precede start-year")
            manifest = args.manifest or args.raw_dir / "retrieval_manifest.json"
            workbooks, _ = download_henex_annual_archives(
                range(args.start_year, args.end_year + 1),
                raw_dir=args.raw_dir,
                manifest_path=manifest,
            )
            frame = normalize_henex_workbooks(workbooks)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "normalize-henex-directory":
            workbooks = find_henex_result_workbooks(args.directory)
            if not workbooks:
                raise HenexParseError(
                    f"No YYYYMMDD_EL-DAM_Results_EN_v##.xlsx files below {args.directory}"
                )
            frame = normalize_henex_workbooks(workbooks)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "fetch-henex-daily":
            henex_daily_client = HenexDailyClient()
            entries = henex_daily_client.discover(
                args.start_day,
                args.end_day,
                max_pages=args.max_catalog_pages,
            )
            if not entries:
                raise HenexDailyError("No HEnEx daily results found for the requested dates")
            manifest = args.manifest or args.raw_dir / "daily_retrieval_manifest.json"
            workbooks, _ = henex_daily_client.download_results(
                entries,
                raw_dir=args.raw_dir,
                manifest_path=manifest,
            )
            frame = normalize_henex_workbooks(workbooks)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "fetch-entsoe":
            entsoe_client = EntsoeClient(
                raw_cache_dir=args.raw_cache_dir,
                timeout_seconds=args.timeout_seconds,
                max_attempts=args.max_attempts,
                retry_backoff_seconds=args.retry_backoff_seconds,
            )
            frame = entsoe_client.fetch_prices(args.start, args.end, chunk_days=args.chunk_days)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "list-admie-filetypes":
            filetypes = AdmieClient().list_filetypes()
            _write_json(filetypes, args.output)
            print(json.dumps({"filetype_count": len(filetypes)}, indent=2))
            return 0
        elif args.command == "fetch-admie-files":
            admie_client = AdmieClient()
            discovered = []
            empty_filetypes = []
            for filetype in args.filetypes:
                found = admie_client.find_files(
                    filetype, args.start_day, args.end_day, overlap=True
                )
                if not found:
                    empty_filetypes.append(filetype)
                discovered.extend(found)
            if empty_filetypes:
                raise AdmieError(
                    _admie_empty_discovery_message(
                        admie_client, empty_filetypes, args.start_day, args.end_day
                    )
                )
            selected = (
                discovered if args.all_revisions else select_latest_admie_revisions(discovered)
            )
            manifest = args.manifest or args.raw_dir / "retrieval_manifest.json"
            records = admie_client.download_files(
                selected,
                raw_dir=args.raw_dir,
                manifest_path=manifest,
            )
            print(
                json.dumps(
                    {
                        "discovered_file_count": len(discovered),
                        "downloaded_file_count": len(records),
                        "latest_revision_selection": not args.all_revisions,
                        "manifest": str(manifest),
                    },
                    indent=2,
                )
            )
            return 0
        elif args.command == "audit-admie-publication-timing":
            timing = audit_admie_publication_timing(
                read_retrieval_manifests(args.manifests),
                schedule=_read_gate_closure_schedule(args.gate_closure),
                filetypes=args.filetypes,
                start_day=args.start_day,
                end_day=args.end_day,
            )
            observations_path = args.observations or _sibling_path(
                args.output, ".observations.csv"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(timing.delivery_days, args.output)
            _write_plain_csv(timing.observations, observations_path)
            _write_json(timing.summary, summary_path)
            print(json.dumps(timing.summary, indent=2))
            return 0 if timing.summary["timing_accepted"] else 2
        elif args.command == "record-run-manifest":
            summary_payload = json.loads(args.summary.read_text(encoding="utf-8"))
            if not isinstance(summary_payload, dict):
                raise ReportContractError("A result summary must be one JSON object")
            declared_inputs = (
                json.loads(args.declared_inputs.read_text(encoding="utf-8"))
                if args.declared_inputs is not None
                else {}
            )
            if not isinstance(declared_inputs, dict):
                raise ReportContractError("declared inputs must be one JSON object")
            manifest_record = build_run_manifest(
                summary_payload,
                kind_id=args.result_kind,
                manifest_id=args.manifest_id,
                produced_by=args.produced_by,
                declared_inputs=declared_inputs,
            )
            write_run_manifest(args.output, manifest_record)
            print(json.dumps(manifest_record.to_dict(), indent=2, default=str))
            return 0
        elif args.command == "verify-run-manifest":
            verified = read_run_manifest(args.manifest)
            print(
                json.dumps(
                    {
                        "schema_version": verified.schema_version,
                        "manifest_id": verified.manifest_id,
                        "result_kind": verified.result_kind,
                        "basis": verified.basis,
                        "result_label": verified.result_label,
                        "project_version": verified.project_version,
                    },
                    indent=2,
                )
            )
            return 0
        elif args.command == "merge-canonical":
            frame = concat_canonical(_read_canonical_csv(path) for path in args.inputs)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "compare-sources":
            comparison = compare_sources(
                _read_canonical_csv(args.left),
                _read_canonical_csv(args.right),
                tolerance_eur_per_mwh=args.tolerance,
            )
            if args.output.suffix.lower() != ".csv":
                raise ValueError("Cross-source comparison output must be .csv")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            comparison.to_csv(args.output, index=False)
            counts = comparison["comparison_status"].value_counts().to_dict()
            print(json.dumps({"row_count": len(comparison), "status_counts": counts}, indent=2))
            return 0 if set(counts) <= {"match"} else 2
        elif args.command == "optimize-perfect-foresight":
            config = _read_battery_config(args.config)
            optimizer = (
                optimize_daily_perfect_foresight
                if args.daily_solves
                else optimize_perfect_foresight
            )
            dispatch_result = optimizer(
                _read_canonical_csv(args.prices),
                config,
                availability=args.availability,
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_outputs(
                dispatch_result.schedule, dispatch_result.summary, args.output, summary_path
            )
            print(json.dumps(dispatch_result.summary, indent=2))
            return 0
        elif args.command == "forecast-naive":
            forecast_result = generate_naive_forecasts(
                _read_canonical_csv(args.prices),
                methods=args.methods,
                rolling_window_days=args.rolling_window_days,
                start_day=args.start_day,
            )
            metrics_path = args.metrics or args.output.with_suffix(".metrics.json")
            _write_plain_csv(forecast_result.forecasts, args.output)
            _write_json(forecast_result.metrics, metrics_path)
            print(json.dumps(forecast_result.metrics, indent=2))
            return 0
        elif args.command == "forecast-ml":
            ml_forecast_result = generate_ml_forecasts(
                _read_canonical_csv(args.prices), _ml_config_from_args(args)
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(ml_forecast_result.forecasts, args.output)
            _write_json(ml_forecast_result.summary, summary_path)
            print(json.dumps(ml_forecast_result.summary, indent=2))
            return 0
        elif args.command == "backtest-forecast-dispatch":
            forecast_backtest_result = backtest_forecast_dispatch(
                _read_canonical_csv(args.prices),
                _read_battery_config(args.config),
                method=args.method,
                rolling_window_days=args.rolling_window_days,
                start_day=args.start_day,
            )
            daily_path = args.daily_output or args.output.with_suffix(".daily.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(forecast_backtest_result.interval_schedule, args.output)
            _write_plain_csv(forecast_backtest_result.daily_results, daily_path)
            _write_json(forecast_backtest_result.summary, summary_path)
            print(json.dumps(forecast_backtest_result.summary, indent=2))
            return 0
        elif args.command == "backtest-ml-dispatch":
            prices = _read_canonical_csv(args.prices)
            ml_result = generate_ml_forecasts(prices, _ml_config_from_args(args))
            ml_dispatch_result = backtest_ml_dispatch_benchmark(
                prices, _read_battery_config(args.config), ml_result
            )
            forecasts_path = args.forecasts_output or _sibling_path(args.output, ".forecasts.csv")
            daily_path = args.daily_output or _sibling_path(args.output, ".daily.csv")
            forecast_summary_path = args.forecast_summary or _sibling_path(
                args.output, ".forecast.summary.json"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(ml_dispatch_result.selected_model_interval_schedule, args.output)
            _write_plain_csv(ml_result.forecasts, forecasts_path)
            _write_plain_csv(ml_dispatch_result.daily_results, daily_path)
            _write_json(ml_result.summary, forecast_summary_path)
            _write_json(ml_dispatch_result.summary, summary_path)
            print(json.dumps(ml_dispatch_result.summary, indent=2))
            return 0
        elif args.command == "simulate-degradation-dispatch":
            degradation_result = simulate_degradation_dispatch(
                _read_canonical_csv(args.prices),
                _read_battery_config(args.config),
                _read_degradation_config(args.degradation_config),
            )
            daily_path = args.daily_output or _sibling_path(args.output, ".daily.csv")
            cohort_path = args.cohort_output or _sibling_path(args.output, ".cohorts.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(degradation_result.interval_schedule, args.output)
            _write_plain_csv(degradation_result.daily_results, daily_path)
            _write_plain_csv(degradation_result.cohort_states, cohort_path)
            _write_json(degradation_result.summary, summary_path)
            print(json.dumps(degradation_result.summary, indent=2))
            return 0
        elif args.command == "evaluate-project-finance":
            finance_result = evaluate_project_finance(
                pd.read_csv(args.daily_results),
                _read_finance_config(args.finance_config),
            )
            daily_path = args.daily_output or _sibling_path(args.output, ".daily.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(finance_result.annual_cash_flows, args.output)
            _write_plain_csv(finance_result.daily_cash_flows, daily_path)
            _write_json(finance_result.summary, summary_path)
            print(json.dumps(finance_result.summary, indent=2))
            return 0
        elif args.command == "generate-bootstrap-paths":
            bootstrap_result = generate_seasonal_bootstrap_paths(
                _read_canonical_csv(args.prices), _read_bootstrap_config(args.config)
            )
            provenance_path = args.provenance or _sibling_path(args.output, ".provenance.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            export = bootstrap_result.paths.copy()
            export["quality_flags"] = export["quality_flags"].map(json.dumps)
            _write_plain_csv(export, args.output)
            _write_plain_csv(bootstrap_result.provenance, provenance_path)
            _write_json(bootstrap_result.summary, summary_path)
            print(json.dumps(bootstrap_result.summary, indent=2))
            return 0
        elif args.command == "dispatch-bootstrap-paths":
            if args.availability is not None and args.availability_schedule is not None:
                raise AvailabilityInputError(
                    "Declare either --availability or --availability-schedule, not both; "
                    "two availability assumptions for one run have no resolution"
                )
            dispatch_paths = _read_bootstrap_paths_csv(args.paths)
            availability_profile = None
            if args.availability_schedule is not None:
                availability_profile = build_availability_profile(
                    dispatch_paths, _read_availability_config(args.availability_schedule)
                )
            bootstrap_dispatch_result = dispatch_bootstrap_paths(
                dispatch_paths,
                _read_battery_config(args.config),
                availability=(
                    availability_profile
                    if availability_profile is not None
                    else (1.0 if args.availability is None else args.availability)
                ),
            )
            path_summary_path = args.path_summary or _sibling_path(args.output, ".paths.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(bootstrap_dispatch_result.interval_results, args.output)
            _write_plain_csv(bootstrap_dispatch_result.path_summaries, path_summary_path)
            if availability_profile is not None:
                _write_plain_csv(
                    availability_profile.provenance,
                    args.availability_provenance or _sibling_path(args.output, ".availability.csv"),
                )
            _write_json(bootstrap_dispatch_result.summary, summary_path)
            print(json.dumps(bootstrap_dispatch_result.summary, indent=2))
            return 0
        elif args.command == "report-scenario-ensemble":
            ensemble_result = report_scenario_ensemble(_read_scenario_manifest(args.manifest))
            margins_path = args.margins or _sibling_path(args.output, ".margins.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(ensemble_result.scenario_ranges, args.output)
            _write_plain_csv(ensemble_result.scenario_margins, margins_path)
            _write_json(ensemble_result.summary, summary_path)
            print(json.dumps(ensemble_result.summary, indent=2))
            return 0
        elif args.command == "decompose-annual-replay":
            annual_result = decompose_annual_replay(
                _read_canonical_csv(args.prices),
                perfect_foresight_schedule=(
                    _read_schedule_csv(args.perfect_foresight_schedule)
                    if args.perfect_foresight_schedule
                    else None
                ),
                daily_results_by_method=_read_daily_results(args.daily_results),
                energy_capacity_mwh=args.energy_capacity_mwh,
            )
            forecast_path = args.forecast_output or _sibling_path(args.output, ".forecast.csv")
            common_day_path = args.common_day_output or _sibling_path(
                args.output, ".common_day.csv"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(annual_result.annual_overview, args.output)
            _write_plain_csv(annual_result.annual_forecast, forecast_path)
            _write_plain_csv(annual_result.annual_common_day, common_day_path)
            _write_json(annual_result.summary, summary_path)
            print(json.dumps(annual_result.summary, indent=2))
            return 0
        elif args.command == "record-custody":
            custody = build_custody_record(
                args.directory,
                artifact_name=args.artifact_name,
                source_run_id=args.source_run_id,
                source_workflow=args.source_workflow,
                published_artifact_digest_sha256=args.published_digest,
            )
            _write_json(custody.to_dict(), args.output)
            print(json.dumps(custody.to_dict(), indent=2))
            return 0
        elif args.command == "verify-custody":
            custody = read_custody_record(args.record)
            differences = verify_custody_record(custody, args.directory)
            result = {
                "artifact_name": custody.artifact_name,
                "source_run_id": custody.source_run_id,
                "recorded_at_utc": custody.recorded_at_utc,
                "file_count": custody.file_count,
                "difference_count": len(differences),
                "differences": differences,
                "verified": not differences,
            }
            if args.report is not None:
                _write_json(result, args.report)
            print(json.dumps(result, indent=2))
            return 0 if not differences else 2
        elif args.command == "apply-price-level-shock":
            shock_result = apply_price_level_shock(
                _read_bootstrap_paths_csv(args.paths), _read_price_level_config(args.config)
            )
            provenance_path = args.provenance or _sibling_path(args.output, ".provenance.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            export = shock_result.paths.copy()
            export["quality_flags"] = export["quality_flags"].map(json.dumps)
            _write_plain_csv(export, args.output)
            _write_plain_csv(shock_result.provenance, provenance_path)
            _write_json(shock_result.summary, summary_path)
            print(json.dumps(shock_result.summary, indent=2))
            return 0
        elif args.command == "compress-spread":
            compression_result = apply_spread_compression(
                _read_bootstrap_paths_csv(args.paths), _read_spread_compression_config(args.config)
            )
            provenance_path = args.provenance or _sibling_path(args.output, ".provenance.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            export = compression_result.paths.copy()
            export["quality_flags"] = export["quality_flags"].map(json.dumps)
            _write_plain_csv(export, args.output)
            _write_plain_csv(compression_result.provenance, provenance_path)
            _write_json(compression_result.summary, summary_path)
            print(json.dumps(compression_result.summary, indent=2))
            return 0
        elif args.command == "apply-negative-price-events":
            event_result = apply_negative_price_events(
                _read_bootstrap_paths_csv(args.paths),
                _read_negative_price_event_config(args.config),
            )
            provenance_path = args.provenance or _sibling_path(args.output, ".provenance.csv")
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            export = event_result.paths.copy()
            export["quality_flags"] = export["quality_flags"].map(json.dumps)
            _write_plain_csv(export, args.output)
            _write_plain_csv(event_result.provenance, provenance_path)
            _write_json(event_result.summary, summary_path)
            print(json.dumps(event_result.summary, indent=2))
            return 0
        else:  # pragma: no cover - argparse makes this unreachable.
            raise AssertionError(f"Unhandled command: {args.command}")

        _write_outputs(frame, report, args.output)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.is_valid else 2
    except (
        ValueError,
        DispatchInputError,
        DispatchSolveError,
        EntsoeError,
        HenexParseError,
        HenexArchiveError,
        HenexDailyError,
        AdmieError,
        AdmiePublicationTimingError,
        OfficialDataDownloadError,
        BootstrapInputError,
        AvailabilityInputError,
        BootstrapDispatchInputError,
        PriceLevelShockInputError,
        ScenarioEnsembleInputError,
        AnnualDecompositionError,
        CustodyError,
        ReportContractError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _write_outputs(frame: pd.DataFrame, report: QualityReport, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("The ingestion foundation currently writes .csv outputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    export = frame.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)

    temporary_csv = output.with_suffix(output.suffix + ".tmp")
    export.to_csv(temporary_csv, index=False)
    temporary_csv.replace(output)

    quality_path = output.with_suffix(".quality.json")
    temporary_quality = quality_path.with_suffix(quality_path.suffix + ".tmp")
    temporary_quality.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    temporary_quality.replace(quality_path)


def _add_ml_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--validation-start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--test-start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--models", nargs="+", choices=ML_MODELS, default=list(ML_MODELS))
    parser.add_argument("--feature-window-days", type=int, default=28)
    parser.add_argument("--refit-frequency-days", type=int, default=7)
    parser.add_argument("--min-training-days", type=int, default=28)
    parser.add_argument("--training-window-days", type=int)
    parser.add_argument("--ridge-alpha", type=float, default=10.0)
    parser.add_argument("--gradient-max-iter", type=int, default=150)
    parser.add_argument("--random-seed", type=int, default=42)


def _ml_config_from_args(args: argparse.Namespace) -> MLForecastConfig:
    return MLForecastConfig(
        validation_start_day=args.validation_start_day,
        test_start_day=args.test_start_day,
        models=tuple(args.models),
        feature_window_days=args.feature_window_days,
        refit_frequency_days=args.refit_frequency_days,
        min_training_days=args.min_training_days,
        training_window_days=args.training_window_days,
        ridge_alpha=args.ridge_alpha,
        gradient_max_iter=args.gradient_max_iter,
        random_seed=args.random_seed,
    )


def _sibling_path(output: Path, suffix: str) -> Path:
    return output.with_name(output.stem + suffix)


def _read_canonical_csv(path: Path) -> pd.DataFrame:
    return read_canonical_csv(path)


def _read_bootstrap_paths_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "path_id" not in frame:
        raise BootstrapDispatchInputError("Missing bootstrap path columns: path_id")
    path_frames: list[pd.DataFrame] = []
    for path_id, group in frame.groupby("path_id", sort=True):
        group = group.drop(columns="path_id").copy()
        group["delivery_start_utc"] = pd.to_datetime(group["delivery_start_utc"], utc=True)
        group["delivery_end_utc"] = pd.to_datetime(group["delivery_end_utc"], utc=True)
        group["retrieved_at_utc"] = pd.to_datetime(group["retrieved_at_utc"], utc=True)
        group["delivery_start_market"] = group["delivery_start_utc"].dt.tz_convert(MARKET_TZ)
        group["delivery_start_greece"] = group["delivery_start_utc"].dt.tz_convert(GREECE_TZ)
        group["quality_flags"] = group["quality_flags"].map(
            lambda value: json.loads(value) if isinstance(value, str) else []
        )
        canonical = ensure_canonical(group)
        canonical.insert(0, "path_id", path_id)
        path_frames.append(canonical)
    return pd.concat(path_frames, ignore_index=True)


def _read_schedule_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "delivery_start_utc" not in frame:
        raise AnnualDecompositionError(
            "Perfect-foresight schedule is missing columns: delivery_start_utc"
        )
    frame["delivery_start_utc"] = pd.to_datetime(frame["delivery_start_utc"], utc=True)
    return frame


def _read_daily_results(pairs: list[str]) -> dict[str, pd.DataFrame]:
    daily_results: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        method, separator, raw_path = pair.partition("=")
        if not separator or not method or not raw_path:
            raise AnnualDecompositionError(
                f"--daily-results expects METHOD=PATH pairs, not {pair!r}"
            )
        if method in daily_results:
            raise AnnualDecompositionError(f"--daily-results repeats the method {method!r}")
        daily_results[method] = pd.read_csv(Path(raw_path))
    return daily_results


def _write_dispatch_outputs(
    schedule: pd.DataFrame,
    summary: dict[str, object],
    output: Path,
    summary_path: Path,
) -> None:
    _write_dispatch_csv(schedule, output)
    _write_json(summary, summary_path)


def _read_battery_config(path: Path) -> BatteryDispatchConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Battery config JSON must contain one object")
    return BatteryDispatchConfig(**payload)


def _read_degradation_config(path: Path) -> DegradationConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DegradationConfig.from_dict(payload)


def _read_finance_config(path: Path) -> FinanceConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FinanceConfig.from_dict(payload)


def _read_bootstrap_config(path: Path) -> BootstrapConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BootstrapConfig.from_dict(payload)


def _read_price_level_config(path: Path) -> PriceLevelShockConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PriceLevelShockConfig.from_dict(payload)


def _admie_empty_discovery_message(
    client: AdmieClient, filetypes: list[str], start_day: date, end_day: date
) -> str:
    """Explain an empty ADMIE discovery, distinguishing a wrong name from a quiet publisher.

    An empty retrieval used to write an empty manifest and exit zero. Downstream, every audited
    delivery day then reported ``no_record``, which reads as "the publisher published nothing" —
    one of the four things the timing audit explicitly does not establish. A misspelled or
    renamed filetype must not be able to impersonate that finding, so the live catalog is
    consulted and the two cases are named apart.
    """

    window = f"{start_day.isoformat()}..{end_day.isoformat()}"
    try:
        catalog = sorted(
            {str(entry.get("filetype", "")) for entry in client.list_filetypes()} - {""}
        )
    except (AdmieError, OfficialDataDownloadError):
        catalog = []
    if not catalog:
        return (
            f"ADMIE returned no files for {', '.join(filetypes)} over {window}, and the filetype "
            "catalog could not be read to check the names. An empty retrieval is refused rather "
            "than written as an empty manifest."
        )
    unknown = [name for name in filetypes if name not in catalog]
    if unknown:
        return (
            f"ADMIE publishes no filetype named {', '.join(unknown)}. The live catalog offers: "
            f"{', '.join(catalog)}. A retrieval naming a filetype the provider does not publish "
            "is refused, because downstream it is indistinguishable from a delivery day the "
            "provider genuinely never published for."
        )
    return (
        f"ADMIE published no {', '.join(filetypes)} file covering {window}. The filetype names "
        "are valid, so this is an empty window rather than a wrong name. An empty retrieval is "
        "refused rather than written as an empty manifest; widen the window or record the "
        "absence deliberately."
    )


def _read_gate_closure_schedule(path: Path) -> GateClosureSchedule:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return GateClosureSchedule.from_dict(payload)


def _read_availability_config(path: Path) -> AvailabilityScheduleConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AvailabilityScheduleConfig.from_dict(payload)


def _read_scenario_manifest(path: Path) -> list[ScenarioRun]:
    """Read the explicit list of named scenarios an ensemble is built from.

    Every field is required, including ``transformation_summary_json``: a scenario with no
    transformation states that as ``null`` rather than omitting the key, so an untransformed
    replay is a declared member of the ensemble and never an implicit baseline. Relative
    paths resolve against the manifest's own directory.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScenarioEnsembleInputError("Scenario manifest JSON must contain one object")
    unknown = sorted(set(payload) - {"scenarios"})
    if unknown:
        raise ScenarioEnsembleInputError(f"Unknown scenario manifest fields: {', '.join(unknown)}")
    declared = payload.get("scenarios")
    if not isinstance(declared, list):
        raise ScenarioEnsembleInputError("Scenario manifest must declare a scenarios list")

    root = path.parent
    required = {
        "name",
        "run_id",
        "path_summaries_csv",
        "dispatch_summary_json",
        "bootstrap_summary_json",
        "transformation_summary_json",
    }
    runs: list[ScenarioRun] = []
    for entry in declared:
        if not isinstance(entry, dict):
            raise ScenarioEnsembleInputError("Every manifest scenario must be one object")
        unknown = sorted(set(entry) - required)
        missing = sorted(required - set(entry))
        if unknown:
            raise ScenarioEnsembleInputError(f"Unknown scenario fields: {', '.join(unknown)}")
        if missing:
            raise ScenarioEnsembleInputError(f"Missing scenario fields: {', '.join(missing)}")
        transformation = entry["transformation_summary_json"]
        runs.append(
            ScenarioRun(
                name=entry["name"],
                run_id=entry["run_id"],
                path_summaries=pd.read_csv(root / str(entry["path_summaries_csv"])),
                dispatch_summary=_read_summary_json(root / str(entry["dispatch_summary_json"])),
                bootstrap_summary=_read_summary_json(root / str(entry["bootstrap_summary_json"])),
                transformation_summary=(
                    None
                    if transformation is None
                    else _read_summary_json(root / str(transformation))
                ),
            )
        )
    return runs


def _read_summary_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScenarioEnsembleInputError(f"{path.name} must contain one summary object")
    return payload


def _read_spread_compression_config(path: Path) -> SpreadCompressionConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SpreadCompressionConfig.from_dict(payload)


def _read_negative_price_event_config(path: Path) -> NegativePriceEventConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return NegativePriceEventConfig.from_dict(payload)


def _write_dispatch_csv(schedule: pd.DataFrame, output: Path) -> None:
    export = schedule.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)
    _write_plain_csv(export, output)


def _write_plain_csv(frame: pd.DataFrame, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("Tabular output must be .csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(output)


def _write_json(payload: object, output: Path) -> None:
    if output.suffix.lower() != ".json":
        raise ValueError("JSON output must be .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


if __name__ == "__main__":
    raise SystemExit(main())
