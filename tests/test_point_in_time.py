"""The point-in-time feature contract: what a feature table must carry, and what it refuses.

The table exists to make one claim checkable: a bidder could have had this value before they had
to decide. Everything below defends that claim from a different direction — a value with no
publication instant, a unit that does not match its registry entry, two rows that disagree about
what they describe, a row order that changes the table, a market day the calendar does not have.
Design section 11 cases 5, 12 and 13 are here by name; the property tests generate the calendar
rather than enumerating the days somebody thought to write down.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from greek_bess.data.point_in_time import (
    ASSUMED,
    POINT_IN_TIME_COLUMNS,
    PROVIDER_DECLARED,
    VARIABLE_UNITS,
    PointInTimeSchemaError,
    SamplingGeography,
    ensure_point_in_time,
    feature_coverage,
    read_point_in_time_csv,
    read_sampling_geography,
    write_point_in_time_csv,
)
from greek_bess.data.timezones import MARKET_TZ, UTC, expected_interval_count, market_day_starts

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

MARKET_DAYS = st.dates(min_value=date(2021, 3, 1), max_value=date(2035, 12, 31))

SLOW = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def _row(
    *,
    start: str = "2026-08-26T00:00:00+00:00",
    variable: str = "temperature_2m",
    unit: str | None = None,
    value: float = 300.0,
    document: str = "gfs.20260825/00/atmos/gfs.t00z.pgrb2.0p25.f024#m581",
    revision: object = None,
    published: str | None = "2026-08-25T04:00:00+00:00",
    retrieved: str = "2026-08-26T09:00:00+00:00",
    grade: str = PROVIDER_DECLARED,
    digest: str = "a" * 64,
    resolution: int = 60,
    issued: str = "2026-08-25T00:00:00+00:00",
) -> dict[str, Any]:
    begins = pd.Timestamp(start)
    return {
        "delivery_start_utc": begins,
        "delivery_end_utc": begins + pd.Timedelta(resolution, unit="min"),
        "market_day": None,
        "source": "noaa_gfs",
        "dataset": "gfs.0p25",
        "variable": variable,
        "area": "GR",
        "unit": VARIABLE_UNITS[variable] if unit is None else unit,
        "resolution_minutes": resolution,
        "value": value,
        "published_at_utc": None if published is None else pd.Timestamp(published),
        "retrieved_at_utc": pd.Timestamp(retrieved),
        "source_document_id": document,
        "source_revision": revision,
        "raw_sha256": digest,
        "forecast_issue_time_utc": pd.Timestamp(issued),
        "forecast_horizon_minutes": None,
        "availability_evidence_grade": grade,
        "availability_evidence_detail": "s3_last_modified",
    }


def _frame(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(list(rows) or [_row()])


class SchemaShapeTests(unittest.TestCase):
    def test_a_validated_table_carries_every_column_in_canonical_order(self) -> None:
        frame = ensure_point_in_time(_frame())
        self.assertEqual(tuple(frame.columns), POINT_IN_TIME_COLUMNS)

    def test_an_unknown_column_cannot_ride_along(self) -> None:
        frame = _frame()
        frame["operator_note"] = "hello"
        with self.assertRaisesRegex(PointInTimeSchemaError, "Unknown point-in-time columns"):
            ensure_point_in_time(frame)

    def test_the_market_day_is_derived_from_the_market_clock(self) -> None:
        # 22:00 UTC on 25 August is 00:00 CEST on 26 August, so the value belongs to the 26th.
        frame = ensure_point_in_time(_frame(_row(start="2026-08-25T22:00:00+00:00")))
        self.assertEqual(frame.at[0, "market_day"], date(2026, 8, 26))

    def test_a_supplied_market_day_that_disagrees_is_refused(self) -> None:
        row = _row(start="2026-08-25T22:00:00+00:00")
        row["market_day"] = date(2026, 8, 25)
        with self.assertRaisesRegex(PointInTimeSchemaError, "market_day disagrees"):
            ensure_point_in_time(_frame(row))

    def test_the_forecast_horizon_is_derived_and_verified(self) -> None:
        frame = ensure_point_in_time(_frame(_row(start="2026-08-26T00:00:00+00:00")))
        self.assertEqual(float(frame.at[0, "forecast_horizon_minutes"]), 1440.0)
        row = _row()
        row["forecast_horizon_minutes"] = 60
        with self.assertRaisesRegex(PointInTimeSchemaError, "forecast_horizon_minutes disagrees"):
            ensure_point_in_time(_frame(row))

    def test_a_resolution_that_disagrees_with_its_interval_is_refused(self) -> None:
        row = _row()
        row["delivery_end_utc"] = row["delivery_start_utc"] + pd.Timedelta(30, unit="min")
        with self.assertRaisesRegex(PointInTimeSchemaError, "resolution_minutes disagrees"):
            ensure_point_in_time(_frame(row))


class MissingPublicationTimeTests(unittest.TestCase):
    """Design section 11, case 5."""

    def test_an_accepted_table_refuses_a_row_with_no_publication_instant(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "published_at_utc is absent"):
            ensure_point_in_time(_frame(_row(published=None)))

    def test_the_quarantine_path_retains_it_only_under_the_assumed_grade(self) -> None:
        quarantined = ensure_point_in_time(
            _frame(_row(published=None, grade=ASSUMED)), require_publication_time=False
        )
        self.assertEqual(len(quarantined), 1)
        self.assertTrue(pd.isna(quarantined.at[0, "published_at_utc"]))

    def test_a_row_without_a_publication_instant_may_not_claim_a_stronger_grade(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "do not carry"):
            ensure_point_in_time(
                _frame(_row(published=None, grade=PROVIDER_DECLARED)),
                require_publication_time=False,
            )

    def test_a_value_retrieved_before_it_was_published_is_refused(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "cannot be retrieved"):
            ensure_point_in_time(
                _frame(
                    _row(
                        published="2026-08-26T10:00:00+00:00",
                        retrieved="2026-08-26T09:00:00+00:00",
                    )
                )
            )

    def test_a_naive_instant_is_refused_rather_than_localized(self) -> None:
        row = _row()
        row["published_at_utc"] = pd.Timestamp("2026-08-25T04:00:00")
        with self.assertRaisesRegex(PointInTimeSchemaError, "timezone aware"):
            ensure_point_in_time(_frame(row))


class UnitRegistryTests(unittest.TestCase):
    """Design section 11, case 12."""

    def test_a_unit_that_is_not_the_registered_one_is_refused(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "no silent unit conversion"):
            ensure_point_in_time(_frame(_row(variable="dswrf_surface", unit="kW/m2")))

    def test_an_unregistered_variable_is_refused_by_name(self) -> None:
        row = _row()
        row["variable"] = "realized_price_gr"
        row["unit"] = "EUR/MWh"
        with self.assertRaisesRegex(PointInTimeSchemaError, "Unregistered feature variables"):
            ensure_point_in_time(_frame(row))

    def test_every_registered_variable_declares_a_unit(self) -> None:
        for variable, unit in VARIABLE_UNITS.items():
            with self.subTest(variable=variable):
                self.assertTrue(unit.strip())


class DuplicateTests(unittest.TestCase):
    """Design section 11, case 13."""

    def test_an_identical_duplicate_is_one_observation(self) -> None:
        frame = ensure_point_in_time(_frame(_row(), _row()))
        self.assertEqual(len(frame), 1)

    def test_a_conflicting_duplicate_names_both_rows_and_refuses(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "refuses to choose"):
            ensure_point_in_time(_frame(_row(value=300.0), _row(value=301.0)))

    def test_two_revisions_of_one_datum_are_two_rows(self) -> None:
        frame = ensure_point_in_time(
            _frame(
                _row(revision=1, value=300.0, digest="a" * 64),
                _row(revision=2, value=301.0, digest="b" * 64),
            )
        )
        self.assertEqual(len(frame), 2)
        # A revision is an identity, not a quantity: it is normalized to a string so that an
        # absent revision reads back from CSV as absent rather than as NaN.
        self.assertEqual(sorted(frame["source_revision"].tolist()), ["1", "2"])

    def test_a_digest_that_is_not_a_sha256_is_refused(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "raw_sha256"):
            ensure_point_in_time(_frame(_row(digest="not-a-digest")))


class OrderingTests(unittest.TestCase):
    def test_row_order_does_not_change_the_table(self) -> None:
        rows = [
            _row(start="2026-08-26T00:00:00+00:00", document="a", digest="a" * 64),
            _row(start="2026-08-26T01:00:00+00:00", document="b", digest="b" * 64),
            _row(
                start="2026-08-26T00:00:00+00:00",
                variable="dswrf_surface",
                value=0.0,
                document="c",
                digest="c" * 64,
            ),
        ]
        first = ensure_point_in_time(_frame(*rows))
        second = ensure_point_in_time(_frame(*reversed(rows)))
        pd.testing.assert_frame_equal(first, second)

    def test_validation_is_idempotent(self) -> None:
        once = ensure_point_in_time(_frame(_row()))
        pd.testing.assert_frame_equal(once, ensure_point_in_time(once))


class RoundTripTests(unittest.TestCase):
    def test_a_written_table_reads_back_identical(self) -> None:
        frame = ensure_point_in_time(
            _frame(
                _row(start="2026-08-26T00:00:00+00:00"),
                _row(start="2026-08-26T01:00:00+00:00", document="b", digest="b" * 64),
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.csv"
            write_point_in_time_csv(frame, path)
            restored = read_point_in_time_csv(path)
        pd.testing.assert_frame_equal(frame, restored)

    def test_coverage_counts_what_is_present_and_states_nothing_about_gaps(self) -> None:
        frame = ensure_point_in_time(
            _frame(
                _row(start="2026-08-26T00:00:00+00:00"),
                _row(start="2026-08-26T01:00:00+00:00", document="b", digest="b" * 64),
            )
        )
        coverage = feature_coverage(frame)
        self.assertEqual(coverage.at[0, "row_count"], 2)
        self.assertEqual(coverage.at[0, "distinct_interval_count"], 2)


class SamplingGeographyTests(unittest.TestCase):
    def test_the_committed_example_is_refused_as_a_declaration(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "not a declaration"):
            read_sampling_geography(CONFIG_DIR / "fundamentals_geography.example.json")

    def test_weights_must_form_an_aggregate(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "do not sum to one"):
            SamplingGeography.from_dict(
                {
                    "geography_id": "declared",
                    "area": "GR",
                    "points": [
                        {"point_id": "a", "latitude": 38.0, "longitude": 23.75, "weight": 0.4}
                    ],
                    "reference": "Declared for tests.",
                }
            )

    def test_a_geography_needs_at_least_one_point(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "at least one point"):
            SamplingGeography.from_dict(
                {
                    "geography_id": "declared",
                    "area": "GR",
                    "points": [],
                    "reference": "Declared for tests.",
                }
            )

    def test_only_the_greek_bidding_zone_is_sampled(self) -> None:
        with self.assertRaisesRegex(PointInTimeSchemaError, "Greek bidding zone"):
            SamplingGeography.from_dict(
                {
                    "geography_id": "declared",
                    "area": "DE",
                    "points": [
                        {"point_id": "a", "latitude": 51.0, "longitude": 10.0, "weight": 1.0}
                    ],
                    "reference": "Declared for tests.",
                }
            )


class MarketCalendarPropertyTests(unittest.TestCase):
    """Generated days, so a transition the examples missed still has to satisfy the schema."""

    @given(delivery_day=MARKET_DAYS)
    @SLOW
    def test_a_full_hourly_day_validates_and_derives_its_own_market_day(
        self, delivery_day: date
    ) -> None:
        starts = market_day_starts(delivery_day, 60).tz_convert(UTC)
        rows = [
            _row(
                start=start.isoformat(),
                document=f"key-f{index:03d}",
                digest=f"{index:064x}",
                issued=(start - pd.Timedelta(3, unit="D")).isoformat(),
                published=(start - pd.Timedelta(2, unit="D")).isoformat(),
                retrieved=(start + pd.Timedelta(1, unit="D")).isoformat(),
            )
            for index, start in enumerate(starts)
        ]
        frame = ensure_point_in_time(pd.DataFrame(rows))

        self.assertEqual(len(frame), expected_interval_count(delivery_day, 60))
        self.assertTrue((frame["market_day"] == delivery_day).all())
        self.assertTrue(frame["delivery_start_utc"].is_monotonic_increasing)

    @given(delivery_day=MARKET_DAYS)
    @SLOW
    def test_the_hours_of_a_transition_day_are_kept_apart_by_their_instants(
        self, delivery_day: date
    ) -> None:
        starts = market_day_starts(delivery_day, 60)
        local_labels = {start.strftime("%Y-%m-%d %H:%M") for start in starts}
        # A fall-back day repeats a wall-clock label; the UTC instants still differ, which is
        # exactly why the table is keyed on the instant and never on the label.
        self.assertEqual(len(set(starts.tz_convert(UTC))), len(starts))
        if len(starts) == 25:
            self.assertLess(len(local_labels), len(starts))

    @given(delivery_day=MARKET_DAYS, offset=st.integers(min_value=0, max_value=23))
    @SLOW
    def test_a_derived_market_day_matches_the_market_clock_for_any_hour(
        self, delivery_day: date, offset: int
    ) -> None:
        starts = market_day_starts(delivery_day, 60).tz_convert(UTC)
        start = starts[offset % len(starts)]
        frame = ensure_point_in_time(_frame(_row(start=start.isoformat())))
        self.assertEqual(
            frame.at[0, "market_day"], start.tz_convert(MARKET_TZ).date()
        )


class DayLengthTests(unittest.TestCase):
    def test_the_known_hard_days_have_the_lengths_the_market_calendar_says(self) -> None:
        self.assertEqual(expected_interval_count(date(2026, 3, 29), 60), 23)
        self.assertEqual(expected_interval_count(date(2026, 10, 25), 60), 25)
        self.assertEqual(
            expected_interval_count(date(2026, 3, 29) + timedelta(days=1), 60), 24
        )


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
