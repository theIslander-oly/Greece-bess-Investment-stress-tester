"""Property-based checks on the canonical schema and the market-day clock.

The example-based suites pin the known-hard days: 2025-03-30 with 23 hours,
2025-10-26 with 25, and their quarter-hour counterparts. These generate the
calendar instead of enumerating it, so a transition rule that changes, or a day
nobody thought to write down, still has to satisfy the same invariants.
"""

from __future__ import annotations

import json
import unittest
from datetime import date, timedelta

import pandas as pd
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import (
    CANONICAL_COLUMNS,
    ensure_canonical,
    read_canonical_csv,
)
from greek_bess.data.timezones import (
    GREECE_TZ,
    MARKET_TZ,
    UTC,
    expected_interval_count,
    market_day_starts,
    parse_iso_duration,
)

# Wide enough to contain many spring-forward and fall-back days under the
# current European rule, and to keep running if that rule is ever changed.
MARKET_DAYS = st.dates(min_value=date(2015, 1, 1), max_value=date(2035, 12, 31))
RESOLUTIONS = st.sampled_from([15, 60])

SPRING_FORWARD = date(2025, 3, 30)
FALL_BACK = date(2025, 10, 26)

SLOW = settings(
    max_examples=150,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def canonical_day(delivery_day: date, resolution_minutes: int) -> pd.DataFrame:
    """Build a complete, well-formed canonical frame for one market day."""

    starts = market_day_starts(delivery_day, resolution_minutes)
    starts_utc = starts.tz_convert(UTC)
    duration = pd.Timedelta(resolution_minutes, unit="min")
    return ensure_canonical(
        pd.DataFrame(
            {
                "delivery_start_utc": starts_utc,
                "delivery_end_utc": starts_utc + duration,
                "delivery_start_market": starts,
                "delivery_start_greece": starts_utc.tz_convert(GREECE_TZ),
                "duration_hours": resolution_minutes / 60,
                "price_eur_per_mwh": [
                    float(index % 97) - 20.0 for index in range(len(starts))
                ],
                "bidding_zone": "GR",
                "source": "synthetic",
                "source_version": "property-test",
                "retrieved_at_utc": pd.Timestamp("2026-01-01T00:00:00Z"),
                "raw_sha256": "synthetic-no-official-source",
                "quality_flags": [["synthetic_demo_data"] for _ in range(len(starts))],
            }
        )
    )


class MarketDayClockProperties(unittest.TestCase):
    @given(delivery_day=MARKET_DAYS, resolution_minutes=RESOLUTIONS)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=60)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=15)
    @example(delivery_day=FALL_BACK, resolution_minutes=60)
    @example(delivery_day=FALL_BACK, resolution_minutes=15)
    @SLOW
    def test_a_market_day_is_contiguous_and_covers_exactly_one_local_day(
        self, delivery_day: date, resolution_minutes: int
    ) -> None:
        starts = market_day_starts(delivery_day, resolution_minutes)
        starts_utc = starts.tz_convert(UTC)

        self.assertGreater(len(starts), 0)
        self.assertEqual(len(starts), expected_interval_count(delivery_day, resolution_minutes))

        # Every interval abuts the next in real elapsed time, whatever the wall
        # clock did in between.
        gaps = starts_utc.to_series().diff().dropna()
        self.assertTrue(
            (gaps == pd.Timedelta(resolution_minutes, unit="min")).all(),
            f"{delivery_day} is not contiguous in UTC",
        )

        # The day starts at local midnight and ends at the next local midnight.
        self.assertEqual(
            starts[0], pd.Timestamp(delivery_day).tz_localize(MARKET_TZ)
        )
        expected_end = pd.Timestamp(delivery_day + timedelta(days=1)).tz_localize(MARKET_TZ)
        self.assertEqual(
            starts_utc[-1] + pd.Timedelta(resolution_minutes, unit="min"),
            expected_end.tz_convert(UTC),
        )

    @given(delivery_day=MARKET_DAYS, resolution_minutes=RESOLUTIONS)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=60)
    @example(delivery_day=FALL_BACK, resolution_minutes=15)
    @SLOW
    def test_only_the_three_legal_day_lengths_are_ever_produced(
        self, delivery_day: date, resolution_minutes: int
    ) -> None:
        count = expected_interval_count(delivery_day, resolution_minutes)
        legal = {60: {23, 24, 25}, 15: {92, 96, 100}}[resolution_minutes]
        self.assertIn(count, legal, f"{delivery_day} produced {count} intervals")

        # The interval count and the real elapsed duration have to tell the
        # same story: a 23-hour day is short because time was skipped, not
        # because an interval went missing.
        starts = market_day_starts(delivery_day, resolution_minutes)
        elapsed = (
            pd.Timestamp(delivery_day + timedelta(days=1)).tz_localize(MARKET_TZ)
            - pd.Timestamp(delivery_day).tz_localize(MARKET_TZ)
        )
        self.assertEqual(
            elapsed, len(starts) * pd.Timedelta(resolution_minutes, unit="min")
        )

    @given(delivery_day=MARKET_DAYS)
    @SLOW
    def test_the_two_resolutions_describe_the_same_day(self, delivery_day: date) -> None:
        hourly = market_day_starts(delivery_day, 60)
        quarterly = market_day_starts(delivery_day, 15)

        self.assertEqual(len(quarterly), 4 * len(hourly))
        # Every hourly start is also a quarter-hourly start, on both a 23- and
        # a 25-hour day.
        self.assertTrue(set(hourly.tz_convert(UTC)) <= set(quarterly.tz_convert(UTC)))

    @given(
        hours=st.integers(min_value=0, max_value=48),
        minutes=st.integers(min_value=0, max_value=59),
    )
    def test_iso_durations_parse_to_their_own_length(
        self, hours: int, minutes: int
    ) -> None:
        assume(hours or minutes)
        parsed = parse_iso_duration(f"PT{hours}H{minutes}M")
        self.assertEqual(parsed, timedelta(hours=hours, minutes=minutes))


