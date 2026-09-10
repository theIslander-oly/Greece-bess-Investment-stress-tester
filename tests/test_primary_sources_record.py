"""Every declared primary source is cited in the committed record, by URL and by digest."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARED = ROOT / "config" / "primary_sources.json"
RECORD = ROOT / "docs" / "primary_sources" / "README.md"


class PrimarySourceRecordTests(unittest.TestCase):
    """The record is a citation, so it has to name what it cites.

    A document retained but never cited would be evidence nobody can find, and a digest quoted
    in the record but absent from the release would be a fingerprint of nothing. These checks
    cover the first case; the release itself is outside Git and is checked by the workflow.
    """

    def setUp(self) -> None:
        self.declared = json.loads(DECLARED.read_text(encoding="utf-8"))
        self.record = RECORD.read_text(encoding="utf-8")

    def test_every_declared_document_is_cited_by_url(self) -> None:
        for document in self.declared["documents"]:
            with self.subTest(url=document["url"]):
                self.assertIn(document["url"], self.record)

    def test_every_cited_document_carries_a_sha256(self) -> None:
        digests = re.findall(r"`([0-9a-f]{64})`", self.record)
        self.assertEqual(len(digests), len(self.declared["documents"]))
        self.assertEqual(len(set(digests)), len(digests))

    def test_the_record_names_the_release_the_documents_are_retained_on(self) -> None:
        self.assertIn(self.declared["release_tag"], self.record)

    def test_the_record_states_what_it_does_not_establish(self) -> None:
        # The acceptance boundary this project keeps everywhere else: a citation is not an
        # acceptance, and retained text does not make a declaration correct beyond what it says.
        self.assertIn("does not accept a feature value", self.record)
