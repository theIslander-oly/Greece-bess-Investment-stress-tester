"""One command that runs one declared integrated study."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

import pandas as pd

from ..data.provenance import sha256_bytes
from ..data.synthetic import generate_synthetic_prices
from ..reporting import (
    RunManifest,
    build_run_manifest,
    render_report,
    write_report,
    write_run_manifest,
)
from ..study import (
    IntegratedStudyConfig,
    IntegratedStudyInputError,
    assemble_integrated_study,
    read_integrated_study_config,
    run_integrated_study,
)
from ._registry import Command
from ._support import _read_canonical_csv, _write_json, _write_plain_csv


def configure_run_integrated_study(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "prices",
        nargs="?",
        type=Path,
        help=(
            "Canonical price history covering the declared window and prior history. Omit only "
            "when the study configuration declares synthetic_price_generation"
        ),
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
    parser.add_argument(
        "--declared-inputs",
        type=Path,
        help="Additional provenance JSON to record beside the automatic input digests",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Also render the verified study manifest to this self-contained HTML report",
    )


def run_run_integrated_study(args: argparse.Namespace) -> int:
    config = read_integrated_study_config(args.study_config)
    prices, price_inputs = _prices_and_provenance(args.prices, config)
    declared_inputs = _declared_inputs(args, config, price_inputs)
    result = assemble_integrated_study(run_integrated_study(prices, config))

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
    write_run_manifest(
        manifest_path,
        _manifest(result.summary, config, args.manifest_id, declared_inputs),
    )

    report_path: Path | None = args.report
    report_index_path: Path | None = None
    if report_path is not None:
        rendered = render_report([manifest_path])
        report_index_path = write_report(rendered, report_path)

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
                "report": str(report_path) if report_path is not None else None,
                "report_index": (
                    str(report_index_path) if report_index_path is not None else None
                ),
            },
            indent=2,
        )
    )
    return 0


def _manifest(
    summary: dict[str, object],
    config: IntegratedStudyConfig,
    manifest_id: str | None,
    declared_inputs: dict[str, object],
) -> RunManifest:
    return build_run_manifest(
        summary,
        kind_id="integrated_study",
        manifest_id=manifest_id or config.study_id,
        produced_by="run-integrated-study",
        declared_inputs=declared_inputs,
    )


def _prices_and_provenance(
    prices_path: Path | None, config: IntegratedStudyConfig
) -> tuple[pd.DataFrame, dict[str, object]]:
    if prices_path is not None:
        prices = _read_canonical_csv(prices_path)
        sources = set(prices["source"].astype(str))
        if config.price_source == "synthetic" and sources != {"synthetic"}:
            raise IntegratedStudyInputError(
                "A study declaring price_source synthetic can read only synthetic prices"
            )
        if config.price_source == "official" and "synthetic" in sources:
            raise IntegratedStudyInputError(
                "A study declaring price_source official cannot read synthetic prices"
            )
        return prices, {
            "price_input": str(prices_path),
            "price_input_sha256": sha256_bytes(prices_path.read_bytes()),
        }
    generation = config.synthetic_price_generation
    if config.price_source != "synthetic" or generation is None:
        raise IntegratedStudyInputError(
            "A prices file is required unless price_source is synthetic and the configuration "
            "declares every synthetic_price_generation input"
        )
    prices = generate_synthetic_prices(
        generation.history_start_day,
        config.window_end_day + timedelta(days=1),
        resolution_minutes=generation.resolution_minutes,
        seed=generation.seed,
        negative_price_share=generation.negative_price_share,
    )
    prices["retrieved_at_utc"] = pd.Timestamp(generation.retrieved_at_utc)
    generation_payload = json.dumps(
        generation.to_dict(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return prices, {
        "price_input": "generated from synthetic_price_generation in the study configuration",
        "synthetic_price_generation": generation.to_dict(),
        "synthetic_price_generation_sha256": sha256_bytes(generation_payload),
    }


def _declared_inputs(
    args: argparse.Namespace,
    config: IntegratedStudyConfig,
    price_inputs: dict[str, object],
) -> dict[str, object]:
    automatic: dict[str, object] = {
        "price_source": config.price_source,
        "window_start_day": config.window_start_day.isoformat(),
        "window_end_day": config.window_end_day.isoformat(),
        "strategy_ids": [strategy.strategy_id for strategy in config.strategies],
        "study_config": str(args.study_config),
        "study_config_sha256": sha256_bytes(args.study_config.read_bytes()),
        **price_inputs,
    }
    if args.declared_inputs is None:
        return automatic
    extra = json.loads(args.declared_inputs.read_text(encoding="utf-8"))
    if not isinstance(extra, dict):
        raise IntegratedStudyInputError("--declared-inputs must contain one JSON object")
    collisions = sorted(set(extra) & set(automatic))
    if collisions:
        raise IntegratedStudyInputError(
            "Additional declared inputs cannot replace automatic provenance: "
            + ", ".join(collisions)
        )
    return {**automatic, **extra}


COMMANDS: tuple[Command, ...] = (
    Command(
        name="run-integrated-study",
        help="Run one declared window end to end: plan, settle, age and finance every "
            "declared strategy, then record the result",
        configure=configure_run_integrated_study,
        run=run_run_integrated_study,
    ),
)
