"""Custody records that fingerprint accepted official artifacts without their prices.

An accepted official retrieval lives outside Git, so the repository cannot hold the
data itself. It can hold a fingerprint. A custody record states which artifact was
accepted, the digest of every file it contained, and content-level invariants of the
normalized price series, including a digest of the interval and price series itself.

Two operations depend on that record. A copy held in private storage can be proven to
be the accepted baseline rather than merely plausible, and a later re-retrieval can be
proven identical to the accepted baseline or shown to differ. The second case matters:
official publications are revised, so a re-retrieval is not reproducible in principle,
and a silent revision would otherwise replace an accepted baseline unnoticed.

No official price is ever written into a custody record. The record carries digests,
counts, timestamps and flag names only, which is what makes it safe to commit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import SupportsFloat

import pandas as pd

from .provenance import utc_now_iso
from .schema import CANONICAL_COLUMNS, CanonicalSchemaError, read_canonical_csv
from .timezones import MARKET_TZ

CUSTODY_RECORD_VERSION = 1
"""Incremented only when a recorded field changes meaning, never for new fields."""

PRICE_DIGEST_DECIMALS = 6
"""Fixed decimals used by the price-series digest.

Official Greek DAM prices are published to the cent. Six decimals preserve every
published value exactly while removing the float-repr differences that would
otherwise make the digest depend on the pandas and NumPy versions in use.
"""

MISSING_PRICE_TOKEN = ""
"""A missing price is digested as an empty field, never as a substituted number."""


class CustodyError(ValueError):
    """Raised when a custody record cannot be built or read."""


@dataclass(frozen=True)
class CustodyFile:
    """One file inside an accepted artifact."""

    relative_path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ContentFingerprint:
    """Content-level invariants of one normalized canonical price file."""

    interval_count: int
    first_interval_utc: str | None
    last_interval_utc: str | None
    market_day_count: int
    negative_price_count: int
    zero_price_count: int
    missing_price_count: int
    interval_counts_by_delivery_year: dict[str, int]
    interval_counts_by_duration_hours: dict[str, int]
    interval_counts_by_source: dict[str, int]
    quality_flag_counts: dict[str, int]
    price_series_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CustodyRecord:
    """The committed fingerprint of one accepted official artifact."""

    record_version: int
    artifact_name: str
    source_run_id: str
    source_workflow: str | None
    published_artifact_digest_sha256: str | None
    recorded_at_utc: str
    file_count: int
    total_size_bytes: int
    files: list[CustodyFile] = field(default_factory=list)
    content: dict[str, ContentFingerprint] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["files"] = [entry.to_dict() for entry in self.files]
        payload["content"] = {name: value.to_dict() for name, value in self.content.items()}
        return payload

    @classmethod
    def from_dict(cls, payload: object) -> CustodyRecord:
        if not isinstance(payload, dict):
            raise CustodyError("A custody record must be one JSON object")

        version = payload.get("record_version")
        if version != CUSTODY_RECORD_VERSION:
            raise CustodyError(
                f"Unsupported custody record version {version!r}; "
                f"this build reads version {CUSTODY_RECORD_VERSION}"
            )

        missing = [
            key
            for key in ("artifact_name", "source_run_id", "recorded_at_utc", "files", "content")
            if key not in payload
        ]
        if missing:
            raise CustodyError(f"Custody record is missing fields: {', '.join(missing)}")

        try:
            files = [CustodyFile(**entry) for entry in payload["files"]]
            content = {
                str(name): ContentFingerprint(**value)
                for name, value in payload["content"].items()
            }
        except TypeError as exc:
            raise CustodyError(f"Custody record has malformed entries: {exc}") from exc

        return cls(
            record_version=CUSTODY_RECORD_VERSION,
            artifact_name=str(payload["artifact_name"]),
            source_run_id=str(payload["source_run_id"]),
            source_workflow=_optional_str(payload.get("source_workflow")),
            published_artifact_digest_sha256=_optional_str(
                payload.get("published_artifact_digest_sha256")
            ),
            recorded_at_utc=str(payload["recorded_at_utc"]),
            file_count=int(payload.get("file_count", len(files))),
            total_size_bytes=int(
                payload.get("total_size_bytes", sum(entry.size_bytes for entry in files))
            ),
            files=files,
            content=content,
        )


def sha256_file(path: Path) -> str:
    """Digest a file in bounded memory, so artifact size never dictates usage."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def price_series_digest(frame: pd.DataFrame) -> str:
    """Digest the interval and price series of a canonical frame.

    The digest covers exactly what must not change silently: which intervals exist and
    what price each one carries. It is deliberately independent of CSV column order,
    file formatting and float repr, so a re-export of the same history digests the same,
    while a revised price or a changed interval set does not.
    """

    if frame.empty:
        return hashlib.sha256(b"").hexdigest()

    ordered = frame.sort_values(
        ["delivery_start_utc", "delivery_end_utc"], kind="stable"
    ).reset_index(drop=True)

    digest = hashlib.sha256()
    starts = ordered["delivery_start_utc"]
    ends = ordered["delivery_end_utc"]
    prices = ordered["price_eur_per_mwh"]
    for start, end, price in zip(starts, ends, prices, strict=True):
        digest.update(
            f"{start.isoformat()}|{end.isoformat()}|{_format_price(price)}\n".encode()
        )
    return digest.hexdigest()


