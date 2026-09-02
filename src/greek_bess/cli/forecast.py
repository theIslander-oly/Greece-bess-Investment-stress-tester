"""Walk-forward naive and machine-learning price forecasts."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from ..forecast import FORECAST_METHODS, generate_ml_forecasts, generate_naive_forecasts
from ._registry import Command
from ._support import (
    _add_ml_arguments,
    _ml_config_from_args,
    _read_canonical_csv,
    _write_json,
    _write_plain_csv,
)


def configure_forecast_naive(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=FORECAST_METHODS,
        default=list(FORECAST_METHODS),
    )
    parser.add_argument("--rolling-window-days", type=int, default=28)
    parser.add_argument("--start-day", type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path, help="Forecast CSV")
    parser.add_argument("--metrics", type=Path, help="Metrics JSON; defaults beside forecast CSV")


def run_forecast_naive(args: argparse.Namespace) -> int:
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


def configure_forecast_ml(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    _add_ml_arguments(parser)
    parser.add_argument(
        "--output", required=True, type=Path, help="Validation/test forecast CSV"
    )
    parser.add_argument(
        "--summary", type=Path, help="Benchmark JSON; defaults beside forecast CSV"
    )


def run_forecast_ml(args: argparse.Namespace) -> int:
    ml_forecast_result = generate_ml_forecasts(
        _read_canonical_csv(args.prices), _ml_config_from_args(args)
    )
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(ml_forecast_result.forecasts, args.output)
    _write_json(ml_forecast_result.summary, summary_path)
    print(json.dumps(ml_forecast_result.summary, indent=2))
    return 0


COMMANDS: tuple[Command, ...] = (
    Command(
        name="forecast-naive",
        help="Generate leakage-safe walk-forward price forecast baselines",
        configure=configure_forecast_naive,
        run=run_forecast_naive,
    ),
    Command(
        name="forecast-ml",
        help="Run leakage-safe walk-forward ML and naïve forecast benchmarks",
        configure=configure_forecast_ml,
        run=run_forecast_ml,
    ),
)
