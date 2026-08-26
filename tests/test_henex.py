from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from greek_bess.data.henex import HenexParseError, parse_henex_results
from greek_bess.data.quality import assess_quality


class HenexParserTests(unittest.TestCase):
    def _write_workbook(
        self, frame: pd.DataFrame, directory: str, *, startrow: int = 0
    ) -> Path:
        path = Path(directory) / "20260115_EL-DAM_Results_EN_v01.xlsx"
        frame.to_excel(path, index=False, sheet_name="Results", startrow=startrow)
        return path

    def test_reduces_repeated_asset_rows_to_one_price_per_mtu(self) -> None:
        rows = []
        for sort, price in [(1, -3.0), (2, 20.0), (3, 50.0), (4, 90.0)]:
            for asset in ("LOAD", "SUPPLY"):
                rows.append(
                    {
                        "DDAY": "2026-01-15",
                        "SORT": sort,
                        "DELIVERY_DURATION": 15,
                        "MCP": price,
                        "VER": 1,
                        "ASSET_DESCR": asset,
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_workbook(pd.DataFrame(rows), directory)
            frame = parse_henex_results(path, retrieved_at_utc="2026-01-14T12:00Z")
        self.assertEqual(len(frame), 4)
        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [-3.0, 20.0, 50.0, 90.0])
        self.assertEqual(frame["source_version"].unique().tolist(), ["v01"])

    def test_discovers_header_below_preamble_rows(self) -> None:
        rows = [
            {
                "DDAY": "2026-01-15",
                "SORT": 1,
                "DELIVERY_DURATION": 15,
                "MCP": 45,
                "VER": 1,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_workbook(pd.DataFrame(rows), directory, startrow=4)
            frame = parse_henex_results(path)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["price_eur_per_mwh"], 45)

    def test_conflicting_prices_are_rejected(self) -> None:
        rows = [
            {"DDAY": "2026-01-15", "SORT": 1, "DELIVERY_DURATION": 15, "MCP": 10, "VER": 1},
            {"DDAY": "2026-01-15", "SORT": 1, "DELIVERY_DURATION": 15, "MCP": 11, "VER": 1},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_workbook(pd.DataFrame(rows), directory)
            with self.assertRaisesRegex(HenexParseError, "Conflicting MCP"):
                parse_henex_results(path)

    def test_one_cent_rounding_consensus_is_flagged(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "DDAY": "2025-01-01",
                    "SORT": 1,
                    "DELIVERY_DURATION": 60,
                    "MCP": price,
                    "VER": 1,
                }
                for price in (70.05, 70.05, 70.04)
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "20250101_EL-DAM_Results_EN_v01.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                rows.to_excel(writer, index=False)
            frame = parse_henex_results(path)
            report = assess_quality(frame, require_complete_days=False)

        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [70.05])
        self.assertEqual(
            frame["quality_flags"].tolist(), [["henex_mcp_rounding_consensus"]]
        )
        self.assertEqual(
            [(issue.code, issue.count) for issue in report.issues],
            [("henex_mcp_rounding_consensus", 1)],
        )

    def test_large_majority_price_disagreement_is_rejected(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "DDAY": "2025-01-01",
                    "SORT": 1,
                    "DELIVERY_DURATION": 60,
                    "MCP": price,
                    "VER": 1,
                }
                for price in (70.0, 70.0, 20.0)
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "20250101_EL-DAM_Results_EN_v01.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                rows.to_excel(writer, index=False)
            with self.assertRaisesRegex(HenexParseError, "Conflicting MCP"):
                parse_henex_results(path)

    def test_fall_back_sort_maps_to_25_distinct_hourly_intervals(self) -> None:
        rows = [
            {
                "DDAY": date(2026, 10, 25),
                "SORT": sort,
                "DELIVERY_DURATION": 60,
                "MCP": sort,
                "VER": 1,
            }
            for sort in range(1, 26)
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_workbook(pd.DataFrame(rows), directory)
            frame = parse_henex_results(path)
        self.assertEqual(len(frame), 25)
        self.assertEqual(frame["delivery_start_utc"].nunique(), 25)


if __name__ == "__main__":
    unittest.main()
