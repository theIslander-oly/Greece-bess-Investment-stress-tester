from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.schema import concat_canonical
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    BootstrapInputError,
    detect_source_eras,
    generate_seasonal_bootstrap_paths,
    select_source_era,
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


def mixed_resolution_history() -> pd.DataFrame:
    """An hourly winter era followed contiguously by a quarter-hour spring era."""

    hourly = generate_synthetic_prices(
        date(2024, 12, 1), date(2025, 3, 1), resolution_minutes=60, negative_price_share=0
    )
    quarter = generate_synthetic_prices(
        date(2025, 3, 1), date(2025, 6, 1), resolution_minutes=15, negative_price_share=0
    )
    return concat_canonical([hourly, quarter])


class SourceEraPolicyTests(unittest.TestCase):
    def test_eras_are_maximal_contiguous_single_resolution_runs(self) -> None:
        eras = detect_source_eras(mixed_resolution_history())

        self.assertEqual([era.resolution_minutes for era in eras], [60, 15])
        self.assertEqual(eras[0].first_day, date(2024, 12, 1))
        self.assertEqual(eras[0].last_day, date(2025, 2, 28))
        self.assertEqual(eras[1].first_day, date(2025, 3, 1))
        self.assertEqual(eras[1].last_day, date(2025, 5, 31))
        self.assertEqual(eras[0].market_day_count, 90)

    def test_a_gap_in_market_days_ends_an_era(self) -> None:
        first = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 2, 1), negative_price_share=0
        )
        second = generate_synthetic_prices(
            date(2025, 2, 2), date(2025, 3, 1), negative_price_share=0
        )
        eras = detect_source_eras(concat_canonical([first, second]))

        self.assertEqual(len(eras), 2)
        self.assertTrue(all(era.resolution_minutes == 60 for era in eras))
        self.assertEqual(eras[0].last_day, date(2025, 1, 31))
        self.assertEqual(eras[1].first_day, date(2025, 2, 2))

    def test_a_mixed_history_refuses_to_choose_an_era_implicitly(self) -> None:
        config = BootstrapConfig(
            start_day=date(2026, 1, 1), end_day=date(2026, 1, 8), block_days=3
        )
        with self.assertRaises(BootstrapInputError) as raised:
            generate_seasonal_bootstrap_paths(mixed_resolution_history(), config)

        message = str(raised.exception)
        self.assertIn("must", message)
        self.assertIn("source_resolution_minutes", message)
        self.assertIn("60min", message)
        self.assertIn("15min", message)

    def test_a_declared_era_bounds_every_sampled_block(self) -> None:
        history = mixed_resolution_history()
        config = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 15),
            block_days=3,
            random_seed=5,
            source_resolution_minutes=60,
        )
        result = generate_seasonal_bootstrap_paths(history, config)

        self.assertEqual(result.summary["resolution_minutes"], 60)
        self.assertEqual(result.summary["available_source_era_count"], 2)
        self.assertTrue(result.summary["source_era_declared"])
        self.assertEqual(
            result.summary["selected_source_era"],
            {
                "resolution_minutes": 60,
                "first_day": "2024-12-01",
                "last_day": "2025-02-28",
                "market_day_count": 90,
            },
        )
        self.assertEqual(result.summary["sampled_source_market_day_count"], 90)
        sources = pd.to_datetime(result.provenance["source_start_day"]).dt.date
        ends = pd.to_datetime(result.provenance["source_end_day"]).dt.date
        self.assertTrue((sources >= date(2024, 12, 1)).all())
        self.assertTrue((ends <= date(2025, 2, 28)).all())
        self.assertTrue(
            (result.provenance["source_era_resolution_minutes"] == 60).all()
        )
        self.assertTrue((result.paths["duration_hours"] == 1.0).all())

    def test_declaring_the_quarter_hour_era_changes_the_sampled_regime(self) -> None:
        history = mixed_resolution_history()
        config = BootstrapConfig(
            start_day=date(2026, 4, 1),
            end_day=date(2026, 4, 8),
            block_days=7,
            random_seed=5,
            source_resolution_minutes=15,
        )
        result = generate_seasonal_bootstrap_paths(history, config)

        self.assertEqual(result.summary["resolution_minutes"], 15)
        self.assertTrue((result.paths["duration_hours"] == 0.25).all())
        self.assertEqual(result.summary["interval_count_per_path"], 7 * 96)
        sources = pd.to_datetime(result.provenance["source_start_day"]).dt.date
        self.assertTrue((sources >= date(2025, 3, 1)).all())

    def test_an_ambiguous_declaration_must_be_narrowed(self) -> None:
        first = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 2, 1), negative_price_share=0
        )
        second = generate_synthetic_prices(
            date(2025, 2, 2), date(2025, 3, 1), negative_price_share=0
        )
        eras = detect_source_eras(concat_canonical([first, second]))
        ambiguous = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            source_resolution_minutes=60,
        )
        with self.assertRaisesRegex(BootstrapInputError, "more than one source era"):
            select_source_era(eras, ambiguous)

        narrowed = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            source_resolution_minutes=60,
            source_start_day=date(2025, 2, 2),
        )
        self.assertEqual(select_source_era(eras, narrowed).first_day, date(2025, 2, 2))

    def test_the_generator_still_refuses_a_non_contiguous_history(self) -> None:
        first = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 2, 1), negative_price_share=0
        )
        second = generate_synthetic_prices(
            date(2025, 2, 2), date(2025, 3, 1), negative_price_share=0
        )
        config = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            source_resolution_minutes=60,
            source_start_day=date(2025, 2, 2),
        )
        with self.assertRaisesRegex(BootstrapInputError, "non_contiguous_horizon"):
            generate_seasonal_bootstrap_paths(concat_canonical([first, second]), config)

    def test_the_source_window_narrows_within_the_selected_era(self) -> None:
        history = mixed_resolution_history()
        config = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            block_days=7,
            random_seed=5,
            source_resolution_minutes=60,
            source_start_day=date(2025, 1, 1),
            source_end_day=date(2025, 2, 1),
        )
        result = generate_seasonal_bootstrap_paths(history, config)

        self.assertEqual(result.summary["sampled_source_market_day_count"], 31)
        first_days = result.provenance["source_era_first_day"].unique().tolist()
        last_days = result.provenance["source_era_last_day"].unique().tolist()
        self.assertEqual(first_days, ["2025-01-01"])
        self.assertEqual(last_days, ["2025-01-31"])
        sources = pd.to_datetime(result.provenance["source_start_day"]).dt.date
        self.assertTrue((sources >= date(2025, 1, 1)).all())

    def test_a_single_era_history_needs_no_declaration(self) -> None:
        history = generate_synthetic_prices(
            date(2024, 12, 1), date(2025, 3, 1), negative_price_share=0
        )
        config = BootstrapConfig(
            start_day=date(2026, 1, 1), end_day=date(2026, 1, 8), block_days=7
        )
        result = generate_seasonal_bootstrap_paths(history, config)

        self.assertEqual(result.summary["available_source_era_count"], 1)
        self.assertFalse(result.summary["source_era_declared"])
        self.assertEqual(result.summary["selected_source_era"]["resolution_minutes"], 60)

    def test_a_declared_era_absent_from_the_history_is_refused(self) -> None:
        history = generate_synthetic_prices(
            date(2024, 12, 1), date(2025, 3, 1), negative_price_share=0
        )
        config = BootstrapConfig(
            start_day=date(2026, 1, 1),
            end_day=date(2026, 1, 8),
            source_resolution_minutes=15,
        )
        with self.assertRaisesRegex(BootstrapInputError, "No source era matches"):
            generate_seasonal_bootstrap_paths(history, config)

    def test_candidate_scarcity_is_reported(self) -> None:
        history = generate_synthetic_prices(
            date(2024, 12, 1), date(2025, 3, 1), negative_price_share=0
        )
        config = BootstrapConfig(
            start_day=date(2026, 1, 1), end_day=date(2026, 1, 8), block_days=7, random_seed=5
        )
        result = generate_seasonal_bootstrap_paths(history, config)

        self.assertGreaterEqual(result.summary["minimum_block_candidate_count"], 1)
        self.assertEqual(
            result.summary["minimum_block_candidate_count"],
            int(result.provenance["candidate_count"].min()),
        )

    def test_a_market_day_mixing_resolutions_is_refused(self) -> None:
        hourly = generate_synthetic_prices(
            date(2025, 1, 1), date(2025, 1, 3), negative_price_share=0
        )
        quarter = generate_synthetic_prices(
            date(2025, 1, 2), date(2025, 1, 3), resolution_minutes=15, negative_price_share=0
        )
        broken = pd.concat([hourly, quarter], ignore_index=True)
        with self.assertRaisesRegex(BootstrapInputError, "mixes interval resolutions"):
            detect_source_eras(broken)

    def test_source_window_and_resolution_values_are_validated(self) -> None:
        with self.assertRaisesRegex(BootstrapInputError, "source_resolution_minutes"):
            BootstrapConfig(
                start_day=date(2026, 1, 1),
                end_day=date(2026, 1, 8),
                source_resolution_minutes=30,
            )
        with self.assertRaisesRegex(BootstrapInputError, "source_end_day"):
            BootstrapConfig(
                start_day=date(2026, 1, 1),
                end_day=date(2026, 1, 8),
                source_start_day=date(2025, 3, 1),
                source_end_day=date(2025, 3, 1),
            )

    def test_source_era_fields_round_trip_through_config_json(self) -> None:
        config = BootstrapConfig.from_dict(
            {
                "start_day": "2026-01-01",
                "end_day": "2026-01-08",
                "source_resolution_minutes": 15,
                "source_start_day": "2025-10-01",
                "source_end_day": "2026-08-26",
            }
        )
        self.assertEqual(config.source_resolution_minutes, 15)
        self.assertEqual(config.source_start_day, date(2025, 10, 1))
        payload = config.to_dict()
        self.assertEqual(payload["source_start_day"], "2025-10-01")
        self.assertEqual(payload["source_end_day"], "2026-08-26")
        self.assertEqual(BootstrapConfig.from_dict(payload), config)


if __name__ == "__main__":
    unittest.main()
