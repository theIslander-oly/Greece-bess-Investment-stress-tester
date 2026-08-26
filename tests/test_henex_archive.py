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


def _conflicting_workbook_bytes(*, revision: int) -> bytes:
    rows = pd.DataFrame(
        [
            {
                "DDAY": "2025-01-01",
                "SORT": 1,
                "DELIVERY_DURATION": 60,
                "MCP": price,
                "VER": revision,
            }
            for price in (50.0, 60.0)
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


def _nested_archive_bytes() -> bytes:
    dam_buffer = io.BytesIO()
    with zipfile.ZipFile(dam_buffer, "w") as dam_archive:
        dam_archive.writestr(
            "20210101_EL-DAM_Results_EN_v01.xlsx",
            _workbook_bytes(price=45.0, revision=1),
        )
    outer_buffer = io.BytesIO()
    with zipfile.ZipFile(outer_buffer, "w") as outer_archive:
        outer_archive.writestr("2021_EL-DAM_Results.zip", dam_buffer.getvalue())
        outer_archive.writestr("2021_EL-LIDA1_Results.zip", b"not relevant")
    return outer_buffer.getvalue()


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

    def test_superseded_conflicting_workbook_is_not_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "20250101_EL-DAM_Results_EN_v01.xlsx"
            latest = root / "20250101_EL-DAM_Results_EN_v02.xlsx"
            old.write_bytes(_conflicting_workbook_bytes(revision=1))
            latest.write_bytes(_workbook_bytes(price=55.0, revision=2))

            frame = normalize_henex_workbooks(
                [old, latest], retrieved_at_utc="2026-08-26T08:00:00+00:00"
            )

        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [55.0])
        self.assertEqual(frame["source_version"].tolist(), ["v02"])

    def test_nested_annual_dam_archive_is_extracted_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbooks, records = download_henex_annual_archives(
                [2021],
                raw_dir=root,
                fetcher=lambda _url: _nested_archive_bytes(),
                retrieved_at_utc="2026-08-26T08:00:00+00:00",
            )
            frame = normalize_henex_workbooks(workbooks)

        self.assertEqual(len(workbooks), 1)
        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [45.0])
        self.assertEqual(
            [record.dataset for record in records],
            [
                "dam_results_annual_archive",
                "dam_results_nested_archive",
                "dam_results_workbook",
            ],
        )
        self.assertEqual(records[2].parent_sha256, records[1].sha256)

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
