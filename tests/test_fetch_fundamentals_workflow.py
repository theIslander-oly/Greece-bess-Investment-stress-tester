"""The sharded fundamentals workflow selects feature tables, not their sidecars."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/fetch-fundamentals.yml")


def test_shard_discovery_excludes_coverage_csvs() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count("-regex '.*/features_[0-9]+\\.csv'") == 2
    assert "-name 'features_*.csv'" not in workflow
