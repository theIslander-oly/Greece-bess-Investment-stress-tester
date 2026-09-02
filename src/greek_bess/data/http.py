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
    byte_range: tuple[int, int] | None = None,
) -> bytes:
    """Retrieve bytes from an allowlisted official HTTPS endpoint.

    ``byte_range`` requests one inclusive byte range. It exists because a gridded forecast
    object is hundreds of megabytes of which a few megabytes are wanted, and the provider
    publishes a sidecar giving the exact offsets; requesting the whole object instead would turn
    a feasible history into an infeasible one. A server that answers ``200`` rather than ``206``
    ignored the range and sent the whole object, which is refused rather than silently accepted
    as the requested slice.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    headers = {
        "Accept": "application/json, application/zip, application/octet-stream, "
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/html",
        "User-Agent": f"greek-bess-investment-stress-tester/{__version__}",
    }
    if byte_range is not None:
        start, end = byte_range
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            raise ValueError("byte_range must be an inclusive (start, end) pair of offsets")
        headers["Range"] = f"bytes={start}-{end}"
    safe_url = validate_https_url(url, allowed_hosts=allowed_hosts)
    request = urllib.request.Request(safe_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if byte_range is not None and response.status != 206:
                raise OfficialDataDownloadError(
                    f"Official-data server answered HTTP {response.status} to a byte-range "
                    "request; it ignored the range and the response is not the requested slice"
                )
            return response.read()
    except urllib.error.HTTPError as exc:
        raise OfficialDataDownloadError(f"Official-data server returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OfficialDataDownloadError(
            f"Official-data connection failed: {exc.reason}"
        ) from exc


def head_https_headers(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    timeout_seconds: int = 60,
) -> dict[str, str]:
    """Return the response headers of a ``HEAD`` against an allowlisted endpoint.

    The publication instant of an object store's object is a response header, not a value inside
    the object, so reading it needs a request that returns headers without a body.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    safe_url = validate_https_url(url, allowed_hosts=allowed_hosts)
    request = urllib.request.Request(
        safe_url,
        headers={"User-Agent": f"greek-bess-investment-stress-tester/{__version__}"},
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return {str(key): str(value) for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        raise OfficialDataDownloadError(f"Official-data server returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OfficialDataDownloadError(
            f"Official-data connection failed: {exc.reason}"
        ) from exc

