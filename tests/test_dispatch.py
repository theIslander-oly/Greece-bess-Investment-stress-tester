from __future__ import annotations

import unittest
from datetime import date

import numpy as np
import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import (
    BatteryDispatchConfig,
    DispatchInputError,
    optimize_perfect_foresight,
)


def price_frame(values: list[float], *, resolution_minutes: int = 60):
    full_day = generate_synthetic_prices(
        date(2026, 1, 5),
        date(2026, 1, 6),
        resolution_minutes=resolution_minutes,
        negative_price_share=0,
    )
    frame = full_day.iloc[: len(values)].copy()
    frame["price_eur_per_mwh"] = values
    return frame


def config(**overrides) -> BatteryDispatchConfig:
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
        "require_complete_market_days": False,
    }
    values.update(overrides)
    return BatteryDispatchConfig(**values)


class PerfectForesightDispatchTests(unittest.TestCase):
    def test_simple_arbitrage_and_terminal_soc(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([10.0, 10.0, 100.0, 100.0]), config()
        )
        self.assertAlmostEqual(result.summary["grid_charge_mwh"], 1.0)
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 1.0)
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 90.0)
        self.assertAlmostEqual(result.summary["terminal_energy_mwh"], 0.0)
        simultaneous = (
            (result.schedule["charge_mw"] > 1e-8)
            & (result.schedule["discharge_mw"] > 1e-8)
        )
        self.assertFalse(simultaneous.any())

    def test_negative_price_cannot_create_simultaneous_dissipation(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([-100.0]),
            config(initial_soc_fraction=1.0, terminal_soc_fraction=1.0),
        )
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 0.0)
        self.assertAlmostEqual(result.schedule["charge_mw"].iloc[0], 0.0)
        self.assertAlmostEqual(result.schedule["discharge_mw"].iloc[0], 0.0)

    def test_efficiency_losses_are_accounted_at_grid_meter(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([10.0, 100.0]),
            config(
                charge_power_mw=2.0,
                discharge_power_mw=2.0,
                charge_efficiency=0.9,
                discharge_efficiency=0.9,
            ),
        )
        self.assertAlmostEqual(result.summary["grid_charge_mwh"], 1 / 0.9, places=6)
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 0.9, places=6)
        self.assertAlmostEqual(
            result.summary["net_market_margin_eur"], 90 - (10 / 0.9), places=6
        )

    def test_availability_blocks_the_only_discharge_interval(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([0.0, 100.0]), config(), availability=[1.0, 0.0]
        )
        self.assertAlmostEqual(result.summary["grid_charge_mwh"], 0.0)
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 0.0)

    def test_daily_cycle_limit_caps_discharged_energy(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([0.0, 100.0, 0.0, 100.0]),
            config(max_daily_equivalent_cycles=1.0),
        )
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 1.0, places=6)
        self.assertAlmostEqual(result.summary["equivalent_full_cycles"], 1.0, places=6)

    def test_quarter_hour_energy_accounting(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([0.0, 0.0, 0.0, 100.0], resolution_minutes=15),
            config(energy_capacity_mwh=0.25),
        )
        self.assertAlmostEqual(result.summary["grid_charge_mwh"], 0.25)
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 0.25)
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 25.0)

    def test_incomplete_day_is_rejected_by_default(self) -> None:
        with self.assertRaisesRegex(DispatchInputError, "incomplete_market_day"):
            optimize_perfect_foresight(
                price_frame([10.0, 100.0]),
                BatteryDispatchConfig(
                    charge_power_mw=1.0,
                    discharge_power_mw=1.0,
                    energy_capacity_mwh=1.0,
                ),
            )

    def test_invalid_availability_is_rejected(self) -> None:
        with self.assertRaisesRegex(DispatchInputError, "availability"):
            optimize_perfect_foresight(
                price_frame([10.0, 100.0]), config(), availability=np.array([1.2, 1.0])
            )

    def test_availability_stays_aligned_when_input_is_unsorted(self) -> None:
        frame = price_frame([0.0, 100.0]).iloc[::-1].reset_index(drop=True)
        result = optimize_perfect_foresight(
            frame,
            config(initial_soc_fraction=1.0, terminal_soc_fraction=0.0),
            availability=[1.0, 0.0],
        )
        self.assertAlmostEqual(result.summary["grid_discharge_mwh"], 1.0)
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 100.0)

    def test_missing_whole_market_day_is_rejected(self) -> None:
        first = generate_synthetic_prices(date(2026, 1, 5), date(2026, 1, 6))
        third = generate_synthetic_prices(date(2026, 1, 7), date(2026, 1, 8))
        with self.assertRaisesRegex(DispatchInputError, "non_contiguous_horizon"):
            optimize_perfect_foresight(
                pd.concat([first, third], ignore_index=True),
                config(require_complete_market_days=True),
            )


if __name__ == "__main__":
    unittest.main()
