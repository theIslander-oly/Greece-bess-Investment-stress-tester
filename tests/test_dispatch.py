from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import (
    BatteryDispatchConfig,
    DispatchInputError,
    optimize_daily_perfect_foresight,
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


class DailyComposedDispatchTests(unittest.TestCase):
    def multi_day_prices(self) -> pd.DataFrame:
        frame = generate_synthetic_prices(
            date(2025, 12, 30), date(2026, 1, 2), negative_price_share=0
        )
        slot = frame["delivery_start_market"].dt.hour
        frame["price_eur_per_mwh"] = slot.map(lambda hour: 10.0 if hour < 12 else 100.0)
        return frame

    def daily_config(self, **overrides) -> BatteryDispatchConfig:
        values = {
            "charge_power_mw": 1.0,
            "discharge_power_mw": 1.0,
            "energy_capacity_mwh": 4.0,
            "soc_min_fraction": 0.0,
            "soc_max_fraction": 1.0,
            "initial_soc_fraction": 0.0,
            "terminal_soc_fraction": 0.0,
            "charge_efficiency": 1.0,
            "discharge_efficiency": 1.0,
        }
        values.update(overrides)
        return BatteryDispatchConfig(**values)

    def test_every_day_is_solved_independently_and_returns_to_initial_soc(self) -> None:
        prices = self.multi_day_prices()
        result = optimize_daily_perfect_foresight(prices, self.daily_config())

        self.assertEqual(result.summary["solve_mode"], "daily_independent_solves")
        self.assertEqual(result.summary["interval_count"], len(prices))
        self.assertEqual(result.summary["market_day_count"], 3)
        self.assertEqual(result.summary["solver_status_counts"], {"0": 3})
        self.assertLess(result.summary["maximum_terminal_energy_error_mwh"], 1e-6)
        self.assertEqual(
            sorted(result.schedule["market_day"].unique()),
            [date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 1)],
        )
        for _, day in result.schedule.groupby("market_day"):
            self.assertAlmostEqual(float(day["energy_end_mwh"].iloc[-1]), 0.0, places=6)

    def test_daily_composition_never_exceeds_the_full_horizon_bound(self) -> None:
        prices = self.multi_day_prices()
        config = self.daily_config()
        daily = optimize_daily_perfect_foresight(prices, config)
        horizon = optimize_perfect_foresight(prices, config)

        self.assertLessEqual(
            daily.summary["net_market_margin_eur"],
            horizon.summary["net_market_margin_eur"] + 1e-6,
        )

    def test_daily_composition_requires_a_restored_terminal_soc(self) -> None:
        prices = self.multi_day_prices()
        with self.assertRaisesRegex(DispatchInputError, "terminal_soc_fraction"):
            optimize_daily_perfect_foresight(
                prices,
                self.daily_config(initial_soc_fraction=0.0, terminal_soc_fraction=1.0),
            )

    def test_shuffled_input_keeps_availability_with_its_own_interval(self) -> None:
        prices = self.multi_day_prices()
        market_day = prices["delivery_start_market"].dt.date
        availability = np.where(market_day.eq(date(2025, 12, 31)).to_numpy(), 0.0, 1.0)

        order = np.random.default_rng(3).permutation(len(prices))
        shuffled = prices.iloc[order].reset_index(drop=True)
        shuffled_availability = availability[order]

        ordered = optimize_daily_perfect_foresight(
            prices, self.daily_config(), availability=availability
        )
        scrambled = optimize_daily_perfect_foresight(
            shuffled, self.daily_config(), availability=shuffled_availability
        )
        self.assertAlmostEqual(
            scrambled.summary["net_market_margin_eur"],
            ordered.summary["net_market_margin_eur"],
        )
        idle = scrambled.schedule.loc[scrambled.schedule["market_day"] == date(2025, 12, 31)]
        self.assertAlmostEqual(float(idle["discharge_grid_mwh"].sum()), 0.0)

    def test_interval_availability_is_applied_to_its_own_day(self) -> None:
        prices = self.multi_day_prices()
        market_day = prices["delivery_start_market"].dt.date
        availability = np.where(market_day.eq(date(2025, 12, 31)).to_numpy(), 0.0, 1.0)

        result = optimize_daily_perfect_foresight(
            prices, self.daily_config(), availability=availability
        )
        idle = result.schedule.loc[result.schedule["market_day"] == date(2025, 12, 31)]
        active = result.schedule.loc[result.schedule["market_day"] == date(2025, 12, 30)]

        self.assertAlmostEqual(float(idle["discharge_grid_mwh"].sum()), 0.0)
        self.assertGreater(float(active["discharge_grid_mwh"].sum()), 0.0)


