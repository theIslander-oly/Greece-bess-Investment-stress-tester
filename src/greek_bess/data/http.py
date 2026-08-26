"""Small HTTPS retrieval helpers with explicit host restrictions."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable

from .. import __version__


class OfficialDataDownloadError(RuntimeError):
    """Raised when an official-data HTTP request is unsafe or unsuccessful."""


def validate_https_url(url: str, *, allowed_hosts: Iterable[str]) -> str:
    """Return a normalized URL after enforcing HTTPS and an exact host allowlist."""

    parsed = urllib.parse.urlsplit(url)
    allowed = {host.lower() for host in allowed_hosts}
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise OfficialDataDownloadError(f"Official-data URL must use HTTPS: {url!r}")
    if parsed.username or parsed.password:
        raise OfficialDataDownloadError("Official-data URL must not contain credentials")
    if host not in allowed:
        raise OfficialDataDownloadError(f"Official-data URL host is not allowed: {host!r}")
    if parsed.fragment:
        parsed = parsed._replace(fragment="")
    return urllib.parse.urlunsplit(parsed)


def fetch_https_bytes(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    timeout_seconds: int = 60,
) -> bytes:
    """Retrieve bytes from an allowlisted official HTTPS endpoint."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    safe_url = validate_https_url(url, allowed_hosts=allowed_hosts)
    request = urllib.request.Request(
        safe_url,
        headers={
            "Accept": "application/json, application/zip, application/octet-stream, "
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/html",
            "User-Agent": f"greek-bess-investment-stress-tester/{__version__}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise OfficialDataDownloadError(f"Official-data server returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OfficialDataDownloadError(
            f"Official-data connection failed: {exc.reason}"
        ) from exc

