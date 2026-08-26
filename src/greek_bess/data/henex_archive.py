"""HEnEx annual-archive and multi-workbook DAM price ingestion."""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

import pandas as pd

from .henex import HenexParseError, parse_henex_results
from .http import fetch_https_bytes
from .provenance import (
    RetrievalRecord,
    atomic_write_bytes,
    sha256_bytes,
    utc_now_iso,
    write_retrieval_manifest,
)
from .schema import empty_canonical_frame, ensure_canonical

HENEX_ALLOWED_HOSTS = frozenset({"www.enexgroup.gr", "enexgroup.gr"})
HENEX_ANNUAL_RESULTS_ARCHIVES = {
    2020: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=3c970a88-5230-26ef-bac7-a9b0891a2b73"
    ),
    2021: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=eb8ea827-88d7-10c3-16c1-356e386439ae"
    ),
    2022: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=6feb2af7-daa6-9d77-557c-db32ba4573a2"
    ),
    2023: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=f543600f-3948-d3e9-c337-8ff7ee997794"
    ),
    2024: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=6f2dc5b3-ef9b-b3a9-c935-ca44e7648b93"
    ),
    2025: (
        "https://www.enexgroup.gr/c/document_library/get_file?"
        "groupId=20126&uuid=73d205d3-0885-f876-b995-d73ad1b934b8"
    ),
}

_RESULT_NAME = re.compile(
    r"^(?P<day>\d{8})_EL-DAM_Results_EN_v(?P<revision>\d+)\.xlsx$", re.IGNORECASE
)
_NESTED_DAM_ARCHIVE = re.compile(r"^(?P<year>\d{4})_EL-DAM_Results\.zip$", re.IGNORECASE)
_VERSION = re.compile(r"^v(?P<revision>\d+)$", re.IGNORECASE)
_MAX_WORKBOOK_SIZE_BYTES = 100 * 1024 * 1024
_MAX_NESTED_ARCHIVE_SIZE_BYTES = 250 * 1024 * 1024


class HenexArchiveError(RuntimeError):
    """Raised when a HEnEx archive cannot be safely retrieved or interpreted."""


def download_henex_annual_archives(
    years: Iterable[int],
    *,
    raw_dir: Path,
    manifest_path: Path | None = None,
    fetcher: Callable[[str], bytes] | None = None,
    retrieved_at_utc: str | None = None,
) -> tuple[list[Path], list[RetrievalRecord]]:
    """Download official annual ZIPs and extract only English DAM result workbooks."""

    selected_years = sorted(set(years))
    unsupported = [year for year in selected_years if year not in HENEX_ANNUAL_RESULTS_ARCHIVES]
    if unsupported:
        supported = f"{min(HENEX_ANNUAL_RESULTS_ARCHIVES)}-{max(HENEX_ANNUAL_RESULTS_ARCHIVES)}"
        raise HenexArchiveError(
            "No verified annual HEnEx results archive for years "
            f"{unsupported}; supported {supported}"
        )
    if not selected_years:
        raise HenexArchiveError("At least one HEnEx archive year is required")

    get_bytes = fetcher or (
        lambda url: fetch_https_bytes(url, allowed_hosts=HENEX_ALLOWED_HOSTS)
    )
    retrieved = retrieved_at_utc or utc_now_iso()
    records: list[RetrievalRecord] = []
    workbooks: list[Path] = []

    for year in selected_years:
        url = HENEX_ANNUAL_RESULTS_ARCHIVES[year]
        archive = get_bytes(url)
        archive_sha = sha256_bytes(archive)
        archive_path = raw_dir / "archives" / f"{year}_EL-DAM_results_{archive_sha[:12]}.zip"
        atomic_write_bytes(archive_path, archive)
        records.append(
            RetrievalRecord(
                source="henex",
                dataset="dam_results_annual_archive",
                source_url=url,
                local_path=archive_path.relative_to(raw_dir).as_posix(),
                retrieved_at_utc=retrieved,
                sha256=archive_sha,
                size_bytes=len(archive),
                coverage_start="2020-11-01" if year == 2020 else f"{year}-01-01",
                coverage_end=f"{year}-12-31",
                availability_classification="published_after_day_ahead_auction",
            )
        )
        extracted_paths, extracted_records = _extract_result_workbooks(
            archive,
            destination=raw_dir / "results" / str(year),
            source_url=url,
            retrieved_at_utc=retrieved,
            parent_sha256=archive_sha,
            raw_dir=raw_dir,
        )
        workbooks.extend(extracted_paths)
        records.extend(extracted_records)

    if not workbooks:
        raise HenexArchiveError("Verified HEnEx archives contained no English DAM result files")
    if manifest_path is not None:
        write_retrieval_manifest(manifest_path, records, created_at_utc=retrieved)
    return sorted(workbooks), records


