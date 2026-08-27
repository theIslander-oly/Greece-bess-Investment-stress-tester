from __future__ import annotations

import unittest
import urllib.error
from unittest import mock

from greek_bess.data.entsoe import (
    EntsoeClient,
    EntsoeResponseError,
    parse_entsoe_price_xml,
)

SAMPLE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
  <mRID>sample-document</mRID>
  <revisionNumber>2</revisionNumber>
  <TimeSeries>
    <currency_Unit.name>EUR</currency_Unit.name>
    <price_Measure_Unit.name>MWH</price_Measure_Unit.name>
    <Period>
      <timeInterval>
        <start>2026-01-01T00:00Z</start>
        <end>2026-01-01T01:00Z</end>
      </timeInterval>
      <resolution>PT15M</resolution>
      <Point><position>1</position><price.amount>-5.50</price.amount></Point>
      <Point><position>2</position><price.amount>0</price.amount></Point>
      <Point><position>3</position><price.amount>75.25</price.amount></Point>
      <Point><position>4</position><price.amount>80.00</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
"""


class EntsoeParserTests(unittest.TestCase):
    def test_parses_quarter_hour_prices_and_preserves_negative_values(self) -> None:
        frame = parse_entsoe_price_xml(SAMPLE_XML, retrieved_at_utc="2026-01-01T12:00Z")
        self.assertEqual(len(frame), 4)
        self.assertEqual(frame["duration_hours"].unique().tolist(), [0.25])
        self.assertEqual(frame["price_eur_per_mwh"].tolist(), [-5.5, 0.0, 75.25, 80.0])
        self.assertEqual(frame["source_version"].unique().tolist(), ["sample-document:r2"])
        self.assertEqual(str(frame.iloc[0]["delivery_start_utc"]), "2026-01-01 00:00:00+00:00")

    def test_rejection_document_is_reported(self) -> None:
        rejection = (
            b"<Acknowledgement_MarketDocument><Reason><text>Bad request</text></Reason>"
            b"</Acknowledgement_MarketDocument>"
        )
        with self.assertRaisesRegex(EntsoeResponseError, "Bad request"):
            parse_entsoe_price_xml(rejection)


class EntsoeRetryTests(unittest.TestCase):
    def _client(self, **overrides: object) -> tuple[EntsoeClient, list[float]]:
        waits: list[float] = []
        client = EntsoeClient(
            token="test-token",
            retry_backoff_seconds=1.0,
            sleep=waits.append,
            **overrides,  # type: ignore[arg-type]
        )
        return client, waits

    def test_a_transient_timeout_is_retried_and_then_succeeds(self) -> None:
        client, waits = self._client()
        response = mock.MagicMock()
        response.read.return_value = SAMPLE_XML
        response.__enter__.return_value = response
        opener = mock.Mock(side_effect=[TimeoutError("The read operation timed out"), response])
        with mock.patch("urllib.request.urlopen", opener):
            frame = client.fetch_prices("2026-01-01T00:00Z", "2026-01-01T01:00Z")
        self.assertEqual(len(frame), 4)
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(waits, [1.0])

    def test_repeated_connection_failures_stop_after_the_attempt_budget(self) -> None:
        client, waits = self._client(max_attempts=3)
        opener = mock.Mock(side_effect=urllib.error.URLError("connection refused"))
        with mock.patch("urllib.request.urlopen", opener):
            with self.assertRaisesRegex(EntsoeResponseError, "connection refused"):
                client.fetch_prices("2026-01-01T00:00Z", "2026-01-01T01:00Z")
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(waits, [1.0, 2.0])

    def test_a_rejected_request_is_not_retried_and_never_reveals_the_token(self) -> None:
        client, waits = self._client()
        opener = mock.Mock(
            side_effect=urllib.error.HTTPError(
                "https://web-api.tp.entsoe.eu/api?securityToken=test-token",
                401,
                "Unauthorized",
                {},  # type: ignore[arg-type]
                None,
            )
        )
        with mock.patch("urllib.request.urlopen", opener):
            with self.assertRaises(EntsoeResponseError) as caught:
                client.fetch_prices("2026-01-01T00:00Z", "2026-01-01T01:00Z")
        self.assertNotIn("test-token", str(caught.exception))
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(waits, [])


if __name__ == "__main__":
    unittest.main()
