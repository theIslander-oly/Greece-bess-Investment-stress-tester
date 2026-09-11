"""Guard and index the declared Stage 9 run; analytical code stays in greek_bess."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path

DOCUMENT = Path("docs/selection_run_declaration_2026-09-11.md")
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
    text = DOCUMENT.read_text()
    require(text.count("```json\n") == 1, "Expected one machine-readable declaration")
    return json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])


def guard() -> dict:
    declared = declaration()
    require(
        os.environ["HISTORY_RUN_ID"] == declared["history_run_id"],
        "History run differs from the declaration",
    )
    require(
        declared["evidence_class"] == "retrospective_supplementary",
        "Inspected history cannot support a confirmatory claim",
    )
    for name, expected in declared["input_sha256"].items():
        require(digest(Path(name)) == expected, f"Declared input changed: {name}")
    custody = json.loads(Path("docs/custody/greek-dam-official-history.json").read_text())
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
    require(actual == expected, "Price calendar differs from the declared complete window")


def seal(declared: dict) -> None:
    payload = json.loads((PRIVATE / "selection.summary.json").read_text())
    summary = payload["summary"]
    for key in (
        "evidence_class", "validation_first_day", "validation_last_day",
        "evaluation_first_day", "evaluation_last_day",
    ):
        require(summary[key] == declared[key], f"Result differs from declaration: {key}")
    for prefix in ("validation", "evaluation"):
        first = date.fromisoformat(declared[f"{prefix}_first_day"])
        last = date.fromisoformat(declared[f"{prefix}_last_day"])
        require(
            summary[f"{prefix}_day_count"] == (last - first).days + 1,
            f"Result omits declared {prefix} days",
        )
    frozen = dict(payload["frozen_selection"])
    expected = frozen.pop("frozen_selection_sha256")
    actual = hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    require(actual == expected == summary["frozen_selection_sha256"], "Broken selection seal")
    # Index every required output regardless of the sign of the comparison.
    required = (
        "prices.csv", "forecasts.csv", "selection.csv", "validation.csv",
        "selection.summary.json", "command.log", "declaration.md", "custody.verification.json",
    )
    files = {name: digest(PRIVATE / name) for name in required}
    index = {
        "result_label": summary["result_label"],
        "evidence_class": summary["evidence_class"],
        "declaration_document_sha256": digest(DOCUMENT),
        "declaration": declared,
        "source_commit": os.environ["GITHUB_SHA"],
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "workflow_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "python": platform.python_version(),
        "packages": {name: version(name) for name in (
            "numpy", "pandas", "scipy", "scikit-learn", "greek-bess-investment-stress-tester",
        )},
        "files_sha256": files,
        "frozen_selection_sha256": expected,
        "candidate_forecast_sha256": summary["candidate_forecast_sha256"],
        "publication_authorized": False,
    }
    (PRIVATE / "evidence_index.json").write_text(json.dumps(index, indent=2) + "\n")


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
        raise ValueError("Unknown selection workflow action")


if __name__ == "__main__":
    main()
