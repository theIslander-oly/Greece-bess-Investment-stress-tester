"""Small HTTPS retrieval helpers with explicit host restrictions.

Two things this module does are load-bearing for the point-in-time evidence path, and both are
here rather than at the call site because they are properties of the transport.

**A failure is classified, not collapsed.** A store that answers ``404`` is saying the object is
not there; a store that answers ``503``, resets the connection or truncates a body is saying
nothing about the object at all. Before this distinction existed, both arrived as one untyped
error, and the NOAA GFS client's key-layout loop read every one of them as "not at this key" —
so a transient fault was reported to the operator as a provider non-publication. Every
:class:`OfficialDataDownloadError` therefore carries a :attr:`~OfficialDataDownloadError.kind`
and, when the server answered at all, the HTTP status it answered with.

**A retryable failure is retried, and nothing else is.** The declared v0.9 fundamentals window is
roughly 200,000 HTTPS round trips. At any per-request failure rate above about one in a million,
a run with no retries does not finish, and the first dispatched attempt did not: four of its
twenty-three slices died on a single connection reset or truncated body apiece. Retries apply to
transport faults and 5xx answers only. A ``404`` is never retried — absence is an answer, and
re-asking cannot change it — and neither is any refusal this module makes about the shape of a
response, because those are deterministic.

Concurrency is deliberately absent. Retrying a failed request repeats the same conversation with
the provider; issuing many at once changes how an accepted evidence path talks to it.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .. import __version__

#: The request was refused here, before it was made: a non-HTTPS scheme, embedded credentials, a
#: host outside the allowlist or a malformed byte range. Never retried.
UNSAFE_REQUEST = "unsafe_request"

#: The store answered that the object is not there (``404``, or ``410`` for one it removed). This
#: is an answer about the object, and the only kind a caller may read as absence.
ABSENT = "absent"

#: The store answered, and refused: ``403``, ``400`` and every other 4xx that is not absence.
#: Not absence, and not retried — re-asking the same question gets the same refusal.
CLIENT_ERROR = "client_error"

#: The store answered ``5xx``. It says nothing about whether the object exists. Retried.
SERVER_ERROR = "server_error"

#: The request never completed: connection reset, TLS failure, DNS failure, timeout, or a body
#: that stopped short of its declared length. It says nothing about whether the object exists.
#: Retried.
TRANSPORT = "transport"

#: The store answered successfully with something this module will not accept as the answer —
#: today, a ``200`` to a byte-range request, which is the whole object rather than the slice that
#: was asked for. Deterministic, so not retried, and not absence.
UNUSABLE_RESPONSE = "unusable_response"

#: Every failure kind, in the order they are documented above.
FAILURE_KINDS = (
    UNSAFE_REQUEST,
    ABSENT,
    CLIENT_ERROR,
    SERVER_ERROR,
    TRANSPORT,
    UNUSABLE_RESPONSE,
)

#: The kinds that say nothing about the object and may be re-asked. Absence is not among them,
#: and neither is any refusal this module makes deterministically.
RETRYABLE_FAILURE_KINDS = frozenset({SERVER_ERROR, TRANSPORT})

#: The statuses that mean the object is not there. ``410 Gone`` is included because it is an
#: assertion of absence; every other 4xx is a refusal to answer, which is a different fact.
ABSENCE_STATUSES = frozenset({404, 410})


class OfficialDataDownloadError(RuntimeError):
    """Raised when an official-data HTTP request is unsafe or unsuccessful.

    ``kind`` names what went wrong in the vocabulary above, and ``status`` carries the HTTP
    status when the server answered with one. A caller that needs to tell absence from a
    transport fault must read :attr:`is_absence` rather than the message text.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str = TRANSPORT,
        status: int | None = None,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        if kind not in FAILURE_KINDS:
            raise ValueError(f"Unknown official-data failure kind: {kind!r}")
        self.kind = kind
        self.status = status
        self.attempts = attempts

    @property
    def is_absence(self) -> bool:
        """Whether the store answered that the object is not there."""

        return self.kind == ABSENT

    @property
    def is_retryable(self) -> bool:
        """Whether re-asking the same question could get a different answer."""

        return self.kind in RETRYABLE_FAILURE_KINDS


@dataclass(frozen=True)
class RetryPolicy:
    """How many times a retryable official-data request is re-asked, and how long between.

    The defaults are deliberately small and fixed rather than configurable. A retrieval that is
    accepted as evidence should talk to the provider the same way every time it is run, and the
    worst case here is bounded: four waits of 1, 2, 4 and 8 seconds, so a request that never
    succeeds costs fifteen seconds rather than a slice.
    """

    attempts: int = 5
    initial_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    maximum_backoff_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be at least 1")
        if self.initial_backoff_seconds < 0 or self.maximum_backoff_seconds < 0:
            raise ValueError("backoff seconds must not be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")


#: The policy every official-data request uses unless a caller states another.
DEFAULT_RETRY_POLICY = RetryPolicy()


def classify_http_status(status: int) -> str:
    """Return the failure kind an HTTP status code represents."""

    if status in ABSENCE_STATUSES:
        return ABSENT
    if status >= 500:
        return SERVER_ERROR
    return CLIENT_ERROR


