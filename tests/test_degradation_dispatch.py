from __future__ import annotations

import unittest
from datetime import date

from greek_bess.backtest import (
    DegradationDispatchInputError,
    simulate_degradation_dispatch,
)
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.degradation import AugmentationEvent, DegradationConfig
from greek_bess.dispatch import BatteryDispatchConfig


def arbitrage_prices(start: date, end: date, *, resolution_minutes: int = 60):
    frame = generate_synthetic_prices(
        start,
        end,
        resolution_minutes=resolution_minutes,
        negative_price_share=0,
    )
    frame["price_eur_per_mwh"] = 50.0
    market_day = frame["delivery_start_market"].dt.date
    for day in market_day.unique():
        positions = frame.index[market_day == day]
        frame.loc[positions[0], "price_eur_per_mwh"] = 0.0
        frame.loc[positions[-1], "price_eur_per_mwh"] = 100.0
    return frame


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
        "max_daily_equivalent_cycles": 1.0,
    }
    values.update(overrides)
    return BatteryDispatchConfig(**values)


class DegradationDispatchTests(unittest.TestCase):
    def test_dispatch_uses_beginning_of_day_degraded_limits(self) -> None:
        result = simulate_degradation_dispatch(
            arbitrage_prices(date(2026, 1, 1), date(2026, 1, 3)),
            battery(),
            DegradationConfig(
                project_start_day=date(2026, 1, 1),
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.10,
            ),
        )
        first, second = result.daily_results.iloc[0], result.daily_results.iloc[1]
        self.assertAlmostEqual(first["grid_discharge_mwh"], 1.0)
        self.assertAlmostEqual(first["usable_energy_mwh_end"], 0.9)
        self.assertAlmostEqual(second["usable_energy_mwh_start"], 0.9)
        self.assertAlmostEqual(second["grid_discharge_mwh"], 0.9)
        self.assertAlmostEqual(second["usable_energy_mwh_end"], 0.81)
        self.assertAlmostEqual(result.summary["final_usable_energy_mwh"], 0.81)

    def test_augmentation_increases_next_dispatch_limits_and_records_cost(self) -> None:
        result = simulate_degradation_dispatch(
            arbitrage_prices(date(2026, 1, 1), date(2026, 1, 3)),
            battery(),
            DegradationConfig(
                project_start_day=date(2026, 1, 1),
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.10,
                augmentation_events=(
                    AugmentationEvent(
                        event_id="day-2-addition",
                        day=date(2026, 1, 2),
                        added_energy_mwh=1.0,
                        added_charge_power_mw=1.0,
                        added_discharge_power_mw=1.0,
                        cost_eur=500.0,
                    ),
                ),
            ),
        )
        second = result.daily_results.iloc[1]
        self.assertAlmostEqual(second["usable_energy_mwh_start"], 1.9)
        self.assertAlmostEqual(second["grid_discharge_mwh"], 1.9)
        self.assertEqual(second["augmentation_event_ids"], "day-2-addition")
        self.assertEqual(result.summary["augmentation_cost_eur"], 500.0)
        self.assertEqual(
            result.summary["applied_augmentation_event_ids"], ["day-2-addition"]
        )

    def test_enforced_warranty_cap_stops_later_discharge(self) -> None:
        result = simulate_degradation_dispatch(
            arbitrage_prices(date(2026, 1, 1), date(2026, 1, 3)),
            battery(),
            DegradationConfig(
                project_start_day=date(2026, 1, 1),
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.0,
                warranty_max_equivalent_full_cycles=1.0,
                enforce_warranty_throughput_limit=True,
            ),
        )
        self.assertAlmostEqual(result.daily_results.iloc[0]["grid_discharge_mwh"], 1.0)
        self.assertAlmostEqual(result.daily_results.iloc[1]["grid_discharge_mwh"], 0.0)
        self.assertAlmostEqual(
            result.daily_results.iloc[1]["effective_max_daily_equivalent_cycles"],
            0.0,
        )
        self.assertFalse(result.summary["warranty_throughput_exceeded"])

    def test_quarter_hour_spring_dst_day_remains_complete(self) -> None:
        result = simulate_degradation_dispatch(
            arbitrage_prices(
                date(2026, 3, 29),
                date(2026, 3, 30),
                resolution_minutes=15,
            ),
            battery(),
            DegradationConfig(
                project_start_day=date(2026, 3, 29),
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.0,
            ),
        )
        self.assertEqual(len(result.interval_schedule), 92)
        self.assertEqual(result.daily_results.iloc[0]["interval_count"], 92)

    def test_daily_soc_reset_is_required(self) -> None:
        with self.assertRaisesRegex(
            DegradationDispatchInputError, "terminal_soc_fraction"
        ):
            simulate_degradation_dispatch(
                arbitrage_prices(date(2026, 1, 1), date(2026, 1, 2)),
                battery(initial_soc_fraction=0.0, terminal_soc_fraction=0.5),
                DegradationConfig(
                    project_start_day=date(2026, 1, 1),
                    calendar_fade_fraction_per_year=0.0,
                    cycle_fade_fraction_per_equivalent_cycle=0.0,
                ),
            )


if __name__ == "__main__":
    unittest.main()
