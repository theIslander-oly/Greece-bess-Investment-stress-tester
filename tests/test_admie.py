from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from greek_bess.cli import main
from greek_bess.data.admie import (
    LEAKAGE_RELEVANT_FILETYPES,
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
            "20260826_ISP2DayAheadLoadForecast_01.xlsx": b"revision-one",
            "20260826_ISP2DayAheadLoadForecast_02.xlsx": b"revision-two",
        }
        api_payload = [
            _api_record("20260826_ISP2DayAheadLoadForecast_01.xlsx", "25.08.2026 09:00"),
            _api_record("20260826_ISP2DayAheadLoadForecast_02.xlsx", "25.08.2026 11:00"),
        ]

        def fetcher(url: str) -> bytes:
            parsed = urlsplit(url)
            if parsed.path == "/getOperationMarketFilewRange":
                query = parse_qs(parsed.query)
                self.assertEqual(query["FileCategory"], ["ISP2DayAheadLoadForecast"])
                return json.dumps(api_payload).encode()
            return file_payloads[Path(parsed.path).name]

        client = AdmieClient(fetcher=fetcher)
        discovered = client.find_files(
            "ISP2DayAheadLoadForecast", date(2026, 8, 26), date(2026, 8, 26)
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

    def test_leakage_relevant_filetypes_match_live_catalog_acceptance(self) -> None:
        self.assertEqual(
            LEAKAGE_RELEVANT_FILETYPES,
            {
                "ISP1DayAheadLoadForecast",
                "ISP1DayAheadRESForecast",
                "ISP2DayAheadLoadForecast",
                "ISP2DayAheadRESForecast",
            },
        )

    def test_foreign_download_host_is_rejected(self) -> None:
        payload = _api_record("20260826_DayAheadLoadForecast_01.xlsx", "25.08.2026 09:00")
        payload["file_path"] = "https://example.com/untrusted.xlsx"
        client = AdmieClient(fetcher=lambda _url: json.dumps([payload]).encode())
        with self.assertRaisesRegex(AdmieError, "invalid URL"):
            client.find_files(
                "DayAheadLoadForecast", date(2026, 8, 26), date(2026, 8, 26)
            )


class EmptyDiscoveryTests(unittest.TestCase):
    """An empty ADMIE retrieval must not be written as an empty manifest.

    The first live audit run (2026-08-31) discovered zero files and produced `no_record` for
    every audited delivery day — a verdict that reads as "the publisher published nothing",
    which is one of the four things the timing audit explicitly does not establish. A wrong
    filetype name must not be able to impersonate that finding.
    """

    def _run(self, catalog: list[str]) -> str:
        client = mock.MagicMock()
        client.find_files.return_value = []
        client.list_filetypes.return_value = [{"filetype": name} for name in catalog]
        errors = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch("greek_bess.cli.admie.AdmieClient", return_value=client),
                redirect_stdout(io.StringIO()),
                redirect_stderr(errors),
            ):
                code = main(
                    [
                        "fetch-admie-files",
                        "--filetypes",
                        "DayAheadLoadForecast",
                        "--start-day",
                        "2026-08-26",
                        "--end-day",
                        "2026-08-28",
                        "--raw-dir",
                        directory,
                    ]
                )
        self.assertEqual(code, 1)
        return errors.getvalue()

    def test_a_filetype_the_provider_does_not_publish_is_named(self) -> None:
        message = self._run(["ISP1DayAheadLoadForecast", "RealTimeSCADARES"])

        self.assertIn("publishes no filetype named DayAheadLoadForecast", message)
        self.assertIn("ISP1DayAheadLoadForecast", message)

    def test_a_valid_filetype_with_an_empty_window_is_reported_differently(self) -> None:
        message = self._run(["DayAheadLoadForecast"])

        self.assertIn("empty window rather than a wrong name", message)

    def test_an_unreadable_catalog_still_refuses_the_empty_retrieval(self) -> None:
        client = mock.MagicMock()
        client.find_files.return_value = []
        client.list_filetypes.side_effect = AdmieError("catalog unavailable")
        errors = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch("greek_bess.cli.admie.AdmieClient", return_value=client),
                redirect_stdout(io.StringIO()),
                redirect_stderr(errors),
            ):
                code = main(
                    [
                        "fetch-admie-files",
                        "--filetypes",
                        "DayAheadLoadForecast",
                        "--start-day",
                        "2026-08-26",
                        "--end-day",
                        "2026-08-28",
                        "--raw-dir",
                        directory,
                    ]
                )

        self.assertEqual(code, 1)
        self.assertIn("could not be read to check the names", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
