"""The sharded fundamentals workflow selects feature tables, not their sidecars."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/fetch-fundamentals.yml")


def test_shard_discovery_excludes_coverage_csvs() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count("-regex '.*/features_[0-9]+\\.csv'") == 2
    assert "-name 'features_*.csv'" not in workflow


def test_slices_can_be_recombined_from_an_earlier_run_without_retrieval() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    # Retrieval is skipped only under the explicit input; combination then reads the slices the
    # named run uploaded, under the same count guard and the same official reconciliation.
    assert "shards_from_run_id:" in workflow
    assert "if: ${{ inputs.shards_from_run_id == '' }}" in workflow
    assert "run-id: ${{ env.SHARDS_FROM_RUN_ID }}" in workflow
    assert "needs.retrieve.result == 'skipped'" in workflow
    assert "permissions:\n  contents: read\n" in workflow
    assert "  actions: read\n" in workflow
    # Combination still refuses a failed or cancelled retrieval.
    assert "!cancelled() && needs.plan.result == 'success'" in workflow
    assert workflow.count("greek-bess combine-feature-tables") == 1
    assert "--official" in workflow


def test_feature_table_custody_names_the_workflow_that_produced_it() -> None:
    # The artifact is produced by the fetch workflow; a record naming its consumer as the source
    # would be a correct fingerprint under a wrong provenance label.
    for path in (
        Path(".github/workflows/record-artifact-custody.yml"),
        Path(".github/workflows/publish-encrypted-custody.yml"),
        Path(".github/workflows/benchmark-fundamentals.yml"),
        Path(".github/workflows/preflight-fundamentals.yml"),
    ):
        text = path.read_text(encoding="utf-8")
        feature_step = text.index("custody_step.sh accepted-fundamentals-feature-table")
        assert '"Fetch point-in-time fundamentals"' in text[feature_step:][:200]
        assert '"Benchmark point-in-time fundamentals"' not in text
