"""Raw-file provenance records for reproducible private data retrieval."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .timezones import UTC


@dataclass(frozen=True)
class RetrievalRecord:
    """One downloaded or extracted official source file."""

    source: str
    dataset: str
    source_url: str
    local_path: str
    retrieved_at_utc: str
    sha256: str
    size_bytes: int
    coverage_start: str | None = None
    coverage_end: str | None = None
    published_at_source: str | None = None
    published_at_utc: str | None = None
    revision: int | None = None
    parent_sha256: str | None = None
    availability_classification: str = "not_assessed"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def utc_now_iso() -> str:
    return pd.Timestamp.now(tz=UTC).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write bytes using a sibling temporary file and atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def write_retrieval_manifest(
    path: Path,
    records: list[RetrievalRecord],
    *,
    created_at_utc: str | None = None,
) -> None:
    """Write a deterministic JSON manifest; raw data remain outside Git."""

    payload = {
        "schema_version": 1,
        "created_at_utc": created_at_utc or utc_now_iso(),
        "record_count": len(records),
        "records": [record.to_dict() for record in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

