"""The committed operator declarations are accepted by the code that will read them.

`tests/test_config_examples.py` guards the opposite property: that the committed *examples* stay
recognisable as examples and are refused. This module guards the declarations themselves, and it
exists because they are read by a scheduled workflow rather than by a developer. `witness-
fundamentals.yml` runs unattended once a day and cannot recover a day it fails on: a
contemporaneous observation exists only while it is contemporaneous. An edit that leaves a
declaration parseable but inadmissible — a weight that no longer sums to one, a coordinate nudged
off the grid, a lead that stops being an integer — would therefore be discovered by losing
witnessed days, one per day, silently.

Nothing here checks a declaration against the market rules or against Greek geography. That check
does not exist and cannot: the tooling reports whatever is declared. These are admissibility
checks only.
"""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from greek_bess.data.decision_cutoff import (
    EXAMPLE_PLACEHOLDER_IDENTIFIER,
    EXAMPLE_PLACEHOLDER_MARKER,
    read_decision_cutoff_schedule,
    validate_decision_lead_minutes,
)
from greek_bess.data.gfs import FIRST_HOURLY_DELIVERY_DAY, Grib2Grid, grid_index
from greek_bess.data.point_in_time import read_sampling_geography
from greek_bess.dispatch.perfect_foresight import BatteryDispatchConfig

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = ROOT / "config" / "decision_cutoff.json"
GEOGRAPHY = ROOT / "config" / "fundamentals_geography.json"
LEAD = ROOT / "config" / "decision_lead_minutes.txt"

#: The 0.25 degree GFS grid the declared sampling points must land on. The retrieval resolves
#: points against the grid header of the first decoded message and refuses a point between nodes;
#: this reproduces that grid so the refusal is discovered here rather than in a live run.
GFS_QUARTER_DEGREE_GRID = Grib2Grid(
    ni=1440,
    nj=721,
    first_latitude=90.0,
    first_longitude=0.0,
    latitude_increment=0.25,
    longitude_increment=0.25,
)


class DecisionCutoffDeclarationTest(unittest.TestCase):
    def test_the_declared_schedule_is_accepted(self) -> None:
        schedule = read_decision_cutoff_schedule(CUTOFF)
        self.assertNotEqual(schedule.schedule_id, EXAMPLE_PLACEHOLDER_IDENTIFIER)
        self.assertEqual(len(schedule.regimes), 2)

    def test_every_regime_resolves_a_closure_in_both_clock_offsets(self) -> None:
        schedule = read_decision_cutoff_schedule(CUTOFF)
        for delivery_day in (date(2020, 11, 2), date(2021, 1, 15), date(2026, 7, 1)):
            with self.subTest(delivery_day=delivery_day):
                regime = schedule.regime_for(delivery_day)
                closure = regime.closure_utc(delivery_day)
                self.assertIsNotNone(closure.tzinfo)
                # A day-ahead closure precedes the delivery day it bounds, in UTC as declared.
                self.assertLess(closure.date(), delivery_day)

    def test_the_isolated_era_regime_governs_no_feature_bearing_day(self) -> None:
        """The regime declared from secondary reporting alone must stay inert for v0.9.

        The first regime is the one this project could not check against the primary rulebook.
        It is admissible because every delivery day it governs precedes the first day the GFS
        0.25 degree product can supply an hourly feature, so no accepted feature is ever judged
        against it. If a later decision moves the feature start earlier, this fails.
        """

        schedule = read_decision_cutoff_schedule(CUTOFF)
        coupled_from = schedule.regimes[1].effective_from_delivery_day
        self.assertLess(coupled_from, FIRST_HOURLY_DELIVERY_DAY)
        self.assertEqual(
            schedule.regime_for(FIRST_HOURLY_DELIVERY_DAY), schedule.regimes[1]
        )

    def test_the_declared_lead_is_a_non_negative_whole_number_of_minutes(self) -> None:
        self.assertEqual(validate_decision_lead_minutes(int(LEAD.read_text().strip())), 0)


class SamplingGeographyDeclarationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.geography = read_sampling_geography(GEOGRAPHY)

    def test_the_declared_geography_is_accepted(self) -> None:
        self.assertNotEqual(self.geography.geography_id, EXAMPLE_PLACEHOLDER_IDENTIFIER)
        self.assertNotIn(EXAMPLE_PLACEHOLDER_MARKER, self.geography.reference)
        self.assertEqual(self.geography.area, "GR")

    def test_every_declared_point_is_a_grid_node(self) -> None:
        for point in self.geography.points:
            with self.subTest(point=point.point_id):
                index = grid_index(
                    GFS_QUARTER_DEGREE_GRID, point.latitude, point.longitude
                )
                self.assertGreaterEqual(index, 0)

    def test_the_reference_states_the_basis_and_its_vintage(self) -> None:
        """A geography is only as good as the basis it names, so the basis is asserted."""

        reference = self.geography.reference
        for phrase in ("wind", "31 December 2023", "renormalised"):
            self.assertIn(phrase, reference)


class RepresentativeUnitExampleTest(unittest.TestCase):
    """The researched Greek unit sits beside the accepted example; both must stay loadable."""

    def _config(self, name: str) -> BatteryDispatchConfig:
        payload = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
        return BatteryDispatchConfig(**payload)

    def test_the_accepted_example_is_unchanged_at_two_hours(self) -> None:
        config = self._config("battery_50mw_100mwh.json")
        self.assertEqual(config.charge_power_mw, 50.0)
        self.assertEqual(config.energy_capacity_mwh, 100.0)

    def test_the_representative_unit_is_a_four_hour_unit(self) -> None:
        config = self._config("battery_representative_gr_25mw_100mwh.json")
        self.assertEqual(config.charge_power_mw, config.discharge_power_mw)
        self.assertEqual(
            config.energy_capacity_mwh / config.charge_power_mw, 4.0
        )

    def test_the_representative_unit_keeps_the_accepted_conventions(self) -> None:
        """Only the sizing and the cycle limit differ, so the two remain comparable."""

        accepted = self._config("battery_50mw_100mwh.json")
        representative = self._config("battery_representative_gr_25mw_100mwh.json")
        for name in (
            "soc_min_fraction",
            "soc_max_fraction",
            "initial_soc_fraction",
            "terminal_soc_fraction",
            "charge_efficiency",
            "discharge_efficiency",
            "self_discharge_per_hour",
            "buy_fee_eur_per_mwh",
            "sell_fee_eur_per_mwh",
            "degradation_cost_eur_per_mwh_discharged",
            "require_complete_market_days",
            "solve_strategy",
        ):
            with self.subTest(field=name):
                self.assertEqual(getattr(representative, name), getattr(accepted, name))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
