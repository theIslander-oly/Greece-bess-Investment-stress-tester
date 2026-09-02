"""Retrieval, parsing and merging of canonical Greek DAM price history."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from ..data.entsoe import EntsoeClient
from ..data.henex import HenexParseError, parse_henex_results
from ..data.henex_archive import (
    download_henex_annual_archives,
    find_henex_result_workbooks,
    normalize_henex_workbooks,
)
from ..data.henex_daily import HenexDailyClient, HenexDailyError
from ..data.quality import assess_quality, compare_sources
from ..data.schema import concat_canonical
from ..data.synthetic import generate_synthetic_prices
from ._registry import Command
from ._support import _read_canonical_csv, report_ingestion


def configure_generate_synthetic(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument("--resolution-minutes", type=int, choices=(15, 60), default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--negative-price-share", type=float, default=0.02)
    parser.add_argument("--output", required=True, type=Path)


def run_generate_synthetic(args: argparse.Namespace) -> int:
    frame = generate_synthetic_prices(
        args.start_day,
        args.end_day,
        resolution_minutes=args.resolution_minutes,
        seed=args.seed,
        negative_price_share=args.negative_price_share,
    )
    report = assess_quality(frame)
    return report_ingestion(frame, report, args.output)


def configure_parse_henex(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")


def run_parse_henex(args: argparse.Namespace) -> int:
    frame = parse_henex_results(args.workbook)
    report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
    return report_ingestion(frame, report, args.output)


def configure_fetch_henex_archives(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", required=True, type=int)
    parser.add_argument("--end-year", required=True, type=int)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/henex"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")


def run_fetch_henex_archives(args: argparse.Namespace) -> int:
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
    return report_ingestion(frame, report, args.output)


def configure_normalize_henex_directory(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")


def run_normalize_henex_directory(args: argparse.Namespace) -> int:
    workbooks = find_henex_result_workbooks(args.directory)
    if not workbooks:
        raise HenexParseError(
            f"No YYYYMMDD_EL-DAM_Results_EN_v##.xlsx files below {args.directory}"
        )
    frame = normalize_henex_workbooks(workbooks)
    report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
    return report_ingestion(frame, report, args.output)


def configure_fetch_henex_daily(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument("--max-catalog-pages", type=int, default=100)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/henex"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")


def run_fetch_henex_daily(args: argparse.Namespace) -> int:
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
    return report_ingestion(frame, report, args.output)


def configure_fetch_entsoe(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--start", required=True, help="Timezone-aware start, e.g. 2026-01-01T00:00Z"
    )
    parser.add_argument("--end", required=True, help="Timezone-aware exclusive end")
    parser.add_argument("--chunk-days", type=int, default=31)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retry-backoff-seconds", type=float, default=10.0)
    parser.add_argument("--raw-cache-dir", type=Path, default=Path("data/raw/entsoe"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")


def run_fetch_entsoe(args: argparse.Namespace) -> int:
    entsoe_client = EntsoeClient(
        raw_cache_dir=args.raw_cache_dir,
        timeout_seconds=args.timeout_seconds,
        max_attempts=args.max_attempts,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    frame = entsoe_client.fetch_prices(args.start, args.end, chunk_days=args.chunk_days)
    report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
    return report_ingestion(frame, report, args.output)


def configure_merge_canonical(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--allow-partial-days", action="store_true")
    parser.add_argument("--output", required=True, type=Path)


def run_merge_canonical(args: argparse.Namespace) -> int:
    frame = concat_canonical(_read_canonical_csv(path) for path in args.inputs)
    report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
    return report_ingestion(frame, report, args.output)


def configure_compare_sources(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--output", required=True, type=Path)


def run_compare_sources(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="generate-synthetic",
        help="Create labelled non-official demo prices",
        configure=configure_generate_synthetic,
        run=run_generate_synthetic,
    ),
    Command(
        name="parse-henex",
        help="Import a user-obtained HEnEx DAM results workbook",
        configure=configure_parse_henex,
        run=run_parse_henex,
    ),
    Command(
        name="fetch-henex-archives",
        help="Download and normalize verified HEnEx annual DAM result archives",
        configure=configure_fetch_henex_archives,
        run=run_fetch_henex_archives,
    ),
    Command(
        name="normalize-henex-directory",
        help="Normalize all privately obtained HEnEx DAM result workbooks below a directory",
        configure=configure_normalize_henex_directory,
        run=run_normalize_henex_directory,
    ),
    Command(
        name="fetch-henex-daily",
        help="Incrementally discover and normalize unarchived HEnEx daily DAM results",
        configure=configure_fetch_henex_daily,
        run=run_fetch_henex_daily,
    ),
    Command(
        name="fetch-entsoe",
        help="Fetch official Greek DAM prices using a personal token",
        configure=configure_fetch_entsoe,
        run=run_fetch_entsoe,
    ),
    Command(
        name="merge-canonical",
        help="Merge normalized CSV files from one official source into a single history",
        configure=configure_merge_canonical,
        run=run_merge_canonical,
    ),
    Command(
        name="compare-sources",
        help="Compare two normalized official-source CSV files",
        configure=configure_compare_sources,
        run=run_compare_sources,
    ),
)