if __name__ == "__main__":
    unittest.main()


class SolveStrategyTests(unittest.TestCase):
    """The relaxation shortcut must be a speedup only, never a different answer."""

    def test_relaxation_is_accepted_when_no_interval_wants_to_do_both(self) -> None:
        result = optimize_perfect_foresight(
            price_frame([10.0, 10.0, 100.0, 100.0]), config()
        )

        self.assertEqual(result.summary["solve_strategy"], "relaxation_first")
        self.assertEqual(result.summary["solve_path"], "relaxation_accepted")
        self.assertEqual(result.summary["relaxation_simultaneous_interval_count"], 0)
        self.assertFalse(result.summary["mixed_integer_solve_required"])

    def test_negative_prices_send_the_relaxation_back_to_the_mixed_integer_solve(
        self,
    ) -> None:
        # A full battery at -100 EUR/MWh is the case the binary exists for. Being
        # paid to charge is only reachable by discharging at the same time to make
        # room, and because the round trip returns less than it takes, the pair
        # nets a profit: 1.0 MWh bought at -100 against 0.81 MWh sold at -100.
        # Without the binary the relaxation takes it; with it, the answer is idle.
        prices = price_frame([-100.0])
        strict = config(
            initial_soc_fraction=1.0,
            terminal_soc_fraction=1.0,
            charge_efficiency=0.9,
            discharge_efficiency=0.9,
        )
        result = optimize_perfect_foresight(prices, strict)

        self.assertEqual(result.summary["solve_path"], "mixed_integer")
        self.assertGreater(result.summary["relaxation_simultaneous_interval_count"], 0)
        self.assertTrue(result.summary["mixed_integer_solve_required"])
        simultaneous = (result.schedule["charge_mw"] > 1e-8) & (
            result.schedule["discharge_mw"] > 1e-8
        )
        self.assertFalse(simultaneous.any())
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 0.0)

    def test_both_strategies_agree_across_a_month_of_signed_prices(self) -> None:
        prices = generate_synthetic_prices(
            date(2025, 6, 1),
            date(2025, 7, 1),
            resolution_minutes=60,
            negative_price_share=0.05,
        )
        battery = BatteryDispatchConfig(
            charge_power_mw=25.0, discharge_power_mw=25.0, energy_capacity_mwh=50.0
        )

        exact = optimize_perfect_foresight(
            prices, replace(battery, solve_strategy="mixed_integer")
        )
        shortcut = optimize_perfect_foresight(
            prices, replace(battery, solve_strategy="relaxation_first")
        )

        # A relative tolerance, not an absolute one: where the two solves land on
        # different optima of equal value, the margins agree to floating-point
        # summation order, far inside the solver's own mip_relative_gap.
        self.assertAlmostEqual(
            shortcut.summary["net_market_margin_eur"]
            / exact.summary["net_market_margin_eur"],
            1.0,
            places=12,
        )
        for result in (exact, shortcut):
            simultaneous = (result.schedule["charge_mw"] > 1e-8) & (
                result.schedule["discharge_mw"] > 1e-8
            )
            self.assertFalse(simultaneous.any())

    def test_daily_solve_reports_how_many_days_needed_the_mixed_integer_program(
        self,
    ) -> None:
        prices = generate_synthetic_prices(
            date(2025, 6, 1),
            date(2025, 6, 8),
            resolution_minutes=60,
            negative_price_share=0.0,
        )
        battery = BatteryDispatchConfig(
            charge_power_mw=25.0, discharge_power_mw=25.0, energy_capacity_mwh=50.0
        )
        result = optimize_daily_perfect_foresight(prices, battery)

        self.assertEqual(result.summary["solve_strategy"], "relaxation_first")
        self.assertEqual(result.summary["mixed_integer_solve_count"], 0)
        self.assertEqual(
            result.summary["solve_path_counts"], {"relaxation_accepted": 7}
        )

    def test_an_unknown_solve_strategy_is_rejected(self) -> None:
        with self.assertRaises(DispatchInputError):
            config(solve_strategy="whatever_is_fastest")
