from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from greek_bess.cli import main
from greek_bess.data.custody import (
    CUSTODY_RECORD_VERSION,
    CustodyError,
    CustodyRecord,
    build_custody_record,
    price_series_digest,
    read_custody_record,
    verify_custody_record,
)
from greek_bess.data.synthetic import generate_synthetic_prices


def _write_canonical_csv(frame: object, path: Path) -> None:
    export = frame.copy()  # type: ignore[attr-defined]
    export["quality_flags"] = export["quality_flags"].map(json.dumps)
    path.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(path, index=False)


class CustodyRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.artifact = self.root / "artifact"
        self.frame = generate_synthetic_prices(date(2026, 2, 1), date(2026, 2, 4))
        _write_canonical_csv(self.frame, self.artifact / "prices.csv")
        (self.artifact / "manifest.json").write_text(
            json.dumps({"source": "synthetic"}) + "\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _record(self) -> CustodyRecord:
        return build_custody_record(
            self.artifact,
            artifact_name="test-history",
            source_run_id="1234",
            source_workflow="Fetch official Greek market history",
            published_artifact_digest_sha256="a" * 64,
        )

    def test_record_covers_every_file_and_fingerprints_only_canonical_csvs(self) -> None:
        record = self._record()
        self.assertEqual(record.record_version, CUSTODY_RECORD_VERSION)
        self.assertEqual(record.file_count, 2)
        self.assertEqual(
            sorted(entry.relative_path for entry in record.files),
            ["manifest.json", "prices.csv"],
        )
        self.assertEqual(sorted(record.content), ["prices.csv"])
        self.assertEqual(record.content["prices.csv"].interval_count, 72)
        self.assertEqual(record.content["prices.csv"].market_day_count, 3)

    def test_record_contains_no_official_price(self) -> None:
        record = self._record()
        serialized = json.dumps(record.to_dict())
        for price in self.frame["price_eur_per_mwh"].tolist():
            self.assertNotIn(f"{price:.2f}", serialized)

    def test_unchanged_copy_verifies(self) -> None:
        self.assertEqual(verify_custody_record(self._record(), self.artifact), [])

    def test_changed_price_fails_verification(self) -> None:
        record = self._record()
        altered = self.frame.copy(deep=True)
        altered.loc[3, "price_eur_per_mwh"] += 0.01
        _write_canonical_csv(altered, self.artifact / "prices.csv")

        differences = verify_custody_record(record, self.artifact)
        self.assertTrue(any("sha256" in message for message in differences))
        self.assertTrue(any("price_series_sha256" in message for message in differences))

    def test_reexported_history_keeps_its_price_series_digest(self) -> None:
        """A re-export must digest the same, or the digest cannot detect a revision."""

        record = self._record()
        reordered = self.frame.iloc[::-1].reset_index(drop=True)
        reordered = reordered.loc[:, list(reversed(reordered.columns))]
        _write_canonical_csv(reordered, self.artifact / "prices.csv")

        differences = verify_custody_record(record, self.artifact)
        self.assertTrue(any("sha256" in message for message in differences))
        self.assertFalse(any("price_series_sha256" in message for message in differences))

    def test_missing_and_added_files_are_reported(self) -> None:
        record = self._record()
        (self.artifact / "manifest.json").unlink()
        (self.artifact / "extra.txt").write_text("unexpected\n", encoding="utf-8")

        differences = verify_custody_record(record, self.artifact)
        self.assertTrue(
            any("manifest.json: recorded in custody but absent" in m for m in differences)
        )
        self.assertTrue(
            any("extra.txt: present in the copy but not" in m for m in differences)
        )

    def test_negative_and_zero_prices_are_counted_and_preserved(self) -> None:
        frame = self.frame.copy(deep=True)
        frame["price_eur_per_mwh"] = 50.0
        frame.loc[0, "price_eur_per_mwh"] = -0.0
        frame.loc[1, "price_eur_per_mwh"] = 0.0
        frame.loc[2, "price_eur_per_mwh"] = -12.34
        _write_canonical_csv(frame, self.artifact / "prices.csv")

        fingerprint = self._record().content["prices.csv"]
        self.assertEqual(fingerprint.zero_price_count, 2)
        self.assertEqual(fingerprint.negative_price_count, 1)
        self.assertEqual(fingerprint.missing_price_count, 0)

    def test_negative_zero_digests_as_zero(self) -> None:
        positive = self.frame.copy(deep=True)
        positive.loc[0, "price_eur_per_mwh"] = 0.0
        negative = self.frame.copy(deep=True)
        negative.loc[0, "price_eur_per_mwh"] = -0.0
        self.assertEqual(price_series_digest(positive), price_series_digest(negative))

    def test_quality_flags_are_counted_by_name(self) -> None:
        frame = self.frame.copy(deep=True)
        frame.at[0, "quality_flags"] = ["henex_mcp_rounding_consensus"]
        _write_canonical_csv(frame, self.artifact / "prices.csv")

        fingerprint = self._record().content["prices.csv"]
        self.assertEqual(fingerprint.quality_flag_counts["henex_mcp_rounding_consensus"], 1)
        self.assertEqual(sum(fingerprint.quality_flag_counts.values()), len(self.frame))

    def test_empty_directory_is_rejected(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(CustodyError):
            build_custody_record(empty, artifact_name="x", source_run_id="1")

    def test_unreadable_record_version_is_rejected(self) -> None:
        with self.assertRaises(CustodyError):
            CustodyRecord.from_dict({"record_version": 999})

    def test_record_round_trips_through_json(self) -> None:
        record = self._record()
        path = self.root / "custody.json"
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")

        restored = read_custody_record(path)
        self.assertEqual(restored.to_dict(), record.to_dict())
        self.assertEqual(verify_custody_record(restored, self.artifact), [])


class CustodyCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.artifact = self.root / "artifact"
        self.record_path = self.root / "custody.json"
        frame = generate_synthetic_prices(date(2026, 2, 1), date(2026, 2, 3))
        _write_canonical_csv(frame, self.artifact / "prices.csv")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _record(self) -> int:
        return main(
            [
                "record-custody",
                str(self.artifact),
                "--artifact-name",
                "test-history",
                "--source-run-id",
                "1234",
                "--output",
                str(self.record_path),
            ]
        )

    def test_record_then_verify_succeeds(self) -> None:
        self.assertEqual(self._record(), 0)
        self.assertTrue(self.record_path.is_file())
        exit_code = main(
            ["verify-custody", str(self.artifact), "--record", str(self.record_path)]
        )
        self.assertEqual(exit_code, 0)

    def test_verification_of_an_altered_copy_returns_the_quality_exit_code(self) -> None:
        self.assertEqual(self._record(), 0)
        (self.artifact / "prices.csv").write_text("corrupted\n", encoding="utf-8")

        report_path = self.root / "verification.json"
        exit_code = main(
            [
                "verify-custody",
                str(self.artifact),
                "--record",
                str(self.record_path),
                "--report",
                str(report_path),
            ]
        )
        self.assertEqual(exit_code, 2)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertFalse(report["verified"])
        self.assertGreater(report["difference_count"], 0)


if __name__ == "__main__":
    unittest.main()