def normalize_henex_workbooks(
    workbooks: Iterable[Path],
    *,
    retrieved_at_utc: str | None = None,
) -> pd.DataFrame:
    """Parse many daily workbooks and retain the latest revision per interval."""

    paths = sorted(set(Path(path) for path in workbooks))
    if not paths:
        return empty_canonical_frame()
    paths = _select_latest_workbook_revisions(paths)
    frames = [
        parse_henex_results(path, retrieved_at_utc=retrieved_at_utc) for path in paths
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined["_revision"] = combined["source_version"].map(_revision_number)
    keys = ["delivery_start_utc", "delivery_end_utc"]
    latest = combined.groupby(keys)["_revision"].transform("max")
    candidates = combined.loc[combined["_revision"].eq(latest)].copy()

    conflict_counts = candidates.groupby(keys)["price_eur_per_mwh"].nunique(dropna=False)
    if conflict_counts.gt(1).any():
        sample = conflict_counts[conflict_counts.gt(1)].index[0]
        raise HenexParseError(f"Conflicting latest-revision MCP values for interval {sample}")

    candidates = candidates.sort_values(
        [*keys, "retrieved_at_utc", "raw_sha256"], kind="stable"
    )
    selected = candidates.groupby(keys, as_index=False, sort=False).tail(1)
    return ensure_canonical(selected.drop(columns="_revision"))


def _select_latest_workbook_revisions(paths: list[Path]) -> list[Path]:
    """Select the latest published workbook for each delivery day before parsing.

    Superseded HEnEx workbooks can contain the inconsistency that a later official
    revision was published to correct. Parsing every revision first would reject the
    superseded file before the corrected latest revision can be selected.
    """

    by_day: dict[str, list[tuple[int, Path]]] = {}
    for path in paths:
        match = _RESULT_NAME.fullmatch(path.name)
        if match is None:
            raise HenexParseError(f"Unrecognized HEnEx result filename: {path.name!r}")
        by_day.setdefault(match.group("day"), []).append(
            (int(match.group("revision")), path)
        )

    selected: list[Path] = []
    for candidates in by_day.values():
        latest_revision = max(revision for revision, _ in candidates)
        selected.extend(
            path for revision, path in candidates if revision == latest_revision
        )
    return sorted(selected)


def find_henex_result_workbooks(root: Path) -> list[Path]:
    """Find result workbooks below a private raw-data directory."""

    return sorted(
        path for path in root.rglob("*.xlsx") if _RESULT_NAME.fullmatch(path.name)
    )


def _extract_result_workbooks(
    archive: bytes,
    *,
    destination: Path,
    source_url: str,
    retrieved_at_utc: str,
    parent_sha256: str,
    raw_dir: Path,
    allow_nested_archive: bool = True,
) -> tuple[list[Path], list[RetrievalRecord]]:
    try:
        zipped = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise HenexArchiveError("HEnEx annual archive is not a valid ZIP file") from exc

    workbooks: list[Path] = []
    records: list[RetrievalRecord] = []
    with zipped:
        for member in zipped.infolist():
            if member.is_dir():
                continue
            pure_path = PurePosixPath(member.filename)
            if pure_path.is_absolute() or ".." in pure_path.parts:
                raise HenexArchiveError(f"Unsafe archive member path: {member.filename!r}")
            match = _RESULT_NAME.fullmatch(pure_path.name)
            nested_match = _NESTED_DAM_ARCHIVE.fullmatch(pure_path.name)
            if nested_match is not None and not allow_nested_archive:
                raise HenexArchiveError(
                    f"Nested HEnEx DAM archive exceeds supported depth: {pure_path.name}"
                )
            if nested_match is not None and allow_nested_archive:
                if member.file_size > _MAX_NESTED_ARCHIVE_SIZE_BYTES:
                    raise HenexArchiveError(
                        f"Nested HEnEx DAM archive is unexpectedly large: {pure_path.name}"
                    )
                nested_payload = zipped.read(member)
                nested_sha = sha256_bytes(nested_payload)
                nested_target = (
                    raw_dir
                    / "archives"
                    / f"{pure_path.stem}_{nested_sha[:12]}.zip"
                )
                atomic_write_bytes(nested_target, nested_payload)
                records.append(
                    RetrievalRecord(
                        source="henex",
                        dataset="dam_results_nested_archive",
                        source_url=source_url,
                        local_path=nested_target.relative_to(raw_dir).as_posix(),
                        retrieved_at_utc=retrieved_at_utc,
                        sha256=nested_sha,
                        size_bytes=len(nested_payload),
                        coverage_start=f"{nested_match.group('year')}-01-01",
                        coverage_end=f"{nested_match.group('year')}-12-31",
                        parent_sha256=parent_sha256,
                        availability_classification="published_after_day_ahead_auction",
                    )
                )
                nested_workbooks, nested_records = _extract_result_workbooks(
                    nested_payload,
                    destination=destination,
                    source_url=source_url,
                    retrieved_at_utc=retrieved_at_utc,
                    parent_sha256=nested_sha,
                    raw_dir=raw_dir,
                    allow_nested_archive=False,
                )
                workbooks.extend(nested_workbooks)
                records.extend(nested_records)
                continue
            if match is None:
                continue
            if member.file_size > _MAX_WORKBOOK_SIZE_BYTES:
                raise HenexArchiveError(f"HEnEx workbook is unexpectedly large: {pure_path.name}")
            payload = zipped.read(member)
            target = destination / pure_path.name
            atomic_write_bytes(target, payload)
            digest = sha256_bytes(payload)
            delivery_day = pd.Timestamp(match.group("day")).date().isoformat()
            record = RetrievalRecord(
                source="henex",
                dataset="dam_results_workbook",
                source_url=source_url,
                local_path=target.relative_to(raw_dir).as_posix(),
                retrieved_at_utc=retrieved_at_utc,
                sha256=digest,
                size_bytes=len(payload),
                coverage_start=delivery_day,
                coverage_end=delivery_day,
                revision=int(match.group("revision")),
                parent_sha256=parent_sha256,
                availability_classification="published_after_day_ahead_auction",
            )
            workbooks.append(target)
            records.append(record)
    return workbooks, records


def _revision_number(value: object) -> int:
    match = _VERSION.fullmatch(str(value))
    if match is None:
        raise HenexParseError(f"Unrecognized HEnEx source version: {value!r}")
    return int(match.group("revision"))
