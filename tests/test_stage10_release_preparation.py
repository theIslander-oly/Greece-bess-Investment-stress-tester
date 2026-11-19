"""Release staging verifies evidence and never copies private tables into the review surface."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from greek_bess.reporting import build_run_manifest, render_report, write_run_manifest

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/prepare_stage10_release.py"
SPEC = importlib.util.spec_from_file_location("prepare_stage10_release", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8", newline="\n")


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    """Replace acceptance pins only for an explicitly synthetic, disposable bundle."""
    root = tmp_path / "source"
    root.mkdir()
    manifests = []
    for study_id in RELEASE.STUDIES:
        folder = root / study_id
        folder.mkdir()
        summary = {
            "result_label": "Synthetic release test only; not official market evidence.",
            "result_basis_note": "Synthetic fixture, not expected revenue or a bound.",
            "study_id": study_id,
            "price_source": "synthetic",
            "window_start_day": "2026-01-01",
            "window_end_day": "2026-01-01",
            "window_day_count": 1,
            "strategies": [{"strategy_id": "test-policy", "net_market_margin_eur": 1.0}],
            "coverage": {"built_day_count": 1, "excluded_day_count": 0},
            "shared_ceiling_reported": False,
            "finance_horizon_policy": "Only the one synthetic day.",
        }
        write_json(folder / f"{study_id}.summary.json", summary)
        manifest = build_run_manifest(
            summary, kind_id="integrated_study", manifest_id=study_id,
            produced_by="synthetic-release-test", created_at_utc="2026-01-02T00:00:00+00:00",
        )
        path = folder / f"{study_id}.manifest.json"
        write_run_manifest(path, manifest)
        manifests.append(path)
        for suffix in ("daily.csv", "strategies.csv", "cash_flows.csv", "command.log"):
            (folder / f"{study_id}.{suffix}").write_text("private synthetic fixture\n")
    (root / "declaration.md").write_text("Synthetic test declaration\n")
    (root / "prices.csv").write_text("private synthetic prices\n")
    write_json(root / "custody.verification.json", {"verified": True})
    write_json(root / "declared_inputs.json", {"synthetic_test": True})
    rendered = render_report(manifests)
    (root / "integrated-study-report.html").write_text(
        rendered.html, encoding="utf-8", newline="\n"
    )
    write_json(root / "integrated-study-report.index.json", dict(rendered.index))
    monkeypatch.setattr(RELEASE, "DECLARATION_SHA256", RELEASE.digest(root / "declaration.md"))
    monkeypatch.setattr(
        RELEASE, "REPORT_SHA256", RELEASE.digest(root / "integrated-study-report.html")
    )
    write_json(root / "evidence_index.json", {
        "workflow_run_id": RELEASE.SOURCE_RUN,
        "source_commit": RELEASE.SOURCE_COMMIT,
        "declaration_document_sha256": RELEASE.DECLARATION_SHA256,
        "evidence_class": "retrospective_aggregate_release",
        "publication_authorized": False,
        "files_sha256": {},
    })
    reseal(root, monkeypatch)
    return root


def reseal(root, monkeypatch):
    """Only a test may accept changed fixtures; the command exposes no pin override."""
    path = root / "evidence_index.json"
    evidence = json.loads(path.read_text())
    evidence["files_sha256"] = {
        p.relative_to(root).as_posix(): RELEASE.digest(p)
        for p in root.rglob("*") if p.is_file() and p != path
    }
    write_json(path, evidence)
    monkeypatch.setattr(RELEASE, "EVIDENCE_SHA256", RELEASE.digest(path))


def test_stages_only_original_aggregate_bytes_without_modifying_source(bundle, tmp_path):
    before = {p.relative_to(bundle): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    output = tmp_path / "review"
    receipt = RELEASE.prepare(bundle, output)
    assert {p.name for p in output.iterdir()} == {"index.html", "report.index.json"}
    assert (output / "index.html").read_bytes() == before[Path("integrated-study-report.html")]
    assert (output / "report.index.json").read_bytes() == before[
        Path("integrated-study-report.index.json")
    ]
    assert receipt["publication_authorized"] is False
    assert receipt["state"] == "prepared_for_review"
    assert before == {
        p.relative_to(bundle): p.read_bytes() for p in bundle.rglob("*") if p.is_file()
    }


@pytest.fixture
def archive(bundle, tmp_path, monkeypatch):
    path = tmp_path / "accepted.zip"
    with ZipFile(path, "w") as zipped:
        for member in sorted(bundle.rglob("*")):
            if member.is_file():
                zipped.write(member, member.relative_to(bundle).as_posix())
    monkeypatch.setattr(RELEASE, "ARCHIVE_SHA256", RELEASE.digest(path))
    return path


def test_cli_stages_verified_archive_report(archive, bundle, tmp_path, monkeypatch, capsys):
    output = tmp_path / "review"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(archive), "--output", str(output)])
    RELEASE.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["archive_sha256"] == RELEASE.digest(archive) == RELEASE.ARCHIVE_SHA256
    assert receipt["publication_authorized"] is False
    assert {p.name for p in output.iterdir()} == {"index.html", "report.index.json"}
    assert (output / "index.html").read_bytes() == (
        bundle / "integrated-study-report.html"
    ).read_bytes()
    assert (output / "report.index.json").read_bytes() == (
        bundle / "integrated-study-report.index.json"
    ).read_bytes()


def test_repacked_archive_is_refused_even_when_the_bundle_matches(archive, tmp_path):
    with ZipFile(archive, "a") as zipped:
        zipped.comment = b"This changes only the outer archive"
    output = tmp_path / "review"
    with pytest.raises(ValueError, match="Unaccepted Stage 10 archive"):
        RELEASE.prepare_archive(archive, output)
    assert not output.exists()


@pytest.mark.parametrize("name", ["prices.csv", "declaration.md", "integrated-study-report.html"])
def test_any_changed_indexed_bytes_are_refused_before_output(bundle, tmp_path, name):
    (bundle / name).write_bytes((bundle / name).read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Evidence digest differs"):
        RELEASE.prepare(bundle, tmp_path / "review")
    assert not (tmp_path / "review").exists()


def test_rewritten_evidence_index_is_not_self_authenticating(bundle, tmp_path):
    path = bundle / "evidence_index.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Unaccepted evidence index"):
        RELEASE.prepare(bundle, tmp_path / "review")


def test_validly_hashed_html_must_still_reproduce_manifests(bundle, tmp_path, monkeypatch):
    report = bundle / "integrated-study-report.html"
    report.write_bytes(report.read_bytes() + b"<p>unrecorded figure</p>")
    monkeypatch.setattr(RELEASE, "REPORT_SHA256", RELEASE.digest(report))
    reseal(bundle, monkeypatch)
    with pytest.raises(ValueError, match="Report re-render differs"):
        RELEASE.prepare(bundle, tmp_path / "review")


def test_report_index_must_name_actual_manifest_hashes(bundle, tmp_path, monkeypatch):
    path = bundle / "integrated-study-report.index.json"
    index = json.loads(path.read_text())
    index["manifests"][0]["manifest_sha256"] = "0" * 64
    write_json(path, index)
    reseal(bundle, monkeypatch)
    with pytest.raises(ValueError, match="Report manifest digest differs"):
        RELEASE.prepare(bundle, tmp_path / "review")


def test_custody_failure_is_refused(bundle, tmp_path, monkeypatch):
    write_json(bundle / "custody.verification.json", {"verified": False})
    reseal(bundle, monkeypatch)
    with pytest.raises(ValueError, match="Source custody did not verify"):
        RELEASE.prepare(bundle, tmp_path / "review")


def test_missing_indexed_file_is_refused(bundle, tmp_path):
    (bundle / "prices.csv").unlink()
    with pytest.raises(ValueError, match="Missing evidence file"):
        RELEASE.prepare(bundle, tmp_path / "review")


def test_existing_output_is_preserved(bundle, tmp_path):
    output = tmp_path / "review"
    output.mkdir()
    (output / "keep.txt").write_text("preserve me")
    with pytest.raises(ValueError, match="Output must be a new directory"):
        RELEASE.prepare(bundle, output)
    assert (output / "keep.txt").read_text() == "preserve me"


def test_output_inside_original_bundle_is_refused(bundle):
    with pytest.raises(ValueError, match="outside the original evidence"):
        RELEASE.prepare(bundle, bundle / "review")


def test_link_to_matching_private_file_outside_bundle_is_refused(bundle, tmp_path):
    path = bundle / "prices.csv"
    external = tmp_path / "outside.csv"
    external.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(external)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this host")
    with pytest.raises(ValueError, match="symlinks"):
        RELEASE.prepare(bundle, tmp_path / "review")


@pytest.mark.parametrize("name", ["../outside.csv", "/outside.csv", "folder\\outside.csv"])
def test_evidence_member_cannot_escape_root(bundle, name):
    with pytest.raises(ValueError, match="Invalid evidence path"):
        RELEASE.member(bundle.resolve(), name)
