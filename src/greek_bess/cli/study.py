"""One command that runs one declared integrated study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..reporting import RunManifest, build_run_manifest, write_run_manifest
from ..study import (
    IntegratedStudyConfig,
    assemble_integrated_study,
    read_integrated_study_config,
    run_integrated_study,
)
from ._registry import Command
from ._support import _read_canonical_csv, _write_json, _write_plain_csv


def configure_run_integrated_study(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "prices",
        type=Path,
        help="Canonical price history covering the declared window and the history before it",
    )
    parser.add_argument(
        "--study-config",
        required=True,
        type=Path,
        help="One declared study configuration JSON",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory the study's five artifacts are written to",
    )
    parser.add_argument(
        "--manifest-id",
        help="Identifier for this run; defaults to the declared study_id",
    )


def run_run_integrated_study(args: argparse.Namespace) -> int:
    config = read_integrated_study_config(args.study_config)
    result = assemble_integrated_study(
        run_integrated_study(_read_canonical_csv(args.prices), config)
    )

    # Every artifact is named after the declared study, so a directory holding several
    # studies stays readable and no artifact can be attributed to the wrong one.
    stem = args.output_dir / config.study_id
    daily_path = stem.with_name(f"{config.study_id}.daily.csv")
    strategies_path = stem.with_name(f"{config.study_id}.strategies.csv")
    cash_flows_path = stem.with_name(f"{config.study_id}.cash_flows.csv")
    summary_path = stem.with_name(f"{config.study_id}.summary.json")
    manifest_path = stem.with_name(f"{config.study_id}.manifest.json")

    _write_plain_csv(result.daily_results, daily_path)
    _write_plain_csv(result.strategy_summaries, strategies_path)
    _write_plain_csv(result.cash_flows, cash_flows_path)
    _write_json(result.summary, summary_path)
    write_run_manifest(manifest_path, _manifest(result.summary, config, args.manifest_id))

    print(
        json.dumps(
            {
                "study_id": config.study_id,
                "result_label": result.summary["result_label"],
                "window_start_day": config.window_start_day.isoformat(),
                "window_end_day": config.window_end_day.isoformat(),
                "strategy_count": result.summary["strategy_count"],
                "daily_results": str(daily_path),
                "strategy_summaries": str(strategies_path),
                "cash_flows": str(cash_flows_path),
                "summary": str(summary_path),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0


def _manifest(
    summary: dict[str, object], config: IntegratedStudyConfig, manifest_id: str | None
) -> RunManifest:
    return build_run_manifest(
        summary,
        kind_id="integrated_study",
        manifest_id=manifest_id or config.study_id,
        produced_by="run-integrated-study",
        declared_inputs={
            "price_source": config.price_source,
            "window_start_day": config.window_start_day.isoformat(),
            "window_end_day": config.window_end_day.isoformat(),
            "strategy_ids": [strategy.strategy_id for strategy in config.strategies],
        },
    )


COMMANDS: tuple[Command, ...] = (
    Command(
        name="run-integrated-study",
        help="Run one declared window end to end: plan, settle, age and finance every "
            "declared strategy, then record the result",
        configure=configure_run_integrated_study,
        run=run_run_integrated_study,
    ),
)
