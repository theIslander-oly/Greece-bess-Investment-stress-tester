"""Synthetic-only tests for the v0.9.3 fundamentals forecast ablation.

Nothing here uses official prices or a real forecast vintage, and nothing here accepts a
result. The point of the suite is the opposite: that the ablation refuses every input it could
otherwise reinterpret, that its control arm is provably the accepted benchmark unchanged, and
that a delivery day without an accepted feature leaves both arms rather than acquiring one.
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

from greek_bess.cli import main
from greek_bess.data.decision_cutoff import GateClosureSchedule
from greek_bess.data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    PROVIDER_DECLARED,
    VARIABLE_UNITS,
    WITNESSED,
    write_point_in_time_csv,
)
from greek_bess.data.schema import read_canonical_csv
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.forecast import MLForecastConfig, generate_ml_forecasts
from greek_bess.forecast.fundamentals import (
    EXPLORATORY_LABEL_SUFFIX,
    FUNDAMENTALS_FEATURE_PROVENANCE,
    FUNDAMENTALS_FORECAST_BENCHMARK_LABEL,
    FundamentalsBenchmarkConfig,
    FundamentalsBenchmarkError,
    _complete_meteorological_seasons,
    generate_fundamentals_benchmark,
)
from greek_bess.forecast.ml import MLForecastInputError, _walk_forward_predict
from greek_bess.forecast.point_in_time_join import join_point_in_time_features
from greek_bess.reporting.contract import (
    ReportContractError,
    build_run_manifest,
    read_run_manifest,
    write_run_manifest,
)

START_DAY = date(2026, 1, 1)
END_DAY = date(2026, 3, 12)
VALIDATION_START = date(2026, 2, 12)
TEST_START = date(2026, 2, 26)
BANDS = (0.0, 50.0, 150.0)


def _schedule() -> GateClosureSchedule:
    return GateClosureSchedule.from_dict(
        {
            "schedule_id": "synthetic-benchmark-cutoff",
            "regimes": [
                {
                    "effective_from_delivery_day": "2020-11-01",
                    "closure_day_offset": -1,
                    "closure_local_time": "12:00:00",
                    "closure_timezone": "Europe/Athens",
                    "reference": "Synthetic test declaration only.",
                }
            ],
        }
    )


def _prices(seed: int = 11) -> pd.DataFrame:
    return generate_synthetic_prices(START_DAY, END_DAY, seed=seed)


def _point_in_time_rows(
    prices: pd.DataFrame,
    *,
    omit_days: tuple[date, ...] = (),
    grade: str = PROVIDER_DECLARED,
) -> pd.DataFrame:
    """One synthetic revision per delivery interval, published before every cutoff."""

    rows: list[dict[str, Any]] = []
    for position, row in enumerate(prices.itertuples(index=False)):
        market_day = row.delivery_start_market.date()
        if market_day in omit_days:
            continue
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
                "value": 280.0 + 8.0 * np.sin(position / 12.0),
                "published_at_utc": publication,
                "retrieved_at_utc": publication + pd.Timedelta(1, unit="h"),
                "source_document_id": f"synthetic-{position}",
                "source_revision": "1",
                "raw_sha256": f"{position + 1:064x}",
                "forecast_issue_time_utc": publication - pd.Timedelta(4, unit="h"),
                "forecast_horizon_minutes": None,
                "availability_evidence_grade": grade,
                "availability_evidence_detail": "synthetic fixture",
            }
        )
    return pd.DataFrame(rows)


def _feature_set(
    prices: pd.DataFrame,
    *,
    omit_days: tuple[date, ...] = (),
    grade: str = PROVIDER_DECLARED,
    admitted: tuple[str, ...] = ADMISSIBLE_EVIDENCE_GRADES,
    exploratory: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = join_point_in_time_features(
        prices,
        _point_in_time_rows(prices, omit_days=omit_days, grade=grade),
        schedule=_schedule(),
        decision_lead_minutes=0,
        admitted_grades=admitted,
        exploratory=exploratory,
    )
    return result.feature_frame, result.summary


def _ml_config(**overrides: Any) -> MLForecastConfig:
    settings: dict[str, Any] = {
        "validation_start_day": VALIDATION_START,
        "test_start_day": TEST_START,
        "min_training_days": 28,
        "refit_frequency_days": 7,
        "gradient_max_iter": 25,
    }
    settings.update(overrides)
    return MLForecastConfig(**settings)


def _config(summary: dict[str, Any], **overrides: Any) -> FundamentalsBenchmarkConfig:
    settings: dict[str, Any] = {
        "ml": _ml_config(),
        "feature_set_sha256": summary["feature_set_sha256"],
        "decision_cutoff_schedule_id": summary["schedule_id"],
        "decision_lead_minutes": summary["decision_lead_minutes"],
        "evidence_grades_admitted": tuple(summary["admitted_grades"]),
        "price_regime_bands": BANDS,
    }
    settings.update(overrides)
    return FundamentalsBenchmarkConfig(**settings)


class FundamentalsBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = _prices()
        cls.features, cls.summary = _feature_set(cls.prices)
        cls.result = generate_fundamentals_benchmark(
            cls.prices, cls.features, cls.summary, _config(cls.summary)
        )

    def test_the_control_arm_reproduces_the_accepted_benchmark_bit_for_bit(self) -> None:
        accepted = generate_ml_forecasts(self.prices, _ml_config())
        control_columns = list(_ml_config().models)
        pd.testing.assert_frame_equal(
            accepted.forecasts.loc[:, ["delivery_start_utc", *control_columns]],
            self.result.forecasts.loc[:, ["delivery_start_utc", *control_columns]],
        )
        self.assertEqual(
            accepted.summary["refit_logs"],
            {name: self.result.summary["refit_logs"][name] for name in control_columns},
        )

    def test_both_arms_are_measured_on_the_same_common_days(self) -> None:
        summary = self.result.summary
        methods = [
            "ridge",
            "hist_gradient_boosting",
            "ridge_fundamentals",
            "hist_gradient_boosting_fundamentals",
        ]
        for method in methods:
            self.assertIn(method, self.result.forecasts.columns)
            self.assertEqual(summary["metrics"]["test"][method]["coverage_fraction"], 1.0)
            self.assertEqual(
                summary["metrics"]["test"][method]["observation_count"],
                summary["metrics"]["test"]["ridge"]["observation_count"],
            )
        self.assertEqual(summary["common_day_count"], summary["evaluation_day_count"])
        self.assertEqual(summary["challenger_training_intervals_dropped"], 0)
        self.assertIn(summary["selected_challenger"], methods[2:])
        self.assertIn(summary["selected_control"], methods[:2])
        self.assertEqual(summary["feature_set_sha256"], self.summary["feature_set_sha256"])
        self.assertEqual(summary["fundamentals_feature_columns"], ["temperature_2m"])
        self.assertEqual(
            summary["fundamentals_feature_provenance"]["temperature_2m"],
            FUNDAMENTALS_FEATURE_PROVENANCE["temperature_2m"],
        )

    def test_the_two_arms_are_not_the_same_model(self) -> None:
        difference = (
            self.result.forecasts["ridge_fundamentals"] - self.result.forecasts["ridge"]
        ).abs()
        self.assertGreater(float(difference.max()), 0.0)

    def test_declared_slices_are_reported_on_the_held_out_split_only(self) -> None:
        slices = self.result.summary["metrics_by_slice"]
        self.assertEqual(self.result.summary["sliced_split"], "test")
        self.assertEqual(
            sorted(slices),
            ["delivery_year", "interval_of_day", "price_regime", "resolution_era"],
        )
        self.assertEqual(list(slices["resolution_era"]), ["hourly"])
        self.assertEqual(list(slices["delivery_year"]), ["2026"])
        self.assertEqual(len(slices["interval_of_day"]), 24)
        for label in slices["price_regime"]:
            self.assertIn(label, {"<= 0", "(0, 50]", "(50, 150]", "> 150"})

    def test_repeated_runs_are_bit_identical(self) -> None:
        repeated = generate_fundamentals_benchmark(
            self.prices, self.features, self.summary, _config(self.summary)
        )
        pd.testing.assert_frame_equal(self.result.forecasts, repeated.forecasts)
        self.assertEqual(
            json.dumps(self.result.summary, sort_keys=True, default=str),
            json.dumps(repeated.summary, sort_keys=True, default=str),
        )

    def test_held_out_label_mutation_cannot_change_model_selection(self) -> None:
        mutated_prices = self.prices.copy()
        held_out = mutated_prices["delivery_start_market"].dt.date.map(
            lambda day: day >= TEST_START
        )
        mutated_prices.loc[held_out, "price_eur_per_mwh"] = 9000.0
        features, summary = _feature_set(mutated_prices)
        mutated = generate_fundamentals_benchmark(
            mutated_prices, features, summary, _config(summary)
        )
        self.assertEqual(
            mutated.summary["selected_control"], self.result.summary["selected_control"]
        )
        self.assertEqual(
            mutated.summary["selected_challenger"], self.result.summary["selected_challenger"]
        )
        self.assertEqual(
            mutated.summary["metrics"]["validation"], self.result.summary["metrics"]["validation"]
        )

    def test_a_day_without_an_accepted_feature_leaves_every_arm_by_named_cause(self) -> None:
        excluded_day = date(2026, 3, 2)
        features, summary = _feature_set(self.prices, omit_days=(excluded_day,))
        result = generate_fundamentals_benchmark(
            self.prices, features, summary, _config(summary)
        )
        excluded = {record["market_day"]: record for record in result.summary["excluded_days"]}
        self.assertIn(str(excluded_day), excluded)
        self.assertEqual(excluded[str(excluded_day)]["cause"], "feature_no_publication")
        self.assertEqual(
            result.summary["excluded_days_by_cause"]["feature_no_publication"], 1
        )
        self.assertNotIn(
            excluded_day,
            set(result.forecasts.loc[result.forecasts["is_common_day"], "market_day"]),
        )
        self.assertLess(
            result.summary["common_day_count"], self.result.summary["common_day_count"]
        )
        self.assertGreater(result.summary["challenger_training_intervals_dropped"], 0)

    def test_the_run_is_exploratory_without_a_complete_quarter_hour_season(self) -> None:
        summary = self.result.summary
        self.assertTrue(summary["is_exploratory"])
        self.assertIn(
            "no_complete_meteorological_season_of_quarter_hour_test_days",
            summary["exploratory_causes"],
        )
        self.assertTrue(summary["result_label"].endswith(EXPLORATORY_LABEL_SUFFIX))
        self.assertTrue(
            summary["result_label"].startswith(FUNDAMENTALS_FORECAST_BENCHMARK_LABEL)
        )

    def test_the_summary_declares_the_three_standing_negatives(self) -> None:
        for key in ("is_probabilistic", "is_forecast", "is_investment_evidence"):
            self.assertIs(self.result.summary[key], False)


class FundamentalsBenchmarkRefusalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = _prices(seed=5)
        cls.features, cls.summary = _feature_set(cls.prices)

    def _run(self, features: pd.DataFrame, summary: dict[str, Any], **overrides: Any) -> None:
        generate_fundamentals_benchmark(
            self.prices, features, summary, _config(self.summary, **overrides)
        )

    def test_a_feature_frame_that_is_not_the_declared_feature_set_is_refused(self) -> None:
        mutated = self.features.copy()
        mutated.loc[0, "temperature_2m"] = 0.0
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "different feature sets"):
            self._run(mutated, self.summary)

    def test_a_benchmark_may_not_declare_another_feature_set(self) -> None:
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "the frame supplied is"):
            self._run(self.features, self.summary, feature_set_sha256="0" * 64)

    def test_a_summary_without_a_feature_set_digest_is_refused(self) -> None:
        summary = dict(self.summary)
        summary.pop("feature_set_sha256")
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "no feature_set_sha256"):
            self._run(self.features, summary)

    def test_a_cutoff_other_than_the_one_the_features_were_built_under_is_refused(self) -> None:
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "was built under"):
            self._run(self.features, self.summary, decision_lead_minutes=30)
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "was built under"):
            self._run(self.features, self.summary, decision_cutoff_schedule_id="another")

    def test_grades_other_than_the_join_s_own_are_refused(self) -> None:
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "built admitting"):
            self._run(self.features, self.summary, evidence_grades_admitted=(WITNESSED,))

    def test_the_quarantined_grade_requires_an_exploratory_feature_set(self) -> None:
        features, summary = _feature_set(
            self.prices,
            grade=ASSUMED,
            admitted=(*ADMISSIBLE_EVIDENCE_GRADES, ASSUMED),
            exploratory=True,
        )
        config = _config(
            summary,
            feature_set_sha256=summary["feature_set_sha256"],
            evidence_grades_admitted=tuple(summary["admitted_grades"]),
        )
        result = generate_fundamentals_benchmark(self.prices, features, summary, config)
        self.assertIn("quarantined_assumed_grade_admitted", result.summary["exploratory_causes"])

        pretending = dict(summary, is_exploratory=False)
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "not recorded"):
            generate_fundamentals_benchmark(self.prices, features, pretending, config)

    def test_a_feature_frame_from_other_prices_is_refused(self) -> None:
        other_prices = generate_synthetic_prices(START_DAY, date(2026, 3, 10), seed=5)
        features, summary = _feature_set(other_prices)
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "different delivery intervals"):
            generate_fundamentals_benchmark(
                self.prices, features, summary, _config(summary)
            )

    def test_price_regime_bands_are_required_and_strictly_ascending(self) -> None:
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "must be declared"):
            _config(self.summary, price_regime_bands=())
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "strictly ascending"):
            _config(self.summary, price_regime_bands=(50.0, 0.0))

    def test_an_unexplained_feature_column_is_refused(self) -> None:
        features = self.features.rename(columns={"temperature_2m": "mystery_variable"})
        summary = dict(self.summary, feature_columns=["mystery_variable"])
        summary["feature_set_sha256"] = self.summary["feature_set_sha256"]
        with self.assertRaisesRegex(FundamentalsBenchmarkError, "No recorded provenance"):
            generate_fundamentals_benchmark(
                self.prices,
                features,
                dict(summary, feature_set_sha256=_digest(features)),
                _config(summary, feature_set_sha256=_digest(features)),
            )


class WalkForwardFeatureGuardTests(unittest.TestCase):
    def test_an_absent_feature_value_never_reaches_a_fit(self) -> None:
        prices = generate_synthetic_prices(START_DAY, date(2026, 2, 20), seed=3)
        features, summary = _feature_set(prices)
        from greek_bess.forecast.ml import build_causal_feature_table

        table = build_causal_feature_table(prices).merge(
            features, on="delivery_start_utc", how="left"
        )
        table.loc[0, "temperature_2m"] = float("nan")
        target_days = sorted(
            day for day in table["market_day"].unique() if day >= date(2026, 2, 10)
        )
        with self.assertRaisesRegex(MLForecastInputError, "never imputed"):
            _walk_forward_predict(
                table,
                target_days,
                "ridge",
                _ml_config(validation_start_day=date(2026, 2, 8), test_start_day=date(2026, 2, 10)),
                feature_columns=("rolling_mean", "temperature_2m"),
                require_non_null=("temperature_2m",),
            )
        self.assertEqual(summary["complete_day_count"], summary["delivery_day_count"])

    def test_a_column_required_complete_must_be_a_model_input(self) -> None:
        prices = generate_synthetic_prices(START_DAY, date(2026, 2, 20), seed=3)
        from greek_bess.forecast.ml import build_causal_feature_table

        table = build_causal_feature_table(prices)
        with self.assertRaisesRegex(MLForecastInputError, "not model inputs"):
            _walk_forward_predict(
                table,
                [date(2026, 2, 10)],
                "ridge",
                _ml_config(validation_start_day=date(2026, 2, 8), test_start_day=date(2026, 2, 10)),
                feature_columns=("rolling_mean",),
                require_non_null=("slot_sin",),
            )


class SeasonGateTests(unittest.TestCase):
    def test_a_season_counts_only_when_every_one_of_its_days_is_present(self) -> None:
        spring = [date(2026, 3, 1) + timedelta(days=offset) for offset in range(92)]
        self.assertEqual(_complete_meteorological_seasons(spring), ["2026-MAM"])
        self.assertEqual(_complete_meteorological_seasons(spring[1:]), [])
        self.assertEqual(_complete_meteorological_seasons([]), [])

    def test_winter_is_named_for_the_year_its_january_falls_in(self) -> None:
        winter = [date(2025, 12, 1) + timedelta(days=offset) for offset in range(90)]
        self.assertEqual(_complete_meteorological_seasons(winter), ["2026-DJF"])


class FundamentalsProvenanceTests(unittest.TestCase):
    def test_every_declarable_variable_carries_a_provenance_sentence(self) -> None:
        self.assertEqual(
            sorted(FUNDAMENTALS_FEATURE_PROVENANCE), sorted(VARIABLE_UNITS)
        )
        for sentence in FUNDAMENTALS_FEATURE_PROVENANCE.values():
            self.assertIn("strictly before the declared cutoff", sentence)


class FundamentalsManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        prices = _prices(seed=9)
        features, join_summary = _feature_set(prices)
        cls.summary = generate_fundamentals_benchmark(
            prices, features, join_summary, _config(join_summary)
        ).summary

    def test_the_label_and_guaranteed_keys_survive_recording(self) -> None:
        manifest = build_run_manifest(
            self.summary,
            kind_id="fundamentals_forecast_benchmark",
            manifest_id="synthetic-fundamentals-benchmark",
            produced_by="tests",
            declared_inputs={"accepted_feature_set_sha256": self.summary["feature_set_sha256"]},
        )
        self.assertEqual(manifest.basis, "historical_forecast_backtest")
        self.assertEqual(manifest.result_label, self.summary["result_label"])
        for key in (
            "ablation_arms",
            "feature_set_sha256",
            "decision_cutoff_schedule_id",
            "decision_lead_minutes",
            "evidence_grades_admitted",
            "common_day_count",
            "excluded_days_by_cause",
            "metrics",
            "selected_challenger",
            "is_exploratory",
        ):
            self.assertIn(key, manifest.summary)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            write_run_manifest(path, manifest)
            self.assertEqual(read_run_manifest(path).summary["metrics"], self.summary["metrics"])

    def test_a_summary_missing_a_guaranteed_key_is_refused(self) -> None:
        summary = dict(self.summary)
        summary.pop("selected_challenger")
        with self.assertRaisesRegex(ReportContractError, "selected_challenger"):
            build_run_manifest(
                summary,
                kind_id="fundamentals_forecast_benchmark",
                manifest_id="incomplete",
                produced_by="tests",
            )

    def test_the_quarantined_grade_without_the_exploratory_label_is_refused(self) -> None:
        summary = dict(
            self.summary,
            evidence_grades_admitted=[*ADMISSIBLE_EVIDENCE_GRADES, ASSUMED],
            is_exploratory=False,
        )
        with self.assertRaisesRegex(ReportContractError, "quarantined 'assumed'"):
            build_run_manifest(
                summary,
                kind_id="fundamentals_forecast_benchmark",
                manifest_id="quarantined",
                produced_by="tests",
            )

    def test_a_hand_edited_manifest_is_refused_on_read(self) -> None:
        manifest = build_run_manifest(
            self.summary,
            kind_id="fundamentals_forecast_benchmark",
            manifest_id="synthetic-fundamentals-benchmark",
            produced_by="tests",
            declared_inputs={"accepted_feature_set_sha256": self.summary["feature_set_sha256"]},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            write_run_manifest(path, manifest)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["summary"]["is_forecast"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "is_forecast"):
                read_run_manifest(path)

            payload["summary"]["is_forecast"] = False
            payload["summary"]["evidence_grades_admitted"] = [ASSUMED]
            payload["summary"]["is_exploratory"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "quarantined 'assumed'"):
                read_run_manifest(path)


class BenchmarkCommandTests(unittest.TestCase):
    """The two commands must agree about the feature set across a CSV round trip."""

    def test_the_join_and_the_benchmark_agree_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices_path = root / "prices.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-02-25",
                        "--output",
                        str(prices_path),
                    ]
                )
            prices = read_canonical_csv(prices_path)
            features_path = root / "features.csv"
            write_point_in_time_csv(_point_in_time_rows(prices), features_path)
            cutoff_path = root / "cutoff.json"
            cutoff_path.write_text(
                json.dumps(
                    {
                        "schedule_id": "operator-cutoff",
                        "regimes": [
                            {
                                "effective_from_delivery_day": "2020-11-01",
                                "closure_day_offset": -1,
                                "closure_local_time": "12:00:00",
                                "closure_timezone": "Europe/Athens",
                                "reference": "Synthetic test declaration only.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            frame_path = root / "feature_frame.csv"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "build-point-in-time-features",
                            str(prices_path),
                            str(features_path),
                            "--decision-cutoff",
                            str(cutoff_path),
                            "--decision-lead-minutes",
                            "0",
                            "--admitted-grades",
                            *ADMISSIBLE_EVIDENCE_GRADES,
                            "--output",
                            str(frame_path),
                        ]
                    ),
                    0,
                )
            join_summary = json.loads(
                (root / "feature_frame.summary.json").read_text(encoding="utf-8")
            )
            output = root / "benchmark.csv"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "benchmark-fundamentals-forecast",
                            str(prices_path),
                            "--features",
                            str(frame_path),
                            "--feature-set-sha256",
                            join_summary["feature_set_sha256"],
                            "--decision-cutoff",
                            str(cutoff_path),
                            "--decision-lead-minutes",
                            "0",
                            "--admitted-grades",
                            *ADMISSIBLE_EVIDENCE_GRADES,
                            "--price-regime-bands",
                            "0",
                            "50",
                            "150",
                            "--validation-start-day",
                            "2026-02-05",
                            "--test-start-day",
                            "2026-02-15",
                            "--gradient-max-iter",
                            "25",
                            "--output",
                            str(output),
                        ]
                    ),
                    0,
                )
            summary = json.loads((root / "benchmark.summary.json").read_text(encoding="utf-8"))
            self.assertEqual(
                summary["feature_set_sha256"], join_summary["feature_set_sha256"]
            )
            self.assertEqual(summary["decision_cutoff_schedule_id"], "operator-cutoff")
            self.assertTrue(summary["is_exploratory"])
            forecasts = pd.read_csv(output)
            self.assertIn("ridge_fundamentals", forecasts.columns)
            self.assertTrue(bool(forecasts["is_common_day"].all()))

    def test_a_benchmark_naming_another_feature_set_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame_path = root / "feature_frame.csv"
            pd.DataFrame({"delivery_start_utc": [], "temperature_2m": []}).to_csv(
                frame_path, index=False
            )
            (root / "feature_frame.summary.json").write_text(
                json.dumps({"feature_set_sha256": "0" * 64}), encoding="utf-8"
            )
            cutoff_path = root / "cutoff.json"
            cutoff_path.write_text(
                json.dumps(
                    {
                        "schedule_id": "operator-cutoff",
                        "regimes": [
                            {
                                "effective_from_delivery_day": "2020-11-01",
                                "closure_day_offset": -1,
                                "closure_local_time": "12:00:00",
                                "closure_timezone": "Europe/Athens",
                                "reference": "Synthetic test declaration only.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                code = main(
                    [
                        "benchmark-fundamentals-forecast",
                        str(root / "prices.csv"),
                        "--features",
                        str(frame_path),
                        "--feature-set-sha256",
                        "1" * 64,
                        "--decision-cutoff",
                        str(cutoff_path),
                        "--decision-lead-minutes",
                        "0",
                        "--admitted-grades",
                        *ADMISSIBLE_EVIDENCE_GRADES,
                        "--price-regime-bands",
                        "0",
                        "--validation-start-day",
                        "2026-02-05",
                        "--test-start-day",
                        "2026-02-15",
                        "--output",
                        str(root / "benchmark.csv"),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("error:", errors.getvalue())


def _digest(frame: pd.DataFrame) -> str:
    from greek_bess.forecast.point_in_time_join import frame_digest

    return frame_digest(frame)


if __name__ == "__main__":
    unittest.main()
