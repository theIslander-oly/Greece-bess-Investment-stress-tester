"""Command-line entry points for market data and battery dispatch."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .backtest import (
    backtest_forecast_dispatch,
    backtest_ml_dispatch_benchmark,
    simulate_degradation_dispatch,
)
from .data.entsoe import EntsoeClient, EntsoeError
from .data.henex import HenexParseError, parse_henex_results
from .data.quality import QualityReport, assess_quality, compare_sources
from .data.schema import ensure_canonical
from .data.synthetic import generate_synthetic_prices
from .data.timezones import GREECE_TZ, MARKET_TZ
from .degradation import DegradationConfig
from .dispatch import (
    BatteryDispatchConfig,
    DispatchInputError,
    DispatchSolveError,
    optimize_perfect_foresight,
)
from .finance import FinanceConfig, evaluate_project_finance
from .forecast import (
    FORECAST_METHODS,
    ML_MODELS,
    MLForecastConfig,
    generate_ml_forecasts,
    generate_naive_forecasts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greek-bess",
        description="Ingest and validate Greek Day-Ahead Market prices.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    synthetic = subparsers.add_parser(
        "generate-synthetic", help="Create labelled non-official demo prices"
    )
    synthetic.add_argument("--start-day", required=True, type=date.fromisoformat)
    synthetic.add_argument("--end-day", required=True, type=date.fromisoformat)
    synthetic.add_argument("--resolution-minutes", type=int, choices=(15, 60), default=60)
    synthetic.add_argument("--seed", type=int, default=42)
    synthetic.add_argument("--negative-price-share", type=float, default=0.02)
    synthetic.add_argument("--output", required=True, type=Path)

    henex = subparsers.add_parser(
        "parse-henex", help="Import a user-obtained HEnEx DAM results workbook"
    )
    henex.add_argument("workbook", type=Path)
    henex.add_argument("--output", required=True, type=Path)
    henex.add_argument("--allow-partial-days", action="store_true")

    entsoe = subparsers.add_parser(
        "fetch-entsoe", help="Fetch official Greek DAM prices using a personal token"
    )
    entsoe.add_argument(
        "--start", required=True, help="Timezone-aware start, e.g. 2026-01-01T00:00Z"
    )
    entsoe.add_argument("--end", required=True, help="Timezone-aware exclusive end")
    entsoe.add_argument("--chunk-days", type=int, default=31)
    entsoe.add_argument("--raw-cache-dir", type=Path, default=Path("data/raw/entsoe"))
    entsoe.add_argument("--output", required=True, type=Path)
    entsoe.add_argument("--allow-partial-days", action="store_true")

    compare = subparsers.add_parser(
        "compare-sources", help="Compare two normalized official-source CSV files"
    )
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--tolerance", type=float, default=1e-6)
    compare.add_argument("--output", required=True, type=Path)

    optimize = subparsers.add_parser(
        "optimize-perfect-foresight",
        help="Optimize a labelled DAM gross-margin upper bound",
    )
    optimize.add_argument("prices", type=Path, help="Canonical price CSV")
    optimize.add_argument("--config", required=True, type=Path, help="Battery JSON")
    optimize.add_argument("--availability", type=float, default=1.0)
    optimize.add_argument("--output", required=True, type=Path, help="Dispatch CSV")
    optimize.add_argument(
        "--summary", type=Path, help="Summary JSON; defaults beside dispatch CSV"
    )

    forecast = subparsers.add_parser(
        "forecast-naive",
        help="Generate leakage-safe walk-forward price forecast baselines",
    )
    forecast.add_argument("prices", type=Path, help="Canonical price CSV")
    forecast.add_argument(
        "--methods",
        nargs="+",
        choices=FORECAST_METHODS,
        default=list(FORECAST_METHODS),
    )
    forecast.add_argument("--rolling-window-days", type=int, default=28)
    forecast.add_argument("--start-day", type=date.fromisoformat)
    forecast.add_argument("--output", required=True, type=Path, help="Forecast CSV")
    forecast.add_argument(
        "--metrics", type=Path, help="Metrics JSON; defaults beside forecast CSV"
    )

    ml_forecast = subparsers.add_parser(
        "forecast-ml",
        help="Run leakage-safe walk-forward ML and naïve forecast benchmarks",
    )
    ml_forecast.add_argument("prices", type=Path, help="Canonical price CSV")
    _add_ml_arguments(ml_forecast)
    ml_forecast.add_argument(
        "--output", required=True, type=Path, help="Validation/test forecast CSV"
    )
    ml_forecast.add_argument(
        "--summary", type=Path, help="Benchmark JSON; defaults beside forecast CSV"
    )

    backtest = subparsers.add_parser(
        "backtest-forecast-dispatch",
        help="Plan dispatch on forecasts and settle against realized prices",
    )
    backtest.add_argument("prices", type=Path, help="Canonical price CSV")
    backtest.add_argument("--config", required=True, type=Path, help="Battery JSON")
    backtest.add_argument(
        "--method", choices=FORECAST_METHODS, default="ensemble"
    )
    backtest.add_argument("--rolling-window-days", type=int, default=28)
    backtest.add_argument("--start-day", type=date.fromisoformat)
    backtest.add_argument("--output", required=True, type=Path, help="Interval CSV")
    backtest.add_argument(
        "--daily-output", type=Path, help="Daily CSV; defaults beside interval CSV"
    )
    backtest.add_argument(
        "--summary", type=Path, help="Summary JSON; defaults beside interval CSV"
    )

    ml_backtest = subparsers.add_parser(
        "backtest-ml-dispatch",
        help="Compare ML and naïve forecast dispatch over identical held-out test days",
    )
    ml_backtest.add_argument("prices", type=Path, help="Canonical price CSV")
    ml_backtest.add_argument("--config", required=True, type=Path, help="Battery JSON")
    _add_ml_arguments(ml_backtest)
    ml_backtest.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Selected-model held-out interval dispatch CSV",
    )
    ml_backtest.add_argument("--forecasts-output", type=Path)
    ml_backtest.add_argument("--daily-output", type=Path)
    ml_backtest.add_argument("--forecast-summary", type=Path)
    ml_backtest.add_argument("--summary", type=Path)

    degradation = subparsers.add_parser(
        "simulate-degradation-dispatch",
        help=(
            "Run daily perfect-foresight dispatch with evolving capacity, "
            "warranty screening and augmentation"
        ),
    )
    degradation.add_argument("prices", type=Path, help="Canonical price CSV")
    degradation.add_argument(
        "--config", required=True, type=Path, help="Battery dispatch JSON"
    )
    degradation.add_argument(
        "--degradation-config",
        required=True,
        type=Path,
        help="Degradation and augmentation JSON",
    )
    degradation.add_argument(
        "--output", required=True, type=Path, help="Interval dispatch CSV"
    )
    degradation.add_argument("--daily-output", type=Path)
    degradation.add_argument("--cohort-output", type=Path)
    degradation.add_argument("--summary", type=Path)

    finance = subparsers.add_parser(
        "evaluate-project-finance",
        help=(
            "Calculate unlevered pre-tax project cash flows, NPV, IRR, payback "
            "and break-even outputs from a complete daily operating path"
        ),
    )
    finance.add_argument(
        "daily_results",
        type=Path,
        help="Daily dispatch results with margin, discharge and augmentation columns",
    )
    finance.add_argument(
        "--finance-config", required=True, type=Path, help="Finance assumptions JSON"
    )
    finance.add_argument(
        "--output", required=True, type=Path, help="Annual cash-flow CSV"
    )
    finance.add_argument("--daily-output", type=Path)
    finance.add_argument("--summary", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate-synthetic":
            frame = generate_synthetic_prices(
                args.start_day,
                args.end_day,
                resolution_minutes=args.resolution_minutes,
                seed=args.seed,
                negative_price_share=args.negative_price_share,
            )
            report = assess_quality(frame)
        elif args.command == "parse-henex":
            frame = parse_henex_results(args.workbook)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "fetch-entsoe":
            client = EntsoeClient(raw_cache_dir=args.raw_cache_dir)
            frame = client.fetch_prices(args.start, args.end, chunk_days=args.chunk_days)
            report = assess_quality(frame, require_complete_days=not args.allow_partial_days)
        elif args.command == "compare-sources":
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
        elif args.command == "optimize-perfect-foresight":
            config = _read_battery_config(args.config)
            dispatch_result = optimize_perfect_foresight(
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
        elif args.command == "forecast-naive":
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
        elif args.command == "forecast-ml":
            ml_forecast_result = generate_ml_forecasts(
                _read_canonical_csv(args.prices), _ml_config_from_args(args)
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(ml_forecast_result.forecasts, args.output)
            _write_json(ml_forecast_result.summary, summary_path)
            print(json.dumps(ml_forecast_result.summary, indent=2))
            return 0
        elif args.command == "backtest-forecast-dispatch":
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
        elif args.command == "backtest-ml-dispatch":
            prices = _read_canonical_csv(args.prices)
            ml_result = generate_ml_forecasts(prices, _ml_config_from_args(args))
            ml_dispatch_result = backtest_ml_dispatch_benchmark(
                prices, _read_battery_config(args.config), ml_result
            )
            forecasts_path = args.forecasts_output or _sibling_path(
                args.output, ".forecasts.csv"
            )
            daily_path = args.daily_output or _sibling_path(
                args.output, ".daily.csv"
            )
            forecast_summary_path = args.forecast_summary or _sibling_path(
                args.output, ".forecast.summary.json"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(
                ml_dispatch_result.selected_model_interval_schedule, args.output
            )
            _write_plain_csv(ml_result.forecasts, forecasts_path)
            _write_plain_csv(ml_dispatch_result.daily_results, daily_path)
            _write_json(ml_result.summary, forecast_summary_path)
            _write_json(ml_dispatch_result.summary, summary_path)
            print(json.dumps(ml_dispatch_result.summary, indent=2))
            return 0
        elif args.command == "simulate-degradation-dispatch":
            degradation_result = simulate_degradation_dispatch(
                _read_canonical_csv(args.prices),
                _read_battery_config(args.config),
                _read_degradation_config(args.degradation_config),
            )
            daily_path = args.daily_output or _sibling_path(
                args.output, ".daily.csv"
            )
            cohort_path = args.cohort_output or _sibling_path(
                args.output, ".cohorts.csv"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_dispatch_csv(degradation_result.interval_schedule, args.output)
            _write_plain_csv(degradation_result.daily_results, daily_path)
            _write_plain_csv(degradation_result.cohort_states, cohort_path)
            _write_json(degradation_result.summary, summary_path)
            print(json.dumps(degradation_result.summary, indent=2))
            return 0
        elif args.command == "evaluate-project-finance":
            finance_result = evaluate_project_finance(
                pd.read_csv(args.daily_results),
                _read_finance_config(args.finance_config),
            )
            daily_path = args.daily_output or _sibling_path(
                args.output, ".daily.csv"
            )
            summary_path = args.summary or args.output.with_suffix(".summary.json")
            _write_plain_csv(finance_result.annual_cash_flows, args.output)
            _write_plain_csv(finance_result.daily_cash_flows, daily_path)
            _write_json(finance_result.summary, summary_path)
            print(json.dumps(finance_result.summary, indent=2))
            return 0
        else:  # pragma: no cover - argparse makes this unreachable.
            raise AssertionError(f"Unhandled command: {args.command}")

        _write_outputs(frame, report, args.output)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.is_valid else 2
    except (
        ValueError,
        DispatchInputError,
        DispatchSolveError,
        EntsoeError,
        HenexParseError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _write_outputs(frame: pd.DataFrame, report: QualityReport, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("The ingestion foundation currently writes .csv outputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    export = frame.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)

    temporary_csv = output.with_suffix(output.suffix + ".tmp")
    export.to_csv(temporary_csv, index=False)
    temporary_csv.replace(output)

    quality_path = output.with_suffix(".quality.json")
    temporary_quality = quality_path.with_suffix(quality_path.suffix + ".tmp")
    temporary_quality.write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    temporary_quality.replace(quality_path)


def _add_ml_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--validation-start-day", required=True, type=date.fromisoformat
    )
    parser.add_argument("--test-start-day", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--models", nargs="+", choices=ML_MODELS, default=list(ML_MODELS)
    )
    parser.add_argument("--feature-window-days", type=int, default=28)
    parser.add_argument("--refit-frequency-days", type=int, default=7)
    parser.add_argument("--min-training-days", type=int, default=28)
    parser.add_argument("--training-window-days", type=int)
    parser.add_argument("--ridge-alpha", type=float, default=10.0)
    parser.add_argument("--gradient-max-iter", type=int, default=150)
    parser.add_argument("--random-seed", type=int, default=42)


def _ml_config_from_args(args: argparse.Namespace) -> MLForecastConfig:
    return MLForecastConfig(
        validation_start_day=args.validation_start_day,
        test_start_day=args.test_start_day,
        models=tuple(args.models),
        feature_window_days=args.feature_window_days,
        refit_frequency_days=args.refit_frequency_days,
        min_training_days=args.min_training_days,
        training_window_days=args.training_window_days,
        ridge_alpha=args.ridge_alpha,
        gradient_max_iter=args.gradient_max_iter,
        random_seed=args.random_seed,
    )


def _sibling_path(output: Path, suffix: str) -> Path:
    return output.with_name(output.stem + suffix)


def _read_canonical_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["delivery_start_utc"] = pd.to_datetime(frame["delivery_start_utc"], utc=True)
    frame["delivery_end_utc"] = pd.to_datetime(frame["delivery_end_utc"], utc=True)
    frame["retrieved_at_utc"] = pd.to_datetime(frame["retrieved_at_utc"], utc=True)
    frame["delivery_start_market"] = frame["delivery_start_utc"].dt.tz_convert(MARKET_TZ)
    frame["delivery_start_greece"] = frame["delivery_start_utc"].dt.tz_convert(GREECE_TZ)
    frame["quality_flags"] = frame["quality_flags"].map(
        lambda value: json.loads(value) if isinstance(value, str) else []
    )
    return ensure_canonical(frame)


def _write_dispatch_outputs(
    schedule: pd.DataFrame,
    summary: dict[str, object],
    output: Path,
    summary_path: Path,
) -> None:
    _write_dispatch_csv(schedule, output)
    _write_json(summary, summary_path)


def _read_battery_config(path: Path) -> BatteryDispatchConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Battery config JSON must contain one object")
    return BatteryDispatchConfig(**payload)


def _read_degradation_config(path: Path) -> DegradationConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DegradationConfig.from_dict(payload)


def _read_finance_config(path: Path) -> FinanceConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FinanceConfig.from_dict(payload)


def _write_dispatch_csv(schedule: pd.DataFrame, output: Path) -> None:
    export = schedule.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)
    _write_plain_csv(export, output)


def _write_plain_csv(frame: pd.DataFrame, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("Tabular output must be .csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(output)


def _write_json(payload: object, output: Path) -> None:
    if output.suffix.lower() != ".json":
        raise ValueError("JSON output must be .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


if __name__ == "__main__":
    raise SystemExit(main())
