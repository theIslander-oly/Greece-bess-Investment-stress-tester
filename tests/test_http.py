"""What an official-data HTTP failure means, and which failures are worth re-asking.

Two facts the point-in-time evidence path rests on are properties of this module, so they are
pinned here rather than inferred from a caller's behaviour: a ``404`` is an answer about the
object and everything else is not, and only a failure that says nothing about the object is
retried. Nothing here reaches a network — ``urllib.request.urlopen`` is replaced, and the
backoff sleeps into a list.
"""

from __future__ import annotations

import http.client
import unittest
import urllib.error
import urllib.request
from typing import Any
from unittest import mock

from greek_bess.data.http import (
    ABSENT,
    CLIENT_ERROR,
    DEFAULT_RETRY_POLICY,
    SERVER_ERROR,
    TRANSPORT,
    UNSAFE_REQUEST,
    UNUSABLE_RESPONSE,
    OfficialDataDownloadError,
    RetryPolicy,
    classify_http_status,
    fetch_https_bytes,
    head_https_headers,
    retry_official_request,
    validate_https_url,
)

HOST = "www.admie.gr"
URL = f"https://{HOST}/file.xls"

#: Short and cheap: three attempts, and the waits are recorded rather than taken.
FAST = RetryPolicy(attempts=3, initial_backoff_seconds=1.0, backoff_multiplier=2.0)


def _http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(URL, status, "refused", {}, None)  # type: ignore[arg-type]


class _Server:
    """A stand-in ``urlopen``: raises the queued failures, then answers."""

    def __init__(
        self,
        *failures: BaseException,
        body: bytes = b"payload",
        status: int = 200,
        headers: dict[str, str] | None = None,
        read_error: BaseException | None = None,
    ) -> None:
        self.failures = list(failures)
        self.body = body
        self.status = status
        self.headers = headers or {"Last-Modified": "Wed, 19 Aug 2026 03:52:00 GMT"}
        self.read_error = read_error
        self.calls: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: int) -> Any:
        self.calls.append(request)
        if self.failures:
            raise self.failures.pop(0)
        response = mock.MagicMock()
        response.status = self.status
        response.headers.items.return_value = list(self.headers.items())
        if self.read_error is not None:
            response.read.side_effect = self.read_error
        else:
            response.read.return_value = self.body
        response.__enter__.return_value = response
        return response


class _Clock:
    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


class UrlValidationTests(unittest.TestCase):
    def test_https_allowlist_accepts_expected_host(self) -> None:
        result = validate_https_url(
            "https://www.admie.gr/getFiletypeInfoEN#fragment",
            allowed_hosts={"www.admie.gr"},
        )
        self.assertEqual(result, "https://www.admie.gr/getFiletypeInfoEN")

    def test_credentials_http_and_foreign_hosts_are_rejected(self) -> None:
        for url in (
            "http://www.admie.gr/file.xls",
            "https://token@www.admie.gr/file.xls",
            "https://example.com/file.xls",
        ):
            with self.subTest(url=url):
                with self.assertRaises(OfficialDataDownloadError) as caught:
                    validate_https_url(url, allowed_hosts={"www.admie.gr"})
                # A request this module refuses to make is not a statement about the object,
                # and is never retried or read as absence.
                self.assertEqual(caught.exception.kind, UNSAFE_REQUEST)
                self.assertFalse(caught.exception.is_absence)
                self.assertFalse(caught.exception.is_retryable)


class StatusClassificationTests(unittest.TestCase):
    def test_only_the_absence_statuses_are_absence(self) -> None:
        self.assertEqual(classify_http_status(404), ABSENT)
        self.assertEqual(classify_http_status(410), ABSENT)
        self.assertEqual(classify_http_status(403), CLIENT_ERROR)
        self.assertEqual(classify_http_status(400), CLIENT_ERROR)
        self.assertEqual(classify_http_status(500), SERVER_ERROR)
        self.assertEqual(classify_http_status(503), SERVER_ERROR)

    def test_only_a_server_error_or_a_transport_fault_is_retryable(self) -> None:
        retryable = {
            kind: OfficialDataDownloadError("x", kind=kind).is_retryable
            for kind in (ABSENT, CLIENT_ERROR, SERVER_ERROR, TRANSPORT, UNSAFE_REQUEST)
        }
        self.assertEqual(
            retryable,
            {
                ABSENT: False,
                CLIENT_ERROR: False,
                SERVER_ERROR: True,
                TRANSPORT: True,
                UNSAFE_REQUEST: False,
            },
        )

    def test_a_kind_outside_the_vocabulary_cannot_be_invented(self) -> None:
        with self.assertRaises(ValueError):
            OfficialDataDownloadError("x", kind="probably_missing")


class AbsenceTests(unittest.TestCase):
    """A 404 is the store's answer, and it is delivered as an answer rather than after a wait."""

    def test_a_404_is_absence_and_is_never_retried(self) -> None:
        server = _Server(_http_error(404))
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            with self.assertRaises(OfficialDataDownloadError) as caught:
                fetch_https_bytes(
                    URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
                )
        self.assertTrue(caught.exception.is_absence)
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.attempts, 1)
        self.assertEqual(len(server.calls), 1)
        self.assertEqual(clock.waits, [])

    def test_a_head_404_is_absence_and_a_head_503_is_not(self) -> None:
        for status, absence in ((404, True), (503, False)):
            with self.subTest(status=status):
                server = _Server(*[_http_error(status)] * FAST.attempts)
                with mock.patch("urllib.request.urlopen", server):
                    with self.assertRaises(OfficialDataDownloadError) as caught:
                        head_https_headers(
                            URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=_Clock()
                        )
                self.assertEqual(caught.exception.is_absence, absence)

    def test_a_403_is_neither_absence_nor_retried(self) -> None:
        server = _Server(_http_error(403))
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            with self.assertRaises(OfficialDataDownloadError) as caught:
                fetch_https_bytes(
                    URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
                )
        self.assertFalse(caught.exception.is_absence)
        self.assertEqual(caught.exception.kind, CLIENT_ERROR)
        self.assertEqual(len(server.calls), 1)
        self.assertEqual(clock.waits, [])