def fingerprint_canonical_frame(frame: pd.DataFrame) -> ContentFingerprint:
    """Summarize a canonical frame into committable, price-free invariants."""

    if frame.empty:
        return ContentFingerprint(
            interval_count=0,
            first_interval_utc=None,
            last_interval_utc=None,
            market_day_count=0,
            negative_price_count=0,
            zero_price_count=0,
            missing_price_count=0,
            interval_counts_by_delivery_year={},
            interval_counts_by_duration_hours={},
            interval_counts_by_source={},
            quality_flag_counts={},
            price_series_sha256=price_series_digest(frame),
        )

    starts = frame["delivery_start_utc"]
    prices = frame["price_eur_per_mwh"]
    market_starts = starts.dt.tz_convert(MARKET_TZ)

    flag_counts: dict[str, int] = {}
    for flags in frame["quality_flags"]:
        for flag in flags:
            flag_counts[str(flag)] = flag_counts.get(str(flag), 0) + 1

    return ContentFingerprint(
        interval_count=int(len(frame)),
        first_interval_utc=starts.min().isoformat(),
        last_interval_utc=frame["delivery_end_utc"].max().isoformat(),
        market_day_count=int(market_starts.dt.date.nunique()),
        negative_price_count=int((prices < 0).sum()),
        zero_price_count=int((prices == 0).sum()),
        missing_price_count=int(prices.isna().sum()),
        interval_counts_by_delivery_year=_counts(market_starts.dt.year),
        interval_counts_by_duration_hours=_counts(frame["duration_hours"]),
        interval_counts_by_source=_counts(frame["source"]),
        quality_flag_counts=dict(sorted(flag_counts.items())),
        price_series_sha256=price_series_digest(frame),
    )


