from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.forecast import calculate_forecast_metrics, generate_naive_forecasts


def repeating_prices(start: date, end: date, *, resolution_minutes: int = 60):
    frame = generate_synthetic_prices(
        start,
        end,
        resolution_minutes=resolution_minutes,
        negative_price_share=0,
    )
    slot = (
        frame["delivery_start_market"].dt.hour * 60
        + frame["delivery_start_market"].dt.minute
    )
    frame["price_eur_per_mwh"] = slot.map(lambda value: 10.0 if value < 720 else 100.0)
    return frame


class NaiveForecastTests(unittest.TestCase):
    def test_coarser_history_covers_the_hourly_to_quarter_hour_transition(self) -> None:
        hourly = repeating_prices(
            date(2025, 9, 1), date(2025, 10, 1), resolution_minutes=60
        )
        quarter_hour = repeating_prices(
            date(2025, 10, 1), date(2025, 10, 3), resolution_minutes=15
        )
        frame = pd.concat([hourly, quarter_hour], ignore_index=True)

        result = generate_naive_forecasts(
            frame,
            methods=[
                "daily_persistence",
                "weekly_persistence",
                "rolling_mean",
                "ensemble",
            ],
            rolling_window_days=28,
            start_day=date(2025, 10, 1),
        )

        first_quarter_hour_day = result.forecasts.loc[
            result.forecasts["market_day"].eq(date(2025, 10, 1))
        ]
        self.assertEqual(len(first_quarter_hour_day), 96)
        for method in result.methods:
            with self.subTest(method=method):
                self.assertFalse(first_quarter_hour_day[method].isna().any())
        quarter_past_three = first_quarter_hour_day.loc[
            first_quarter_hour_day["market_slot_minutes"].eq(3 * 60 + 15)
        ].iloc[0]
        # The 03:00 hourly observation contains the 03:15 quarter-hour. Repeating prices
        # make every causal method's expected aligned value transparent.
        for method in result.methods:
            with self.subTest(method=method):
                self.assertEqual(float(quarter_past_three[method]), 10.0)

    def test_finer_history_is_not_silently_aggregated_for_an_hourly_target(self) -> None:
        quarter_hour = repeating_prices(
            date(2025, 9, 30), date(2025, 10, 1), resolution_minutes=15
        )
        hourly = repeating_prices(
            date(2025, 10, 1), date(2025, 10, 2), resolution_minutes=60
        )
        frame = pd.concat([quarter_hour, hourly], ignore_index=True)

        result = generate_naive_forecasts(
            frame,
            methods=["daily_persistence", "rolling_mean"],
            start_day=date(2025, 10, 1),
        )

        self.assertTrue(result.forecasts["daily_persistence"].isna().all())
        self.assertTrue(result.forecasts["rolling_mean"].isna().all())

    def test_daily_persistence_is_exact_for_repeating_profile(self) -> None:
        frame = repeating_prices(date(2026, 1, 1), date(2026, 1, 5))
        result = generate_naive_forecasts(frame, methods=["daily_persistence"])
        available = result.forecasts.dropna(subset=["daily_persistence"])
        self.assertEqual(len(available), 72)
        self.assertTrue(
            available["daily_persistence"].eq(
                available["actual_price_eur_per_mwh"]
            ).all()
        )
        self.assertAlmostEqual(
            result.metrics["daily_persistence"]["mae_eur_per_mwh"], 0.0
        )

    def test_future_mutation_cannot_change_earlier_forecasts(self) -> None:
        frame = generate_synthetic_prices(
            date(2026, 1, 1), date(2026, 1, 12), negative_price_share=0
        )
        original = generate_naive_forecasts(frame).forecasts
        changed = frame.copy()
        last_day = changed["delivery_start_market"].dt.date.eq(date(2026, 1, 11))
        changed.loc[last_day, "price_eur_per_mwh"] = 10000.0
        mutated = generate_naive_forecasts(changed).forecasts
        earlier = original["market_day"].map(lambda day: day < date(2026, 1, 11))
        pd.testing.assert_frame_equal(
            original.loc[earlier].reset_index(drop=True),
            mutated.loc[earlier].reset_index(drop=True),
        )

    def test_weekly_persistence_remains_complete_across_spring_dst(self) -> None:
        frame = repeating_prices(date(2026, 3, 20), date(2026, 4, 5))
        result = generate_naive_forecasts(
            frame,
            methods=["weekly_persistence"],
            start_day=date(2026, 3, 27),
        )
        self.assertFalse(result.forecasts["weekly_persistence"].isna().any())
        dst_day = result.forecasts["market_day"].eq(date(2026, 3, 29))
        self.assertEqual(int(dst_day.sum()), 23)

    def test_metrics_support_zero_and_negative_prices(self) -> None:
        table = pd.DataFrame(
            {
                "actual_price_eur_per_mwh": [0.0, -10.0, 10.0],
                "daily_persistence": [1.0, -5.0, -1.0],
            }
        )
        metrics = calculate_forecast_metrics(
            table, methods=["daily_persistence"]
        )["daily_persistence"]
        self.assertEqual(metrics["observation_count"], 3)
        self.assertAlmostEqual(metrics["negative_price_precision"], 0.5)
        self.assertAlmostEqual(metrics["negative_price_recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
