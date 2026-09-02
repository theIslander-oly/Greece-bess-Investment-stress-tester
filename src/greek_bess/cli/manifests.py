"""Recording, verifying and rendering run manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..reporting import (
    RESULT_KINDS,
    ReportContractError,
    build_run_manifest,
    read_run_manifest,
    render_report,
    write_report,
    write_run_manifest,
)
from ._registry import Command


def configure_record_run_manifest(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("summary", type=Path, help="Summary JSON a result command wrote")
    parser.add_argument(
        "--result-kind", required=True, choices=sorted(RESULT_KINDS), help="Declared result kind"
    )
    parser.add_argument("--manifest-id", required=True, help="Identifier for this run")
    parser.add_argument(
        "--produced-by", required=True, help="Command or API call that produced the summary"
    )
    parser.add_argument(
        "--declared-inputs", type=Path, help="JSON object naming the run's declared inputs"
    )
    parser.add_argument("--output", required=True, type=Path, help="Run manifest JSON")


def run_record_run_manifest(args: argparse.Namespace) -> int:
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


def configure_verify_run_manifest(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("manifest", type=Path)


def run_verify_run_manifest(args: argparse.Namespace) -> int:
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


def configure_render_report(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "manifests",
        nargs="*",
        type=Path,
        help=(
            "Run manifest JSON files. Supplying none renders the declaration checklist, which "
            "is the landing state: no judgmental input has a default, so there is no result to "
            "show before one is declared"
        ),
    )
    parser.add_argument("--output", required=True, type=Path, help="Self-contained report HTML")
    parser.add_argument(
        "--index",
        type=Path,
        help="Machine-readable index of the manifests rendered; defaults beside the output",
    )


def run_render_report(args: argparse.Namespace) -> int:
    rendered = render_report(args.manifests)
    index_path = write_report(rendered, args.output, index_path=args.index)
    print(
        json.dumps(
            {
                "report": str(args.output),
                "index": str(index_path),
                **dict(rendered.index),
            },
            indent=2,
            default=str,
        )
    )
    return 0


COMMANDS: tuple[Command, ...] = (
    Command(
        name="record-run-manifest",
        help="Record a result summary under the versioned run-manifest contract",
        configure=configure_record_run_manifest,
        run=run_record_run_manifest,
    ),
    Command(
        name="verify-run-manifest",
        help="Read a run manifest and refuse an unknown schema version or result kind",
        configure=configure_verify_run_manifest,
        run=run_verify_run_manifest,
    ),
    Command(
        name="render-report",
        help="Render verified run manifests into one self-contained static report",
        configure=configure_render_report,
        run=run_render_report,
    ),
)
