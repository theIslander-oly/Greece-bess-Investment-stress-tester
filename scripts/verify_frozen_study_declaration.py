"""Read-only identity check; this neither authorizes nor executes an official study."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree_digest(root: Path) -> str:
    """Hash sorted relative names and exact bytes, including added or removed modules."""
    source = root / "src" / "greek_bess"
    paths = sorted([*source.rglob("*.py"), source / "py.typed"])
    entries = {path.relative_to(root).as_posix(): digest(path) for path in paths}
    return hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify(root: Path, document: Path, expected_digest: str) -> dict:
    if digest(document) != expected_digest:
        raise ValueError("Declaration document differs from the reviewed digest")
    text = document.read_text(encoding="utf-8")
    if text.count("```json\n") != 1:
        raise ValueError("Expected exactly one machine-readable declaration")
    declared = json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])
    if declared["evidence_class"] != "retrospective_supplementary":
        raise ValueError("Inspected history cannot become confirmatory evidence")
    root = root.resolve()
    for name, expected in declared["input_sha256"].items():
        path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or path == root:
            raise ValueError("Declared input must stay inside the repository")
        if digest(path) != expected:
            raise ValueError(f"Declared input changed: {name}")
    if source_tree_digest(root) != declared["source_tree_sha256"]:
        raise ValueError("Declared package source tree changed")
    return declared


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    verify(Path(__file__).resolve().parents[1], args.document, args.sha256)
    print("Declaration and implementation identities verified; no study executed or authorized.")


if __name__ == "__main__":
    main()
