"""Stage the accepted Stage 10 aggregate for review without running or publishing a study."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from greek_bess.reporting import read_run_manifest, render_report

SOURCE_RUN = "35252229873"
SOURCE_COMMIT = "76d48d5aea505fefe51ca948cc901d6fbda594a0"
EVIDENCE_SHA256 = "214a4caaf52d16f9bd7cb508eb9334f94bfa3a98696cc4820b89eec612daf938"
DECLARATION_SHA256 = "007c90444aedf17135601035c3b46a9731b7117a531692f92e4173f28cdcbe79"
REPORT_SHA256 = "5fb8ccc56b083d9f2cc3a1fdf05b0252c86a4599da1cec29913d3bbb9bdbd342"
STUDIES = (
    "official-integrated-study-25mw-100mwh",
    "official-integrated-study-50mw-100mwh",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def member(root: Path, name: str) -> Path:
    """Refuse traversal and links before reading a named evidence file."""
    relative = PurePosixPath(name)
    require(
        bool(relative.parts) and not relative.is_absolute()
        and ".." not in relative.parts and "\\" not in name,
        "Invalid evidence path",
    )
    path = root
    for part in relative.parts:
        path = path / part
        require(not path.is_symlink(), "Evidence paths must not contain symlinks")
    require(path.is_file(), f"Missing evidence file: {name}")
    require(path.resolve().is_relative_to(root), "Evidence path escapes the bundle")
    return path


def prepare(root: Path, output: Path) -> dict:
    root = root.resolve(strict=True)
    require(not output.exists() and not output.is_symlink(), "Output must be a new directory")
    require(
        not output.resolve().is_relative_to(root),
        "Review output must be outside the original evidence bundle",
    )
    evidence_path = member(root, "evidence_index.json")
    require(digest(evidence_path) == EVIDENCE_SHA256, "Unaccepted evidence index")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    require(
        str(evidence["workflow_run_id"]) == SOURCE_RUN
        and evidence["source_commit"] == SOURCE_COMMIT,
        "Source run or commit differs",
    )
    require(
        evidence["declaration_document_sha256"] == DECLARATION_SHA256
        and evidence["evidence_class"] == "retrospective_aggregate_release",
        "Declaration or evidence class differs",
    )
    # This is a review package. Preserve the original authorization record as evidence;
    # neither a local command nor a workflow dispatch grants publication authorization.
    require(evidence["publication_authorized"] is False, "Unexpected source authorization record")
    files = evidence["files_sha256"]
    require(isinstance(files, dict) and len(files) == 18, "Evidence inventory differs")
    for name, expected in files.items():
        require(digest(member(root, name)) == expected, f"Evidence digest differs: {name}")
    declaration = member(root, "declaration.md")
    require(digest(declaration) == DECLARATION_SHA256, "Declaration bytes differ")
    custody = json.loads(member(root, "custody.verification.json").read_text(encoding="utf-8"))
    require(custody["verified"] is True, "Source custody did not verify")

    manifests = []
    for study_id in STUDIES:
        manifest_path = member(root, f"{study_id}/{study_id}.manifest.json")
        summary_path = member(root, f"{study_id}/{study_id}.summary.json")
        manifest = read_run_manifest(manifest_path)
        require(
            manifest.manifest_id == study_id and manifest.result_kind == "integrated_study"
            and manifest.basis == "historical_replay_simulation",
            "Manifest identity or basis differs",
        )
        require(
            manifest.summary == json.loads(summary_path.read_text(encoding="utf-8")),
            "Manifest and recorded summary differ",
        )
        manifests.append(manifest_path)

    report = member(root, "integrated-study-report.html")
    index_path = member(root, "integrated-study-report.index.json")
    require(digest(report) == REPORT_SHA256, "Report differs from the reviewed bytes")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    require(
        index["state"] == "rendered_manifests" and index["manifest_count"] == 2
        and index["bases_rendered"] == ["historical_replay_simulation"],
        "Report index identity or basis differs",
    )
    indexed = {entry["manifest_id"]: entry for entry in index["manifests"]}
    require(len(index["manifests"]) == 2 and set(indexed) == set(STUDIES), "Report omits a study")
    for study_id, manifest_path in zip(STUDIES, manifests, strict=True):
        require(
            indexed[study_id]["manifest_sha256"] == digest(manifest_path),
            "Report manifest digest differs",
        )
    # Render only: never solve dispatch, fit models, or change an accepted result.
    rendered = render_report(manifests)
    require(rendered.html.encode("utf-8") == report.read_bytes(), "Report re-render differs")
    require(
        {k: v for k, v in rendered.index.items() if k != "rendered_at_utc"}
        == {k: v for k, v in index.items() if k != "rendered_at_utc"},
        "Report index does not describe the rendered manifests",
    )

    # No recursive copy: manifests, prices, logs, schedules and cash-flow tables stay private.
    output.mkdir(parents=True, exist_ok=False)
    (output / "index.html").write_bytes(report.read_bytes())
    (output / "report.index.json").write_bytes(index_path.read_bytes())
    return {
        "state": "prepared_for_review",
        "source_run_id": SOURCE_RUN,
        "source_commit": SOURCE_COMMIT,
        "evidence_index_sha256": EVIDENCE_SHA256,
        "files_sha256": {path.name: digest(path) for path in sorted(output.iterdir())},
        "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.bundle, args.output), indent=2))


if __name__ == "__main__":
    main()
