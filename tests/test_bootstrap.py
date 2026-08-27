from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    BootstrapInputError,
    generate_seasonal_bootstrap_paths,
)


class SeasonalBootstrapTests(unittest.TestCase):
    def test_seed_is_reproducible_and_provenance_audits_every_block(self) -> None:
        history = generate_synthetic_prices(
            date(2024, 12, 1), date(2025, 2, 28), seed=11, negative_price_share=0
        )
        history.loc[0, "price_eur_per_mwh"] = 0.0
        history.loc[24, "price_eur_per_mwh"] = -7.5
        config = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            path_count=2,
            block_days=3,
            random_seed=918,
        )

        first = generate_seasonal_bootstrap_paths(history, config)
        second = generate_seasonal_bootstrap_paths(history, config)

        pd.testing.assert_frame_equal(first.paths, second.paths)
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        self.assertEqual(len(first.provenance), 6)
        self.assertEqual(first.paths.groupby("path_id").size().tolist(), [168, 168])
        self.assertTrue(first.paths["delivery_start_utc"].dt.tz is not None)
        self.assertTrue(first.paths["delivery_start_market"].dt.tz is not None)
        self.assertIn("not forecasts", first.summary["result_label"])

    def test_zero_and_negative_sampled_prices_are_copied_exactly(self) -> None:
        history = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 1, 2), seed=3, negative_price_share=0
        )
        history.loc[0, "price_eur_per_mwh"] = 0.0
        history.loc[1, "price_eur_per_mwh"] = -12.25
        result = generate_seasonal_bootstrap_paths(
            history,
            BootstrapConfig(date(2026, 1, 1), date(2026, 1, 2), random_seed=1),
        )

        self.assertEqual(result.paths.loc[0, "price_eur_per_mwh"], 0.0)
        self.assertEqual(result.paths.loc[1, "price_eur_per_mwh"], -12.25)

    def test_dst_market_day_structure_is_preserved(self) -> None:
        spring_history = generate_synthetic_prices(
            date(2025, 3, 30),
            date(2025, 3, 31),
            resolution_minutes=15,
            negative_price_share=0,
        )
        autumn_history = generate_synthetic_prices(
            date(2025, 10, 26),
            date(2025, 10, 27),
            resolution_minutes=15,
            negative_price_share=0,
        )

        spring = generate_seasonal_bootstrap_paths(
            spring_history,
            BootstrapConfig(date(2026, 3, 29), date(2026, 3, 30)),
        )
        autumn = generate_seasonal_bootstrap_paths(
            autumn_history,
            BootstrapConfig(date(2026, 10, 25), date(2026, 10, 26)),
        )

        self.assertEqual(len(spring.paths), 92)
        self.assertEqual(len(autumn.paths), 100)
        self.assertFalse(spring.paths["delivery_start_utc"].duplicated().any())
        self.assertFalse(autumn.paths["delivery_start_utc"].duplicated().any())

    def test_missing_price_and_missing_interval_fail_without_filling(self) -> None:
        history = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 1, 3), negative_price_share=0
        )
        missing_price = history.copy()
        missing_price.loc[2, "price_eur_per_mwh"] = float("nan")
        missing_interval = history.drop(index=2).reset_index(drop=True)
        config = BootstrapConfig(date(2026, 1, 1), date(2026, 1, 2))

        with self.assertRaisesRegex(BootstrapInputError, "missing_price"):
            generate_seasonal_bootstrap_paths(missing_price, config)
        with self.assertRaisesRegex(BootstrapInputError, "non_contiguous_horizon"):
            generate_seasonal_bootstrap_paths(missing_interval, config)

    def test_config_rejects_unknown_fields_and_invalid_ranges(self) -> None:
        with self.assertRaisesRegex(BootstrapInputError, "Unknown"):
            BootstrapConfig.from_dict(
                {"start_day": "2026-01-01", "end_day": "2026-01-02", "extra": 1}
            )
        with self.assertRaises(BootstrapInputError):
            BootstrapConfig(date(2026, 1, 2), date(2026, 1, 1))
        with self.assertRaisesRegex(BootstrapInputError, "path_count must be an integer"):
            BootstrapConfig(date(2026, 1, 1), date(2026, 1, 2), path_count=1.5)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