def build_custody_record(
    directory: Path,
    *,
    artifact_name: str,
    source_run_id: str,
    source_workflow: str | None = None,
    published_artifact_digest_sha256: str | None = None,
    recorded_at_utc: str | None = None,
) -> CustodyRecord:
    """Fingerprint every file below ``directory`` as one accepted artifact.

    Every file is digested. A ``.csv`` that parses as a canonical price history also
    receives a content fingerprint; one that does not is digested as bytes only, so a
    manifest or quality report is still covered without being misread as prices.
    """

    if not directory.is_dir():
        raise CustodyError(f"{directory} is not a directory")

    paths = sorted(path for path in directory.rglob("*") if path.is_file())
    if not paths:
        raise CustodyError(f"{directory} contains no files to record")

    files: list[CustodyFile] = []
    content: dict[str, ContentFingerprint] = {}
    for path in paths:
        relative = path.relative_to(directory).as_posix()
        files.append(
            CustodyFile(
                relative_path=relative,
                size_bytes=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )
        frame = _read_canonical_or_none(path)
        if frame is not None:
            content[relative] = fingerprint_canonical_frame(frame)

    return CustodyRecord(
        record_version=CUSTODY_RECORD_VERSION,
        artifact_name=artifact_name,
        source_run_id=source_run_id,
        source_workflow=source_workflow,
        published_artifact_digest_sha256=published_artifact_digest_sha256,
        recorded_at_utc=recorded_at_utc or utc_now_iso(),
        file_count=len(files),
        total_size_bytes=sum(entry.size_bytes for entry in files),
        files=files,
        content=content,
    )


def verify_custody_record(record: CustodyRecord, directory: Path) -> list[str]:
    """Re-derive the record from ``directory`` and return every difference found.

    An empty list means the directory holds exactly the accepted artifact. Differences
    are returned rather than raised: a mismatch is a finding to record and investigate,
    and the caller decides whether that finding fails a job.
    """

    observed = build_custody_record(
        directory,
        artifact_name=record.artifact_name,
        source_run_id=record.source_run_id,
        recorded_at_utc=record.recorded_at_utc,
    )

    differences: list[str] = []
    expected_files = {entry.relative_path: entry for entry in record.files}
    observed_files = {entry.relative_path: entry for entry in observed.files}

    for name in sorted(set(expected_files) - set(observed_files)):
        differences.append(f"{name}: recorded in custody but absent from the copy")
    for name in sorted(set(observed_files) - set(expected_files)):
        differences.append(f"{name}: present in the copy but not in the custody record")

    for name in sorted(set(expected_files) & set(observed_files)):
        expected = expected_files[name]
        actual = observed_files[name]
        if expected.sha256 != actual.sha256:
            differences.append(
                f"{name}: sha256 {actual.sha256} does not match the recorded {expected.sha256}"
            )
        if expected.size_bytes != actual.size_bytes:
            differences.append(
                f"{name}: {actual.size_bytes} bytes does not match the recorded "
                f"{expected.size_bytes}"
            )

    for name in sorted(set(record.content) | set(observed.content)):
        expected_content = record.content.get(name)
        actual_content = observed.content.get(name)
        if expected_content is None:
            differences.append(
                f"{name}: the copy parses as canonical prices "
                "but the custody record holds no fingerprint for it"
            )
            continue
        if actual_content is None:
            differences.append(f"{name}: recorded as canonical prices but the copy does not parse")
            continue
        differences.extend(
            f"{name}: {message}"
            for message in _compare_fingerprints(expected_content, actual_content)
        )

    return differences


def read_custody_record(path: Path) -> CustodyRecord:
    """Load a committed custody record."""

    return CustodyRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _compare_fingerprints(expected: ContentFingerprint, actual: ContentFingerprint) -> list[str]:
    differences: list[str] = []
    for name, expected_value in expected.to_dict().items():
        actual_value = getattr(actual, name)
        if expected_value != actual_value:
            differences.append(f"{name} is {actual_value!r}, recorded as {expected_value!r}")
    return differences


def _read_canonical_or_none(path: Path) -> pd.DataFrame | None:
    if path.suffix.lower() != ".csv":
        return None
    try:
        header = pd.read_csv(path, nrows=0)
    except (ValueError, OSError, pd.errors.ParserError):
        return None
    if any(column not in header.columns for column in CANONICAL_COLUMNS):
        return None
    try:
        return read_canonical_csv(path)
    except (CanonicalSchemaError, ValueError, KeyError) as exc:
        raise CustodyError(f"{path} looks canonical but does not parse: {exc}") from exc


def _counts(values: Iterable[object]) -> dict[str, int]:
    counts = pd.Series(list(values)).value_counts()
    ordered = sorted(counts.items(), key=lambda item: str(item[0]))
    return {str(name): int(count) for name, count in ordered}


def _format_price(price: SupportsFloat | None) -> str:
    if price is None or pd.isna(price):
        return MISSING_PRICE_TOKEN
    # Adding zero normalizes -0.0, which would otherwise digest as "-0.000000".
    return f"{float(price) + 0.0:.{PRICE_DIGEST_DECIMALS}f}"


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
