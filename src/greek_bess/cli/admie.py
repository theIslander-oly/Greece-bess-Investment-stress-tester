"""ADMIE/IPTO catalog retrieval and pre-auction publication timing audit."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from ..data.admie import AdmieClient, AdmieError, select_latest_admie_revisions
from ..data.admie_timing import audit_admie_publication_timing, read_retrieval_manifests
from ._registry import Command
from ._support import (
    _admie_empty_discovery_message,
    _read_gate_closure_schedule,
    _sibling_path,
    _write_json,
    _write_plain_csv,
)


def configure_list_admie_filetypes(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True, type=Path)


def run_list_admie_filetypes(args: argparse.Namespace) -> int:
    filetypes = AdmieClient().list_filetypes()
    _write_json(filetypes, args.output)
    print(json.dumps({"filetype_count": len(filetypes)}, indent=2))
    return 0


def configure_fetch_admie_files(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--filetypes", nargs="+", required=True)
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/admie"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--all-revisions", action="store_true")


def run_fetch_admie_files(args: argparse.Namespace) -> int:
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


def configure_audit_admie_publication_timing(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "manifests", nargs="+", type=Path, help="ADMIE retrieval manifest JSON files"
    )
    parser.add_argument(
        "--gate-closure",
        required=True,
        type=Path,
        help="Declared gate-closure schedule JSON; there is no default closure time",
    )
    parser.add_argument("--filetypes", nargs="+", required=True)
    parser.add_argument("--start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--end-day", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--output", required=True, type=Path, help="Per-delivery-day verdict CSV"
    )
    parser.add_argument("--observations", type=Path, help="Per-observation evidence CSV")
    parser.add_argument("--summary", type=Path, help="Audit summary JSON")


def run_audit_admie_publication_timing(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="list-admie-filetypes",
        help="Save the current public ADMIE filetype catalog",
        configure=configure_list_admie_filetypes,
        run=run_list_admie_filetypes,
    ),
    Command(
        name="fetch-admie-files",
        help="Discover and download official ADMIE files with publication-time provenance",
        configure=configure_fetch_admie_files,
        run=run_fetch_admie_files,
    ),
    Command(
        name="audit-admie-publication-timing",
        help="Audit ADMIE retrieval manifests against a declared day-ahead gate closure, "
            "without parsing any file",
        configure=configure_audit_admie_publication_timing,
        run=run_audit_admie_publication_timing,
    ),
)
