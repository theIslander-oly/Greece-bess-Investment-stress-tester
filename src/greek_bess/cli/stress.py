"""Named, declared stress scenarios over a replayed history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..stress import (
    AvailabilityInputError,
    apply_negative_price_events,
    apply_price_level_shock,
    apply_spread_compression,
    build_availability_profile,
    dispatch_bootstrap_paths,
    generate_seasonal_bootstrap_paths,
    report_scenario_ensemble,
)
from ._registry import Command
from ._support import (
    _read_availability_config,
    _read_battery_config,
    _read_bootstrap_config,
    _read_bootstrap_paths_csv,
    _read_canonical_csv,
    _read_negative_price_event_config,
    _read_price_level_config,
    _read_scenario_manifest,
    _read_spread_compression_config,
    _sibling_path,
    _write_dispatch_csv,
    _write_json,
    _write_plain_csv,
)


def configure_generate_bootstrap_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical historical price CSV")
    parser.add_argument("--config", required=True, type=Path, help="Bootstrap assumptions JSON")
    parser.add_argument("--output", required=True, type=Path, help="Synthetic paths CSV")
    parser.add_argument("--provenance", type=Path, help="Sampled-block provenance CSV")
    parser.add_argument("--summary", type=Path, help="Method and configuration JSON")


def run_generate_bootstrap_paths(args: argparse.Namespace) -> int:
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


def configure_dispatch_bootstrap_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    parser.add_argument("--config", required=True, type=Path, help="Battery JSON")
    parser.add_argument(
        "--availability",
        type=float,
        default=None,
        help="Constant available fraction applied to every interval of every path",
    )
    parser.add_argument(
        "--availability-schedule",
        type=Path,
        help=(
            "Declared availability schedule JSON: a baseline fraction with no default plus "
            "declared outage windows. Mutually exclusive with --availability"
        ),
    )
    parser.add_argument(
        "--availability-provenance",
        type=Path,
        help="Per-interval availability provenance CSV; defaults beside output",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Interval dispatch CSV"
    )
    parser.add_argument("--path-summary", type=Path, help="Path summaries CSV")
    parser.add_argument("--summary", type=Path, help="Method summary JSON")


def run_dispatch_bootstrap_paths(args: argparse.Namespace) -> int:
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


def configure_report_scenario_ensemble(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help=(
            "Scenario manifest JSON. Every scenario is named explicitly; there is no default "
            "scenario set and no implicit baseline"
        ),
    )
    parser.add_argument("--output", required=True, type=Path, help="Per-path range CSV")
    parser.add_argument(
        "--margins",
        type=Path,
        help="Per-scenario, per-path margin CSV with provenance; defaults beside output",
    )
    parser.add_argument(
        "--summary", type=Path, help="Method summary JSON; defaults beside output"
    )


def run_report_scenario_ensemble(args: argparse.Namespace) -> int:
    ensemble_result = report_scenario_ensemble(_read_scenario_manifest(args.manifest))
    margins_path = args.margins or _sibling_path(args.output, ".margins.csv")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(ensemble_result.scenario_ranges, args.output)
    _write_plain_csv(ensemble_result.scenario_margins, margins_path)
    _write_json(ensemble_result.summary, summary_path)
    print(json.dumps(ensemble_result.summary, indent=2))
    return 0


def configure_apply_price_level_shock(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    parser.add_argument(
        "--config", required=True, type=Path, help="Price-level shock assumptions JSON"
    )
    parser.add_argument("--output", required=True, type=Path, help="Shocked paths CSV")
    parser.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    parser.add_argument("--summary", type=Path, help="Method and configuration JSON")


def run_apply_price_level_shock(args: argparse.Namespace) -> int:
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


def configure_compress_spread(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    parser.add_argument(
        "--config", required=True, type=Path, help="Spread compression assumptions JSON"
    )
    parser.add_argument("--output", required=True, type=Path, help="Compressed paths CSV")
    parser.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    parser.add_argument("--summary", type=Path, help="Method and configuration JSON")


def run_compress_spread(args: argparse.Namespace) -> int:
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


def configure_apply_negative_price_events(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", type=Path, help="Synthetic bootstrap paths CSV")
    parser.add_argument(
        "--config", required=True, type=Path, help="Declared negative-price events JSON"
    )
    parser.add_argument("--output", required=True, type=Path, help="Transformed paths CSV")
    parser.add_argument("--provenance", type=Path, help="Interval provenance CSV")
    parser.add_argument("--summary", type=Path, help="Method and configuration JSON")


def run_apply_negative_price_events(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="generate-bootstrap-paths",
        help="Generate labelled synthetic seasonal block-bootstrap price paths",
        configure=configure_generate_bootstrap_paths,
        run=run_generate_bootstrap_paths,
    ),
    Command(
        name="dispatch-bootstrap-paths",
        help="Dispatch each validated synthetic bootstrap path independently",
        configure=configure_dispatch_bootstrap_paths,
        run=run_dispatch_bootstrap_paths,
    ),
    Command(
        name="report-scenario-ensemble",
        help="Report the non-probabilistic range of margins across named, already-dispatched "
            "scenarios",
        configure=configure_report_scenario_ensemble,
        run=run_report_scenario_ensemble,
    ),
    Command(
        name="apply-price-level-shock",
        help="Apply a labelled additive price-level shock to synthetic bootstrap paths",
        configure=configure_apply_price_level_shock,
        run=run_apply_price_level_shock,
    ),
    Command(
        name="compress-spread",
        help="Compress within-day spread of synthetic bootstrap paths about a daily reference",
        configure=configure_compress_spread,
        run=run_compress_spread,
    ),
    Command(
        name="apply-negative-price-events",
        help="Apply explicitly declared negative-price event windows to synthetic bootstrap paths",
        configure=configure_apply_negative_price_events,
        run=run_apply_negative_price_events,
    ),
)
