"""One project version, declared in three places that must agree.

`greek_bess.__version__` is not decoration: it is sent as the `User-Agent` on every
official HEnEx and ENTSO-E retrieval, so a stale value mislabels the client that fetched an
accepted artifact. It had drifted to `0.7.2` while `pyproject.toml` and the README release
line had moved on. These tests keep the three declarations locked together.
"""

from __future__ import annotations

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
