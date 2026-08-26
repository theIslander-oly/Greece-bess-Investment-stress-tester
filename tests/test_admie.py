from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from greek_bess.data.admie import (
    AdmieClient,
    AdmieError,
    select_latest_admie_revisions,
)


def _api_record(filename: str, published: str) -> dict[str, str]:
    return {
        "file_path": (
            "https://www.admie.gr/sites/default/files/attached-files/type-file/2026/08/"
            + filename
        ),
        "file_description": "Day-ahead load forecast",
        "file_process": "DAM",
        "file_datatype": "Load Forecast",
        "file_coverageperiod": "DAY",
        "file_fromdate": "26.08.2026",
        "file_todate": "26.08.2026",
        "file_published": published,
    }


class AdmieClientTests(unittest.TestCase):
    def test_find_select_latest_download_and_manifest(self) -> None:
        file_payloads = {
            "20260826_DayAheadLoadForecast_01.xlsx": b"revision-one",
            "20260826_DayAheadLoadForecast_02.xlsx": b"revision-two",
        }
        api_payload = [
            _api_record("20260826_DayAheadLoadForecast_01.xlsx", "25.08.2026 09:00"),
            _api_record("20260826_DayAheadLoadForecast_02.xlsx", "25.08.2026 11:00"),
        ]

        def fetcher(url: str) -> bytes:
            parsed = urlsplit(url)
            if parsed.path == "/getOperationMarketFilewRange":
                query = parse_qs(parsed.query)
                self.assertEqual(query["FileCategory"], ["DayAheadLoadForecast"])
                return json.dumps(api_payload).encode()
            return file_payloads[Path(parsed.path).name]

        client = AdmieClient(fetcher=fetcher)
        discovered = client.find_files(
            "DayAheadLoadForecast", date(2026, 8, 26), date(2026, 8, 26)
        )
        selected = select_latest_admie_revisions(discovered)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            records = client.download_files(
                selected,
                raw_dir=root,
                manifest_path=manifest,
                retrieved_at_utc="2026-08-26T08:00:00+00:00",
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            downloaded = root / records[0].local_path
            downloaded_bytes = downloaded.read_bytes()

        self.assertEqual(len(discovered), 2)
        self.assertEqual([record.revision for record in selected], [2])
        self.assertEqual(downloaded_bytes, b"revision-two")
        self.assertEqual(payload["records"][0]["published_at_utc"], "2026-08-25T08:00:00+00:00")
        self.assertEqual(
            payload["records"][0]["availability_classification"],
            "requires_pre_auction_timing_validation",
        )

    def test_foreign_download_host_is_rejected(self) -> None:
        payload = _api_record("20260826_DayAheadLoadForecast_01.xlsx", "25.08.2026 09:00")
        payload["file_path"] = "https://example.com/untrusted.xlsx"
        client = AdmieClient(fetcher=lambda _url: json.dumps([payload]).encode())
        with self.assertRaisesRegex(AdmieError, "invalid URL"):
            client.find_files(
                "DayAheadLoadForecast", date(2026, 8, 26), date(2026, 8, 26)
            )


if __name__ == "__main__":
    unittest.main()

