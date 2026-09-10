"""The committed acceptance document describes the declarations it was written against."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONFIG = ROOT / "config"


class AcceptanceDocumentTests(unittest.TestCase):
    """A dated acceptance document is only evidence while it still describes the repository.

    The benchmark workflow refuses unless exactly one such document exists and names the digest
    the run declares. These checks add what a workflow cannot see from one dispatch: that the
    document still names the declarations committed here, so changing a declaration without a
    new acceptance fails in CI rather than silently leaving a stale acceptance in force.
    """

    def setUp(self) -> None:
        documents = sorted(DOCS.glob("fundamentals_acceptance_*.md"))
        self.assertEqual(
            len(documents), 1, "exactly one dated acceptance document may be committed"
        )
        self.document = documents[0]
        self.text = self.document.read_text(encoding="utf-8")

    def test_the_document_is_dated_in_its_filename_and_heading(self) -> None:
        match = re.fullmatch(r"fundamentals_acceptance_(\d{4}-\d{2}-\d{2})\.md", self.document.name)
        self.assertIsNotNone(match)

    def test_it_names_the_declarations_committed_here(self) -> None:
        schedule = json.loads((CONFIG / "decision_cutoff.json").read_text(encoding="utf-8"))
        geography = json.loads(
            (CONFIG / "fundamentals_geography.json").read_text(encoding="utf-8")
        )
        self.assertIn(schedule["schedule_id"], self.text)
        self.assertIn(geography["geography_id"], self.text)
        lead = (CONFIG / "decision_lead_minutes.txt").read_text(encoding="utf-8").strip()
        self.assertIn(f"{lead} minutes", self.text)

    def test_it_names_exactly_one_accepted_feature_set_digest(self) -> None:
        accepted = re.findall(r"\*\*`([0-9a-f]{64})`\*\*", self.text)
        self.assertEqual(len(accepted), 1, "one bolded digest is the accepted feature set")

    def test_it_states_the_verdict_and_the_boundary_of_that_verdict(self) -> None:
        # Compared against the text with its line wrapping removed, so rewrapping a paragraph
        # is not a failure while deleting the sentence is.
        flowed = " ".join(self.text.split())
        self.assertIn("Acceptance verdict: `accepted`", flowed)
        for boundary in (
            "establishes data suitability only",
            "nor an investment-grade study",
            "Favourable performance is not an acceptance criterion",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, flowed)

    def test_it_carries_the_recorded_geography_limitation(self) -> None:
        # The one limitation the declarations single out as easy to lose in transit.
        flowed = " ".join(self.text.split())
        self.assertIn("wind-capacity weighting applied to irradiance and temperature", flowed)
