"""Incremental HEnEx daily-results discovery for the current unarchived year."""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

from .henex_archive import HENEX_ALLOWED_HOSTS
from .http import fetch_https_bytes, validate_https_url
from .provenance import (
    RetrievalRecord,
    atomic_write_bytes,
    sha256_bytes,
    utc_now_iso,
    write_retrieval_manifest,
)

HENEX_DAM_PUBLICATIONS_URL = (
    "https://www.enexgroup.gr/markets-publications-el-day-ahead-market"
)
HENEX_DAM_CATALOG_URL = (
    "https://www.enexgroup.gr/web/guest/markets-publications-el-day-ahead-market"
)
HENEX_RESULTS_PORTLET_INSTANCE = "6eBaUXF5VIb7"
_PORTLET_ID = (
    "com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_"
    + HENEX_RESULTS_PORTLET_INSTANCE
)
_FILENAME = re.compile(
    r"(?P<day>\d{8})_EL-DAM_Results_EN_v(?P<revision>\d+)(?:\.xlsx)?\b",
    re.IGNORECASE,
)


class HenexDailyError(RuntimeError):
    """Raised when the incremental HEnEx catalog cannot be interpreted."""


@dataclass(frozen=True)
class HenexDailyCatalogEntry:
    delivery_day: date
    revision: int
    filename: str
    detail_or_download_url: str


class HenexDailyClient:
    """Discover and download daily English DAM result workbooks from HEnEx."""

    def __init__(
        self,
        *,
        fetcher: Callable[[str], bytes] | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self._fetcher = fetcher
        self.timeout_seconds = timeout_seconds

    def discover(
        self,
        start_day: date,
        end_day: date,
        *,
        max_pages: int = 100,
    ) -> list[HenexDailyCatalogEntry]:
        if end_day < start_day:
            raise ValueError("end_day must not precede start_day")
        if max_pages <= 0:
            raise ValueError("max_pages must be positive")

        found: dict[tuple[date, int], HenexDailyCatalogEntry] = {}
        seen_catalog_entries: set[tuple[date, int]] = set()
        for page in range(1, max_pages + 1):
            html = self._get_bytes(_catalog_url(page)).decode("utf-8", errors="strict")
            page_entries = _parse_catalog(html)
            if not page_entries:
                break
            page_keys = {
                (entry.delivery_day, entry.revision) for entry in page_entries
            }
            if page > 1 and page_keys.issubset(seen_catalog_entries):
                raise HenexDailyError(
                    "HEnEx daily catalog pagination repeated an earlier page"
                )
            seen_catalog_entries.update(page_keys)
            for entry in page_entries:
                if start_day <= entry.delivery_day <= end_day:
                    key = (entry.delivery_day, entry.revision)
                    if key not in found:
                        found[key] = entry
            if min(entry.delivery_day for entry in page_entries) < start_day:
                break

        latest: dict[date, HenexDailyCatalogEntry] = {}
        for entry in found.values():
            incumbent = latest.get(entry.delivery_day)
            if incumbent is None or entry.revision > incumbent.revision:
                latest[entry.delivery_day] = entry
        expected_days = {
            start_day + timedelta(days=offset)
            for offset in range((end_day - start_day).days + 1)
        }
        missing_days = sorted(expected_days.difference(latest))
        if missing_days:
            raise HenexDailyError(
                "HEnEx daily catalog is missing "
                f"{len(missing_days)} requested delivery day(s); "
                f"first missing day: {missing_days[0].isoformat()}"
            )
        return sorted(latest.values(), key=lambda entry: entry.delivery_day)

    def download_results(
        self,
        entries: list[HenexDailyCatalogEntry],
        *,
        raw_dir: Path,
        manifest_path: Path | None = None,
        retrieved_at_utc: str | None = None,
    ) -> tuple[list[Path], list[RetrievalRecord]]:
        retrieved = retrieved_at_utc or utc_now_iso()
        workbooks: list[Path] = []
        records: list[RetrievalRecord] = []
        for entry in entries:
            download_url = self._resolve_download_url(entry)
            payload = self._get_bytes(download_url)
            if not payload.startswith(b"PK"):
                raise HenexDailyError(
                    f"HEnEx daily result is not an XLSX ZIP container: {entry.filename}"
                )
            target = raw_dir / "results" / str(entry.delivery_day.year) / entry.filename
            atomic_write_bytes(target, payload)
            digest = sha256_bytes(payload)
            records.append(
                RetrievalRecord(
                    source="henex",
                    dataset="dam_results_workbook",
                    source_url=download_url,
                    local_path=target.relative_to(raw_dir).as_posix(),
                    retrieved_at_utc=retrieved,
                    sha256=digest,
                    size_bytes=len(payload),
                    coverage_start=entry.delivery_day.isoformat(),
                    coverage_end=entry.delivery_day.isoformat(),
                    revision=entry.revision,
                    availability_classification="published_after_day_ahead_auction",
                )
            )
            workbooks.append(target)
        if manifest_path is not None:
            write_retrieval_manifest(manifest_path, records, created_at_utc=retrieved)
        return workbooks, records

    def _resolve_download_url(self, entry: HenexDailyCatalogEntry) -> str:
        candidate = validate_https_url(
            entry.detail_or_download_url, allowed_hosts=HENEX_ALLOWED_HOSTS
        )
        if _looks_like_download(candidate):
            return candidate
        detail = self._get_bytes(candidate).decode("utf-8", errors="strict")
        links = _parse_download_links(detail)
        if not links:
            raise HenexDailyError(f"No XLSX download link found for {entry.filename}")
        exact = [link for link in links if entry.filename.lower() in link.lower()]
        return exact[0] if exact else links[0]

    def _get_bytes(self, url: str) -> bytes:
        safe_url = validate_https_url(url, allowed_hosts=HENEX_ALLOWED_HOSTS)
        if self._fetcher is not None:
            return self._fetcher(safe_url)
        return fetch_https_bytes(
            safe_url,
            allowed_hosts=HENEX_ALLOWED_HOSTS,
            timeout_seconds=self.timeout_seconds,
        )


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text).strip()))
            self._href = None
            self._text = []


