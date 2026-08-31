"""Declared availability and outage paths for synthetic bootstrap paths.

The schedules below are hand-written windows over a two-day hourly horizon, so the interval
counts and derated hours are numbers a reader can confirm by eye.
"""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.stress import (
    AvailabilityInputError,
    AvailabilityScheduleConfig,
    BootstrapConfig,
    OutageWindow,
    build_availability_profile,
    dispatch_bootstrap_paths,
    generate_seasonal_bootstrap_paths,
)


def _paths(path_count: int = 2) -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 4), seed=7, negative_price_share=0
    )
    return generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(
            date(2026, 1, 1), date(2026, 1, 3), path_count=path_count, random_seed=3
        ),
    ).paths


def _window(hour: int, hours: int, fraction: float, name: str = "outage") -> OutageWindow:
    start = datetime(2025, 12, 31, 23, tzinfo=UTC) + timedelta(hours=hour)
    return OutageWindow(
        outage_id=name,
        start_utc=start,
        end_utc=start + timedelta(hours=hours),
        available_fraction=fraction,
    )


def _schedule(*windows: OutageWindow, baseline: float = 1.0) -> AvailabilityScheduleConfig:
    return AvailabilityScheduleConfig(
        schedule_id="declared_schedule",
        baseline_available_fraction=baseline,
        windows=windows,
    )


class ProfileTests(unittest.TestCase):
    def test_a_declared_outage_derates_exactly_the_intervals_it_covers(self) -> None:
        paths = _paths()
        profile = build_availability_profile(paths, _schedule(_window(0, 6, 0.0)))

        self.assertEqual(len(profile.values), 48)
        self.assertEqual(int((profile.values == 0.0).sum()), 6)
        self.assertEqual(int((profile.values == 1.0).sum()), 42)
        self.assertEqual(profile.values[:6].tolist(), [0.0] * 6)
        self.assertEqual(profile.summary["fully_unavailable_interval_count"], 6)
        self.assertEqual(profile.summary["fully_unavailable_hours"], 6.0)
        self.assertEqual(profile.summary["derated_hours"], 6.0)
        self.assertEqual(profile.summary["horizon_hours"], 48.0)
        self.assertEqual(profile.summary["minimum_available_fraction"], 0.0)
        self.assertEqual(profile.summary["declared_window_count"], 1)

    def test_a_partial_derate_is_applied_at_its_declared_depth(self) -> None:
        profile = build_availability_profile(_paths(), _schedule(_window(10, 4, 0.4)))

        self.assertEqual(int((profile.values == 0.4).sum()), 4)
        self.assertEqual(profile.summary["derated_interval_count"], 4)
        self.assertEqual(profile.summary["fully_unavailable_interval_count"], 0)
        self.assertEqual(profile.summary["minimum_available_fraction"], 0.4)

    def test_several_windows_are_applied_independently(self) -> None:
        profile = build_availability_profile(
            _paths(),
            _schedule(_window(0, 3, 0.0, "planned"), _window(20, 5, 0.5, "derate")),
        )

        self.assertEqual(int((profile.values == 0.0).sum()), 3)
        self.assertEqual(int((profile.values == 0.5).sum()), 5)
        self.assertEqual(
            profile.summary["applied_interval_count_by_outage"],
            {"planned": 3, "derate": 5},
        )
        self.assertEqual(profile.declaration["derated_interval_count"], 8)

    def test_a_schedule_with_no_window_is_a_declared_full_availability_scenario(self) -> None:
        profile = build_availability_profile(_paths(), _schedule(baseline=1.0))

        self.assertTrue(np.all(profile.values == 1.0))
        self.assertEqual(profile.summary["declared_window_count"], 0)
        self.assertEqual(profile.summary["derated_interval_count"], 0)
        self.assertEqual(profile.declaration["type"], "declared_schedule")

    def test_a_declared_baseline_below_one_derates_the_whole_horizon(self) -> None:
        profile = build_availability_profile(_paths(), _schedule(baseline=0.8))

        self.assertTrue(np.all(profile.values == 0.8))
        self.assertEqual(profile.declaration["baseline_available_fraction"], 0.8)

    def test_two_runs_produce_an_identical_profile(self) -> None:
        paths = _paths()
        schedule = _schedule(_window(4, 8, 0.25))

        first = build_availability_profile(paths, schedule)
        second = build_availability_profile(paths, schedule)

        self.assertEqual(first.values.tolist(), second.values.tolist())
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        self.assertEqual(first.summary, second.summary)


