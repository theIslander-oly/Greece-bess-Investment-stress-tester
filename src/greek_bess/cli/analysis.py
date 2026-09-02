"""Decomposition of an accepted replay by delivery year."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..analysis import decompose_annual_replay
from ._registry import Command
from ._support import (
    _read_canonical_csv,
    _read_daily_results,
    _read_schedule_csv,
    _sibling_path,
    _write_json,
    _write_plain_csv,
)


def configure_decompose_annual_replay(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Accepted canonical price CSV")
    parser.add_argument(
        "--perfect-foresight-schedule",
        type=Path,
        help="Interval dispatch CSV from optimize-perfect-foresight over the same history",
    )
    parser.add_argument(
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
    parser.add_argument(
        "--energy-capacity-mwh",
        type=float,
        help="Battery energy capacity; required only for equivalent-full-cycle columns",
    )
    parser.add_argument("--output", required=True, type=Path, help="Per-year overview CSV")
    parser.add_argument(
        "--forecast-output", type=Path, help="Per-year, per-method CSV; defaults beside output"
    )
    parser.add_argument(
        "--common-day-output",
        type=Path,
        help="Per-year like-for-like CSV; defaults beside output",
    )
    parser.add_argument("--summary", type=Path, help="Summary JSON; defaults beside output")


def run_decompose_annual_replay(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="decompose-annual-replay",
        help="Split an accepted replay into delivery years on the CET/CEST market clock",
        configure=configure_decompose_annual_replay,
        run=run_decompose_annual_replay,
    ),
)
