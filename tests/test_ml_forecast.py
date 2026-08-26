from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.forecast import (
    FEATURE_COLUMNS,
    MLForecastConfig,
    MLForecastInputError,
    generate_ml_forecasts,
)


class MLForecastTests(unittest.TestCase):
    def test_time_splits_refits_and_metrics_are_auditable(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 1, 1), date(2026, 3, 1), seed=17
        )
        config = MLForecastConfig(
            validation_start_day=date(2026, 2, 5),
            test_start_day=date(2026, 2, 15),
            min_training_days=28,
            refit_frequency_days=5,
            gradient_max_iter=25,
        )
        result = generate_ml_forecasts(prices, config)

        self.assertEqual(set(result.forecasts["split"]), {"validation", "test"})
        self.assertFalse(result.forecasts[list(config.models)].isna().any().any())
        self.assertIn(result.summary["selected_model"], config.models)
        self.assertEqual(result.summary["feature_columns"], list(FEATURE_COLUMNS))
        self.assertEqual(
            result.summary["model_selection_policy"],
            "Lowest validation RMSE; test metrics are not used for selection",
        )
        for model in config.models:
            self.assertEqual(
                result.summary["metrics"]["test"][model]["coverage_fraction"], 1.0
            )
            for event in result.summary["refit_logs"][model]:
                self.assertLess(
                    event["training_end_day"], event["forecast_start_day"]
                )
            self.assertIn(
                str(config.test_start_day),
                {
                    event["forecast_start_day"]
                    for event in result.summary["refit_logs"][model]
                },
            )

    def test_future_price_mutation_cannot_change_earlier_ml_predictions(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 1, 1), date(2026, 2, 25), seed=23
        )
        config = MLForecastConfig(
            validation_start_day=date(2026, 2, 1),
            test_start_day=date(2026, 2, 12),
            min_training_days=28,
            refit_frequency_days=4,
            gradient_max_iter=20,
        )
        original = generate_ml_forecasts(prices, config).forecasts
        changed = prices.copy()
        mutation_day = date(2026, 2, 21)
        future = changed["delivery_start_market"].dt.date.map(
            lambda day: day >= mutation_day
        )
        changed.loc[future, "price_eur_per_mwh"] = 10000.0
        mutated = generate_ml_forecasts(changed, config).forecasts
        earlier = original["market_day"].map(lambda day: day < mutation_day)
        columns = [
            "delivery_start_utc",
            "daily_persistence",
            "weekly_persistence",
            "rolling_mean",
            "ensemble",
            *config.models,
        ]
        pd.testing.assert_frame_equal(
            original.loc[earlier, columns].reset_index(drop=True),
            mutated.loc[earlier, columns].reset_index(drop=True),
        )

    def test_quarter_hour_ml_forecasts_remain_complete_across_spring_dst(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 3, 1),
            date(2026, 4, 3),
            resolution_minutes=15,
            seed=29,
        )
        result = generate_ml_forecasts(
            prices,
            MLForecastConfig(
                validation_start_day=date(2026, 3, 22),
                test_start_day=date(2026, 3, 28),
                models=("ridge",),
                min_training_days=20,
                refit_frequency_days=3,
            ),
        )
        test = result.forecasts.loc[result.forecasts["split"].eq("test")]
        counts = test.groupby("market_day").size().to_dict()
        self.assertEqual(counts[date(2026, 3, 29)], 92)
        self.assertEqual(counts[date(2026, 3, 30)], 96)
        self.assertFalse(test["ridge"].isna().any())
        self.assertLess(
            result.summary["metrics"]["test"]["daily_persistence"][
                "coverage_fraction"
            ],
            1.0,
        )
        self.assertEqual(
            result.summary["metrics"]["test"]["ridge"]["coverage_fraction"],
            1.0,
        )

    def test_invalid_split_and_insufficient_history_are_rejected(self) -> None:
        with self.assertRaisesRegex(MLForecastInputError, "earlier"):
            MLForecastConfig(
                validation_start_day=date(2026, 2, 1),
                test_start_day=date(2026, 2, 1),
            )
        prices = generate_synthetic_prices(
            date(2026, 1, 1), date(2026, 1, 20), seed=31
        )
        with self.assertRaisesRegex(MLForecastInputError, "training days"):
            generate_ml_forecasts(
                prices,
                MLForecastConfig(
                    validation_start_day=date(2026, 1, 10),
                    test_start_day=date(2026, 1, 15),
                    models=("ridge",),
                    min_training_days=12,
                ),
            )


if __name__ == "__main__":
    unittest.main()