class ProvenanceTests(unittest.TestCase):
    def test_provenance_names_the_outage_on_every_covered_interval(self) -> None:
        profile = build_availability_profile(_paths(), _schedule(_window(2, 3, 0.0, "planned")))
        provenance = profile.provenance

        self.assertEqual(len(provenance), 48)
        self.assertEqual(int(provenance["outage_id"].notna().sum()), 3)
        covered = provenance.loc[provenance["outage_id"].notna()]
        self.assertEqual(covered["outage_id"].unique().tolist(), ["planned"])
        self.assertTrue((provenance["schedule_id"] == "declared_schedule").all())
        self.assertTrue((provenance["baseline_available_fraction"] == 1.0).all())
        self.assertEqual(covered["available_fraction"].tolist(), [0.0, 0.0, 0.0])

    def test_the_declaration_records_each_window_and_what_it_covered(self) -> None:
        profile = build_availability_profile(_paths(), _schedule(_window(6, 2, 0.0, "planned")))
        declared = profile.declaration["windows"]

        self.assertEqual(len(declared), 1)
        self.assertEqual(declared[0]["outage_id"], "planned")
        self.assertEqual(declared[0]["available_fraction"], 0.0)
        self.assertEqual(declared[0]["applied_interval_count"], 2)
        self.assertIn("start_utc", declared[0])
        self.assertIn("end_utc", declared[0])

    def test_the_labels_deny_a_forecast_and_a_probability(self) -> None:
        summary = build_availability_profile(_paths(), _schedule(_window(0, 1, 0.0))).summary

        self.assertFalse(summary["is_forecast"])
        self.assertFalse(summary["is_probabilistic"])
        self.assertIn("not a forecast, a probability or an outage rate", summary["result_label"])
        self.assertIn("never sampled", summary["policy"])


class RefusalTests(unittest.TestCase):
    def test_overlapping_windows_are_refused(self) -> None:
        with self.assertRaises(AvailabilityInputError) as raised:
            _schedule(_window(0, 5, 0.0, "first"), _window(3, 5, 0.5, "second"))
        self.assertIn("overlap", str(raised.exception))

    def test_a_window_covering_no_dispatched_interval_is_refused(self) -> None:
        far = OutageWindow(
            outage_id="elsewhere",
            start_utc=datetime(2030, 6, 1, tzinfo=UTC),
            end_utc=datetime(2030, 6, 2, tzinfo=UTC),
            available_fraction=0.0,
        )

        with self.assertRaises(AvailabilityInputError) as raised:
            build_availability_profile(_paths(), _schedule(far))
        self.assertIn("covers no dispatched interval", str(raised.exception))

    def test_a_boundary_inside_an_interval_is_refused_rather_than_prorated(self) -> None:
        misaligned = OutageWindow(
            outage_id="half_hour",
            start_utc=datetime(2025, 12, 31, 23, 30, tzinfo=UTC),
            end_utc=datetime(2026, 1, 1, 3, 0, tzinfo=UTC),
            available_fraction=0.0,
        )

        with self.assertRaises(AvailabilityInputError) as raised:
            build_availability_profile(_paths(), _schedule(misaligned))
        message = str(raised.exception)
        self.assertIn("falls inside delivery interval", message)
        self.assertIn("not prorated", message)

    def test_a_reversed_or_empty_window_is_refused(self) -> None:
        start = datetime(2026, 1, 1, 5, tzinfo=UTC)
        for end in (start, start - timedelta(hours=1)):
            with self.assertRaises(AvailabilityInputError) as raised:
                OutageWindow("backwards", start, end, 0.0)
            self.assertIn("later than start_utc", str(raised.exception))

    def test_a_naive_timestamp_is_refused(self) -> None:
        with self.assertRaises(AvailabilityInputError) as raised:
            OutageWindow(
                "naive", datetime(2026, 1, 1, 0), datetime(2026, 1, 1, 2), 0.0
            )
        self.assertIn("timezone aware", str(raised.exception))

    def test_fractions_outside_the_unit_interval_are_refused(self) -> None:
        for fraction in (-0.1, 1.5, float("nan"), True):
            with self.assertRaises(AvailabilityInputError):
                _schedule(baseline=fraction)
        for fraction in (-0.1, 1.5):
            with self.assertRaises(AvailabilityInputError):
                _window(0, 1, fraction)

    def test_a_missing_baseline_has_no_default(self) -> None:
        with self.assertRaises(AvailabilityInputError) as raised:
            AvailabilityScheduleConfig.from_dict(
                {"schedule_id": "no_baseline", "windows": []}
            )
        self.assertIn("baseline_available_fraction", str(raised.exception))

    def test_duplicate_outage_identifiers_are_refused(self) -> None:
        with self.assertRaises(AvailabilityInputError) as raised:
            _schedule(_window(0, 2, 0.0, "same"), _window(6, 2, 0.0, "same"))
        self.assertIn("Duplicate outage_id", str(raised.exception))

    def test_unknown_configuration_fields_are_refused(self) -> None:
        with self.assertRaises(AvailabilityInputError) as raised:
            AvailabilityScheduleConfig.from_dict(
                {
                    "schedule_id": "extra",
                    "baseline_available_fraction": 1.0,
                    "windows": [],
                    "forced_outage_rate": 0.03,
                }
            )
        self.assertIn("forced_outage_rate", str(raised.exception))


