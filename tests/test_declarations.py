"""The approved v0.9 declarations remain executable and mutually consistent."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from greek_bess.cli._support import _read_battery_config
from greek_bess.data.decision_cutoff import (
    read_decision_cutoff_schedule,
    validate_decision_lead_minutes,
)
from greek_bess.data.point_in_time import read_sampling_geography

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


class FundamentalsDeclarationTests(unittest.TestCase):
    def test_cutoff_regimes_resolve_at_the_declared_utc_instants(self) -> None:
        schedule = read_decision_cutoff_schedule(CONFIG / "decision_cutoff.json")

        self.assertEqual(schedule.schedule_id, "greek-dam-gate-closure-2026-09-10")
        # One closure throughout: 12:00 CET/CEST on D-1 from the 1 November 2020 launch, as the
        # retained HEnEx timeline decisions state (docs/primary_sources/README.md). The
        # superseded 2026-09-03 declaration placed the pre-coupling closure one hour earlier.
        self.assertEqual(
            schedule.closure_utc(date(2020, 11, 1)).isoformat(),
            "2020-10-31T11:00:00+00:00",
        )
        self.assertEqual(
            schedule.closure_utc(date(2020, 12, 15)).isoformat(),
            "2020-12-14T11:00:00+00:00",
        )
        self.assertEqual(
            schedule.closure_utc(date(2020, 12, 16)).isoformat(),
            "2020-12-15T11:00:00+00:00",
        )
        self.assertEqual(
            schedule.closure_utc(date(2025, 10, 1)).isoformat(),
            "2025-09-30T10:00:00+00:00",
        )

    def test_declared_decision_lead_is_zero_not_absent(self) -> None:
        text = (CONFIG / "decision_lead_minutes.txt").read_text(encoding="utf-8")
        self.assertEqual(validate_decision_lead_minutes(int(text)), 0)

    def test_geography_is_a_normalized_exact_gfs_grid_aggregate(self) -> None:
        geography = read_sampling_geography(CONFIG / "fundamentals_geography.json")

        self.assertEqual(geography.area, "GR")
        self.assertEqual(len(geography.points), 3)
        self.assertAlmostEqual(sum(point.weight for point in geography.points), 1.0)
        for point in geography.points:
            with self.subTest(point=point.point_id):
                self.assertEqual(point.latitude * 4, round(point.latitude * 4))
                self.assertEqual(point.longitude * 4, round(point.longitude * 4))


class RepresentativeBatteryExampleTests(unittest.TestCase):
    def test_representative_example_is_four_hour_and_one_cycle(self) -> None:
        config = _read_battery_config(
            ROOT / "examples" / "battery_representative_gr_25mw_100mwh.json"
        )

        self.assertEqual(config.charge_power_mw, 25.0)
        self.assertEqual(config.discharge_power_mw, 25.0)
        self.assertEqual(config.energy_capacity_mwh, 100.0)
        self.assertEqual(config.grid_import_limit_mw, 25.0)
        self.assertEqual(config.grid_export_limit_mw, 25.0)
        self.assertEqual(config.max_daily_equivalent_cycles, 1.0)

    def test_accepted_comparison_example_is_unchanged(self) -> None:
        payload = json.loads(
            (ROOT / "examples" / "battery_50mw_100mwh.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["charge_power_mw"], 50.0)
        self.assertEqual(payload["discharge_power_mw"], 50.0)
        self.assertEqual(payload["energy_capacity_mwh"], 100.0)
        self.assertEqual(payload["max_daily_equivalent_cycles"], 1.5)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
