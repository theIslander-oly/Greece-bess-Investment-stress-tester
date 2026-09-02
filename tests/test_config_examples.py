"""The committed configuration examples parse, and are refused as declarations.

Every judgmental input in this project has no default. The examples exist so that an operator
can see the file format without the repository supplying a value on their behalf, which makes
two properties load-bearing at once: an example must still parse through the code that will read
the real declaration, so the format cannot drift away from the reader; and an example must stay
recognisable as an example, so it cannot be copied into a run and mistaken for a declaration. A
test that checked only the first would let the placeholder text be edited away; a test that
checked only the second would let the format rot.
"""

from __future__ import annotations

import json
import re
import unittest
from datetime import date
from pathlib import Path
from typing import Any

from greek_bess.data.admie_timing import GateClosureSchedule

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

PLACEHOLDER_MARKER = "REPLACE BEFORE USE."
PLACEHOLDER_IDENTIFIER = "example-not-a-declaration"

GATE_CLOSURE_EXAMPLES = (
    "admie_gate_closure.example.json",
    "decision_cutoff.example.json",
)


def _load(name: str) -> Any:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


class GateClosureExampleTest(unittest.TestCase):
    """The ADMIE gate-closure and the v0.9 decision-cutoff examples share one format."""

    def test_examples_parse_through_the_schedule_reader(self) -> None:
        for name in GATE_CLOSURE_EXAMPLES:
            with self.subTest(config=name):
                schedule = GateClosureSchedule.from_dict(_load(name))
                self.assertTrue(schedule.regimes)
                # A parsed schedule must also resolve a closure, so an example cannot pass the
                # reader while declaring a regime no delivery day can be audited against.
                closure = schedule.closure_utc(date(2026, 1, 15))
                self.assertIsNotNone(closure.tzinfo)

    def test_examples_are_refused_as_declarations(self) -> None:
        for name in GATE_CLOSURE_EXAMPLES:
            with self.subTest(config=name):
                payload = _load(name)
                self.assertEqual(payload["schedule_id"], PLACEHOLDER_IDENTIFIER)
                for regime in payload["regimes"]:
                    self.assertIn(PLACEHOLDER_MARKER, regime["reference"])


class FundamentalsGeographyExampleTest(unittest.TestCase):
    """The declared sampling geography for gridded fundamentals (v0.9 design, section 5.1)."""

    def setUp(self) -> None:
        self.payload = _load("fundamentals_geography.example.json")

    def test_example_is_refused_as_a_declaration(self) -> None:
        self.assertEqual(self.payload["geography_id"], PLACEHOLDER_IDENTIFIER)
        self.assertIn(PLACEHOLDER_MARKER, self.payload["reference"])

    def test_points_are_named_weighted_and_unique(self) -> None:
        points = self.payload["points"]
        self.assertTrue(points)
        identifiers = [point["point_id"] for point in points]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for point in points:
            self.assertIsInstance(point["latitude"], float)
            self.assertIsInstance(point["longitude"], float)
            self.assertGreater(point["weight"], 0.0)

    def test_weights_form_an_aggregate(self) -> None:
        total = sum(float(point["weight"]) for point in self.payload["points"])
        self.assertAlmostEqual(total, 1.0)

    def test_area_is_the_greek_bidding_zone(self) -> None:
        self.assertEqual(self.payload["area"], "GR")



class DecisionLeadExampleTest(unittest.TestCase):
    """The decision lead is one integer, and the example is deliberately not one.

    A placeholder integer would be the one placeholder a reader could not tell from a
    declaration, because any integer is a syntactically valid lead. So the example carries no
    number at all: copying it unchanged fails the reader that expects one.
    """

    def setUp(self) -> None:
        self.text = (CONFIG_DIR / "decision_lead_minutes.example.txt").read_text(
            encoding="utf-8"
        )

    def test_the_example_is_refused_as_a_declaration(self) -> None:
        self.assertIn(PLACEHOLDER_MARKER, self.text)
        self.assertFalse(re.fullmatch(r"\s*\d+\s*", self.text))

    def test_the_example_states_that_zero_is_a_declaration_and_not_a_default(self) -> None:
        normalized = " ".join(self.text.split())
        self.assertIn("There is no default", normalized)
        self.assertIn("Zero is a valid declaration", normalized)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
