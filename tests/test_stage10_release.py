"""Stage 10 declaration, configuration sensitivity and official-run refusal gates."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greek_bess.study import read_integrated_study_config

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/integrated_study_run.py"
DOCUMENT = ROOT / "docs/integrated_study_run_declaration_2026-09-14.md"
WORKFLOW = ROOT / ".github/workflows/run-integrated-study.yml"
CONFIG_50 = ROOT / "config/integrated_study_official_50mw_100mwh.json"
CONFIG_25 = ROOT / "config/integrated_study_official_25mw_100mwh.json"

SPEC = importlib.util.spec_from_file_location("integrated_study_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


def _declared() -> dict:
    text = DOCUMENT.read_text(encoding="utf-8")
    return json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])


class Stage10ConfigurationTests(unittest.TestCase):
    def test_both_official_configs_parse_and_differ_only_as_declared(self) -> None:
        fifty = read_integrated_study_config(CONFIG_50)
        twenty_five = read_integrated_study_config(CONFIG_25)

        self.assertEqual(fifty.window_days, twenty_five.window_days)
        self.assertEqual(fifty.strategies, twenty_five.strategies)
        self.assertEqual(fifty.degradation, twenty_five.degradation)
        self.assertEqual(fifty.finance, twenty_five.finance)
        self.assertEqual(fifty.price_source, twenty_five.price_source)
        self.assertEqual(fifty.price_source, "official")
        self.assertIsNone(fifty.synthetic_price_generation)
        self.assertIsNone(twenty_five.synthetic_price_generation)
        self.assertEqual(fifty.battery.to_dict(), json.loads(
            (ROOT / "examples/battery_50mw_100mwh.json").read_text(encoding="utf-8")
        ))
        self.assertEqual(twenty_five.battery.to_dict(), json.loads(
            (ROOT / "examples/battery_representative_gr_25mw_100mwh.json").read_text(
                encoding="utf-8"
            )
        ))

    def test_declaration_names_the_exact_two_configs_and_no_optimal_size_claim(self) -> None:
        declared = _declared()
        self.assertEqual(declared["study_day_count"], 329)
        self.assertEqual(
            [study["study_id"] for study in declared["studies"]],
            [
                "official-integrated-study-50mw-100mwh",
                "official-integrated-study-25mw-100mwh",
            ],
        )
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("configuration sensitivity", text.lower())
        self.assertIn("not evidence of an optimal", text.lower())


class Stage10WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        declared = _declared()
        for name in [str(DOCUMENT.relative_to(ROOT)), *declared["input_sha256"]]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.env = patch.dict(
            os.environ,
            {
                "HISTORY_RUN_ID": declared["history_run_id"],
                "DECLARATION_DOCUMENT_SHA256": RUN.digest(DOCUMENT),
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)

    def test_committed_declaration_passes_without_reading_official_prices(self) -> None:
        declared = RUN.guard()
        self.assertEqual(declared["evidence_class"], "retrospective_aggregate_release")
        self.assertFalse(Path("private/prices.csv").exists())

    def test_wrong_declaration_history_or_changed_input_is_refused(self) -> None:
        os.environ["DECLARATION_DOCUMENT_SHA256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Declaration digest"):
            RUN.guard()
        os.environ["DECLARATION_DOCUMENT_SHA256"] = RUN.digest(Path(
            "docs/integrated_study_run_declaration_2026-09-14.md"
        ))
        os.environ["HISTORY_RUN_ID"] = "123"
        with self.assertRaisesRegex(ValueError, "History run"):
            RUN.guard()
        os.environ["HISTORY_RUN_ID"] = _declared()["history_run_id"]
        changed = Path("config/integrated_study_official_50mw_100mwh.json")
        changed.write_bytes(changed.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Declared input changed"):
            RUN.guard()

    def test_workflow_orders_custody_run_render_and_seal_without_publication(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        steps = [
            "integrated_study_run.py guard",
            "Download accepted history",
            "verify-custody",
            "merge-canonical",
            "integrated_study_run.py check-prices",
            "run-integrated-study",
            "render-report",
            "integrated_study_run.py seal",
            "actions/upload-artifact@v4",
        ]
        positions = [text.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        for required in (
            "if: always()",
            "retention-days: 90",
            "contents: read",
            "actions: read",
            "retrospective_aggregate_release",
            "Publication requires separate review and authorization",
        ):
            self.assertIn(required, text)
        for forbidden in ("contents: write", "pages: write", "deploy-pages", "pull_request:"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
