"""Exercise the official-run refusals without reading official data."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(".github/scripts/selection_run.py")
DOCUMENT = Path("docs/selection_run_declaration_2026-09-11.md")
WORKFLOW = Path(".github/workflows/benchmark-selection.yml")
SPEC = importlib.util.spec_from_file_location("selection_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


class SelectionWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        declared = json.loads(DOCUMENT.read_text().split("```json\n")[1].split("```")[0])
        for name in [str(DOCUMENT), *declared["input_sha256"]]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(name, target)
        self.env = patch.dict(os.environ, {
            "HISTORY_RUN_ID": declared["history_run_id"],
            "DECLARATION_DOCUMENT_SHA256": RUN.digest(DOCUMENT),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)

    def test_committed_declaration_passes_without_reading_prices(self) -> None:
        declared = RUN.guard()
        self.assertEqual(declared["evaluation_last_day"], "2026-08-25")
        self.assertFalse(Path("private/prices.csv").exists())

    def test_wrong_document_digest_refused(self) -> None:
        os.environ["DECLARATION_DOCUMENT_SHA256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Declaration digest"):
            RUN.guard()

    def test_substituted_history_run_refused(self) -> None:
        os.environ["HISTORY_RUN_ID"] = "123"
        with self.assertRaisesRegex(ValueError, "History run"):
            RUN.guard()

    def test_changed_inputs_or_missing_custody_refused(self) -> None:
        declared = RUN.guard()
        for name in declared["input_sha256"]:
            with self.subTest(name=name):
                path = Path(name)
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with self.assertRaisesRegex(ValueError, "Declared input changed"):
                    RUN.guard()
                path.write_bytes(original)
        Path("docs/custody/greek-dam-official-history.json").unlink()
        with self.assertRaises(FileNotFoundError):
            RUN.guard()

    def test_confirmatory_label_refused_even_with_new_document_digest(self) -> None:
        DOCUMENT.write_text(DOCUMENT.read_text().replace(
            '"evidence_class": "retrospective_supplementary"',
            '"evidence_class": "predeclared_untouched"',
        ))
        os.environ["DECLARATION_DOCUMENT_SHA256"] = RUN.digest(DOCUMENT)
        with self.assertRaisesRegex(ValueError, "confirmatory"):
            RUN.guard()

    def test_calendar_refuses_missing_or_extra_whole_days(self) -> None:
        import pandas as pd

        from greek_bess.cli import main

        Path("private").mkdir()
        self.assertEqual(main([
            "generate-synthetic", "--start", "2026-01-01", "--end", "2026-01-04",
            "--output", "private/prices.csv",
        ]), 0)
        declared = {"history_first_day": "2026-01-01", "history_last_day": "2026-01-03"}
        RUN.check_prices(declared)
        declared["history_last_day"] = "2026-01-04"
        with self.assertRaisesRegex(ValueError, "calendar"):
            RUN.check_prices(declared)
        declared["history_last_day"] = "2026-01-02"
        with self.assertRaisesRegex(ValueError, "calendar"):
            RUN.check_prices(declared)
        frame = pd.read_csv("private/prices.csv")
        frame.iloc[1:].to_csv("private/prices.csv", index=False)
        with self.assertRaisesRegex(ValueError, "Invalid price"):
            RUN.check_prices(declared)

    def test_bad_result_windows_and_seal_refused(self) -> None:
        Path("private").mkdir()
        declared = RUN.guard()
        summary = {key: declared[key] for key in (
            "evidence_class", "validation_first_day", "validation_last_day",
            "evaluation_first_day", "evaluation_last_day",
        )}
        summary.update(validation_day_count=365, evaluation_day_count=329)
        frozen = {"selected": "synthetic"}
        frozen["frozen_selection_sha256"] = hashlib.sha256(
            json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        summary["frozen_selection_sha256"] = frozen["frozen_selection_sha256"]
        path = Path("private/selection.summary.json")
        for key, value, message in (
            ("evaluation_day_count", 328, "omits"),
            ("evaluation_last_day", "2026-08-24", "differs"),
            ("frozen_selection_sha256", "0" * 64, "seal"),
        ):
            with self.subTest(key=key):
                path.write_text(json.dumps({
                    "summary": {**summary, key: value}, "frozen_selection": frozen,
                }))
                with self.assertRaisesRegex(ValueError, message):
                    RUN.seal(declared)
        self.assertFalse(Path("private/evidence_index.json").exists())

    def test_workflow_order_and_private_logging(self) -> None:
        text = WORKFLOW.read_text()
        steps = [
            "selection_run.py guard", "Download accepted history", "verify-custody",
            "merge-canonical", "selection_run.py check-prices", "compare-selection-objectives",
            "selection_run.py seal", "actions/upload-artifact@v4",
        ]
        self.assertEqual([text.index(step) for step in steps],
                         sorted(text.index(step) for step in steps))
        for required in (
            "workflow_dispatch:", "if: always()", "retention-days: 90",
            ">private/command.log 2>&1", "contents: read", "actions: read",
            "--validation-start-day 2024-10-01 --evaluation-start-day 2025-10-01",
            "--feature-window-days 28 --refit-frequency-days 7 --min-training-days 28",
            "--random-seed 42 --evidence-class retrospective_supplementary",
        ):
            self.assertIn(required, text)
        for forbidden in ("contents: write", "pages:", "record-custody", "pull_request:"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("margin_minus_rmse_selection_eur", text)

    def test_synthetic_cli_bundle_seals_and_retains_any_result_sign(self) -> None:
        from greek_bess.cli import main

        Path("private").mkdir()
        self.assertEqual(main([
            "generate-synthetic", "--start", "2026-01-01", "--end", "2026-02-10",
            "--output", "private/prices.csv",
        ]), 0)
        self.assertEqual(main([
            "compare-selection-objectives", "private/prices.csv",
            "--battery", "examples/battery_50mw_100mwh.json",
            "--validation-start-day", "2026-02-01", "--evaluation-start-day", "2026-02-05",
            "--output", "private/selection.csv",
            "--validation-scoreboard", "private/validation.csv",
            "--summary", "private/selection.summary.json", "--forecasts", "private/forecasts.csv",
        ]), 0)
        declared = RUN.guard()
        declared.update(
            validation_first_day="2026-02-01", validation_last_day="2026-02-04",
            evaluation_first_day="2026-02-05", evaluation_last_day="2026-02-09",
        )
        shutil.copyfile(DOCUMENT, "private/declaration.md")
        Path("private/command.log").write_text("Synthetic test diagnostics\n")
        Path("private/custody.verification.json").write_text("{}\n")
        with patch.dict(os.environ, {
            "GITHUB_SHA": "synthetic", "GITHUB_RUN_ID": "test", "GITHUB_RUN_ATTEMPT": "1",
        }), patch.object(RUN, "version", return_value="test"):
            RUN.seal(declared)
            path = Path("private/selection.summary.json")
            payload = json.loads(path.read_text())
            for sign in (-1, 0, 1):
                # Retention is independent of performance; analytical correctness is tested
                # by test_value_based_selection, not by this workflow's provenance index.
                payload["summary"]["margin_minus_rmse_selection_eur"] = sign
                path.write_text(json.dumps(payload))
                RUN.seal(declared)
                index = json.loads(Path("private/evidence_index.json").read_text())
                self.assertFalse(index["publication_authorized"])
                self.assertEqual(index["files_sha256"]["selection.summary.json"], RUN.digest(path))


if __name__ == "__main__":
    unittest.main()
