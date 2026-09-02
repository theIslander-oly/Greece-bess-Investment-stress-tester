#!/usr/bin/env python3
"""Measure synthetic daily perfect-foresight dispatch throughput."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import date, timedelta
from importlib.metadata import version
from typing import Any

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig, optimize_daily_perfect_foresight


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark independent daily dispatch solves on deterministic synthetic prices. "
            "The result is an engineering measurement, not investment evidence."
        )
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--resolution-minutes", type=int, choices=(15, 60), default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--negative-price-share", type=float, default=0.02)
    return parser


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if args.days < 1:
        raise ValueError("--days must be at least 1")

    start_day = date(2025, 1, 1)
    prices = generate_synthetic_prices(
        start_day,
        start_day + timedelta(days=args.days),
        resolution_minutes=args.resolution_minutes,
        seed=args.seed,
        negative_price_share=args.negative_price_share,
    )
    config = BatteryDispatchConfig(
        charge_power_mw=25.0,
        discharge_power_mw=25.0,
        energy_capacity_mwh=50.0,
        initial_soc_fraction=0.5,
        terminal_soc_fraction=0.5,
    )

    started = time.perf_counter()
    result = optimize_daily_perfect_foresight(prices, config)
    elapsed_seconds = time.perf_counter() - started
    solve_count = int(result.summary["market_day_count"])
    interval_count = int(result.summary["interval_count"])
    return {
        "benchmark": "synthetic_daily_perfect_foresight_dispatch",
        "interpretation": "engineering timing only; synthetic data are not investment evidence",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": version("numpy"),
        "scipy": version("scipy"),
        "days_requested": args.days,
        "resolution_minutes": args.resolution_minutes,
        "seed": args.seed,
        "negative_price_share": args.negative_price_share,
        "battery_config": config.to_dict(),
        "interval_count": interval_count,
        "daily_solve_count": solve_count,
        "relaxation_solve_count": int(
            result.summary["solve_path_counts"].get("relaxation_accepted", 0)
        ),
        "mixed_integer_solve_count": int(result.summary["mixed_integer_solve_count"]),
        "elapsed_seconds": elapsed_seconds,
        "daily_solves_per_second": solve_count / elapsed_seconds,
        "intervals_per_second": interval_count / elapsed_seconds,
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        measurement = run_benchmark(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(measurement, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
