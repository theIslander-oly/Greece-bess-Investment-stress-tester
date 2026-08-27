"""ENTSO-E Transparency Platform client for Greek DAM prices (A44)."""

from __future__ import annotations

import hashlib
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pandas as pd

from .. import __version__
from .schema import empty_canonical_frame, ensure_canonical
from .timezones import GREECE_TZ, MARKET_TZ, UTC, as_utc_timestamp, parse_iso_duration

ENTSOE_API_ENDPOINT = "https://web-api.tp.entsoe.eu/api"
GREECE_BIDDING_ZONE_EIC = "10YGR-HTSO-----Y"
RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})


class EntsoeError(RuntimeError):
    """Base error for ENTSO-E retrieval and parsing failures."""


class EntsoeAuthenticationError(EntsoeError):
    """Raised when no personal security token is available."""


class EntsoeResponseError(EntsoeError):
    """Raised for a rejected request or malformed API response."""


class EntsoeClient:
    """Minimal, auditable client for ENTSO-E day-ahead price documents."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout_seconds: int = 60,
        endpoint: str = ENTSOE_API_ENDPOINT,
        raw_cache_dir: str | Path | None = None,
        max_attempts: int = 5,
        retry_backoff_seconds: float = 10.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = token or os.getenv("ENTSOE_SECURITY_TOKEN")
        if not self._token or self._token == "replace-with-your-personal-token":
            raise EntsoeAuthenticationError(
                "Set ENTSOE_SECURITY_TOKEN to a personal ENTSO-E API token"
            )
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative")
        self.timeout_seconds = timeout_seconds
        self.endpoint = endpoint
        self.raw_cache_dir = Path(raw_cache_dir) if raw_cache_dir else None
        self.max_attempts = max_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self._sleep = sleep

    def fetch_prices(
        self,
        start: datetime | str | pd.Timestamp,
        end: datetime | str | pd.Timestamp,
        *,
        chunk_days: int = 31,
    ) -> pd.DataFrame:
        """Fetch Greek DAM prices for the half-open UTC interval `[start, end)`."""

        start_utc = as_utc_timestamp(start)
        end_utc = as_utc_timestamp(end)
        if end_utc <= start_utc:
            raise ValueError("end must be later than start")
        if not 1 <= chunk_days <= 366:
            raise ValueError("chunk_days must be between 1 and 366")

        frames: list[pd.DataFrame] = []
        cursor = start_utc
        while cursor < end_utc:
            chunk_end = min(cursor + pd.Timedelta(days=chunk_days), end_utc)
            raw = self._fetch_document(cursor, chunk_end)
            digest = hashlib.sha256(raw).hexdigest()
            retrieved = pd.Timestamp.now(tz=UTC)
            self._cache_raw(raw, cursor, chunk_end, digest)
            frame = parse_entsoe_price_xml(
                raw,
                retrieved_at_utc=retrieved,
                raw_sha256=digest,
            )
            frames.append(frame)
            cursor = chunk_end

        if not frames:
            return empty_canonical_frame()
        return ensure_canonical(pd.concat(frames, ignore_index=True))

    def _fetch_document(self, start_utc: pd.Timestamp, end_utc: pd.Timestamp) -> bytes:
        params = {
            "securityToken": self._token,
            "documentType": "A44",
            "in_Domain": GREECE_BIDDING_ZONE_EIC,
            "out_Domain": GREECE_BIDDING_ZONE_EIC,
            "periodStart": start_utc.strftime("%Y%m%d%H%M"),
            "periodEnd": end_utc.strftime("%Y%m%d%H%M"),
        }
        request = urllib.request.Request(
            f"{self.endpoint}?{urllib.parse.urlencode(params)}",
            headers={
                "Accept": "application/xml, text/xml",
                "User-Agent": f"greek-bess-investment-stress-tester/{__version__}",
            },
            method="GET",
        )
        # A multi-year retrieval issues dozens of sequential requests, so a single
        # timeout or transient server error must not discard the whole window.
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    result: bytes = response.read()
                    return result
            except urllib.error.HTTPError as exc:
                # Do not include exc.url: ENTSO-E tokens are query parameters.
                if exc.code not in RETRYABLE_HTTP_STATUS or attempt == self.max_attempts:
                    raise EntsoeResponseError(
                        f"ENTSO-E returned HTTP {exc.code} for {start_utc:%Y-%m-%dT%H:%MZ} "
                        f"to {end_utc:%Y-%m-%dT%H:%MZ}{_rejection_detail(exc)}"
                    ) from exc
                detail = f"HTTP {exc.code}"
            except (TimeoutError, urllib.error.URLError) as exc:
                reason = getattr(exc, "reason", exc)
                if attempt == self.max_attempts:
                    raise EntsoeResponseError(f"ENTSO-E connection failed: {reason}") from exc
                detail = str(reason)
            self._report_retry(start_utc, end_utc, attempt, detail)
            self._sleep(self.retry_backoff_seconds * attempt)
        raise EntsoeResponseError("ENTSO-E retrieval exhausted every attempt")

    def _report_retry(
        self,
        start_utc: pd.Timestamp,
        end_utc: pd.Timestamp,
        attempt: int,
        detail: str,
    ) -> None:
        # The request period is provenance; the endpoint carries the token and is omitted.
        print(
            f"ENTSO-E request for {start_utc:%Y-%m-%d} to {end_utc:%Y-%m-%d} failed on "
            f"attempt {attempt} of {self.max_attempts} ({detail}); retrying",
            file=sys.stderr,
        )

    def _cache_raw(
        self,
        raw: bytes,
        start_utc: pd.Timestamp,
        end_utc: pd.Timestamp,
        digest: str,
    ) -> None:
        if self.raw_cache_dir is None:
            return
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)
        name = (
            f"entsoe_a44_gr_{start_utc:%Y%m%d%H%M}_{end_utc:%Y%m%d%H%M}_"
            f"{digest[:12]}.xml"
        )
        (self.raw_cache_dir / name).write_bytes(raw)


def _rejection_detail(error: urllib.error.HTTPError) -> str:
    """Return the acknowledgement reason ENTSO-E sent with a rejected request."""

    try:
        body = error.read()
    except (OSError, ValueError):
        return ""
    if not body:
        return ""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return ""
    reasons = [
        stripped
        for element in _descendants(root, "text")
        if (text := element.text) and (stripped := text.strip())
    ]
    if not reasons:
        return ""
    return ": " + "; ".join(reasons)[:500]


def parse_entsoe_price_xml(
    raw: bytes | str,
    *,
    retrieved_at_utc: datetime | str | pd.Timestamp | None = None,
    raw_sha256: str | None = None,
) -> pd.DataFrame:
    """Parse an ENTSO-E A44 XML document into the canonical interval schema."""

    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    digest = raw_sha256 or hashlib.sha256(raw_bytes).hexdigest()
    retrieved = (
        as_utc_timestamp(retrieved_at_utc)
        if retrieved_at_utc is not None
        else pd.Timestamp.now(tz=UTC)
    )

    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as exc:
        raise EntsoeResponseError("ENTSO-E response is not valid XML") from exc

    time_series = _descendants(root, "TimeSeries")
    if not time_series:
        reasons = [text for element in _descendants(root, "text") if (text := element.text)]
        detail = "; ".join(reasons) if reasons else "No TimeSeries found"
        raise EntsoeResponseError(f"ENTSO-E rejected or returned no price data: {detail}")

    document_id = _first_text(root, "mRID", default="unknown")
    revision = _first_text(root, "revisionNumber", default="unknown")
    source_version = f"{document_id}:r{revision}"

    rows: list[dict[str, object]] = []
    for series in time_series:
        currency = _first_text(series, "currency_Unit.name", default="EUR") or "EUR"
        measure = _first_text(series, "price_Measure_Unit.name", default="MWH") or "MWH"
        if currency.upper() != "EUR":
            raise EntsoeResponseError(f"Expected EUR prices, received {currency}")
        if measure.upper() not in {"MWH", "MAW"}:
            raise EntsoeResponseError(f"Unexpected price measure unit: {measure}")

        for period in _children(series, "Period"):
            start_text = _nested_text(period, ["timeInterval", "start"])
            resolution_text = _first_text(period, "resolution")
            if start_text is None or resolution_text is None:
                raise EntsoeResponseError("A price period lacks start time or resolution")
            period_start = as_utc_timestamp(start_text)
            resolution = parse_iso_duration(resolution_text)
            duration_hours = resolution.total_seconds() / 3600
            if duration_hours not in (0.25, 1.0):
                raise EntsoeResponseError(
                    f"Unsupported ENTSO-E price resolution: {resolution_text}"
                )

            for point in _children(period, "Point"):
                position_text = _first_text(point, "position")
                price_text = _first_text(point, "price.amount")
                if position_text is None or price_text is None:
                    raise EntsoeResponseError("A price point lacks position or price")
                position = int(position_text)
                if position < 1:
                    raise EntsoeResponseError("ENTSO-E point positions must start at 1")
                start = period_start + (position - 1) * resolution
                end = start + resolution
                rows.append(
                    {
                        "delivery_start_utc": start,
                        "delivery_end_utc": end,
                        "delivery_start_market": start.tz_convert(MARKET_TZ),
                        "delivery_start_greece": start.tz_convert(GREECE_TZ),
                        "duration_hours": duration_hours,
                        "price_eur_per_mwh": float(price_text),
                        "bidding_zone": "GR",
                        "source": "entsoe",
                        "source_version": source_version,
                        "retrieved_at_utc": retrieved,
                        "raw_sha256": digest,
                        "quality_flags": [],
                    }
                )

    return ensure_canonical(pd.DataFrame(rows))


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [candidate for candidate in element.iter() if _local_name(candidate.tag) == name]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [candidate for candidate in element if _local_name(candidate.tag) == name]


def _first_text(element: ET.Element, name: str, default: str | None = None) -> str | None:
    for candidate in element.iter():
        if _local_name(candidate.tag) == name and candidate.text is not None:
            return candidate.text.strip()
    return default


def _nested_text(element: ET.Element, names: list[str]) -> str | None:
    current = element
    for name in names:
        match = next((child for child in current if _local_name(child.tag) == name), None)
        if match is None:
            return None
        current = match
    return current.text.strip() if current.text else None
