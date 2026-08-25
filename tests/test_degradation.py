from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.degradation import (
    AugmentationEvent,
    DegradationConfig,
    DegradationInputError,
    simulate_degradation,
)


class DegradationModelTests(unittest.TestCase):
    def test_calendar_and_cycle_fade_are_additive(self) -> None:
        config = DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.02,
            cycle_fade_fraction_per_equivalent_cycle=0.10,
        )
        result = simulate_degradation(
            pd.DataFrame(
                {
                    "market_day": [date(2026, 1, 1), date(2027, 1, 1)],
                    "cell_discharge_mwh": [100.0, 0.0],
                }
            ),
            nominal_energy_mwh=100.0,
            nominal_charge_power_mw=50.0,
            nominal_discharge_power_mw=50.0,
            config=config,
        )
        self.assertAlmostEqual(
            result.daily_states.loc[0, "usable_energy_mwh_end"], 90.0
        )
        expected_retention = 1 - 0.10 - (365 / 365.25) * 0.02
        self.assertAlmostEqual(
            result.daily_states.loc[1, "retained_capacity_fraction_start"],
            expected_retention,
        )
        self.assertAlmostEqual(
            result.summary["final_usable_energy_mwh"],
            100.0 * expected_retention,
        )

    def test_augmentation_is_a_separately_aged_cohort(self) -> None:
        config = DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.0,
            cycle_fade_fraction_per_equivalent_cycle=0.10,
            augmentation_events=(
                AugmentationEvent(
                    event_id="augmentation-1",
                    day=date(2026, 1, 2),
                    added_energy_mwh=100.0,
                    added_charge_power_mw=50.0,
                    added_discharge_power_mw=50.0,
                    cost_eur=1_000_000.0,
                ),
            ),
        )
        result = simulate_degradation(
            pd.DataFrame(
                {
                    "market_day": [date(2026, 1, 1), date(2026, 1, 2)],
                    "cell_discharge_mwh": [100.0, 190.0],
                }
            ),
            nominal_energy_mwh=100.0,
            nominal_charge_power_mw=50.0,
            nominal_discharge_power_mw=50.0,
            config=config,
        )
        second = result.daily_states.iloc[1]
        self.assertAlmostEqual(second["nominal_energy_mwh_start"], 200.0)
        self.assertAlmostEqual(second["usable_energy_mwh_start"], 190.0)
        self.assertAlmostEqual(second["usable_energy_mwh_end"], 171.0)
        self.assertEqual(second["augmentation_event_ids"], "augmentation-1")
        self.assertEqual(result.summary["augmentation_cost_eur"], 1_000_000.0)
        cohorts = result.cohort_states.set_index("cohort_id")
        self.assertAlmostEqual(
            cohorts.loc["initial", "cumulative_equivalent_full_cycles"], 1.9
        )
        self.assertAlmostEqual(
            cohorts.loc["augmentation-1", "cumulative_equivalent_full_cycles"],
            1.0,
        )

    def test_enforced_warranty_throughput_rejects_excess(self) -> None:
        config = DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.0,
            cycle_fade_fraction_per_equivalent_cycle=0.0,
            warranty_max_equivalent_full_cycles=1.0,
            enforce_warranty_throughput_limit=True,
        )
        with self.assertRaisesRegex(DegradationInputError, "warranty headroom"):
            simulate_degradation(
                pd.DataFrame(
                    {
                        "market_day": [date(2026, 1, 1)],
                        "cell_discharge_mwh": [101.0],
                    }
                ),
                nominal_energy_mwh=100.0,
                nominal_charge_power_mw=50.0,
                nominal_discharge_power_mw=50.0,
                config=config,
            )

    def test_replacement_retires_old_cohort_before_adding_new_capacity(self) -> None:
        config = DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.0,
            cycle_fade_fraction_per_equivalent_cycle=0.10,
            augmentation_events=(
                AugmentationEvent(
                    event_id="replacement-1",
                    day=date(2026, 1, 2),
                    added_energy_mwh=100.0,
                    added_charge_power_mw=50.0,
                    added_discharge_power_mw=50.0,
                    cost_eur=2_000_000.0,
                    retired_cohort_ids=("initial",),
                ),
            ),
        )
        result = simulate_degradation(
            pd.DataFrame(
                {
                    "market_day": [date(2026, 1, 1), date(2026, 1, 2)],
                    "cell_discharge_mwh": [100.0, 0.0],
                }
            ),
            nominal_energy_mwh=100.0,
            nominal_charge_power_mw=50.0,
            nominal_discharge_power_mw=50.0,
            config=config,
        )
        second = result.daily_states.iloc[1]
        self.assertAlmostEqual(second["usable_energy_mwh_start"], 100.0)
        self.assertEqual(second["retired_cohort_ids"], "initial")
        self.assertEqual(result.cohort_states["cohort_id"].tolist(), ["replacement-1"])

    def test_invalid_warranty_and_augmentation_assumptions_are_rejected(self) -> None:
        with self.assertRaisesRegex(DegradationInputError, "must be set together"):
            DegradationConfig(
                project_start_day=date(2026, 1, 1),
                calendar_fade_fraction_per_year=0.01,
                cycle_fade_fraction_per_equivalent_cycle=0.001,
                warranty_years=10,
            )
        with self.assertRaisesRegex(DegradationInputError, "cannot precede"):
            DegradationConfig(
                project_start_day=date(2026, 1, 2),
                calendar_fade_fraction_per_year=0.01,
                cycle_fade_fraction_per_equivalent_cycle=0.001,
                augmentation_events=(
                    AugmentationEvent(
                        event_id="too-early",
                        day=date(2026, 1, 1),
                        added_energy_mwh=1,
                        added_charge_power_mw=1,
                        added_discharge_power_mw=1,
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
