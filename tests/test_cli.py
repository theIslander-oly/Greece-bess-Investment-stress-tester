from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

from greek_bess.cli import main


class CliTests(unittest.TestCase):
    def test_bootstrap_dispatch_command_writes_interval_and_path_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            bootstrap_config = root / "bootstrap.json"
            paths = root / "paths.csv"
            battery = root / "battery.json"
            output = root / "dispatch.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-01-01",
                        "--end-day",
                        "2025-01-04",
                        "--output",
                        str(prices),
                    ]
                )
            bootstrap_config.write_text(
                json.dumps({"start_day": "2026-01-01", "end_day": "2026-01-02", "path_count": 2})
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
                        "charge_efficiency": 1,
                        "discharge_efficiency": 1,
                    }
                )
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "generate-bootstrap-paths",
                            str(prices),
                            "--config",
                            str(bootstrap_config),
                            "--output",
                            str(paths),
                        ]
                    ),
                    0,
                )
                exit_code = main(
                    [
                        "dispatch-bootstrap-paths",
                        str(paths),
                        "--config",
                        str(battery),
                        "--availability",
                        "0.8",
                        "--output",
                        str(output),
                    ]
                )

            intervals = pd.read_csv(output)
            path_results = pd.read_csv(root / "dispatch.paths.csv")
            summary = json.loads((root / "dispatch.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(intervals), 48)
            self.assertEqual(len(path_results), 2)
            self.assertEqual(summary["availability_assumption"]["fraction"], 0.8)
            self.assertFalse(summary["is_forecast"])

    def test_price_level_shock_command_writes_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            bootstrap_config = root / "bootstrap.json"
            paths = root / "paths.csv"
            shock_config = root / "shock.json"
            shocked = root / "shocked.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-01-01",
                        "--end-day",
                        "2025-01-04",
                        "--output",
                        str(prices),
                    ]
                )
            bootstrap_config.write_text(
                json.dumps({"start_day": "2026-01-01", "end_day": "2026-01-02"}), encoding="utf-8"
            )
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-bootstrap-paths",
                        str(prices),
                        "--config",
                        str(bootstrap_config),
                        "--output",
                        str(paths),
                    ]
                )
            shock_config.write_text(
                json.dumps({"shift_eur_per_mwh": -20.0, "transformation_id": "down_20"}),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "apply-price-level-shock",
                        str(paths),
                        "--config",
                        str(shock_config),
                        "--output",
                        str(shocked),
                    ]
                )

            output = pd.read_csv(shocked)
            original = pd.read_csv(paths)
            provenance = pd.read_csv(root / "shocked.provenance.csv")
            summary = json.loads((root / "shocked.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(output), 24)
            self.assertEqual(len(provenance), 24)
            self.assertEqual(output["path_id"].tolist(), original["path_id"].tolist())
            self.assertTrue(
                np.allclose(output["price_eur_per_mwh"], original["price_eur_per_mwh"] - 20)
            )
            self.assertEqual(summary["configuration"]["transformation_id"], "down_20")

    def test_compress_spread_command_writes_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            bootstrap_config = root / "bootstrap.json"
            paths = root / "paths.csv"
            compression_config = root / "compression.json"
            compressed = root / "compressed.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-01-01",
                        "--end-day",
                        "2025-01-04",
                        "--output",
                        str(prices),
                    ]
                )
            bootstrap_config.write_text(
                json.dumps({"start_day": "2026-01-01", "end_day": "2026-01-02"}), encoding="utf-8"
            )
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-bootstrap-paths",
                        str(prices),
                        "--config",
                        str(bootstrap_config),
                        "--output",
                        str(paths),
                    ]
                )
            compression_config.write_text(
                json.dumps(
                    {
                        "compression_factor": 0.5,
                        "reference_basis": "daily_mean",
                        "transformation_id": "half_spread",
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "compress-spread",
                        str(paths),
                        "--config",
                        str(compression_config),
                        "--output",
                        str(compressed),
                    ]
                )

            output = pd.read_csv(compressed)
            original = pd.read_csv(paths)
            provenance = pd.read_csv(root / "compressed.provenance.csv")
            summary = json.loads((root / "compressed.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(output), 24)
            self.assertEqual(len(provenance), 24)
            self.assertEqual(output["path_id"].tolist(), original["path_id"].tolist())
            # The daily mean is preserved and the daily range is halved.
            self.assertTrue(
                np.isclose(output["price_eur_per_mwh"].mean(), original["price_eur_per_mwh"].mean())
            )
            self.assertTrue(
                np.isclose(
                    output["price_eur_per_mwh"].max() - output["price_eur_per_mwh"].min(),
                    (original["price_eur_per_mwh"].max() - original["price_eur_per_mwh"].min())
                    * 0.5,
                )
            )
            self.assertEqual(summary["configuration"]["transformation_id"], "half_spread")
            self.assertEqual(summary["configuration"]["reference_basis"], "daily_mean")

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
            forecast_summary = json.loads(forecasts.with_suffix(".summary.json").read_text())
            dispatch_summary = json.loads(intervals.with_suffix(".summary.json").read_text())
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
            finance_summary = json.loads(annual_cash_flows.with_suffix(".summary.json").read_text())
            self.assertEqual(finance_exit, 0)
            self.assertEqual(finance_summary["modeled_day_count"], 2)
            self.assertIn("upper bound", finance_summary["operating_margin_interpretation"])

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

            summary = json.loads(annual_output.with_suffix(".summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertTrue(annual_output.exists())
            self.assertTrue(root.joinpath("project_cash_flows.daily.csv").exists())
            self.assertEqual(summary["modeled_day_count"], 2)
            self.assertEqual(summary["initial_capex_eur"], 1_000.0)
            self.assertIn("not a bankable", summary["result_label"])

    def test_merge_canonical_command_combines_adjacent_history_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.csv"
            second = root / "second.csv"
            merged = root / "merged.csv"
            with redirect_stdout(io.StringIO()):
                for output, start_day, end_day in (
                    (first, "2026-02-01", "2026-02-03"),
                    (second, "2026-02-03", "2026-02-05"),
                ):
                    self.assertEqual(
                        main(
                            [
                                "generate-synthetic",
                                "--start-day",
                                start_day,
                                "--end-day",
                                end_day,
                                "--output",
                                str(output),
                            ]
                        ),
                        0,
                    )
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "merge-canonical",
                            str(second),
                            str(first),
                            "--output",
                            str(merged),
                        ]
                    )
            self.assertEqual(exit_code, 0)
            report = json.loads(stdout.getvalue())
            self.assertTrue(report["is_valid"])
            self.assertEqual(report["row_count"], 96)
            frame = pd.read_csv(merged)
            self.assertEqual(len(frame), 96)
            self.assertTrue(
                pd.to_datetime(frame["delivery_start_utc"], utc=True).is_monotonic_increasing
            )
            self.assertTrue(merged.with_suffix(".quality.json").exists())

    def test_annual_decomposition_command_writes_year_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            battery = root / "battery.json"
            schedule = root / "dispatch.csv"
            daily = root / "backtest.daily.csv"
            output = root / "annual.csv"
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
                        "charge_efficiency": 1,
                        "discharge_efficiency": 1,
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-12-20",
                        "--end-day",
                        "2026-01-06",
                        "--negative-price-share",
                        "0",
                        "--output",
                        str(prices),
                    ]
                )
                main(
                    [
                        "optimize-perfect-foresight",
                        str(prices),
                        "--config",
                        str(battery),
                        "--output",
                        str(schedule),
                    ]
                )
                main(
                    [
                        "backtest-forecast-dispatch",
                        str(prices),
                        "--config",
                        str(battery),
                        "--method",
                        "rolling_mean",
                        "--rolling-window-days",
                        "3",
                        "--output",
                        str(root / "backtest.csv"),
                        "--daily-output",
                        str(daily),
                    ]
                )
                exit_code = main(
                    [
                        "decompose-annual-replay",
                        str(prices),
                        "--perfect-foresight-schedule",
                        str(schedule),
                        "--daily-results",
                        f"rolling_mean={daily}",
                        "--energy-capacity-mwh",
                        "1",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(exit_code, 0)
            overview = pd.read_csv(output)
            forecast = pd.read_csv(root / "annual.forecast.csv")
            common_day = pd.read_csv(root / "annual.common_day.csv")
            summary = json.loads((root / "annual.summary.json").read_text())

            self.assertEqual(overview["delivery_year"].tolist(), [2025, 2026])
            self.assertEqual(forecast["forecast_method"].unique().tolist(), ["rolling_mean"])
            self.assertEqual(len(common_day), 2)
            self.assertEqual(summary["delivery_years"], [2025, 2026])
            self.assertAlmostEqual(
                summary["perfect_foresight_margin_reconciliation_residual_eur"], 0.0
            )
            self.assertAlmostEqual(
                float(overview["perfect_foresight_net_market_margin_eur"].sum()),
                summary["perfect_foresight_net_market_margin_eur"],
            )

    def test_annual_decomposition_rejects_a_malformed_daily_results_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices = root / "prices.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-01-04",
                        "--output",
                        str(prices),
                    ]
                )
                exit_code = main(
                    [
                        "decompose-annual-replay",
                        str(prices),
                        "--daily-results",
                        "no-separator.csv",
                        "--output",
                        str(root / "annual.csv"),
                    ]
                )
            self.assertEqual(exit_code, 1)


    def test_scenario_ensemble_command_reports_a_range_across_named_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            battery = root / "battery.json"
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
                        "charge_efficiency": 1,
                        "discharge_efficiency": 1,
                    }
                ),
                encoding="utf-8",
            )
            (root / "bootstrap.json").write_text(
                json.dumps(
                    {"start_day": "2026-01-01", "end_day": "2026-01-02", "path_count": 2}
                ),
                encoding="utf-8",
            )
            (root / "compression.json").write_text(
                json.dumps(
                    {
                        "compression_factor": 0.5,
                        "reference_basis": "daily_mean",
                        "transformation_id": "half_spread",
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2025-01-01",
                        "--end-day",
                        "2025-01-04",
                        "--output",
                        str(root / "prices.csv"),
                    ]
                )
                main(
                    [
                        "generate-bootstrap-paths",
                        str(root / "prices.csv"),
                        "--config",
                        str(root / "bootstrap.json"),
                        "--output",
                        str(root / "paths.csv"),
                    ]
                )
                main(
                    [
                        "dispatch-bootstrap-paths",
                        str(root / "paths.csv"),
                        "--config",
                        str(battery),
                        "--output",
                        str(root / "baseline.csv"),
                    ]
                )
                main(
                    [
                        "compress-spread",
                        str(root / "paths.csv"),
                        "--config",
                        str(root / "compression.json"),
                        "--output",
                        str(root / "compressed.csv"),
                    ]
                )
                main(
                    [
                        "dispatch-bootstrap-paths",
                        str(root / "compressed.csv"),
                        "--config",
                        str(battery),
                        "--output",
                        str(root / "compressed_dispatch.csv"),
                    ]
                )
            manifest = root / "ensemble.json"
            manifest.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "name": "baseline_replay",
                                "run_id": "local-baseline",
                                "path_summaries_csv": "baseline.paths.csv",
                                "dispatch_summary_json": "baseline.summary.json",
                                "bootstrap_summary_json": "paths.summary.json",
                                "transformation_summary_json": None,
                            },
                            {
                                "name": "half_spread",
                                "run_id": "local-compression",
                                "path_summaries_csv": "compressed_dispatch.paths.csv",
                                "dispatch_summary_json": "compressed_dispatch.summary.json",
                                "bootstrap_summary_json": "paths.summary.json",
                                "transformation_summary_json": "compressed.summary.json",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "report-scenario-ensemble",
                        "--manifest",
                        str(manifest),
                        "--output",
                        str(root / "ensemble.csv"),
                    ]
                )

            ranges = pd.read_csv(root / "ensemble.csv")
            margins = pd.read_csv(root / "ensemble.margins.csv")
            summary = json.loads((root / "ensemble.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(ranges), 2)
            self.assertEqual(len(margins), 4)
            self.assertEqual(summary["scenario_count"], 2)
            self.assertEqual(summary["scenario_names"], ["baseline_replay", "half_spread"])
            self.assertFalse(summary["is_probabilistic"])
            # Compressing the spread cannot raise a perfect-foresight margin, so the
            # baseline is the maximum of every path and the range is non-negative.
            self.assertTrue((ranges["maximum_scenario_name"] == "baseline_replay").all())
            self.assertTrue((ranges["minimum_scenario_name"] == "half_spread").all())
            self.assertTrue((ranges["spread_net_market_margin_eur"] >= 0).all())
            self.assertTrue(
                np.allclose(
                    ranges["spread_net_market_margin_eur"],
                    ranges["maximum_net_market_margin_eur"]
                    - ranges["minimum_net_market_margin_eur"],
                )
            )
            self.assertEqual(
                sorted(margins["input_run_id"].unique().tolist()),
                ["local-baseline", "local-compression"],
            )
            compression_row = margins.loc[margins["scenario_name"] == "half_spread"].iloc[0]
            self.assertEqual(
                json.loads(compression_row["transformation_parameters"])["compression_factor"],
                0.5,
            )
            self.assertEqual(compression_row["source_era_resolution_minutes"], 60)

    def test_scenario_ensemble_command_refuses_a_single_scenario_ensemble(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame({"path_id": [0], "net_market_margin_eur": [10.0]}).to_csv(
                root / "paths.csv", index=False
            )
            (root / "dispatch.json").write_text(
                json.dumps(
                    {
                        "battery_configuration": {
                            "charge_power_mw": 1.0,
                            "discharge_power_mw": 1.0,
                            "energy_capacity_mwh": 1.0,
                            "soc_min_fraction": 0.0,
                            "soc_max_fraction": 1.0,
                            "initial_soc_fraction": 0.0,
                            "terminal_soc_fraction": 0.0,
                        },
                        "availability_assumption": {"type": "constant", "fraction": 1.0},
                        "path_count": 1,
                    }
                ),
                encoding="utf-8",
            )
            (root / "bootstrap.json").write_text(
                json.dumps(
                    {
                        "selected_source_era": {
                            "resolution_minutes": 60,
                            "first_day": "2025-01-01",
                            "last_day": "2025-01-03",
                            "market_day_count": 3,
                        },
                        "configuration": {"random_seed": 42},
                    }
                ),
                encoding="utf-8",
            )
            manifest = root / "ensemble.json"
            manifest.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "name": "baseline_replay",
                                "run_id": "local-baseline",
                                "path_summaries_csv": "paths.csv",
                                "dispatch_summary_json": "dispatch.json",
                                "bootstrap_summary_json": "bootstrap.json",
                                "transformation_summary_json": None,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                exit_code = main(
                    [
                        "report-scenario-ensemble",
                        "--manifest",
                        str(manifest),
                        "--output",
                        str(root / "ensemble.csv"),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("at least two named scenarios", errors.getvalue())
            self.assertFalse((root / "ensemble.csv").exists())


    def _availability_fixture(self, root: Path) -> Path:
        battery = root / "battery.json"
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
                    "charge_efficiency": 1,
                    "discharge_efficiency": 1,
                }
            ),
            encoding="utf-8",
        )
        (root / "bootstrap.json").write_text(
            json.dumps({"start_day": "2026-01-01", "end_day": "2026-01-02"}), encoding="utf-8"
        )
        with redirect_stdout(io.StringIO()):
            main(
                [
                    "generate-synthetic",
                    "--start-day",
                    "2025-01-01",
                    "--end-day",
                    "2025-01-04",
                    "--output",
                    str(root / "prices.csv"),
                ]
            )
            main(
                [
                    "generate-bootstrap-paths",
                    str(root / "prices.csv"),
                    "--config",
                    str(root / "bootstrap.json"),
                    "--output",
                    str(root / "paths.csv"),
                ]
            )
        return battery

    def test_dispatch_accepts_a_declared_availability_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            battery = self._availability_fixture(root)
            (root / "availability.json").write_text(
                json.dumps(
                    {
                        "schedule_id": "planned_maintenance",
                        "baseline_available_fraction": 1.0,
                        "windows": [
                            {
                                "outage_id": "morning_outage",
                                "start_utc": "2025-12-31T23:00:00+00:00",
                                "end_utc": "2026-01-01T05:00:00+00:00",
                                "available_fraction": 0.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "dispatch-bootstrap-paths",
                        str(root / "paths.csv"),
                        "--config",
                        str(battery),
                        "--availability-schedule",
                        str(root / "availability.json"),
                        "--output",
                        str(root / "dispatch.csv"),
                    ]
                )

            summary = json.loads((root / "dispatch.summary.json").read_text())
            availability = pd.read_csv(root / "dispatch.availability.csv")
            intervals = pd.read_csv(root / "dispatch.csv")
            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["availability_assumption"]["type"], "declared_schedule")
            self.assertEqual(
                summary["availability_assumption"]["schedule_id"], "planned_maintenance"
            )
            self.assertEqual(summary["availability_assumption"]["derated_hours"], 6.0)
            self.assertEqual(len(availability), 24)
            self.assertEqual(int(availability["outage_id"].notna().sum()), 6)
            # The battery cannot trade while it is declared unavailable.
            idle = intervals.loc[intervals["availability_fraction"] == 0.0]
            self.assertEqual(len(idle), 6)
            self.assertTrue(np.allclose(idle["charge_grid_mwh"], 0.0))
            self.assertTrue(np.allclose(idle["discharge_grid_mwh"], 0.0))

    def test_dispatch_refuses_two_availability_assumptions_for_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            battery = self._availability_fixture(root)
            (root / "availability.json").write_text(
                json.dumps(
                    {
                        "schedule_id": "planned",
                        "baseline_available_fraction": 1.0,
                        "windows": [],
                    }
                ),
                encoding="utf-8",
            )

            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                exit_code = main(
                    [
                        "dispatch-bootstrap-paths",
                        str(root / "paths.csv"),
                        "--config",
                        str(battery),
                        "--availability",
                        "0.9",
                        "--availability-schedule",
                        str(root / "availability.json"),
                        "--output",
                        str(root / "dispatch.csv"),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("not both", errors.getvalue())
            self.assertFalse((root / "dispatch.csv").exists())


if __name__ == "__main__":
    unittest.main()
