from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    PriceLevelShockConfig,
    PriceLevelShockInputError,
    apply_price_level_shock,
    generate_seasonal_bootstrap_paths,
)


def _paths() -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 4), seed=4, negative_price_share=0
    )
    history.loc[0, "price_eur_per_mwh"] = 5.0
    history.loc[1, "price_eur_per_mwh"] = 0.0
    paths = generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(date(2026, 1, 1), date(2026, 1, 2), random_seed=1),
    ).paths
    paths.loc[0, "price_eur_per_mwh"] = 5.0
    paths.loc[1, "price_eur_per_mwh"] = 0.0
    return paths


class PriceLevelShockTests(unittest.TestCase):
    def test_additive_shock_is_reproducible_and_interval_auditable(self) -> None:
        paths = _paths()
        config = PriceLevelShockConfig(-5.0, "down_5_eur_mwh")

        first = apply_price_level_shock(paths, config)
        second = apply_price_level_shock(paths, config)

        pd.testing.assert_frame_equal(first.paths, second.paths)
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        self.assertEqual(first.paths["path_id"].tolist(), paths["path_id"].tolist())
        self.assertTrue(first.paths["delivery_start_utc"].equals(paths["delivery_start_utc"]))
        self.assertEqual(first.paths.loc[0, "price_eur_per_mwh"], 0.0)
        self.assertEqual(first.paths.loc[1, "price_eur_per_mwh"], -5.0)
        self.assertEqual(
            first.provenance["original_price_eur_per_mwh"].tolist(),
            paths["price_eur_per_mwh"].tolist(),
        )
        self.assertEqual(len(first.provenance), len(paths))
        self.assertIn("not forecasts", first.summary["result_label"])

    def test_rejects_missing_duplicate_and_incomplete_paths(self) -> None:
        paths = _paths()
        config = PriceLevelShockConfig(10.0, "up_10")

        missing = paths.copy()
        missing.loc[0, "price_eur_per_mwh"] = float("nan")
        duplicate = pd.concat([paths, paths.iloc[[0]]], ignore_index=True)
        incomplete = paths.drop(index=2).reset_index(drop=True)

        with self.assertRaisesRegex(PriceLevelShockInputError, "missing_price"):
            apply_price_level_shock(missing, config)
        with self.assertRaisesRegex(PriceLevelShockInputError, "Duplicate"):
            apply_price_level_shock(duplicate, config)
        with self.assertRaisesRegex(PriceLevelShockInputError, "non_contiguous_horizon"):
            apply_price_level_shock(incomplete, config)

    def test_config_schema_is_strict_and_finite(self) -> None:
        with self.assertRaisesRegex(PriceLevelShockInputError, "Unknown"):
            PriceLevelShockConfig.from_dict(
                {"shift_eur_per_mwh": 1, "transformation_id": "one", "extra": 2}
            )
        with self.assertRaisesRegex(PriceLevelShockInputError, "Missing"):
            PriceLevelShockConfig.from_dict({"shift_eur_per_mwh": 1})
        with self.assertRaisesRegex(PriceLevelShockInputError, "finite"):
            PriceLevelShockConfig(float("inf"), "invalid")
        with self.assertRaisesRegex(PriceLevelShockInputError, "non-empty"):
            PriceLevelShockConfig(1.0, "")


if __name__ == "__main__":
    unittest.main()
