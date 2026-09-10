"""The primary-source retention workflow is manual, retrieves only, and decides nothing."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/retain-primary-sources.yml")


def test_retention_is_manual_on_standard_runners_and_keeps_bytes_out_of_git() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "config/primary_sources.json" in text
    assert "runs-on: ubuntu-latest" in text
    # A retained copy is never overwritten by a fresh download.
    assert "--clobber" not in text
    assert "retention-days: 90" in text
    # Bytes leave as an artifact or a release asset; nothing is committed by the job.
    assert "git commit" not in text and "git push" not in text
    # Only the repository token is used; no external credential.
    assert "secrets.GITHUB_TOKEN" in text
    assert text.count("secrets.") == 1
    # Every retained document is identified by digest.
    assert "hashlib.sha256" in text and "RETRIEVAL.json" in text
    # The job never touches an operator declaration.
    assert "config/decision_cutoff.json" not in text.split("\non:", 1)[1]
    assert "config/fundamentals_geography.json" not in text.split("\non:", 1)[1]


def test_declared_document_set_is_https_only_and_names_a_release() -> None:
    import json

    declared = json.loads(Path("config/primary_sources.json").read_text(encoding="utf-8"))
    assert declared["release_tag"].startswith("primary-sources-")
    for url in declared["list_pages"] + [d["url"] for d in declared["documents"]]:
        assert url.startswith("https://"), url
