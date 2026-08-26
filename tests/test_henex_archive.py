from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from greek_bess.data.henex_archive import (
    HenexArchiveError,
    download_henex_annual_archives,
    normalize_henex_workbooks,
)


def _workbook_bytes(*, price: float, revision: int) -> bytes:
    rows = pd.DataFrame(
        [
            {
                "DDAY": "2025-01-01",
                "SORT": 1,
                "DELIVERY_DURATION": 60,
                "MCP": price,
                "VER": revision,
            }
        ]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        rows.to_excel(writer, index=False, sheet_name="Results")
    return buffer.getvalue()


def _archive_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("notes/readme.txt", "not market data")
        archive.writestr(
            "daily/20250101_EL-DAM_Results_EN_v01.xlsx",
            _workbook_bytes(price=50.0, revision=1),
        )
        archive.writestr(
            "daily/20250101_EL-DAM_Results_EN_v02.xlsx",
            _workbook_bytes(price=55.0, revision=2),
        )
    return buffer.getvalue()


class HenexArchiveTests(unittest.TestCase):
    def test_download_extract_manifest_and_latest_revision_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            workbooks, records = download_henex_annual_archives(
                [2025],
                raw_dir=root,
                manifest_path=manifest,
                fetcher=lambda _url: _archive_bytes(),
                retrieved_at_utc="2026-08-26T08:00:00+00:00",
            )
            frame = normalize_henex_workbooks(
                workbooks, retrieved_at_utc="2026-08-26T08:00:00+00:00"
            )
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(len(workbooks), 2)
        self.assertEqual(len(records), 3)
        self.assertEqual(manifest_payload["record_count"], 3)
        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [55.0])
        self.assertEqual(frame["source_version"].tolist(), ["v02"])

    def test_unsupported_archive_year_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(HenexArchiveError, "No verified annual"):
                download_henex_annual_archives(
                    [2026], raw_dir=Path(directory), fetcher=lambda _url: b""
                )

    def test_archive_path_traversal_is_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../unsafe.txt", "unsafe")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(HenexArchiveError, "Unsafe archive member"):
                download_henex_annual_archives(
                    [2025],
                    raw_dir=Path(directory),
                    fetcher=lambda _url: buffer.getvalue(),
                )


if __name__ == "__main__":
    unittest.main()