def retry_official_request[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Run ``operation``, re-running it while it fails in a way that may yet succeed.

    A non-retryable failure — absence above all — is re-raised untouched on its first occurrence,
    so a caller that reads ``is_absence`` sees the store's own answer and not a verdict this
    helper reached after waiting. When every attempt fails, the last failure is re-raised with
    its kind and status preserved and the attempt count recorded, so an exhausted retry is never
    mistaken for a single fault.
    """

    delay = policy.initial_backoff_seconds
    for attempt in range(1, policy.attempts + 1):
        try:
            return operation()
        except OfficialDataDownloadError as exc:
            if not exc.is_retryable:
                raise
            if attempt == policy.attempts:
                raise OfficialDataDownloadError(
                    f"{exc} ({policy.attempts} attempts were made and every one failed this "
                    "way, so the request was not completed and the object's existence is "
                    "unknown)",
                    kind=exc.kind,
                    status=exc.status,
                    attempts=policy.attempts,
                ) from exc
            sleeper(delay)
            delay = min(delay * policy.backoff_multiplier, policy.maximum_backoff_seconds)
    raise AssertionError("unreachable: the retry loop always returns or raises")


def validate_https_url(url: str, *, allowed_hosts: Iterable[str]) -> str:
    """Return a normalized URL after enforcing HTTPS and an exact host allowlist."""

    parsed = urllib.parse.urlsplit(url)
    allowed = {host.lower() for host in allowed_hosts}
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise OfficialDataDownloadError(
            f"Official-data URL must use HTTPS: {url!r}", kind=UNSAFE_REQUEST
        )
    if parsed.username or parsed.password:
        raise OfficialDataDownloadError(
            "Official-data URL must not contain credentials", kind=UNSAFE_REQUEST
        )
    if host not in allowed:
        raise OfficialDataDownloadError(
            f"Official-data URL host is not allowed: {host!r}", kind=UNSAFE_REQUEST
        )
    if parsed.fragment:
        parsed = parsed._replace(fragment="")
    return urllib.parse.urlunsplit(parsed)


def fetch_https_bytes(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    timeout_seconds: int = 60,
    byte_range: tuple[int, int] | None = None,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleeper: Callable[[float], None] = time.sleep,
) -> bytes:
    """Retrieve bytes from an allowlisted official HTTPS endpoint.

    ``byte_range`` requests one inclusive byte range. It exists because a gridded forecast
    object is hundreds of megabytes of which a few megabytes are wanted, and the provider
    publishes a sidecar giving the exact offsets; requesting the whole object instead would turn
    a feasible history into an infeasible one. A server that answers ``200`` rather than ``206``
    ignored the range and sent the whole object, which is refused rather than silently accepted
    as the requested slice.

    Transport faults and 5xx answers are retried under ``retry_policy``. A ``404`` is not: the
    store answering that the object is not there is an answer, and the caller is told so through
    :attr:`OfficialDataDownloadError.is_absence` rather than after a wait.
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

    def attempt() -> bytes:
        request = urllib.request.Request(safe_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                if byte_range is not None and response.status != 206:
                    raise OfficialDataDownloadError(
                        f"Official-data server answered HTTP {response.status} to a byte-range "
                        "request; it ignored the range and the response is not the requested "
                        "slice",
                        kind=UNUSABLE_RESPONSE,
                        status=int(response.status),
                    )
                return bytes(response.read())
        except urllib.error.HTTPError as exc:
            raise _http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise OfficialDataDownloadError(
                f"Official-data connection failed: {exc.reason}", kind=TRANSPORT
            ) from exc
        except _TRANSPORT_FAULTS as exc:
            raise _transport_error(exc) from exc

    return retry_official_request(attempt, policy=retry_policy, sleeper=sleeper)


def head_https_headers(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    timeout_seconds: int = 60,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, str]:
    """Return the response headers of a ``HEAD`` against an allowlisted endpoint.

    The publication instant of an object store's object is a response header, not a value inside
    the object, so reading it needs a request that returns headers without a body. Failures are
    classified and retried exactly as they are for :func:`fetch_https_bytes`, which is what lets
    a caller probing several keys tell "not at this key" from "the store did not answer".
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    safe_url = validate_https_url(url, allowed_hosts=allowed_hosts)

    def attempt() -> dict[str, str]:
        request = urllib.request.Request(
            safe_url,
            headers={"User-Agent": f"greek-bess-investment-stress-tester/{__version__}"},
            method="HEAD",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return {str(key): str(value) for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            raise _http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise OfficialDataDownloadError(
                f"Official-data connection failed: {exc.reason}", kind=TRANSPORT
            ) from exc
        except _TRANSPORT_FAULTS as exc:
            raise _transport_error(exc) from exc

    return retry_official_request(attempt, policy=retry_policy, sleeper=sleeper)


#: Faults that are not :class:`urllib.error.URLError` because they happen after the response
#: began: a body that stops short of its declared length, a reset or TLS failure mid-read, a
#: read that times out. ``IncompleteRead`` is the one that killed a slice of the first dispatched
#: retrieval, and it reached the caller as a raw ``http.client`` exception.
_TRANSPORT_FAULTS = (
    http.client.HTTPException,
    ConnectionError,
    TimeoutError,
    socket.timeout,
    ssl.SSLError,
)


def _http_error(exc: urllib.error.HTTPError) -> OfficialDataDownloadError:
    status = int(exc.code)
    kind = classify_http_status(status)
    detail = (
        "; the object is not at this location"
        if kind == ABSENT
        else "; the answer says nothing about whether the object exists"
        if kind == SERVER_ERROR
        else ""
    )
    return OfficialDataDownloadError(
        f"Official-data server returned HTTP {status}{detail}", kind=kind, status=status
    )


def _transport_error(exc: BaseException) -> OfficialDataDownloadError:
    return OfficialDataDownloadError(
        f"Official-data transfer failed: {type(exc).__name__}: {exc}", kind=TRANSPORT
    )
