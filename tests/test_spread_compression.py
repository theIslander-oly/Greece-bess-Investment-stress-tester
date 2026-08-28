from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    SpreadCompressionConfig,
    SpreadCompressionInputError,
    apply_spread_compression,
    generate_seasonal_bootstrap_paths,
)


def _paths() -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 4), seed=4, negative_price_share=0
    )
    return generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(date(2026, 1, 1), date(2026, 1, 3), random_seed=1),
    ).paths


def _daily_ranges(paths: pd.DataFrame) -> pd.Series:
    day = paths["delivery_start_market"].dt.date
    grouped = paths["price_eur_per_mwh"].astype(float).groupby([paths["path_id"], day])
    return grouped.max() - grouped.min()


class SpreadCompressionTests(unittest.TestCase):
    def test_compression_is_reproducible_and_interval_auditable(self) -> None:
        paths = _paths()
        config = SpreadCompressionConfig(0.5, "daily_mean", "half_spread")

        first = apply_spread_compression(paths, config)
        second = apply_spread_compression(paths, config)

        pd.testing.assert_frame_equal(first.paths, second.paths)
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        self.assertEqual(first.paths["path_id"].tolist(), paths["path_id"].tolist())
        self.assertTrue(first.paths["delivery_start_utc"].equals(paths["delivery_start_utc"]))
        self.assertEqual(len(first.provenance), len(paths))
        self.assertEqual(
            first.provenance["original_price_eur_per_mwh"].tolist(),
            paths["price_eur_per_mwh"].astype(float).tolist(),
        )
        self.assertIn("not forecasts", first.summary["result_label"])

    def test_factor_one_is_the_identity_and_factor_zero_flattens_each_day(self) -> None:
        paths = _paths()

        identity = apply_spread_compression(
            paths, SpreadCompressionConfig(1.0, "daily_mean", "identity")
        )
        flattened = apply_spread_compression(
            paths, SpreadCompressionConfig(0.0, "daily_mean", "flat")
        )

        pd.testing.assert_series_equal(
            identity.paths["price_eur_per_mwh"].astype(float),
            paths["price_eur_per_mwh"].astype(float),
            check_names=False,
        )
        self.assertAlmostEqual(float(_daily_ranges(flattened.paths).max()), 0.0, places=9)
        self.assertGreater(float(_daily_ranges(paths).max()), 0.0)

    def test_compression_shrinks_every_daily_range_toward_zero(self) -> None:
        paths = _paths()
        before = _daily_ranges(paths)

        after = _daily_ranges(
            apply_spread_compression(
                paths, SpreadCompressionConfig(0.25, "daily_mean", "quarter")
            ).paths
        )

        pd.testing.assert_series_equal(after, before * 0.25, check_names=False)

    def test_daily_mean_basis_preserves_each_daily_mean(self) -> None:
        paths = _paths()
        config = SpreadCompressionConfig(0.3, "daily_mean", "third")

        result = apply_spread_compression(paths, config)

        day = paths["delivery_start_market"].dt.date
        before = paths["price_eur_per_mwh"].astype(float).groupby([paths["path_id"], day]).mean()
        after = (
            result.paths["price_eur_per_mwh"]
            .astype(float)
            .groupby([result.paths["path_id"], day])
            .mean()
        )
        pd.testing.assert_series_equal(after, before, check_names=False)
        self.assertAlmostEqual(
            float(result.summary["max_absolute_daily_mean_shift_eur_per_mwh"]), 0.0, places=9
        )

    def test_negative_results_are_preserved_and_sign_changes_are_counted(self) -> None:
        paths = _paths()
        # Force one market day to straddle zero so compression must pull a price across it.
        first_day = (
            paths["delivery_start_market"].dt.date == paths.loc[0, "delivery_start_market"].date()
        )
        indices = paths.index[first_day & (paths["path_id"] == paths.loc[0, "path_id"])]
        paths.loc[indices[0], "price_eur_per_mwh"] = -40.0
        paths.loc[indices[1], "price_eur_per_mwh"] = 80.0

        result = apply_spread_compression(
            paths, SpreadCompressionConfig(0.1, "daily_mean", "strong")
        )

        compressed = result.paths.loc[indices[0], "price_eur_per_mwh"]
        reference = result.provenance.loc[indices[0], "reference_level_eur_per_mwh"]
        # Never clipped or floored: the value moves toward the reference, not toward zero.
        self.assertAlmostEqual(compressed, reference + 0.1 * (-40.0 - reference), places=9)
        self.assertGreaterEqual(int(result.summary["sign_change_interval_count"]), 1)
        self.assertEqual(int(result.summary["negative_interval_count_before"]), 1)

    def test_median_basis_is_selectable_and_recorded(self) -> None:
        paths = _paths()

        result = apply_spread_compression(
            paths, SpreadCompressionConfig(0.5, "daily_median", "median_half")
        )

        self.assertEqual(result.summary["configuration"]["reference_basis"], "daily_median")
        self.assertTrue((result.provenance["reference_basis"] == "daily_median").all())

    def test_output_carries_transformation_provenance_and_labels(self) -> None:
        paths = _paths()

        result = apply_spread_compression(
            paths, SpreadCompressionConfig(0.5, "daily_mean", "half_spread")
        )

        self.assertTrue(
            result.paths["source_version"]
            .astype(str)
            .str.contains("spread_compression:half_spread")
            .all()
        )
        self.assertTrue(
            result.paths["quality_flags"].map(lambda flags: "spread_compression" in flags).all()
        )
        self.assertTrue(
            result.paths["quality_flags"].map(lambda flags: "synthetic_not_forecast" in flags).all()
        )

    def test_rejects_missing_duplicate_and_incomplete_paths(self) -> None:
        paths = _paths()
        config = SpreadCompressionConfig(0.5, "daily_mean", "half")

        missing = paths.copy()
        missing.loc[0, "price_eur_per_mwh"] = float("nan")
        duplicate = pd.concat([paths, paths.iloc[[0]]], ignore_index=True)
        incomplete = paths.iloc[1:].copy()

        for invalid in (missing, duplicate, incomplete):
            with self.assertRaises(SpreadCompressionInputError):
                apply_spread_compression(invalid, config)

        with self.assertRaises(SpreadCompressionInputError):
            apply_spread_compression(paths.drop(columns=["path_id"]), config)

    def test_configuration_requires_a_declared_basis_and_bounded_factor(self) -> None:
        for invalid in (-0.1, 1.5, float("nan"), float("inf"), True, "0.5"):
            with self.assertRaises(SpreadCompressionInputError):
                SpreadCompressionConfig(invalid, "daily_mean", "id")

        with self.assertRaises(SpreadCompressionInputError):
            SpreadCompressionConfig(0.5, "daily_volume_weighted", "id")
        with self.assertRaises(SpreadCompressionInputError):
            SpreadCompressionConfig(0.5, "daily_mean", "  ")

    def test_config_from_dict_is_strict(self) -> None:
        payload = {
            "compression_factor": 0.4,
            "reference_basis": "daily_mean",
            "transformation_id": "scenario_a",
        }

        parsed = SpreadCompressionConfig.from_dict(payload)
        self.assertEqual(parsed.to_dict(), payload)

        with self.assertRaises(SpreadCompressionInputError):
            SpreadCompressionConfig.from_dict({**payload, "unexpected": 1})
        with self.assertRaises(SpreadCompressionInputError):
            SpreadCompressionConfig.from_dict({"compression_factor": 0.4})
        with self.assertRaises(SpreadCompressionInputError):
            SpreadCompressionConfig.from_dict([payload])

    def test_summary_reports_the_spread_evidence(self) -> None:
        paths = _paths()

        result = apply_spread_compression(
            paths, SpreadCompressionConfig(0.5, "daily_mean", "half_spread")
        )

        summary = result.summary
        self.assertEqual(int(summary["interval_count"]), len(paths))
        self.assertEqual(int(summary["provenance_row_count"]), len(paths))
        self.assertAlmostEqual(
            float(summary["mean_daily_range_after_eur_per_mwh"]),
            float(summary["mean_daily_range_before_eur_per_mwh"]) * 0.5,
            places=9,
        )
        self.assertIn("no default", summary["policy"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
