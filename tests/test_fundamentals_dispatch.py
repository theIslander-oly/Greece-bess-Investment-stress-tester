"""Synthetic-only tests for the v0.9.4 settled dispatch comparison.

Nothing here uses official prices or a real forecast vintage, and nothing here accepts a
result. The suite exists to hold three properties that a plausible-looking wrong number would
break: that the control arm settled through this path is the accepted ML dispatch benchmark
unchanged, that every arm faced one battery, one price series and one perfect-foresight
ceiling, and that the incremental margin recorded in the summary is the same number as the sum
of the paired daily differences written beside it.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from greek_bess.backtest import backtest_ml_dispatch_benchmark
from greek_bess.backtest.forecast_dispatch import ForecastDispatchInputError
from greek_bess.backtest.fundamentals_dispatch import (
    FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL,
    FundamentalsDispatchInputError,
    _comparison_pairs,
    _incremental_rows,
    _paired_differences,
    _shared_ceiling,
    backtest_fundamentals_dispatch,
)
from greek_bess.backtest.ml_dispatch import _backtest_precomputed_forecast
from greek_bess.cli import main
from greek_bess.data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    PROVIDER_DECLARED,
    VARIABLE_UNITS,
)
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.forecast import generate_ml_forecasts
from greek_bess.forecast.fundamentals import (
    EXPLORATORY_LABEL_SUFFIX,
    generate_fundamentals_benchmark,
)
from greek_bess.forecast.point_in_time_join import join_point_in_time_features
from greek_bess.reporting.contract import (
    ReportContractError,
    build_run_manifest,
    read_run_manifest,
    write_run_manifest,
)
from tests.test_fundamentals_benchmark import (
    TEST_START,
    _config,
    _feature_set,
    _ml_config,
    _prices,
    _schedule,
)

CONTROL = "ridge"
CHALLENGER = "ridge_fundamentals"
BASELINE = "rolling_mean"
SETTLED_METHODS = (BASELINE, CONTROL, CHALLENGER)


def _battery(**overrides: Any) -> BatteryDispatchConfig:
    settings: dict[str, Any] = {
        "charge_power_mw": 50.0,
        "discharge_power_mw": 50.0,
        "energy_capacity_mwh": 100.0,
    }
    settings.update(overrides)
    return BatteryDispatchConfig(**settings)


def _informative_rows(prices: pd.DataFrame) -> pd.DataFrame:
    """A synthetic pre-cutoff feature deliberately built to carry the delivery day's shape.

    The fixture of ``test_fundamentals_benchmark`` uses a feature uncorrelated with price, which
    is the honest default: it exercises the pipeline without pretending an exogenous variable
    predicts anything. It also settles identically in both arms, so it cannot exercise the path
    where a challenger's plan actually differs. This helper is the complement — an entirely
    constructed perfect predictor, published a day before its delivery day and therefore
    admissible under the fixture's own cutoff. It makes no claim about any real variable, and
    a fixture is never accepted evidence; it exists so the non-zero incremental path is tested
    rather than assumed.
    """

    rows: list[dict[str, Any]] = []
    for position, row in enumerate(prices.itertuples(index=False)):
        market_day = row.delivery_start_market.date()
        publication = pd.Timestamp(market_day - timedelta(days=1), tz="UTC") + pd.Timedelta(
            4, unit="h"
        )
        rows.append(
            {
                "delivery_start_utc": row.delivery_start_utc,
                "delivery_end_utc": row.delivery_end_utc,
                "market_day": market_day,
                "source": "synthetic",
                "dataset": "synthetic_forecast",
                "variable": "temperature_2m",
                "area": "GR",
                "unit": VARIABLE_UNITS["temperature_2m"],
                "resolution_minutes": 60,
                "value": 273.15 + 0.05 * float(row.price_eur_per_mwh),
                "published_at_utc": publication,
                "retrieved_at_utc": publication + pd.Timedelta(1, unit="h"),
                "source_document_id": f"synthetic-informative-{position}",
                "source_revision": "1",
                "raw_sha256": f"{position + 1:064x}",
                "forecast_issue_time_utc": publication - pd.Timedelta(4, unit="h"),
                "forecast_horizon_minutes": None,
                "availability_evidence_grade": PROVIDER_DECLARED,
                "availability_evidence_detail": "synthetic fixture",
            }
        )
    return pd.DataFrame(rows)


def _informative_feature_set(prices: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = join_point_in_time_features(
        prices,
        _informative_rows(prices),
        schedule=_schedule(),
        decision_lead_minutes=0,
        admitted_grades=ADMISSIBLE_EVIDENCE_GRADES,
        exploratory=False,
    )
    return result.feature_frame, result.summary


class SettledComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = _prices()
        cls.features, cls.join_summary = _informative_feature_set(cls.prices)
        cls.benchmark = generate_fundamentals_benchmark(
            cls.prices, cls.features, cls.join_summary, _config(cls.join_summary)
        )
        cls.battery = _battery()
        cls.result = backtest_fundamentals_dispatch(
            cls.prices,
            cls.battery,
            cls.benchmark.forecasts,
            cls.benchmark.summary,
            methods=SETTLED_METHODS,
        )

    def test_the_control_arm_reproduces_the_accepted_ml_dispatch_benchmark(self) -> None:
        """Arm A through the new path must be the accepted computation, digit for digit."""

        accepted = backtest_ml_dispatch_benchmark(
            self.prices, self.battery, generate_ml_forecasts(self.prices, _ml_config())
        )
        self.assertEqual(
            accepted.summary["common_backtest_day_count"],
            self.result.summary["common_backtest_day_count"],
        )
        for method in (BASELINE, CONTROL):
            recorded = accepted.method_summaries[method]
            settled = self.result.method_summaries[method]
            for key in (
                "realized_margin_eur",
                "perfect_foresight_margin_eur",
                "perfect_foresight_regret_eur",
                "perfect_foresight_capture_ratio",
                "forecast_planned_margin_eur",
                "grid_charge_mwh",
                "grid_discharge_mwh",
            ):
                self.assertEqual(recorded[key], settled[key], msg=f"{method}.{key}")

    def test_every_arm_faced_one_battery_one_price_series_and_one_ceiling(self) -> None:
        basis = self.result.summary["equivalent_basis"]
        self.assertEqual(
            sorted(basis),
            [
                "battery_configuration",
                "common_day_identity",
                "feature_set_identity",
                "perfect_foresight_ceiling",
                "realized_price_identity",
                "terminal_energy_basis",
            ],
        )
        self.assertEqual(basis["perfect_foresight_ceiling"]["maximum_ceiling_spread_eur"], 0.0)
        self.assertEqual(
            basis["terminal_energy_basis"]["effective_terminal_soc_fraction"],
            self.battery.initial_soc_fraction,
        )
        self.assertNotIn("energy_capacity_mwh", basis["battery_configuration"])
        self.assertEqual(
            basis["feature_set_identity"]["feature_set_sha256"],
            self.join_summary["feature_set_sha256"],
        )
        ceilings = {
            summary["perfect_foresight_margin_eur"]
            for summary in self.result.method_summaries.values()
        }
        self.assertEqual(len(ceilings), 1)

    def test_the_incremental_margin_equals_the_paired_daily_differences(self) -> None:
        differences = self.result.paired_differences
        for row in self.result.summary["incremental_realized_margin_eur"]:
            paired = differences.loc[differences["comparison_id"].eq(row["comparison_id"])]
            self.assertEqual(
                len(paired), self.result.summary["common_backtest_day_count"]
            )
            self.assertAlmostEqual(
                row["incremental_realized_margin_eur"],
                float(paired["realized_margin_difference_eur"].sum()),
                places=6,
            )
            self.assertAlmostEqual(
                row["incremental_realized_margin_eur"],
                row["challenger_realized_margin_eur"] - row["reference_realized_margin_eur"],
                places=6,
            )

    def test_an_informative_feature_moves_the_settled_plan_and_the_margin(self) -> None:
        [incremental] = self.result.summary["incremental_realized_margin_eur"]
        self.assertEqual(incremental["challenger_method"], CHALLENGER)
        self.assertEqual(incremental["reference_method"], CONTROL)
        self.assertGreater(incremental["incremental_realized_margin_eur"], 0.0)
        self.assertGreater(incremental["days_challenger_settled_higher"], 0)
        schedules = self.result.interval_schedules
        control = schedules.loc[schedules["forecast_method"].eq(CONTROL)]
        challenger = schedules.loc[schedules["forecast_method"].eq(CHALLENGER)]
        planned_difference = (
            challenger["discharge_mw"].to_numpy(dtype=float)
            - control["discharge_mw"].to_numpy(dtype=float)
        )
        self.assertGreater(float(np.abs(planned_difference).max()), 0.0)

    def test_the_comparison_is_recorded_against_each_named_baseline_as_well(self) -> None:
        against_baseline = self.result.summary[
            "incremental_realized_margin_versus_baseline_eur"
        ]
        self.assertEqual([row["reference_method"] for row in against_baseline], [BASELINE])
        self.assertEqual(
            [row["reference_role"] for row in against_baseline], ["baseline"]
        )

    def test_the_label_and_the_standing_negatives_are_recorded(self) -> None:
        summary = self.result.summary
        self.assertTrue(
            summary["result_label"].startswith(FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL)
        )
        self.assertFalse(summary["is_probabilistic"])
        self.assertFalse(summary["is_forecast"])
        self.assertFalse(summary["is_investment_evidence"])
        self.assertEqual(
            summary["exploratory_causes"],
            self.benchmark.summary["exploratory_causes"],
        )
        self.assertTrue(summary["is_exploratory"])
        self.assertTrue(summary["result_label"].endswith(EXPLORATORY_LABEL_SUFFIX))

    def test_repeated_runs_are_bit_identical(self) -> None:
        repeated = backtest_fundamentals_dispatch(
            self.prices,
            self.battery,
            self.benchmark.forecasts,
            self.benchmark.summary,
            methods=SETTLED_METHODS,
        )
        pd.testing.assert_frame_equal(
            self.result.paired_differences, repeated.paired_differences
        )
        pd.testing.assert_frame_equal(self.result.daily_results, repeated.daily_results)
        self.assertEqual(
            json.dumps(self.result.summary, sort_keys=True, default=str),
            json.dumps(repeated.summary, sort_keys=True, default=str),
        )

    def test_mutating_realized_prices_changes_settlement_and_not_the_plan(self) -> None:
        """Case 17: the plan is made from the forecast; only the settlement sees reality."""

        mutated_prices = self.prices.copy()
        held_out = mutated_prices["delivery_start_market"].dt.date.map(
            lambda day: day >= TEST_START
        )
        mutated_prices.loc[held_out, "price_eur_per_mwh"] += 25.0
        mutated = backtest_fundamentals_dispatch(
            mutated_prices,
            self.battery,
            self.benchmark.forecasts,
            self.benchmark.summary,
            methods=SETTLED_METHODS,
        )
        for column in ("charge_mw", "discharge_mw"):
            np.testing.assert_allclose(
                mutated.interval_schedules[column].to_numpy(dtype=float),
                self.result.interval_schedules[column].to_numpy(dtype=float),
            )
        self.assertNotEqual(
            mutated.summary["perfect_foresight_margin_eur"],
            self.result.summary["perfect_foresight_margin_eur"],
        )
        self.assertNotEqual(
            mutated.method_summaries[CONTROL]["realized_margin_eur"],
            self.result.method_summaries[CONTROL]["realized_margin_eur"],
        )

    def test_the_settled_days_are_exactly_the_recorded_common_held_out_days(self) -> None:
        summary = self.result.summary
        self.assertEqual(
            summary["common_backtest_day_count"],
            self.benchmark.summary["common_test_day_count"],
        )
        settled_days = set(self.result.daily_results["market_day"])
        forecasts = self.benchmark.forecasts
        recorded = set(
            forecasts.loc[
                forecasts["split"].eq("test") & forecasts["is_common_day"], "market_day"
            ]
        )
        self.assertEqual(settled_days, recorded)


class RefusalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = _prices()
        features, join_summary = _feature_set(cls.prices)
        cls.benchmark = generate_fundamentals_benchmark(
            cls.prices, features, join_summary, _config(join_summary)
        )
        cls.battery = _battery()

    def _run(self, **overrides: Any) -> Any:
        parameters: dict[str, Any] = {
            "prices": self.prices,
            "config": self.battery,
            "forecasts": self.benchmark.forecasts,
            "benchmark_summary": self.benchmark.summary,
            "methods": SETTLED_METHODS,
        }
        parameters.update(overrides)
        return backtest_fundamentals_dispatch(
            parameters["prices"],
            parameters["config"],
            parameters["forecasts"],
            parameters["benchmark_summary"],
            methods=parameters["methods"],
        )

    def test_a_challenger_named_without_its_control_is_refused(self) -> None:
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "beside its own control"
        ):
            self._run(methods=(BASELINE, CHALLENGER))

    def test_a_method_no_arm_produced_is_refused(self) -> None:
        with self.assertRaisesRegex(FundamentalsDispatchInputError, "recorded no arm"):
            self._run(methods=(CONTROL, CHALLENGER, "gradient_boosting_v2"))

    def test_an_empty_or_repeated_method_list_is_refused(self) -> None:
        with self.assertRaisesRegex(FundamentalsDispatchInputError, "no default"):
            self._run(methods=())
        with self.assertRaisesRegex(FundamentalsDispatchInputError, "repeated"):
            self._run(methods=(CONTROL, CHALLENGER, CONTROL))

    def test_a_summary_that_does_not_identify_its_ablation_is_refused(self) -> None:
        stripped = dict(self.benchmark.summary)
        del stripped["feature_set_sha256"]
        with self.assertRaisesRegex(FundamentalsDispatchInputError, "feature_set_sha256"):
            self._run(benchmark_summary=stripped)
        without_arms = dict(self.benchmark.summary)
        without_arms["ablation_arms"] = {"control": {"methods": ["ridge"]}}
        with self.assertRaisesRegex(FundamentalsDispatchInputError, "ablation_arms"):
            self._run(benchmark_summary=without_arms)

    def test_a_challenger_arm_with_no_control_counterpart_is_refused(self) -> None:
        """A hand-edited summary must not be able to pair a challenger with anything."""

        edited = dict(self.benchmark.summary)
        arms = json.loads(json.dumps(edited["ablation_arms"], default=str))
        arms["challenger"]["methods"] = ["a_different_model_fundamentals"]
        edited["ablation_arms"] = arms
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "no control counterpart"
        ):
            self._run(benchmark_summary=edited)

    def test_a_gap_on_a_day_recorded_as_common_is_refused(self) -> None:
        forecasts = self.benchmark.forecasts.copy()
        held_out = forecasts["split"].eq("test") & forecasts["is_common_day"]
        forecasts.loc[forecasts.index[held_out][0], CHALLENGER] = np.nan
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "contradicts the forecast benchmark"
        ):
            self._run(forecasts=forecasts)

    def test_a_table_disagreeing_with_its_summary_day_count_is_refused(self) -> None:
        forecasts = self.benchmark.forecasts
        dropped = sorted(
            forecasts.loc[
                forecasts["split"].eq("test") & forecasts["is_common_day"], "market_day"
            ].unique()
        )[0]
        trimmed = forecasts.loc[~forecasts["market_day"].eq(dropped)]
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "must describe one run"
        ):
            self._run(forecasts=trimmed)

    def test_a_table_with_no_common_held_out_day_is_refused(self) -> None:
        forecasts = self.benchmark.forecasts.copy()
        forecasts["is_common_day"] = False
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "no held-out day marked common"
        ):
            self._run(forecasts=forecasts)

    def test_a_terminal_soc_differing_from_the_initial_soc_is_refused(self) -> None:
        with self.assertRaisesRegex(ForecastDispatchInputError, "terminal_soc_fraction"):
            self._run(config=_battery(terminal_soc_fraction=0.6))

    def test_two_batteries_produce_two_ceilings_and_the_comparison_is_refused(self) -> None:
        """Case 18: a difference in the physical basis must be named, never reconciled."""

        forecasts = self.benchmark.forecasts
        held_out = forecasts.loc[forecasts["split"].eq("test") & forecasts["is_common_day"]]
        first = _backtest_precomputed_forecast(
            self.prices, _battery(), held_out, method=CONTROL
        )
        second = _backtest_precomputed_forecast(
            self.prices,
            _battery(energy_capacity_mwh=150.0),
            held_out,
            method=CHALLENGER,
        )
        with self.assertRaisesRegex(
            FundamentalsDispatchInputError, "did not face the same perfect-foresight ceiling"
        ):
            _shared_ceiling({CONTROL: first.summary, CHALLENGER: second.summary})


class IncrementalArithmeticTests(unittest.TestCase):
    """A closed-form two-day case, so the recorded arithmetic is checked and not trusted."""

    ARMS = {
        "baselines": (),
        "control": (CONTROL,),
        "challenger": (CHALLENGER,),
    }
    FIRST = date(2026, 3, 1)
    SECOND = date(2026, 3, 2)

    def _daily(self) -> pd.DataFrame:
        return pd.DataFrame.from_records(
            [
                {
                    "comparison_method": CONTROL,
                    "market_day": self.FIRST,
                    "interval_count": 24,
                    "realized_margin_eur": 100.0,
                    "perfect_foresight_margin_eur": 300.0,
                },
                {
                    "comparison_method": CONTROL,
                    "market_day": self.SECOND,
                    "interval_count": 24,
                    "realized_margin_eur": 200.0,
                    "perfect_foresight_margin_eur": 400.0,
                },
                {
                    "comparison_method": CHALLENGER,
                    "market_day": self.FIRST,
                    "interval_count": 24,
                    "realized_margin_eur": 150.0,
                    "perfect_foresight_margin_eur": 300.0,
                },
                {
                    "comparison_method": CHALLENGER,
                    "market_day": self.SECOND,
                    "interval_count": 24,
                    "realized_margin_eur": 180.0,
                    "perfect_foresight_margin_eur": 400.0,
                },
            ]
        )

    def test_the_paired_differences_and_the_increment_are_the_arithmetic_expected(self) -> None:
        pairs = _comparison_pairs((CONTROL, CHALLENGER), self.ARMS)
        differences = _paired_differences(self._daily(), pairs)
        self.assertEqual(
            list(differences["realized_margin_difference_eur"]), [50.0, -20.0]
        )
        [row] = _incremental_rows(
            differences,
            {
                CONTROL: {
                    "realized_margin_eur": 300.0,
                    "perfect_foresight_capture_ratio": 300.0 / 700.0,
                },
                CHALLENGER: {
                    "realized_margin_eur": 330.0,
                    "perfect_foresight_capture_ratio": 330.0 / 700.0,
                },
            },
            role="control",
        )
        self.assertEqual(row["incremental_realized_margin_eur"], 30.0)
        self.assertEqual(row["common_day_count"], 2)
        self.assertEqual(row["days_challenger_settled_higher"], 1)
        self.assertEqual(row["days_reference_settled_higher"], 1)
        self.assertEqual(row["days_settled_equal"], 0)
        self.assertEqual(row["largest_daily_gain_eur"], 50.0)
        self.assertEqual(row["largest_daily_shortfall_eur"], -20.0)
        self.assertEqual(
            row["incremental_realized_margin_eur"],
            row["challenger_realized_margin_eur"] - row["reference_realized_margin_eur"],
        )

    def test_a_challenger_that_settles_less_is_recorded_as_it_stands(self) -> None:
        daily = self._daily()
        challenger = daily["comparison_method"].eq(CHALLENGER)
        daily.loc[challenger, "realized_margin_eur"] = [40.0, 90.0]
        differences = _paired_differences(
            daily, _comparison_pairs((CONTROL, CHALLENGER), self.ARMS)
        )
        [row] = _incremental_rows(
            differences,
            {
                CONTROL: {
                    "realized_margin_eur": 300.0,
                    "perfect_foresight_capture_ratio": None,
                },
                CHALLENGER: {
                    "realized_margin_eur": 130.0,
                    "perfect_foresight_capture_ratio": None,
                },
            },
            role="control",
        )
        self.assertEqual(row["incremental_realized_margin_eur"], -170.0)
        self.assertEqual(row["days_challenger_settled_higher"], 0)
        self.assertEqual(row["days_reference_settled_higher"], 2)


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        prices = _prices()
        features, join_summary = _feature_set(prices)
        benchmark = generate_fundamentals_benchmark(
            prices, features, join_summary, _config(join_summary)
        )
        cls.summary = backtest_fundamentals_dispatch(
            prices,
            _battery(),
            benchmark.forecasts,
            benchmark.summary,
            methods=(CONTROL, CHALLENGER),
        ).summary

    def test_the_summary_records_under_the_new_kind_and_reads_back(self) -> None:
        manifest = build_run_manifest(
            self.summary,
            kind_id="fundamentals_dispatch_benchmark",
            manifest_id="fundamentals-dispatch-1",
            produced_by="benchmark-fundamentals-dispatch",
            declared_inputs={"feature_set_sha256": self.summary["feature_set_sha256"]},
        )
        self.assertEqual(manifest.basis, "historical_forecast_backtest")
        self.assertEqual(manifest.result_label, self.summary["result_label"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            write_run_manifest(path, manifest)
            recovered = read_run_manifest(path)
        self.assertEqual(recovered.summary["dispatch_ranking"], self.summary["dispatch_ranking"])
        self.assertEqual(
            recovered.summary["incremental_realized_margin_eur"],
            self.summary["incremental_realized_margin_eur"],
        )

    def test_a_hand_edited_manifest_is_refused_on_read(self) -> None:
        manifest = build_run_manifest(
            self.summary,
            kind_id="fundamentals_dispatch_benchmark",
            manifest_id="fundamentals-dispatch-2",
            produced_by="benchmark-fundamentals-dispatch",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            write_run_manifest(path, manifest)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["summary"]["evidence_grades_admitted"] = [ASSUMED]
            payload["summary"]["is_exploratory"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "quarantined 'assumed'"):
                read_run_manifest(path)

    def test_a_summary_missing_a_guaranteed_key_cannot_be_recorded(self) -> None:
        stripped = dict(self.summary)
        del stripped["equivalent_basis"]
        with self.assertRaisesRegex(ReportContractError, "equivalent_basis"):
            build_run_manifest(
                stripped,
                kind_id="fundamentals_dispatch_benchmark",
                manifest_id="fundamentals-dispatch-3",
                produced_by="benchmark-fundamentals-dispatch",
            )


class DispatchCommandTests(unittest.TestCase):
    """The command must carry the ablation's identity across a CSV round trip."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = _prices()
        features, join_summary = _feature_set(cls.prices)
        cls.benchmark = generate_fundamentals_benchmark(
            cls.prices, features, join_summary, _config(join_summary)
        )

    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        prices_path = root / "prices.csv"
        export = self.prices.copy()
        export["quality_flags"] = export["quality_flags"].map(json.dumps)
        export.to_csv(prices_path, index=False)
        forecasts_path = root / "forecasts.csv"
        self.benchmark.forecasts.to_csv(forecasts_path, index=False)
        (root / "forecasts.summary.json").write_text(
            json.dumps(self.benchmark.summary, default=str), encoding="utf-8"
        )
        battery_path = root / "battery.json"
        battery_path.write_text(
            json.dumps(
                {
                    "charge_power_mw": 50.0,
                    "discharge_power_mw": 50.0,
                    "energy_capacity_mwh": 100.0,
                }
            ),
            encoding="utf-8",
        )
        return prices_path, forecasts_path, battery_path

    def test_the_command_writes_the_four_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices_path, forecasts_path, battery_path = self._fixture(root)
            output = root / "settled.csv"
            with redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "benchmark-fundamentals-dispatch",
                        str(prices_path),
                        "--config",
                        str(battery_path),
                        "--forecasts",
                        str(forecasts_path),
                        "--methods",
                        CONTROL,
                        CHALLENGER,
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            paired = pd.read_csv(root / "settled.paired.csv")
            daily = pd.read_csv(root / "settled.daily.csv")
            summary = json.loads((root / "settled.summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["comparison_methods"], [CONTROL, CHALLENGER])
            self.assertEqual(
                summary["feature_set_sha256"], self.benchmark.summary["feature_set_sha256"]
            )
            self.assertEqual(
                sorted(daily["comparison_method"].unique()), sorted([CONTROL, CHALLENGER])
            )
            self.assertEqual(
                list(paired["comparison_id"].unique()), [f"{CHALLENGER}_vs_{CONTROL}"]
            )

    def test_the_command_refuses_an_unpaired_challenger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices_path, forecasts_path, battery_path = self._fixture(root)
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                code = main(
                    [
                        "benchmark-fundamentals-dispatch",
                        str(prices_path),
                        "--config",
                        str(battery_path),
                        "--forecasts",
                        str(forecasts_path),
                        "--methods",
                        CHALLENGER,
                        "--output",
                        str(root / "settled.csv"),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("beside its own control", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
