"""One project version, declared in three places that must agree.

`greek_bess.__version__` is not decoration: it is sent as the `User-Agent` on every
official HEnEx and ENTSO-E retrieval, so a stale value mislabels the client that fetched an
accepted artifact. It had drifted to `0.7.2` while `pyproject.toml` and the README release
line had moved on. These tests keep the three declarations locked together.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import greek_bess
from greek_bess.data.http import fetch_https_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README_RELEASE = re.compile(r"^\*\*Current release:\*\* `v(?P<version>[^`]+)`", re.MULTILINE)


def _pyproject_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    version: str = config["project"]["version"]
    return version


class ProjectVersionTests(unittest.TestCase):
    def test_package_version_matches_pyproject(self) -> None:
        self.assertEqual(greek_bess.__version__, _pyproject_version())

    def test_readme_release_line_matches_pyproject(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        matches = README_RELEASE.findall(readme)
        self.assertEqual(len(matches), 1, "README must state exactly one current release")
        self.assertEqual(matches[0], _pyproject_version())

    def test_the_declared_version_reaches_the_official_data_user_agent(self) -> None:
        captured: list[urllib.request.Request] = []

        def opener(request: urllib.request.Request, timeout: int) -> mock.MagicMock:
            captured.append(request)
            response = mock.MagicMock()
            response.read.return_value = b"{}"
            response.__enter__.return_value = response
            return response

        with mock.patch("urllib.request.urlopen", opener):
            fetch_https_bytes(
                "https://www.enexgroup.gr/example.json",
                allowed_hosts=["www.enexgroup.gr"],
            )

        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0].get_header("User-agent"),
            f"greek-bess-investment-stress-tester/{_pyproject_version()}",
        )


class DocumentationContractTests(unittest.TestCase):
    def test_readme_local_references_resolve(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
        self.assertTrue(targets, "The landing page must link to its reference documents")
        for target in targets:
            if "://" in target or target.startswith("#"):
                continue
            with self.subTest(target=target):
                self.assertTrue((PROJECT_ROOT / target.split("#", 1)[0]).exists())

    def test_limitations_acknowledge_the_accepted_fundamentals_result(self) -> None:
        limitations = (PROJECT_ROOT / "LIMITATIONS.md").read_text(encoding="utf-8")
        normalized = " ".join(limitations.split())

        self.assertIn("docs/fundamentals_acceptance_2026-09-10.md", normalized)
        self.assertIn("one official-history benchmark", normalized)
        self.assertNotIn("no accepted feature table exists", normalized)
        self.assertNotIn("The three real operator declarations are absent", normalized)

    def test_selection_result_identifies_its_linked_declaration(self) -> None:
        report = PROJECT_ROOT / "docs/selection_benchmark_2026-09-11.md"
        text = report.read_text(encoding="utf-8")
        target = re.search(r"\[dated declaration\]\(([^)]+)\)", text)
        recorded = re.search(r"Declaration SHA-256: `([0-9a-f]{64})`", text)
        self.assertIsNotNone(target, "The result must identify its declaration")
        self.assertIsNotNone(recorded, "The result must carry the approved declaration digest")
        assert target is not None and recorded is not None
        declaration = report.parent / target.group(1)
        # Git's text checkout may translate LF on Windows. The recorded digest identifies
        # the committed UTF-8/LF declaration, not the workstation's newline convention.
        committed_text = declaration.read_text(encoding="utf-8").encode("utf-8")
        self.assertEqual(recorded.group(1), hashlib.sha256(committed_text).hexdigest())

    def test_methodology_keeps_declared_availability_outside_the_equivalent_basis(
        self,
    ) -> None:
        # This guard used to read `PLAN.md`, which restated a rule
        # `METHODOLOGY.md` already owned. It now checks the methodology
        # reference itself, so the contract is pinned where the rule lives
        # rather than to a copy of it in a planning document.
        methodology = (PROJECT_ROOT / "METHODOLOGY.md").read_text(encoding="utf-8")
        normalized = " ".join(methodology.split())

        self.assertIn(
            "The price transformation and the availability schedule are on the other "
            "side of that line.",
            normalized,
        )
        self.assertIn(
            "carried as provenance on every reported figure rather than checked as basis",
            normalized,
        )
        # Availability must never join the enumerated equivalent basis.
        self.assertIn(
            "battery parameters, the terminal-energy constraint, the selected source "
            "era and the path identities must match across the ensemble",
            normalized,
        )
        self.assertNotIn(
            "terminal-energy constraints, availability assumptions, source eras",
            normalized,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
