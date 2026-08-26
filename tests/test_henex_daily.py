from __future__ import annotations

import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from greek_bess.data.henex_daily import HenexDailyClient, HenexDailyError, _catalog_url


def _xlsx_bytes() -> bytes:
    frame = pd.DataFrame(
        [
            {
                "DDAY": "2026-08-25",
                "SORT": 1,
                "DELIVERY_DURATION": 15,
                "MCP": 72.5,
                "VER": 2,
            }
        ]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    return buffer.getvalue()


class HenexDailyTests(unittest.TestCase):
    def test_live_catalog_layout_omits_xlsx_suffix(self) -> None:
        catalog = b"""
        <html><body>
          <a href="/markets-publications-el-day-ahead-market/-/asset_publisher/
          6eBaUXF5VIb7/document/id/1">20260825_EL-DAM_Results_EN_v01</a>
        </body></html>
        """

        client = HenexDailyClient(fetcher=lambda _: catalog)
        entries = client.discover(
            date(2026, 8, 25), date(2026, 8, 25), max_pages=1
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].filename, "20260825_EL-DAM_Results_EN_v01.xlsx")

    def test_catalog_url_matches_live_liferay_pagination(self) -> None:
        url = _catalog_url(2)

        self.assertIn("/web/guest/markets-publications-el-day-ahead-market?", url)
        self.assertIn("_cur=2", url)
        self.assertIn("_redirect=%2Fmarkets-publications-el-day-ahead-market", url)

    def test_discovery_continues_past_pages_newer_than_requested_range(self) -> None:
        pages = {
            "_cur=1": b'<a href="/new">20260825_EL-DAM_Results_EN_v01</a>',
            "_cur=2": b'<a href="/target">20260101_EL-DAM_Results_EN_v01</a>',
            "_cur=3": b'<a href="/old">20251231_EL-DAM_Results_EN_v01</a>',
        }

        def fetcher(url: str) -> bytes:
            return next(payload for marker, payload in pages.items() if marker in url)

        entries = HenexDailyClient(fetcher=fetcher).discover(
            date(2026, 1, 1), date(2026, 1, 1), max_pages=3
        )

        self.assertEqual([entry.delivery_day for entry in entries], [date(2026, 1, 1)])

    def test_repeated_catalog_page_is_rejected(self) -> None:
        catalog = b'<a href="/same">20260825_EL-DAM_Results_EN_v01</a>'

        with self.assertRaisesRegex(HenexDailyError, "pagination repeated"):
            HenexDailyClient(fetcher=lambda _: catalog).discover(
                date(2026, 1, 1), date(2026, 8, 25), max_pages=2
            )

    def test_missing_requested_delivery_day_is_rejected(self) -> None:
        catalog = b'<a href="/one">20260825_EL-DAM_Results_EN_v01</a>'

        with self.assertRaisesRegex(HenexDailyError, "first missing day: 2026-08-24"):
            HenexDailyClient(fetcher=lambda _: catalog).discover(
                date(2026, 8, 24), date(2026, 8, 25), max_pages=1
            )

    def test_catalog_discovery_prefers_latest_revision_and_downloads_xlsx(self) -> None:
        catalog = b"""
        <html><body>
          <a href="/markets-publications-el-day-ahead-market/-/asset_publisher/
          6eBaUXF5VIb7/document/id/1">20260825_EL-DAM_Results_EN_v01.xlsx</a>
          <a href="/markets-publications-el-day-ahead-market/-/asset_publisher/
          6eBaUXF5VIb7/document/id/2">20260825_EL-DAM_Results_EN_v02.xlsx</a>
        </body></html>
        """
        detail = b"""
        <a href="/documents/20126/1/20260825_EL-DAM_Results_EN_v02.xlsx/uuid">
        Download</a>
        """

        def fetcher(url: str) -> bytes:
            path = urlsplit(url).path
            if "asset_publisher" in path and path.endswith("/2"):
                return detail
            if "/documents/" in path:
                return _xlsx_bytes()
            return catalog

        client = HenexDailyClient(fetcher=fetcher)
        entries = client.discover(
            date(2026, 8, 25), date(2026, 8, 25), max_pages=1
        )
        with tempfile.TemporaryDirectory() as directory:
            workbooks, records = client.download_results(
                entries,
                raw_dir=Path(directory),
                retrieved_at_utc="2026-08-26T08:00:00+00:00",
            )
            downloaded = workbooks[0].read_bytes()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].revision, 2)
        self.assertEqual(len(records), 1)
        self.assertTrue(downloaded.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
