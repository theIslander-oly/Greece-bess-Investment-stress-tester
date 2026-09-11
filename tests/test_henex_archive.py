from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from greek_bess.cli import main
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


def _full_day_workbook_bytes(*, day: str, revision: int) -> bytes:
    """A complete 24-interval hourly delivery day, so the default quality gate passes."""

    rows = pd.DataFrame(
        [
            {
                "DDAY": day,
                "SORT": hour,
                "DELIVERY_DURATION": 60,
                "MCP": float(hour),
                "VER": revision,
            }
            for hour in range(1, 25)
        ]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        rows.to_excel(writer, index=False, sheet_name="Results")
    return buffer.getvalue()


class NormalizeHenexDirectoryCommandTests(unittest.TestCase):
    """The command was registered and runnable while named nowhere else in the
    repository, so nothing exercised it. These cover the two behaviours it owns
    beyond the helpers it composes: finding the workbooks, and refusing when
    there are none."""

    def test_command_normalizes_every_workbook_below_the_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "2025" / "january"
            nested.mkdir(parents=True)
            (root / "20250101_EL-DAM_Results_EN_v01.xlsx").write_bytes(
                _full_day_workbook_bytes(day="2025-01-01", revision=1)
            )
            # A later revision of the same day, and a second day one level down:
            # discovery has to recurse, and latest-revision selection has to win.
            (nested / "20250101_EL-DAM_Results_EN_v02.xlsx").write_bytes(
                _full_day_workbook_bytes(day="2025-01-01", revision=2)
            )
            (nested / "20250102_EL-DAM_Results_EN_v01.xlsx").write_bytes(
                _full_day_workbook_bytes(day="2025-01-02", revision=1)
            )
            (root / "notes.txt").write_text("not a workbook", encoding="utf-8")
            output = root / "out" / "prices.csv"

            exit_code = main(
                ["normalize-henex-directory", str(root), "--output", str(output)]
            )
            written = pd.read_csv(output)

        self.assertEqual(exit_code, 0)
        # Two days of 24 hourly intervals, with the superseded v01 of 1 January
        # dropped rather than appended alongside its replacement.
        self.assertEqual(len(written), 48)
        self.assertEqual(sorted(set(written["source_version"])), ["v01", "v02"])

    def test_command_refuses_a_directory_holding_no_result_workbooks(self) -> None:
        # A directory with nothing to normalize is an unacceptable input, which
        # the CLI reports as a failed run rather than a traceback.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "readme.txt").write_text("nothing here", encoding="utf-8")
            output = root / "prices.csv"

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(
                    ["normalize-henex-directory", str(root), "--output", str(output)]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("No YYYYMMDD_EL-DAM_Results_EN_v##.xlsx files", stderr.getvalue())
        self.assertFalse(output.exists(), "a refused run must write no history")


if __name__ == "__main__":
    unittest.main()
