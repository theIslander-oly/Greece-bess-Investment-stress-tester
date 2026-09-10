from __future__ import annotations

import unittest
from datetime import date

from greek_bess.backtest import (
    DegradationDispatchInputError,
    simulate_degradation_dispatch,
)
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.degradation import AugmentationEvent, DegradationConfig
from greek_bess.dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from greek_bess.finance.model import OPERATING_MARGIN_CASES, _margin_interpretation
from greek_bess.reporting.contract import RESULT_KINDS, SUPERSEDED_BASES


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


def budgeted_two_day_prices():
    """Two market days whose spreads are EUR 1 and EUR 100 per MWh."""

    frame = generate_synthetic_prices(
        date(2026, 1, 1), date(2026, 1, 3), resolution_minutes=60, negative_price_share=0
    )
    market_day = frame["delivery_start_market"].dt.date
    spreads = [(0.0, 1.0), (0.0, 100.0)]
    for day, (cheap, dear) in zip(sorted(market_day.unique()), spreads, strict=True):
        positions = frame.index[market_day == day]
        frame.loc[positions, "price_eur_per_mwh"] = (cheap + dear) / 2.0
        frame.loc[positions[0], "price_eur_per_mwh"] = cheap
        frame.loc[positions[-1], "price_eur_per_mwh"] = dear
    return frame


class DegradationResultBasisTests(unittest.TestCase):
    """The evolving-state aggregate is a simulation, and says so."""

    def _one_cycle_budget(self) -> DegradationConfig:
        return DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.0,
            cycle_fade_fraction_per_equivalent_cycle=0.0,
            warranty_max_equivalent_full_cycles=1.0,
            enforce_warranty_throughput_limit=True,
        )

    def test_the_daily_policy_earns_one_euro_where_waiting_earns_one_hundred(self) -> None:
        # The counterexample that settles what this result is. One warranted cycle and two
        # days: the daily policy spends the cycle on the EUR 1 spread because that day is
        # solved in isolation, and has nothing left for the EUR 100 spread the next day.
        result = simulate_degradation_dispatch(
            budgeted_two_day_prices(), battery(), self._one_cycle_budget()
        )
        self.assertAlmostEqual(result.summary["net_market_margin_eur"], 1.0, places=9)
        self.assertEqual(
            [round(float(value), 9) for value in result.daily_results["net_market_margin_eur"]],
            [1.0, 0.0],
        )

        # A feasible policy that waits spends the same single cycle on the second day.
        prices = budgeted_two_day_prices()
        market_day = prices["delivery_start_market"].dt.date
        second = prices[market_day == sorted(market_day.unique())[1]].reset_index(drop=True)
        waited = optimize_perfect_foresight(second, battery())
        self.assertAlmostEqual(
            float(waited.summary["net_market_margin_eur"]), 100.0, places=9
        )

        # So the aggregate cannot be a ceiling: a feasible policy beat it a hundredfold.
        self.assertLess(
            result.summary["net_market_margin_eur"],
            float(waited.summary["net_market_margin_eur"]),
        )

    def test_the_aggregate_is_not_labelled_a_lifetime_upper_bound(self) -> None:
        result = simulate_degradation_dispatch(
            budgeted_two_day_prices(), battery(), self._one_cycle_budget()
        )
        label = result.summary["result_label"]
        self.assertIn("simulation", label.lower())
        self.assertIn("not a lifetime optimum or an upper bound", label.lower())
        # The superseded wording called the aggregate a bound outright.
        self.assertNotIn("gross-margin upper bound", label.lower())
        self.assertIn("result_basis_note", result.summary)
        self.assertIn("myopic", result.summary["result_basis_note"].lower())

    def test_the_kind_reports_on_a_simulation_basis(self) -> None:
        kind = RESULT_KINDS["degradation_dispatch"]
        self.assertEqual(kind.basis, "historical_replay_simulation")
        self.assertIn("not a lifetime optimum", kind.description)

    def test_a_stored_upper_bound_manifest_is_refused_with_a_migration_message(self) -> None:
        # Never silently relabelled: the same number means something different under the two
        # bases, so the stored manifest is refused and the operator is told to re-run.
        self.assertIn(
            ("degradation_dispatch", "historical_replay_upper_bound"), SUPERSEDED_BASES
        )
        message = SUPERSEDED_BASES[
            ("degradation_dispatch", "historical_replay_upper_bound")
        ]
        self.assertIn("not one", message)

    def test_a_genuine_fixed_capacity_upper_bound_keeps_its_basis(self) -> None:
        # Only the evolving-state aggregate is reclassified. A perfect-foresight solve over a
        # fixed battery is still a real ceiling and must keep saying so.
        for kind_id in ("perfect_foresight_dispatch", "daily_perfect_foresight_dispatch"):
            self.assertEqual(
                RESULT_KINDS[kind_id].basis, "historical_replay_upper_bound", kind_id
            )

    def test_the_finance_interpretation_does_not_inherit_upper_bound_wording(self) -> None:
        self.assertIn("daily_policy_degraded_simulation", OPERATING_MARGIN_CASES)
        interpretation = _margin_interpretation("daily_policy_degraded_simulation")
        self.assertIn("not a lifetime optimum or an upper bound", interpretation)
        # The genuine bound case is unchanged.
        self.assertIn(
            "upper bound", _margin_interpretation("perfect_foresight_upper_bound")
        )
