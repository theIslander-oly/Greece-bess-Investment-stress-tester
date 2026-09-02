"""Perfect-foresight dispatch and the forecast-planned backtests."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from ..backtest import (
    backtest_forecast_dispatch,
    backtest_ml_dispatch_benchmark,
    simulate_degradation_dispatch,
)
from ..dispatch import optimize_daily_perfect_foresight, optimize_perfect_foresight
from ..forecast import FORECAST_METHODS, generate_ml_forecasts
from ._registry import Command
from ._support import (
    _add_ml_arguments,
    _ml_config_from_args,
    _read_battery_config,
    _read_canonical_csv,
    _read_degradation_config,
    _sibling_path,
    _write_dispatch_csv,
    _write_dispatch_outputs,
    _write_json,
    _write_plain_csv,
)


def configure_optimize_perfect_foresight(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument("--config", required=True, type=Path, help="Battery JSON")
    parser.add_argument("--availability", type=float, default=1.0)
    parser.add_argument(
        "--daily-solves",
        action="store_true",
        help=(
            "Solve every market day independently and compose the schedules, the "
            "convention the forecast backtests are measured against, instead of one "
            "solve over the whole horizon"
        ),
    )
    parser.add_argument("--output", required=True, type=Path, help="Dispatch CSV")
    parser.add_argument("--summary", type=Path, help="Summary JSON; defaults beside dispatch CSV")


def run_optimize_perfect_foresight(args: argparse.Namespace) -> int:
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


def configure_backtest_forecast_dispatch(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument("--config", required=True, type=Path, help="Battery JSON")
    parser.add_argument("--method", choices=FORECAST_METHODS, default="ensemble")
    parser.add_argument("--rolling-window-days", type=int, default=28)
    parser.add_argument("--start-day", type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path, help="Interval CSV")
    parser.add_argument(
        "--daily-output", type=Path, help="Daily CSV; defaults beside interval CSV"
    )
    parser.add_argument("--summary", type=Path, help="Summary JSON; defaults beside interval CSV")


def run_backtest_forecast_dispatch(args: argparse.Namespace) -> int:
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


def configure_backtest_ml_dispatch(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument("--config", required=True, type=Path, help="Battery JSON")
    _add_ml_arguments(parser)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Selected-model held-out interval dispatch CSV",
    )
    parser.add_argument("--forecasts-output", type=Path)
    parser.add_argument("--daily-output", type=Path)
    parser.add_argument("--forecast-summary", type=Path)
    parser.add_argument("--summary", type=Path)


def run_backtest_ml_dispatch(args: argparse.Namespace) -> int:
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


def configure_simulate_degradation_dispatch(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument("--config", required=True, type=Path, help="Battery dispatch JSON")
    parser.add_argument(
        "--degradation-config",
        required=True,
        type=Path,
        help="Degradation and augmentation JSON",
    )
    parser.add_argument("--output", required=True, type=Path, help="Interval dispatch CSV")
    parser.add_argument("--daily-output", type=Path)
    parser.add_argument("--cohort-output", type=Path)
    parser.add_argument("--summary", type=Path)


def run_simulate_degradation_dispatch(args: argparse.Namespace) -> int:
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


COMMANDS: tuple[Command, ...] = (
    Command(
        name="optimize-perfect-foresight",
        help="Optimize a labelled DAM gross-margin upper bound",
        configure=configure_optimize_perfect_foresight,
        run=run_optimize_perfect_foresight,
    ),
    Command(
        name="backtest-forecast-dispatch",
        help="Plan dispatch on forecasts and settle against realized prices",
        configure=configure_backtest_forecast_dispatch,
        run=run_backtest_forecast_dispatch,
    ),
    Command(
        name="backtest-ml-dispatch",
        help="Compare ML and naïve forecast dispatch over identical held-out test days",
        configure=configure_backtest_ml_dispatch,
        run=run_backtest_ml_dispatch,
    ),
    Command(
        name="simulate-degradation-dispatch",
        help="Run daily perfect-foresight dispatch with evolving capacity, "
            "warranty screening and augmentation",
        configure=configure_simulate_degradation_dispatch,
        run=run_simulate_degradation_dispatch,
    ),
)
