"""The public demonstration is reproducible and cannot drift from its committed report."""

from __future__ import annotations

from pathlib import Path

from greek_bess.cli import main


def test_demo_matches_committed_sample(tmp_path: Path) -> None:
    output = tmp_path / "sample_report.html"

    assert main(["demo", "--output", str(output)]) == 0
    committed = Path(__file__).parents[1] / "docs" / "sample_report.html"
    assert output.read_bytes() == committed.read_bytes()
    document = output.read_text(encoding="utf-8")
    assert "deterministic synthetic" in document.lower()
    assert "not investment evidence" in document.lower()
