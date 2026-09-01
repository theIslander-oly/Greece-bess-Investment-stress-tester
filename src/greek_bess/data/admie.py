"""ADMIE/IPTO Operation & Market Files API client and provenance capture.

**Retained but unused.** ADMIE load and RES forecasts are out of scope (decision entry
2026-09-01), so nothing this client retrieves may enter a forecast, feature set, dispatch plan
or reported result. The module is kept, tested and runnable so that a future operator
declaration of the day-ahead gate closure could be tested without rebuilding it. It is the
executable form of a refusal rather than dead code, and should not be pruned on sight.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .http import OfficialDataDownloadError, fetch_https_bytes, validate_https_url
from .provenance import (
    RetrievalRecord,
    atomic_write_bytes,
    sha256_bytes,
    utc_now_iso,
    write_retrieval_manifest,
)
from .timezones import GREECE_TZ, UTC

ADMIE_BASE_URL = "https://www.admie.gr"
ADMIE_ALLOWED_HOSTS = frozenset({"www.admie.gr", "admie.gr"})
LEAKAGE_RELEVANT_FILETYPES = frozenset(
    {
        "ISP1DayAheadLoadForecast",
        "ISP1DayAheadRESForecast",
        "ISP2DayAheadLoadForecast",
        "ISP2DayAheadRESForecast",
    }
)
_REVISION = re.compile(r"_(?P<revision>\d+)\.(?:xlsx?|csv|zip)$", re.IGNORECASE)


class AdmieError(RuntimeError):
    """Raised when ADMIE metadata or file retrieval is invalid."""


@dataclass(frozen=True)
class AdmieFileRecord:
    filetype: str
    file_path: str
    file_description: str
    file_process: str
    file_datatype: str
    file_coverageperiod: str
    file_fromdate: date
    file_todate: date
    file_published: str
    published_at_utc: str
    revision: int | None

    @classmethod
    def from_api(cls, filetype: str, payload: object) -> AdmieFileRecord:
        if not isinstance(payload, dict):
            raise AdmieError("ADMIE file result must be a JSON object")
        required = {
            "file_path",
            "file_description",
            "file_process",
            "file_datatype",
            "file_coverageperiod",
            "file_fromdate",
            "file_todate",
            "file_published",
        }
        missing = sorted(required - payload.keys())
        if missing:
            raise AdmieError(f"ADMIE file result is missing fields: {', '.join(missing)}")
        path = str(payload["file_path"])
        try:
            validate_https_url(path, allowed_hosts=ADMIE_ALLOWED_HOSTS)
            from_day = datetime.strptime(str(payload["file_fromdate"]), "%d.%m.%Y").date()
            to_day = datetime.strptime(str(payload["file_todate"]), "%d.%m.%Y").date()
            published_local = pd.Timestamp(
                datetime.strptime(str(payload["file_published"]), "%d.%m.%Y %H:%M"),
                tz=GREECE_TZ,
            )
        except (ValueError, OfficialDataDownloadError) as exc:
            raise AdmieError("ADMIE file result contains invalid URL or dates") from exc
        if to_day < from_day:
            raise AdmieError("ADMIE file coverage end precedes its start")
        revision_match = _REVISION.search(Path(urllib.parse.urlsplit(path).path).name)
        return cls(
            filetype=filetype,
            file_path=path,
            file_description=str(payload["file_description"]),
            file_process=str(payload["file_process"]),
            file_datatype=str(payload["file_datatype"]),
            file_coverageperiod=str(payload["file_coverageperiod"]),
            file_fromdate=from_day,
            file_todate=to_day,
            file_published=str(payload["file_published"]),
            published_at_utc=published_local.tz_convert(UTC).isoformat(),
            revision=int(revision_match.group("revision")) if revision_match else None,
        )


class AdmieClient:
    """Read the public ADMIE file catalog and download selected official files."""

    def __init__(
        self,
        *,
        fetcher: Callable[[str], bytes] | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self._fetcher = fetcher

    def list_filetypes(self) -> list[dict[str, object]]:
        payload = self._fetch_json(f"{ADMIE_BASE_URL}/getFiletypeInfoEN")
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise AdmieError("ADMIE filetype endpoint did not return a list of objects")
        return sorted(payload, key=lambda item: str(item.get("filetype", "")))

    def find_files(
        self,
        filetype: str,
        start_day: date,
        end_day: date,
        *,
        overlap: bool = True,
    ) -> list[AdmieFileRecord]:
        if end_day < start_day:
            raise ValueError("end_day must not precede start_day")
        if not filetype or not re.fullmatch(r"[A-Za-z0-9_]+", filetype):
            raise ValueError("filetype must contain only letters, digits and underscores")
        endpoint = "getOperationMarketFilewRange" if overlap else "getOperationMarketFile"
        query = urllib.parse.urlencode(
            {
                "dateStart": start_day.isoformat(),
                "dateEnd": end_day.isoformat(),
                "FileCategory": filetype,
            }
        )
        payload = self._fetch_json(f"{ADMIE_BASE_URL}/{endpoint}?{query}")
        if not isinstance(payload, list):
            raise AdmieError("ADMIE file endpoint did not return a JSON list")
        return [AdmieFileRecord.from_api(filetype, item) for item in payload]

    def download_files(
        self,
        records: Iterable[AdmieFileRecord],
        *,
        raw_dir: Path,
        manifest_path: Path | None = None,
        retrieved_at_utc: str | None = None,
    ) -> list[RetrievalRecord]:
        retrieved = retrieved_at_utc or utc_now_iso()
        provenance: list[RetrievalRecord] = []
        for record in sorted(records, key=_record_sort_key):
            payload = self._get_bytes(record.file_path)
            digest = sha256_bytes(payload)
            filename = Path(urllib.parse.urlsplit(record.file_path).path).name
            target = raw_dir / record.filetype / filename
            atomic_write_bytes(target, payload)
            provenance.append(
                RetrievalRecord(
                    source="admie",
                    dataset=record.filetype,
                    source_url=record.file_path,
                    local_path=target.relative_to(raw_dir).as_posix(),
                    retrieved_at_utc=retrieved,
                    sha256=digest,
                    size_bytes=len(payload),
                    coverage_start=record.file_fromdate.isoformat(),
                    coverage_end=record.file_todate.isoformat(),
                    published_at_source=record.file_published,
                    published_at_utc=record.published_at_utc,
                    revision=record.revision,
                    availability_classification=(
                        "requires_pre_auction_timing_validation"
                        if record.filetype in LEAKAGE_RELEVANT_FILETYPES
                        else "historical_explanatory_or_lagged_only_until_validated"
                    ),
                )
            )
        if manifest_path is not None:
            write_retrieval_manifest(manifest_path, provenance, created_at_utc=retrieved)
        return provenance

    def _fetch_json(self, url: str) -> object:
        raw = self._get_bytes(url)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdmieError("ADMIE endpoint did not return valid UTF-8 JSON") from exc

    def _get_bytes(self, url: str) -> bytes:
        if self._fetcher is not None:
            return self._fetcher(url)
        return fetch_https_bytes(
            url,
            allowed_hosts=ADMIE_ALLOWED_HOSTS,
            timeout_seconds=self.timeout_seconds,
        )


def select_latest_admie_revisions(
    records: Iterable[AdmieFileRecord],
) -> list[AdmieFileRecord]:
    """Select the latest publication per filetype and coverage period."""

    selected: dict[tuple[str, date, date], AdmieFileRecord] = {}
    for record in records:
        key = (record.filetype, record.file_fromdate, record.file_todate)
        incumbent = selected.get(key)
        if incumbent is None or _revision_sort_key(record) > _revision_sort_key(incumbent):
            selected[key] = record
    return sorted(selected.values(), key=_record_sort_key)


def _revision_sort_key(record: AdmieFileRecord) -> tuple[pd.Timestamp, int, str]:
    return (
        pd.Timestamp(record.published_at_utc),
        record.revision if record.revision is not None else -1,
        record.file_path,
    )


def _record_sort_key(record: AdmieFileRecord) -> tuple[str, date, date, str]:
    return (
        record.filetype,
        record.file_fromdate,
        record.file_todate,
        record.file_path,
    )
