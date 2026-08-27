from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

from greek_bess.cli import main


class CliTests(unittest.TestCase):
    def test_bootstrap_command_writes_paths_provenance_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            config = root / "bootstrap.json"
            output = root / "paths.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-01-01",
                        "--end-day",
                        "2025-01-15",
                        "--output",
                        str(prices),
                    ]
                )
            config.write_text(
                json.dumps(
                    {
                        "start_day": "2026-01-01",
                        "end_day": "2026-01-04",
                        "path_count": 2,
                        "block_days": 2,
                        "random_seed": 7,
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "generate-bootstrap-paths",
                        str(prices),
                        "--config",
                        str(config),
                        "--output",
                        str(output),
                    ]
                )

            paths = pd.read_csv(output)
            provenance = pd.read_csv(root / "paths.provenance.csv")
            summary = json.loads((root / "paths.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(paths), 144)
            self.assertEqual(len(provenance), 4)
            self.assertIn("not forecasts", summary["result_label"])

    def test_synthetic_command_writes_data_and_quality_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "synthetic.csv"
            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-03-29",
                        "--end-day",
                        "2026-03-30",
                        "--resolution-minutes",
                        "15",
                        "--output",
                        str(output),
                    ]
                )
            quality = json.loads(output.with_suffix(".quality.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertTrue(quality["is_valid"])
            self.assertEqual(quality["row_count"], 92)

    def test_optimizer_command_writes_schedule_and_upper_bound_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            dispatch = root / "dispatch.csv"
            battery = root / "battery.json"
            with redirect_stdout(io.StringIO()):
                generate_exit = main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-05",
                        "--end-day",
                        "2026-01-06",
                        "--negative-price-share",
                        "0",
                        "--output",
                        str(prices),
                    ]
                )
            battery.write_text(
                json.dumps(
                    {
                        "charge_power_mw": 50,
                        "discharge_power_mw": 50,
                        "energy_capacity_mwh": 100,
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                optimize_exit = main(
                    [
                        "optimize-perfect-foresight",
                        str(prices),
                        "--config",
                        str(battery),
                        "--output",
                        str(dispatch),
                    ]
                )

            summary = json.loads(dispatch.with_suffix(".summary.json").read_text())
            self.assertEqual(generate_exit, 0)
            self.assertEqual(optimize_exit, 0)
            self.assertTrue(dispatch.exists())
            self.assertEqual(summary["interval_count"], 24)
            self.assertIn("upper bound", summary["result_label"])

    def test_forecast_and_dispatch_backtest_commands_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            forecasts = root / "forecasts.csv"
            intervals = root / "backtest.csv"
            battery = root / "battery.json"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-01-10",
                        "--negative-price-share",
                        "0",
                        "--output",
                        str(prices),
                    ]
                )
            battery.write_text(
                json.dumps(
                    {
                        "charge_power_mw": 1,
                        "discharge_power_mw": 1,
                        "energy_capacity_mwh": 1,
                        "soc_min_fraction": 0,
                        "soc_max_fraction": 1,
                        "initial_soc_fraction": 0,
                        "terminal_soc_fraction": 0,
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                forecast_exit = main(
                    [
                        "forecast-naive",
                        str(prices),
                        "--methods",
                        "ensemble",
                        "--output",
                        str(forecasts),
                    ]
                )
                backtest_exit = main(
                    [
                        "backtest-forecast-dispatch",
                        str(prices),
                        "--config",
                        str(battery),
                        "--method",
                        "ensemble",
                        "--output",
                        str(intervals),
                    ]
                )
            self.assertEqual(forecast_exit, 0)
            self.assertEqual(backtest_exit, 0)
            self.assertTrue(forecasts.with_suffix(".metrics.json").exists())
            self.assertTrue(intervals.with_suffix(".daily.csv").exists())
            summary = json.loads(intervals.with_suffix(".summary.json").read_text())
            self.assertEqual(summary["backtested_day_count"], 8)
            self.assertIn("research backtest", summary["result_label"])

    def test_ml_forecast_and_dispatch_commands_write_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            forecasts = root / "ml_forecasts.csv"
            intervals = root / "ml_dispatch.csv"
            battery = root / "battery.json"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-02-05",
                        "--output",
                        str(prices),
                    ]
                )
            battery.write_text(
                json.dumps(
                    {
                        "charge_power_mw": 1,
                        "discharge_power_mw": 1,
                        "energy_capacity_mwh": 2,
                        "initial_soc_fraction": 0.5,
                        "terminal_soc_fraction": 0.5,
                    }
                ),
                encoding="utf-8",
            )
            common = [
                "--validation-start-day",
                "2026-01-25",
                "--test-start-day",
                "2026-02-02",
                "--models",
                "ridge",
                "--min-training-days",
                "20",
                "--refit-frequency-days",
                "3",
            ]
            with redirect_stdout(io.StringIO()):
                forecast_exit = main(
                    ["forecast-ml", str(prices), *common, "--output", str(forecasts)]
                )
                backtest_exit = main(
                    [
                        "backtest-ml-dispatch",
                        str(prices),
                        "--config",
                        str(battery),
                        *common,
                        "--output",
                        str(intervals),
                    ]
                )
            self.assertEqual(forecast_exit, 0)
            self.assertEqual(backtest_exit, 0)
            forecast_summary = json.loads(
                forecasts.with_suffix(".summary.json").read_text()
            )
            dispatch_summary = json.loads(
                intervals.with_suffix(".summary.json").read_text()
            )
            self.assertEqual(forecast_summary["selected_model"], "ridge")
            self.assertIn("dispatch_ranking", dispatch_summary)
            self.assertTrue(root.joinpath("ml_dispatch.forecasts.csv").exists())
            self.assertTrue(root.joinpath("ml_dispatch.daily.csv").exists())
            self.assertTrue(root.joinpath("ml_dispatch.forecast.summary.json").exists())

    def test_degradation_dispatch_command_writes_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            intervals = root / "degradation_dispatch.csv"
            battery = root / "battery.json"
            degradation = root / "degradation.json"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-01-03",
                        "--negative-price-share",
                        "0",
                        "--output",
                        str(prices),
                    ]
                )
            battery.write_text(
                json.dumps(
                    {
                        "charge_power_mw": 1,
                        "discharge_power_mw": 1,
                        "energy_capacity_mwh": 2,
                        "soc_min_fraction": 0,
                        "soc_max_fraction": 1,
                        "initial_soc_fraction": 0,
                        "terminal_soc_fraction": 0,
                    }
                ),
                encoding="utf-8",
            )
            degradation.write_text(
                json.dumps(
                    {
                        "project_start_day": "2026-01-01",
                        "calendar_fade_fraction_per_year": 0.01,
                        "cycle_fade_fraction_per_equivalent_cycle": 0.001,
                        "warranty_years": 10,
                        "warranty_retained_capacity_fraction": 0.70,
                        "warranty_max_equivalent_full_cycles": 4000,
                        "enforce_warranty_throughput_limit": True,
                        "augmentation_events": [],
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "simulate-degradation-dispatch",
                        str(prices),
                        "--config",
                        str(battery),
                        "--degradation-config",
                        str(degradation),
                        "--output",
                        str(intervals),
                    ]
                )
            summary = json.loads(intervals.with_suffix(".summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertTrue(intervals.exists())
            self.assertTrue(root.joinpath("degradation_dispatch.daily.csv").exists())
            self.assertTrue(root.joinpath("degradation_dispatch.cohorts.csv").exists())
            self.assertEqual(summary["market_day_count"], 2)
            self.assertIn("upper bound", summary["result_label"])

            finance_config = root / "finance.json"
            annual_cash_flows = root / "annual_cash_flows.csv"
            finance_config.write_text(
                json.dumps(
                    {
                        "project_start_day": "2026-01-01",
                        "project_end_day": "2026-01-02",
                        "operating_margin_case": "perfect_foresight_upper_bound",
                        "discount_rate_fraction": 0.08,
                        "battery_system_capex_eur": 1000.0,
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                finance_exit = main(
                    [
                        "evaluate-project-finance",
                        str(root / "degradation_dispatch.daily.csv"),
                        "--finance-config",
                        str(finance_config),
                        "--output",
                        str(annual_cash_flows),
                    ]
                )
            finance_summary = json.loads(
                annual_cash_flows.with_suffix(".summary.json").read_text()
            )
            self.assertEqual(finance_exit, 0)
            self.assertEqual(finance_summary["modeled_day_count"], 2)
            self.assertIn(
                "upper bound", finance_summary["operating_margin_interpretation"]
            )

    def test_project_finance_command_writes_daily_annual_and_summary_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            daily_results = root / "daily_results.csv"
            finance_config = root / "finance.json"
            annual_output = root / "project_cash_flows.csv"
            pd.DataFrame(
                {
                    "market_day": ["2026-01-01", "2026-01-02"],
                    "net_market_margin_eur": [700.0, 700.0],
                    "grid_discharge_mwh": [2.0, 2.0],
                    "augmentation_cost_eur": [0.0, 100.0],
                }
            ).to_csv(daily_results, index=False)
            finance_config.write_text(
                json.dumps(
                    {
                        "project_start_day": "2026-01-01",
                        "project_end_day": "2026-01-02",
                        "operating_margin_case": "user_supplied_scenario",
                        "discount_rate_fraction": 0.08,
                        "battery_system_capex_eur": 1_000.0,
                        "market_margin_realization_fraction": 1.0,
                        "fixed_opex_eur_per_year": 0.0,
                        "variable_opex_eur_per_mwh_discharged": 5.0,
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "evaluate-project-finance",
                        str(daily_results),
                        "--finance-config",
                        str(finance_config),
                        "--output",
                        str(annual_output),
                    ]
                )

            summary = json.loads(
                annual_output.with_suffix(".summary.json").read_text()
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(annual_output.exists())
            self.assertTrue(root.joinpath("project_cash_flows.daily.csv").exists())
            self.assertEqual(summary["modeled_day_count"], 2)
            self.assertEqual(summary["initial_capex_eur"], 1_000.0)
            self.assertIn("not a bankable", summary["result_label"])


if __name__ == "__main__":
    unittest.main()