def _catalog_url(page: int) -> str:
    params = {
        "p_p_id": _PORTLET_ID,
        "p_p_lifecycle": "0",
        "p_p_state": "normal",
        "p_p_mode": "view",
        f"_{_PORTLET_ID}_cur": page,
        f"_{_PORTLET_ID}_delta": 200,
        f"_{_PORTLET_ID}_redirect": "/markets-publications-el-day-ahead-market",
        "p_r_p_resetCur": "false",
    }
    return f"{HENEX_DAM_CATALOG_URL}?{urllib.parse.urlencode(params)}"


def _parse_catalog(html: str) -> list[HenexDailyCatalogEntry]:
    parser = _AnchorParser()
    parser.feed(html)
    entries: dict[tuple[date, int], HenexDailyCatalogEntry] = {}
    for href, text in parser.anchors:
        match = _FILENAME.search(f"{text} {href}")
        if match is None:
            continue
        filename_match = _FILENAME.search(text) or _FILENAME.search(href)
        assert filename_match is not None
        filename = filename_match.group(0)
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"
        delivery_day = date.fromisoformat(
            f"{match.group('day')[:4]}-{match.group('day')[4:6]}-{match.group('day')[6:]}"
        )
        revision = int(match.group("revision"))
        url = urllib.parse.urljoin(HENEX_DAM_PUBLICATIONS_URL, href)
        entries[(delivery_day, revision)] = HenexDailyCatalogEntry(
            delivery_day=delivery_day,
            revision=revision,
            filename=filename,
            detail_or_download_url=url,
        )
    return sorted(entries.values(), key=lambda entry: (entry.delivery_day, entry.revision))


def _parse_download_links(html: str) -> list[str]:
    parser = _AnchorParser()
    parser.feed(html)
    links: list[str] = []
    for href, _ in parser.anchors:
        url = urllib.parse.urljoin(HENEX_DAM_PUBLICATIONS_URL, href)
        if _looks_like_download(url):
            links.append(validate_https_url(url, allowed_hosts=HENEX_ALLOWED_HOSTS))
    return sorted(set(links))


def _looks_like_download(url: str) -> bool:
    lowered = url.lower()
    return (
        ".xlsx" in lowered
        or "/documents/" in lowered
        or "/c/document_library/get_file" in lowered
    )
