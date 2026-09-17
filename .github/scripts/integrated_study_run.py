"""Guard and seal the declared Stage 10 official study; analysis stays in greek_bess."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path

DOCUMENT = Path("docs/integrated_study_run_declaration_2026-09-17.md")
PRIVATE = Path("private")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def declaration() -> dict:
    require(
        digest(DOCUMENT) == os.environ["DECLARATION_DOCUMENT_SHA256"],
        "Declaration digest does not match the operator's input",
    )
    text = DOCUMENT.read_text(encoding="utf-8")
    require(text.count("```json\n") == 1, "Expected one machine-readable declaration")
    payload = json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])
    require(isinstance(payload, dict), "Machine-readable declaration must be one object")
    return payload


def guard() -> dict:
    declared = declaration()
    require(
        os.environ["HISTORY_RUN_ID"] == declared["history_run_id"],
        "History run differs from the declaration",
    )
    require(
        declared["evidence_class"] == "retrospective_aggregate_release",
        "Inspected history cannot support a confirmatory claim",
    )
    for name, expected in declared["input_sha256"].items():
        require(digest(Path(name)) == expected, f"Declared input changed: {name}")
    custody = json.loads(
        Path("docs/custody/greek-dam-official-history.json").read_text(encoding="utf-8")
    )
    require(custody["source_run_id"] == declared["history_run_id"], "Custody run mismatch")
    return declared


def check_prices(declared: dict) -> None:
    from greek_bess.data.quality import assess_quality
    from greek_bess.data.schema import read_canonical_csv

    prices = read_canonical_csv(PRIVATE / "prices.csv")
    require(assess_quality(prices, require_complete_days=True).is_valid, "Invalid price history")
    first = date.fromisoformat(declared["history_first_day"])
    last = date.fromisoformat(declared["history_last_day"])
    expected = {first + timedelta(days=n) for n in range((last - first).days + 1)}
    actual = set(prices["delivery_start_market"].dt.date)
    require(actual == expected, "Price calendar differs from the declared complete history")


def _verify_study(declared: dict, study: dict) -> tuple[str, Path]:
    from greek_bess.reporting import read_run_manifest

    study_id = study["study_id"]
    root = PRIVATE / study_id
    summary_path = root / f"{study_id}.summary.json"
    manifest_path = root / f"{study_id}.manifest.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(summary["study_id"] == study_id, f"Study identifier changed: {study_id}")
    require(summary["price_source"] == "official", f"Study is not official: {study_id}")
    require(
        summary["window_start_day"] == declared["study_first_day"]
        and summary["window_end_day"] == declared["study_last_day"],
        f"Study window changed: {study_id}",
    )
    require(
        summary["window_day_count"] == declared["study_day_count"],
        f"Day count changed: {study_id}",
    )
    require(summary["strategy_ids"] == declared["strategy_ids"], f"Strategies changed: {study_id}")
    require(summary["shared_ceiling_reported"] is False, f"Shared ceiling reported: {study_id}")
    battery = summary["study_configuration"]["battery"]
    require(
        battery["charge_power_mw"] == study["power_mw"]
        and battery["discharge_power_mw"] == study["power_mw"]
        and battery["energy_capacity_mwh"] == study["energy_mwh"]
        and battery["max_daily_equivalent_cycles"] == study["max_daily_equivalent_cycles"],
        f"Battery configuration changed: {study_id}",
    )
    manifest = read_run_manifest(manifest_path)
    require(manifest.summary == summary, f"Manifest summary differs: {study_id}")
    require(manifest.basis == "historical_replay_simulation", f"Study basis changed: {study_id}")
    inputs = manifest.declared_inputs
    require(inputs["source_commit"] == os.environ["GITHUB_SHA"], f"Commit missing: {study_id}")
    require(
        inputs["evidence_class"] == declared["evidence_class"],
        f"Evidence class changed: {study_id}",
    )
    require(
        inputs["declaration_document_sha256"] == digest(DOCUMENT),
        f"Declaration identity changed: {study_id}",
    )
    return study_id, manifest_path


def seal(declared: dict) -> None:
    studies = [_verify_study(declared, study) for study in declared["studies"]]
    report_index_path = PRIVATE / "integrated-study-report.index.json"
    report_path = PRIVATE / "integrated-study-report.html"
    index = json.loads(report_index_path.read_text(encoding="utf-8"))
    require(index["state"] == "rendered_manifests", "Report did not render manifests")
    require(index["manifest_count"] == len(studies), "Report manifest count changed")
    require(index["bases_rendered"] == ["historical_replay_simulation"], "Report basis changed")
    require(index["figure_count"] > 0, "Official report contains no recorded figures")
    indexed = {entry["manifest_id"]: entry for entry in index["manifests"]}
    for study_id, manifest_path in studies:
        require(study_id in indexed, f"Report omits study: {study_id}")
        require(
            indexed[study_id]["manifest_sha256"] == digest(manifest_path),
            f"Report manifest digest differs: {study_id}",
        )
    document = report_path.read_text(encoding="utf-8")
    for phrase in (
        "Configuration sensitivity only",
        "not a probability-calibrated estimate",
        "not investment evidence, financial advice or a bankable study",
        "Strategies under this declared configuration",
    ):
        require(phrase in document, f"Report omits required limitation: {phrase}")

    required = [
        Path("declaration.md"),
        Path("custody.verification.json"),
        Path("declared_inputs.json"),
        Path("prices.csv"),
        Path("integrated-study-report.html"),
        Path("integrated-study-report.index.json"),
    ]
    for study_id, _ in studies:
        required.extend(
            Path(study_id) / f"{study_id}{suffix}"
            for suffix in (
                ".daily.csv",
                ".strategies.csv",
                ".cash_flows.csv",
                ".summary.json",
                ".manifest.json",
                ".command.log",
            )
        )
    files = {path.as_posix(): digest(PRIVATE / path) for path in required}
    evidence = {
        "result_label": (
            "Retrospective aggregate integrated-study evidence under illustrative assumptions; "
            "configuration sensitivity only, not expected revenue or investment evidence."
        ),
        "evidence_class": declared["evidence_class"],
        "declaration_document_sha256": digest(DOCUMENT),
        "declaration": declared,
        "source_commit": os.environ["GITHUB_SHA"],
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "workflow_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "python": platform.python_version(),
        "packages": {
            name: version(name)
            for name in (
                "numpy",
                "pandas",
                "scipy",
                "greek-bess-investment-stress-tester",
            )
        },
        "files_sha256": files,
        "publication_authorized": False,
    }
    (PRIVATE / "evidence_index.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    declared = guard()
    action = sys.argv[1]
    if action == "guard":
        PRIVATE.mkdir(exist_ok=True)
        (PRIVATE / "declaration.md").write_bytes(DOCUMENT.read_bytes())
    elif action == "check-prices":
        check_prices(declared)
    elif action == "seal":
        seal(declared)
    else:
        raise ValueError("Unknown integrated-study workflow action")


if __name__ == "__main__":
    main()
