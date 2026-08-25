from __future__ import annotations

import unittest
from datetime import date

from greek_bess.backtest import (
    ForecastDispatchInputError,
    backtest_forecast_dispatch,
)
from greek_bess.dispatch import BatteryDispatchConfig

from test_forecast import repeating_prices


def battery(**overrides) -> BatteryDispatchConfig:
    values = {
        "charge_power_mw": 1.0,
        "discharge_power_mw": 1.0,
        "energy_capacity_mwh": 1.0,
        "soc_min_fraction": 0.0,
        "soc_max_fraction": 1.0,
        "initial_soc_fraction": 0.0,
        "terminal_soc_fraction": 0.0,
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
    }
    values.update(overrides)
    return BatteryDispatchConfig(**values)


class ForecastDispatchBacktestTests(unittest.TestCase):
    def test_exact_daily_forecast_captures_daily_perfect_foresight_value(self) -> None:
        prices = repeating_prices(date(2026, 1, 1), date(2026, 1, 5))
        result = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        )
        self.assertEqual(result.summary["backtested_day_count"], 3)
        self.assertAlmostEqual(result.summary["realized_margin_eur"], 270.0)
        self.assertAlmostEqual(result.summary["perfect_foresight_margin_eur"], 270.0)
        self.assertAlmostEqual(result.summary["perfect_foresight_capture_ratio"], 1.0)
        self.assertAlmostEqual(result.summary["equivalent_full_cycles"], 3.0)
        simultaneous = (
            (result.interval_schedule["charge_mw"] > 1e-8)
            & (result.interval_schedule["discharge_mw"] > 1e-8)
        )
        self.assertFalse(simultaneous.any())

    def test_daily_backtest_rejects_different_terminal_soc(self) -> None:
        prices = repeating_prices(date(2026, 1, 1), date(2026, 1, 4))
        with self.assertRaisesRegex(ForecastDispatchInputError, "terminal_soc"):
            backtest_forecast_dispatch(
                prices,
                battery(initial_soc_fraction=0.0, terminal_soc_fraction=1.0),
            )

    def test_wrong_forecast_is_settled_at_realized_prices(self) -> None:
        prices = repeating_prices(date(2026, 1, 1), date(2026, 1, 3))
        first_day = prices["delivery_start_market"].dt.date.eq(date(2026, 1, 1))
        second_day = prices["delivery_start_market"].dt.date.eq(date(2026, 1, 2))
        prices.loc[first_day, "price_eur_per_mwh"] = [0.0, 100.0] + [50.0] * 22
        prices.loc[second_day, "price_eur_per_mwh"] = [
            100.0,
            0.0,
            0.0,
            100.0,
        ] + [50.0] * 20
        result = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        )
        self.assertAlmostEqual(result.summary["forecast_planned_margin_eur"], 100.0)
        self.assertAlmostEqual(result.summary["realized_margin_eur"], -100.0)
        self.assertAlmostEqual(result.summary["perfect_foresight_margin_eur"], 100.0)
        self.assertAlmostEqual(result.summary["perfect_foresight_regret_eur"], 200.0)

    def test_daily_persistence_discloses_spring_dst_exclusion_hourly(self) -> None:
        self._assert_spring_dst_exclusion(
            resolution_minutes=60,
            evaluation_interval_count=95,
            backtested_interval_count=71,
            missing_forecast_interval_count=1,
        )

    def test_daily_persistence_discloses_spring_dst_exclusion_quarter_hourly(
        self,
    ) -> None:
        self._assert_spring_dst_exclusion(
            resolution_minutes=15,
            evaluation_interval_count=380,
            backtested_interval_count=284,
            missing_forecast_interval_count=4,
        )

    def test_ensemble_backtests_every_spring_dst_evaluation_day(self) -> None:
        for resolution_minutes, expected_intervals in ((60, 95), (15, 380)):
            with self.subTest(resolution_minutes=resolution_minutes):
                prices = repeating_prices(
                    date(2026, 3, 27),
                    date(2026, 4, 1),
                    resolution_minutes=resolution_minutes,
                )
                result = backtest_forecast_dispatch(
                    prices,
                    battery(),
                    method="ensemble",
                    start_day=date(2026, 3, 28),
                )

                self.assertEqual(result.summary["evaluation_day_count"], 4)
                self.assertEqual(result.summary["backtested_day_count"], 4)
                self.assertEqual(
                    result.summary["backtested_interval_count"], expected_intervals
                )
                self.assertEqual(
                    result.summary["excluded_incomplete_forecast_days"], []
                )
                self.assertAlmostEqual(
                    result.summary["forecast_metrics"]["coverage_fraction"], 1.0
                )

    def _assert_spring_dst_exclusion(
        self,
        *,
        resolution_minutes: int,
        evaluation_interval_count: int,
        backtested_interval_count: int,
        missing_forecast_interval_count: int,
    ) -> None:
        prices = repeating_prices(
            date(2026, 3, 27),
            date(2026, 4, 1),
            resolution_minutes=resolution_minutes,
        )
        result = backtest_forecast_dispatch(
            prices,
            battery(),
            method="daily_persistence",
            start_day=date(2026, 3, 28),
        )
        summary = result.summary

        self.assertEqual(summary["evaluation_day_count"], 4)
        self.assertEqual(summary["evaluation_interval_count"], evaluation_interval_count)
        self.assertEqual(summary["backtested_day_count"], 3)
        self.assertEqual(
            summary["backtested_interval_count"], backtested_interval_count
        )
        self.assertEqual(summary["excluded_incomplete_forecast_day_count"], 1)
        self.assertEqual(
            summary["missing_forecast_interval_count"],
            missing_forecast_interval_count,
        )
        self.assertEqual(
            summary["excluded_incomplete_forecast_days"],
            [
                {
                    "market_day": "2026-03-30",
                    "interval_count": 24 * 60 // resolution_minutes,
                    "missing_forecast_interval_count": (
                        missing_forecast_interval_count
                    ),
                }
            ],
        )
        self.assertAlmostEqual(
            summary["forecast_metrics"]["coverage_fraction"],
            (evaluation_interval_count - missing_forecast_interval_count)
            / evaluation_interval_count,
        )
        self.assertAlmostEqual(
            summary["backtested_forecast_metrics"]["coverage_fraction"], 1.0
        )
        self.assertAlmostEqual(summary["backtested_day_fraction"], 3 / 4)
        self.assertAlmostEqual(
            summary["backtested_interval_fraction"],
            backtested_interval_count / evaluation_interval_count,
        )


if __name__ == "__main__":
    unittest.main()