class RetryTests(unittest.TestCase):
    """The declared v0.9 window is roughly 200,000 requests; without this it does not finish."""

    def test_a_server_error_that_clears_returns_the_body(self) -> None:
        server = _Server(_http_error(503), _http_error(500), body=b"grib")
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            payload = fetch_https_bytes(
                URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
            )
        self.assertEqual(payload, b"grib")
        self.assertEqual(len(server.calls), 3)
        self.assertEqual(clock.waits, [1.0, 2.0])

    def test_a_connection_reset_is_retried_and_then_succeeds(self) -> None:
        reset = urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))
        server = _Server(reset, body=b"grib")
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            payload = fetch_https_bytes(
                URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
            )
        self.assertEqual(payload, b"grib")
        self.assertEqual(clock.waits, [1.0])

    def test_a_body_that_stops_short_is_a_classified_transport_fault(self) -> None:
        """The failure that killed one slice of the first dispatched retrieval.

        ``IncompleteRead`` is neither ``HTTPError`` nor ``URLError``, so it escaped this module
        untyped and reached the operator as a traceback rather than as a named condition.
        """

        truncated = http.client.IncompleteRead(b"504341 bytes", 432836)
        server = _Server(read_error=truncated)
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            with self.assertRaises(OfficialDataDownloadError) as caught:
                fetch_https_bytes(
                    URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
                )
        self.assertEqual(caught.exception.kind, TRANSPORT)
        self.assertFalse(caught.exception.is_absence)
        self.assertEqual(caught.exception.attempts, FAST.attempts)
        self.assertEqual(len(server.calls), FAST.attempts)

    def test_an_exhausted_retry_keeps_its_kind_status_and_attempt_count(self) -> None:
        server = _Server(*[_http_error(503)] * FAST.attempts)
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            with self.assertRaises(OfficialDataDownloadError) as caught:
                fetch_https_bytes(
                    URL, allowed_hosts=[HOST], retry_policy=FAST, sleeper=clock
                )
        self.assertEqual(caught.exception.kind, SERVER_ERROR)
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.attempts, 3)
        self.assertFalse(caught.exception.is_absence)
        self.assertIn("existence is unknown", str(caught.exception))
        self.assertEqual(clock.waits, [1.0, 2.0])

    def test_the_backoff_doubles_and_is_capped(self) -> None:
        policy = RetryPolicy(
            attempts=6,
            initial_backoff_seconds=1.0,
            backoff_multiplier=2.0,
            maximum_backoff_seconds=4.0,
        )
        clock = _Clock()
        with self.assertRaises(OfficialDataDownloadError):
            retry_official_request(
                lambda: (_ for _ in ()).throw(
                    OfficialDataDownloadError("down", kind=SERVER_ERROR, status=503)
                ),
                policy=policy,
                sleeper=clock,
            )
        self.assertEqual(clock.waits, [1.0, 2.0, 4.0, 4.0, 4.0])

    def test_a_non_retryable_failure_is_raised_as_it_was_first_seen(self) -> None:
        original = OfficialDataDownloadError("gone", kind=ABSENT, status=404)
        clock = _Clock()
        with self.assertRaises(OfficialDataDownloadError) as caught:
            retry_official_request(
                lambda: (_ for _ in ()).throw(original), policy=FAST, sleeper=clock
            )
        self.assertIs(caught.exception, original)
        self.assertEqual(clock.waits, [])

    def test_the_default_policy_is_bounded_and_stated(self) -> None:
        self.assertEqual(DEFAULT_RETRY_POLICY.attempts, 5)
        self.assertEqual(DEFAULT_RETRY_POLICY.initial_backoff_seconds, 1.0)
        self.assertEqual(DEFAULT_RETRY_POLICY.backoff_multiplier, 2.0)
        with self.assertRaises(ValueError):
            RetryPolicy(attempts=0)


class ByteRangeTests(unittest.TestCase):
    def test_a_range_answered_with_the_whole_object_is_refused_and_not_retried(self) -> None:
        server = _Server(status=200, body=b"the whole object")
        clock = _Clock()
        with mock.patch("urllib.request.urlopen", server):
            with self.assertRaises(OfficialDataDownloadError) as caught:
                fetch_https_bytes(
                    URL,
                    allowed_hosts=[HOST],
                    byte_range=(0, 15),
                    retry_policy=FAST,
                    sleeper=clock,
                )
        self.assertEqual(caught.exception.kind, UNUSABLE_RESPONSE)
        self.assertFalse(caught.exception.is_absence)
        self.assertEqual(len(server.calls), 1)
        self.assertEqual(clock.waits, [])

    def test_a_partial_content_answer_returns_the_slice(self) -> None:
        server = _Server(status=206, body=b"slice")
        with mock.patch("urllib.request.urlopen", server):
            payload = fetch_https_bytes(
                URL, allowed_hosts=[HOST], byte_range=(0, 4), sleeper=_Clock()
            )
        self.assertEqual(payload, b"slice")
        self.assertEqual(server.calls[0].get_header("Range"), "bytes=0-4")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