class ConfigParsingTests(unittest.TestCase):
    def test_a_json_schedule_round_trips_through_its_dictionary(self) -> None:
        config = AvailabilityScheduleConfig.from_dict(
            {
                "schedule_id": "summer_maintenance",
                "baseline_available_fraction": 1.0,
                "windows": [
                    {
                        "outage_id": "planned",
                        "start_utc": "2026-01-01T00:00:00+00:00",
                        "end_utc": "2026-01-01T06:00:00+00:00",
                        "available_fraction": 0.0,
                    }
                ],
            }
        )

        payload = config.to_dict()
        self.assertEqual(payload["schedule_id"], "summer_maintenance")
        self.assertEqual(len(payload["windows"]), 1)
        self.assertEqual(payload["windows"][0]["available_fraction"], 0.0)
        self.assertEqual(AvailabilityScheduleConfig.from_dict(payload), config)


class DispatchIntegrationTests(unittest.TestCase):
    def _battery(self) -> BatteryDispatchConfig:
        return BatteryDispatchConfig(
            charge_power_mw=1,
            discharge_power_mw=1,
            energy_capacity_mwh=1,
            soc_min_fraction=0,
            soc_max_fraction=1,
            initial_soc_fraction=0,
            terminal_soc_fraction=0,
            charge_efficiency=1,
            discharge_efficiency=1,
        )

    def test_dispatch_records_the_declared_schedule_by_name(self) -> None:
        paths = _paths()
        profile = build_availability_profile(paths, _schedule(_window(0, 12, 0.0, "planned")))

        result = dispatch_bootstrap_paths(paths, self._battery(), availability=profile)

        assumption = result.summary["availability_assumption"]
        self.assertEqual(assumption["type"], "declared_schedule")
        self.assertEqual(assumption["schedule_id"], "declared_schedule")
        self.assertEqual(assumption["declared_window_count"], 1)
        self.assertEqual(assumption["derated_hours"], 12.0)
        self.assertEqual(assumption["windows"][0]["outage_id"], "planned")

    def test_a_declared_outage_cannot_raise_the_margin_it_constrains(self) -> None:
        paths = _paths()
        battery = self._battery()
        available = build_availability_profile(paths, _schedule())
        outage = build_availability_profile(paths, _schedule(_window(0, 24, 0.0, "day_one")))

        baseline = dispatch_bootstrap_paths(paths, battery, availability=available)
        constrained = dispatch_bootstrap_paths(paths, battery, availability=outage)

        for path_id in baseline.path_summaries["path_id"]:
            unconstrained_margin = float(
                baseline.path_summaries.loc[
                    baseline.path_summaries["path_id"] == path_id, "net_market_margin_eur"
                ].iloc[0]
            )
            constrained_margin = float(
                constrained.path_summaries.loc[
                    constrained.path_summaries["path_id"] == path_id, "net_market_margin_eur"
                ].iloc[0]
            )
            self.assertLessEqual(constrained_margin, unconstrained_margin + 1e-9)

    def test_a_full_outage_holds_the_battery_still_for_its_intervals(self) -> None:
        paths = _paths()
        profile = build_availability_profile(paths, _schedule(_window(0, 24, 0.0, "day_one")))

        result = dispatch_bootstrap_paths(paths, self._battery(), availability=profile)
        first_day = result.interval_results.loc[
            result.interval_results["availability_fraction"] == 0.0
        ]

        self.assertEqual(len(first_day), 48)
        self.assertTrue(np.allclose(first_day["charge_grid_mwh"], 0.0))
        self.assertTrue(np.allclose(first_day["discharge_grid_mwh"], 0.0))

    def test_paths_covering_different_days_are_refused(self) -> None:
        """One schedule must map onto every path, so the paths must share one identity.

        The paths are shifted by a whole day each, so both remain complete market days and
        the refusal comes from the identity check rather than from the quality gate.
        """

        paths = _paths()
        shifted = paths.loc[paths["path_id"] == 1].copy()
        for column in (
            "delivery_start_utc",
            "delivery_end_utc",
            "delivery_start_market",
            "delivery_start_greece",
        ):
            shifted[column] = shifted[column] + timedelta(days=1)
        mixed = pd.concat([paths.loc[paths["path_id"] == 0], shifted], ignore_index=True)

        with self.assertRaises(AvailabilityInputError) as raised:
            build_availability_profile(mixed, _schedule(_window(0, 2, 0.0)))
        self.assertIn("different canonical interval identity", str(raised.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
