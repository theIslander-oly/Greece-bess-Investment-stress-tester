"""Synthetic-only tests for combining point-in-time feature shards.

The declared v0.9 window cannot be retrieved in one job, so it is retrieved in slices and put
back together. These tests hold the two properties that makes that sound: the recombination of
a tiling is exactly the table a single retrieval of the whole window would have produced, and
anything that is not a tiling is refused rather than silently resolved.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from greek_bess.data.feature_shards import (
    FeatureShardError,
    combine_feature_shards,
)
from greek_bess.data.point_in_time import (
    read_point_in_time_csv,
    write_point_in_time_csv,
)
from greek_bess.data.timezones import MARKET_TZ

VARIABLES = ("temperature_2m", "wind_speed_10m")


def _synthetic_day(day: date) -> pd.DataFrame:
    """One clearly synthetic delivery day, hourly, with floats that need every bit."""

    # The market day is the CET/CEST day, so its first interval opens at local midnight, and
    # the vintage is the 00 UTC cycle of the day before, as the declared source is.
    start = pd.Timestamp(day.isoformat(), tz=MARKET_TZ).tz_convert("UTC")
    issued = pd.Timestamp((day - timedelta(days=1)).isoformat(), tz="UTC")
    published = issued + pd.Timedelta(4, unit="h")

    rows = []
    for hour in range(24):
        opening = start + pd.Timedelta(hour, unit="h")
        for index, variable in enumerate(VARIABLES):
            rows.append(
                {
                    "delivery_start_utc": opening,
                    "delivery_end_utc": opening + pd.Timedelta(1, unit="h"),
                    "market_day": day,
                    "source": "synthetic",
                    "dataset": "synthetic.0p25",
                    "variable": variable,
                    "area": "GR",
                    "unit": "K" if variable == "temperature_2m" else "m/s",
                    "resolution_minutes": 60,
                    # A value whose shortest decimal form needs all 17 significant digits, so a
                    # lossy CSV round trip shows up as a difference rather than hiding.
                    "value": 300.06246393537225 + hour + index / 7.0,
                    "published_at_utc": published,
                    "retrieved_at_utc": pd.Timestamp("2026-06-01T00:00:00Z"),
                    "source_document_id": f"synthetic/{day.isoformat()}/{variable}",
                    "source_revision": "",
                    "raw_sha256": hashlib.sha256(
                        f"{day.isoformat()}|{variable}|{hour}".encode()
                    ).hexdigest(),
                    "forecast_issue_time_utc": issued,
                    "forecast_horizon_minutes": (opening - issued).total_seconds() / 60.0,
                    "availability_evidence_grade": "provider_declared",
                    "availability_evidence_detail": "synthetic fixture",
                }
            )
    return pd.DataFrame(rows)


def _write_shard(directory: Path, name: str, days: list[date]) -> Path:
    frame = pd.concat([_synthetic_day(day) for day in days], ignore_index=True)
    features = directory / f"{name}.csv"
    write_point_in_time_csv(frame, features)
    summary = {
        "result_label": "synthetic",
        "method": "point_in_time_feature_retrieval",
        "source": "synthetic",
        "variables": sorted(VARIABLES),
        "geography_id": "synthetic-geography",
        "geography": {"geography_id": "synthetic-geography"},
        "start_day": min(days).isoformat(),
        "end_day": max(days).isoformat(),
        "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
        "feature_row_count": int(len(frame)),
        "document_count": 0,
        "attribution": "synthetic fixture; no provider content",
        "excluded_days_by_cause": [],
        "per_delivery_day": [{"market_day": day.isoformat()} for day in days],
    }
    features.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return features


def _days(first: str, count: int) -> list[date]:
    start = date.fromisoformat(first)
    return [start + timedelta(days=offset) for offset in range(count)]


class CombineFeatureShardsTests(unittest.TestCase):
    def test_a_tiling_reproduces_the_single_window_table_exactly(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            whole_days = _days("2026-03-01", 6)
            whole = _write_shard(directory, "whole", whole_days)
            first = _write_shard(directory, "first", whole_days[:2])
            second = _write_shard(directory, "second", whole_days[2:4])
            third = _write_shard(directory, "third", whole_days[4:])

            combined, summary, _ = combine_feature_shards(
                [third, first, second], created_at_utc="2026-01-02T00:00:00+00:00"
            )
            expected = read_point_in_time_csv(whole)

            pd.testing.assert_frame_equal(
                expected.reset_index(drop=True),
                combined.reset_index(drop=True),
                check_exact=True,
            )
            self.assertEqual(summary["start_day"], whole_days[0].isoformat())
            self.assertEqual(summary["end_day"], whole_days[-1].isoformat())
            self.assertEqual(summary["shard_count"], 3)
            self.assertEqual(summary["feature_row_count"], int(len(expected)))

    def test_the_combined_table_survives_another_write_and_read_unchanged(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            days = _days("2026-03-01", 4)
            first = _write_shard(directory, "first", days[:2])
            second = _write_shard(directory, "second", days[2:])
            combined, _, _ = combine_feature_shards(
                [first, second], created_at_utc="2026-01-02T00:00:00+00:00"
            )
            round_tripped = directory / "combined.csv"
            write_point_in_time_csv(combined, round_tripped)
            pd.testing.assert_frame_equal(
                combined.reset_index(drop=True),
                read_point_in_time_csv(round_tripped).reset_index(drop=True),
                check_exact=True,
            )

    def test_overlapping_shards_are_refused_rather_than_deduplicated(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            first = _write_shard(directory, "first", _days("2026-03-01", 3))
            second = _write_shard(directory, "second", _days("2026-03-03", 3))
            with self.assertRaises(FeatureShardError) as caught:
                combine_feature_shards(
                    [first, second], created_at_utc="2026-01-02T00:00:00+00:00"
                )
            self.assertIn("overlap", str(caught.exception))

    def test_a_gap_between_shards_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            first = _write_shard(directory, "first", _days("2026-03-01", 2))
            second = _write_shard(directory, "second", _days("2026-03-05", 2))
            with self.assertRaises(FeatureShardError) as caught:
                combine_feature_shards(
                    [first, second], created_at_utc="2026-01-02T00:00:00+00:00"
                )
            self.assertIn("2026-03-03..2026-03-04", str(caught.exception))

    def test_shards_retrieved_under_a_different_geography_are_refused(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            first = _write_shard(directory, "first", _days("2026-03-01", 2))
            second = _write_shard(directory, "second", _days("2026-03-03", 2))
            summary_path = second.with_suffix(".summary.json")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["geography_id"] = "a-different-declared-geography"
            summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(FeatureShardError) as caught:
                combine_feature_shards(
                    [first, second], created_at_utc="2026-01-02T00:00:00+00:00"
                )
            self.assertIn("geography_id", str(caught.exception))

    def test_a_shard_without_its_summary_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            first = _write_shard(directory, "first", _days("2026-03-01", 2))
            first.with_suffix(".summary.json").unlink()
            with self.assertRaises(FeatureShardError) as caught:
                combine_feature_shards([first], created_at_utc="2026-01-02T00:00:00+00:00")
            self.assertIn("no retrieval summary", str(caught.exception))

    def test_no_shards_is_refused(self) -> None:
        with self.assertRaises(FeatureShardError):
            combine_feature_shards([], created_at_utc="2026-01-02T00:00:00+00:00")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
