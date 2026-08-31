from __future__ import annotations

import unittest
from datetime import date, timedelta

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    NegativePriceEvent,
    NegativePriceEventConfig,
    NegativePriceEventInputError,
    apply_negative_price_events,
    generate_seasonal_bootstrap_paths,
)


def _paths() -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 4), seed=4, negative_price_share=0
    )
    paths = generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(date(2026, 1, 1), date(2026, 1, 2), path_count=2, random_seed=7),
    ).paths
    paths.loc[0, "price_eur_per_mwh"] = 0.0
    paths.loc[1, "price_eur_per_mwh"] = -4.0
    return paths


def _event(paths: pd.DataFrame, *, price: float = -50.0) -> NegativePriceEvent:
    first_path = paths.loc[paths["path_id"] == paths["path_id"].min()].reset_index(drop=True)
    return NegativePriceEvent(
        "declared_dip",
        first_path.loc[2, "delivery_start_utc"].to_pydatetime(),
        first_path.loc[4, "delivery_start_utc"].to_pydatetime(),
        price,
    )


class NegativePriceEventTests(unittest.TestCase):
    def test_declared_window_arithmetic_is_hand_checkable(self) -> None:
        paths = _paths()
        result = apply_negative_price_events(
            paths, NegativePriceEventConfig("two_intervals", (_event(paths),))
        )
        covered = result.provenance["event_applied"]

        self.assertEqual(int(covered.sum()), 4)  # two intervals on each of two paths
        self.assertTrue((result.paths.loc[covered, "price_eur_per_mwh"] == -50.0).all())
        pd.testing.assert_series_equal(
            result.paths.loc[~covered, "price_eur_per_mwh"],
            paths.loc[~covered, "price_eur_per_mwh"],
        )
        self.assertEqual(result.summary["applied_interval_count_by_event"], {"declared_dip": 2})

    def test_empty_declared_event_list_is_exact_identity(self) -> None:
        paths = _paths()
        result = apply_negative_price_events(paths, NegativePriceEventConfig("identity", ()))

        pd.testing.assert_frame_equal(result.paths, paths)
        self.assertFalse(result.provenance["event_applied"].any())

    def test_unnamed_zero_and_negative_prices_survive_untouched(self) -> None:
        paths = _paths()
        result = apply_negative_price_events(
            paths, NegativePriceEventConfig("events", (_event(paths),))
        )

        self.assertEqual(result.paths.loc[0, "price_eur_per_mwh"], 0.0)
        self.assertEqual(result.paths.loc[1, "price_eur_per_mwh"], -4.0)

    def test_two_runs_are_deterministic_and_provenance_is_complete(self) -> None:
        paths = _paths()
        config = NegativePriceEventConfig("repeatable", (_event(paths, price=-25),))

        first = apply_negative_price_events(paths, config)
        second = apply_negative_price_events(paths, config)

        pd.testing.assert_frame_equal(first.paths, second.paths)
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        self.assertEqual(len(first.provenance), len(paths))
        self.assertEqual(first.summary["provenance_row_count"], len(paths))
        self.assertFalse(first.provenance.isna().all(axis=1).any())

    def test_summary_reports_negative_count_change(self) -> None:
        paths = _paths()
        result = apply_negative_price_events(
            paths, NegativePriceEventConfig("counted", (_event(paths),))
        )

        self.assertEqual(result.summary["negative_interval_count_before"], 1)
        self.assertEqual(result.summary["negative_interval_count_after"], 5)
        self.assertIn("not a horizon-wide additive level shift", result.summary["distinction"])

    def test_missing_prices_are_refused(self) -> None:
        paths = _paths()
        paths.loc[3, "price_eur_per_mwh"] = float("nan")
        with self.assertRaises(NegativePriceEventInputError):
            apply_negative_price_events(paths, NegativePriceEventConfig("missing", ()))

    def test_every_config_and_event_field_is_required(self) -> None:
        event = {
            "event_id": "dip",
            "start_utc": "2026-01-01T01:00:00+00:00",
            "end_utc": "2026-01-01T02:00:00+00:00",
            "price_eur_per_mwh": -10,
        }
        full = {"transformation_id": "declared", "events": [event]}

        for field in full:
            with self.assertRaises(NegativePriceEventInputError):
                NegativePriceEventConfig.from_dict(
                    {key: value for key, value in full.items() if key != field}
                )
        for field in event:
            incomplete = {key: value for key, value in event.items() if key != field}
            with self.assertRaises(NegativePriceEventInputError):
                NegativePriceEventConfig.from_dict({**full, "events": [incomplete]})

    def test_out_of_range_and_malformed_values_are_refused(self) -> None:
        paths = _paths()
        start = paths.loc[2, "delivery_start_utc"].to_pydatetime()
        end = paths.loc[3, "delivery_start_utc"].to_pydatetime()
        for price in (0, 1, float("nan"), float("inf"), True, "-1"):
            with self.assertRaises(NegativePriceEventInputError):
                NegativePriceEvent("dip", start, end, price)
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEvent("dip", start, start, -1)
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEvent("dip", start.replace(tzinfo=None), end, -1)
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEventConfig(" ", ())

    def test_unknown_duplicate_overlap_unaligned_and_empty_windows_are_refused(self) -> None:
        paths = _paths()
        event = _event(paths)
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEventConfig.from_dict(
                {"transformation_id": "id", "events": [], "rate": 0.1}
            )
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEventConfig("duplicates", (event, event))
        overlap = NegativePriceEvent("other", event.start_utc, event.end_utc, -20)
        with self.assertRaises(NegativePriceEventInputError):
            NegativePriceEventConfig("overlap", (event, overlap))

        unaligned = NegativePriceEvent(
            "partial",
            event.start_utc + timedelta(minutes=30),
            event.end_utc,
            -5,
        )
        outside = NegativePriceEvent(
            "outside",
            event.start_utc + timedelta(days=10),
            event.end_utc + timedelta(days=10),
            -5,
        )
        for invalid in (unaligned, outside):
            with self.assertRaises(NegativePriceEventInputError):
                apply_negative_price_events(paths, NegativePriceEventConfig("invalid", (invalid,)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
