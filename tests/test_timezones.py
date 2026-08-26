from __future__ import annotations

import unittest
from datetime import date

from greek_bess.data.timezones import expected_interval_count, parse_iso_duration


class TimezoneTests(unittest.TestCase):
    def test_normal_and_dst_hour_counts(self) -> None:
        self.assertEqual(expected_interval_count(date(2026, 2, 1), 60), 24)
        self.assertEqual(expected_interval_count(date(2026, 3, 29), 60), 23)
        self.assertEqual(expected_interval_count(date(2026, 10, 25), 60), 25)

    def test_normal_and_dst_quarter_hour_counts(self) -> None:
        self.assertEqual(expected_interval_count(date(2026, 2, 1), 15), 96)
        self.assertEqual(expected_interval_count(date(2026, 3, 29), 15), 92)
        self.assertEqual(expected_interval_count(date(2026, 10, 25), 15), 100)

    def test_entsoe_resolutions(self) -> None:
        self.assertEqual(parse_iso_duration("PT60M").total_seconds(), 3600)
        self.assertEqual(parse_iso_duration("PT15M").total_seconds(), 900)


if __name__ == "__main__":
    unittest.main()

