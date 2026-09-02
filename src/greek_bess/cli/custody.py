"""Custody records for accepted official artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..data.custody import build_custody_record, read_custody_record, verify_custody_record
from ._registry import Command
from ._support import _write_json


def configure_record_custody(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "directory", type=Path, help="Directory holding the extracted artifact"
    )
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-workflow")
    parser.add_argument(
        "--published-digest",
        help="SHA-256 the provider publishes for the artifact archive, when it exposes one",
    )
    parser.add_argument("--output", required=True, type=Path, help="Custody record JSON")


def run_record_custody(args: argparse.Namespace) -> int:
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


def configure_verify_custody(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "directory", type=Path, help="Directory holding the copy under verification"
    )
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="Verification result JSON")


def run_verify_custody(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="record-custody",
        help="Fingerprint an accepted official artifact without recording any price",
        configure=configure_record_custody,
        run=run_record_custody,
    ),
    Command(
        name="verify-custody",
        help="Verify a stored copy against a committed custody record",
        configure=configure_verify_custody,
        run=run_verify_custody,
    ),
)
