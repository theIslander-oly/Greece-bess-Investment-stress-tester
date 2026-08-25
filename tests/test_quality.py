from __future__ import annotations

import unittest
from datetime import date, timedelta

from greek_bess.data.quality import assess_quality, compare_sources
from greek_bess.data.synthetic import generate_synthetic_prices


class QualityTests(unittest.TestCase):
    def test_complete_dst_day_is_valid(self) -> None:
        frame = generate_synthetic_prices(
            date(2026, 3, 29), date(2026, 3, 30), resolution_minutes=15
        )
        report = assess_quality(frame)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.row_count, 92)

    def test_missing_interval_is_invalid(self) -> None:
        frame = generate_synthetic_prices(date(2026, 2, 1), date(2026, 2, 2))
        report = assess_quality(frame.drop(index=5).reset_index(drop=True))
        self.assertFalse(report.is_valid)
        self.assertIn("incomplete_market_day", [issue.code for issue in report.issues])

    def test_cross_source_comparison_finds_one_mismatch(self) -> None:
        left = generate_synthetic_prices(date(2026, 2, 1), date(2026, 2, 2))
        left["source"] = "entsoe"
        left["source_version"] = "a"
        right = left.copy(deep=True)
        right["source"] = "henex"
        right["source_version"] = "b"
        right.loc[3, "price_eur_per_mwh"] += 0.5
        comparison = compare_sources(left, right, tolerance_eur_per_mwh=0.001)
        self.assertEqual((comparison["comparison_status"] == "price_mismatch").sum(), 1)
        self.assertEqual((comparison["comparison_status"] == "match").sum(), 23)


if __name__ == "__main__":
    unittest.main()

