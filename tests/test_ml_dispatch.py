from __future__ import annotations

import unittest
from datetime import date

import numpy as np

from greek_bess.backtest import backtest_ml_dispatch_benchmark
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.forecast import MLForecastConfig, generate_ml_forecasts


def battery() -> BatteryDispatchConfig:
    return BatteryDispatchConfig(
        charge_power_mw=1.0,
        discharge_power_mw=1.0,
        energy_capacity_mwh=2.0,
        soc_min_fraction=0.1,
        soc_max_fraction=0.9,
        initial_soc_fraction=0.5,
        terminal_soc_fraction=0.5,
        charge_efficiency=0.93,
        discharge_efficiency=0.92,
        buy_fee_eur_per_mwh=1.0,
        sell_fee_eur_per_mwh=0.5,
        degradation_cost_eur_per_mwh_discharged=4.0,
    )


class MLDispatchTests(unittest.TestCase):
    def test_methods_use_identical_horizon_and_realized_settlement(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 1, 1), date(2026, 2, 18), seed=37
        )
        ml = generate_ml_forecasts(
            prices,
            MLForecastConfig(
                validation_start_day=date(2026, 2, 1),
                test_start_day=date(2026, 2, 12),
                models=("ridge",),
                min_training_days=28,
                refit_frequency_days=3,
            ),
        )
        result = backtest_ml_dispatch_benchmark(prices, battery(), ml)
        methods = result.summary["comparison_methods"]
        perfect_margins = {
            round(result.method_summaries[method]["perfect_foresight_margin_eur"], 7)
            for method in methods
        }
        self.assertEqual(len(perfect_margins), 1)
        self.assertEqual(
            len(result.daily_results),
            result.summary["common_backtest_day_count"] * len(methods),
        )
        self.assertTrue(
            all(
                row["perfect_foresight_regret_eur"] >= -1e-5
                for row in result.summary["dispatch_ranking"]
            )
        )
        schedule = result.selected_model_interval_schedule
        expected_margin = (
            schedule["realized_discharge_energy_revenue_eur"]
            - schedule["realized_charging_energy_cost_eur"]
            - schedule["buy_fee_eur"]
            - schedule["sell_fee_eur"]
            - schedule["degradation_cost_eur"]
        )
        np.testing.assert_allclose(
            schedule["realized_net_market_margin_eur"], expected_margin, atol=1e-8
        )

    def test_common_horizon_discloses_spring_dst_daily_gap(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 2, 20), date(2026, 4, 2), seed=41
        )
        ml = generate_ml_forecasts(
            prices,
            MLForecastConfig(
                validation_start_day=date(2026, 3, 22),
                test_start_day=date(2026, 3, 28),
                models=("ridge",),
                min_training_days=28,
                refit_frequency_days=3,
            ),
        )
        result = backtest_ml_dispatch_benchmark(prices, battery(), ml)
        self.assertEqual(result.summary["test_evaluation_day_count"], 5)
        self.assertEqual(result.summary["common_backtest_day_count"], 4)
        self.assertEqual(
            result.summary["excluded_incomplete_comparison_days"],
            [
                {
                    "market_day": "2026-03-30",
                    "interval_count": 24,
                    "missing_forecast_intervals_by_method": {
                        "daily_persistence": 1
                    },
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
