from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


def load_benchmark_module() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "benchmark_dispatch.py"
    spec = importlib.util.spec_from_file_location("benchmark_dispatch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load benchmark_dispatch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DispatchBenchmarkTests(unittest.TestCase):
    def test_one_day_smoke_measurement_reports_reproducibility_fields(self) -> None:
        benchmark = load_benchmark_module()
        result = benchmark.run_benchmark(
            argparse.Namespace(
                days=1,
                resolution_minutes=60,
                seed=7,
                negative_price_share=0.0,
            )
        )

        self.assertEqual(result["benchmark"], "synthetic_daily_perfect_foresight_dispatch")
        self.assertEqual(result["daily_solve_count"], 1)
        self.assertEqual(result["interval_count"], 24)
        self.assertEqual(result["seed"], 7)
        self.assertEqual(result["battery_config"]["solve_strategy"], "relaxation_first")
        self.assertEqual(result["relaxation_solve_count"], 1)
        self.assertEqual(result["mixed_integer_solve_count"], 0)
        self.assertGreater(result["elapsed_seconds"], 0)
        self.assertGreater(result["daily_solves_per_second"], 0)

    def test_nonpositive_day_count_is_refused(self) -> None:
        benchmark = load_benchmark_module()
        with self.assertRaisesRegex(ValueError, "at least 1"):
            benchmark.run_benchmark(
                argparse.Namespace(
                    days=0,
                    resolution_minutes=15,
                    seed=42,
                    negative_price_share=0.02,
                )
            )