class CanonicalSchemaProperties(unittest.TestCase):
    @given(delivery_day=MARKET_DAYS, resolution_minutes=RESOLUTIONS)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=60)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=15)
    @example(delivery_day=FALL_BACK, resolution_minutes=60)
    @example(delivery_day=FALL_BACK, resolution_minutes=15)
    @SLOW
    def test_a_generated_market_day_passes_the_quality_gate(
        self, delivery_day: date, resolution_minutes: int
    ) -> None:
        report = assess_quality(
            canonical_day(delivery_day, resolution_minutes),
            require_complete_days=True,
        )
        self.assertTrue(
            report.is_valid,
            f"{delivery_day} at {resolution_minutes}min: "
            + "; ".join(f"{issue.code}: {issue.message}" for issue in report.issues),
        )

    @given(
        delivery_day=MARKET_DAYS,
        resolution_minutes=RESOLUTIONS,
        seed=st.integers(min_value=0, max_value=2**32 - 1),
    )
    @SLOW
    def test_canonicalization_does_not_depend_on_input_row_order(
        self, delivery_day: date, resolution_minutes: int, seed: int
    ) -> None:
        frame = canonical_day(delivery_day, resolution_minutes)
        shuffled = frame.sample(frac=1.0, random_state=seed % (2**31))

        pd.testing.assert_frame_equal(ensure_canonical(shuffled), frame)

    @given(delivery_day=MARKET_DAYS, resolution_minutes=RESOLUTIONS)
    @example(delivery_day=FALL_BACK, resolution_minutes=60)
    @SLOW
    def test_canonicalization_is_idempotent(
        self, delivery_day: date, resolution_minutes: int
    ) -> None:
        frame = canonical_day(delivery_day, resolution_minutes)
        pd.testing.assert_frame_equal(ensure_canonical(frame), frame)
        self.assertEqual(list(frame.columns), CANONICAL_COLUMNS)

    @given(delivery_day=MARKET_DAYS, resolution_minutes=RESOLUTIONS)
    @example(delivery_day=SPRING_FORWARD, resolution_minutes=15)
    @example(delivery_day=FALL_BACK, resolution_minutes=15)
    @SLOW
    def test_a_market_day_round_trips_through_the_canonical_csv(
        self, delivery_day: date, resolution_minutes: int
    ) -> None:
        import tempfile
        from pathlib import Path

        frame = canonical_day(delivery_day, resolution_minutes)
        export = frame.copy()
        export["quality_flags"] = export["quality_flags"].map(json.dumps)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.csv"
            export.to_csv(path, index=False)
            restored = read_canonical_csv(path)

        pd.testing.assert_frame_equal(restored, frame)


class CanonicalTimestampResolutionTests(unittest.TestCase):
    """Regression cover for the resolution mismatch the property suite found.

    `generate_synthetic_prices` stamps `retrieved_at_utc` from `Timestamp.now`,
    which is microsecond resolution, while `read_canonical_csv` parses into
    nanoseconds. Before `ensure_canonical` normalized the unit, a history and the
    same history written to CSV and read back described identical instants and
    still compared unequal.
    """

    def test_a_generated_history_equals_itself_after_a_csv_round_trip(self) -> None:
        import tempfile
        from pathlib import Path

        from greek_bess.data.synthetic import generate_synthetic_prices

        frame = generate_synthetic_prices(date(2025, 3, 29), date(2025, 4, 1))
        export = frame.copy()
        export["quality_flags"] = export["quality_flags"].map(json.dumps)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            export.to_csv(path, index=False)
            restored = read_canonical_csv(path)

        pd.testing.assert_frame_equal(restored, frame)

    def test_every_canonical_timestamp_column_shares_one_resolution(self) -> None:
        from greek_bess.data.synthetic import generate_synthetic_prices

        frame = generate_synthetic_prices(date(2025, 6, 1), date(2025, 6, 3))
        for column in (
            "delivery_start_utc",
            "delivery_end_utc",
            "retrieved_at_utc",
            "delivery_start_market",
            "delivery_start_greece",
        ):
            self.assertEqual(frame[column].dt.unit, "ns", column)


if __name__ == "__main__":
    unittest.main()
