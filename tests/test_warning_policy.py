"""The suite's warning policy and the deprecation it exists to catch.

NumPy deprecated its generic timedelta unit, and pandas surfaces that deprecation at the
line that constructed the timedelta. Every `pd.Timedelta` built from a number in this
project therefore declares its unit. These tests prove the deprecation is gone from the
call sites that emitted it and pin the scope of the pytest policy that guards them.
"""

from __future__ import annotations

import tempfile
import tomllib
import unittest
import warnings
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from greek_bess.data.entsoe import EntsoeClient
from greek_bess.data.henex import parse_henex_results
from greek_bess.data.synthetic import generate_synthetic_prices

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
  <mRID>sample-document</mRID>
  <revisionNumber>1</revisionNumber>
  <TimeSeries>
    <currency_Unit.name>EUR</currency_Unit.name>
    <price_Measure_Unit.name>MWH</price_Measure_Unit.name>
    <Period>
      <timeInterval>
        <start>2026-01-01T00:00Z</start>
        <end>2026-01-01T01:00Z</end>
      </timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>42.00</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
"""

GENERIC_UNIT_WARNING = "generic"


def _pytest_filterwarnings() -> list[str]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    filters: list[str] = config["tool"]["pytest"]["ini_options"]["filterwarnings"]
    return filters


class TimedeltaDeprecationTests(unittest.TestCase):
    """The three ingestion call sites that emitted the generic-unit deprecation."""

    def _assert_no_timedelta_deprecation(self, caught: list[warnings.WarningMessage]) -> None:
        offending = [
            record
            for record in caught
            if issubclass(record.category, DeprecationWarning)
            and GENERIC_UNIT_WARNING in str(record.message)
            and "timedelta" in str(record.message)
        ]
        self.assertEqual(offending, [], f"generic-unit timedelta deprecation re-emitted: {caught}")

    def test_synthetic_generation_emits_no_generic_unit_deprecation(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = generate_synthetic_prices(date(2026, 1, 1), date(2026, 1, 3))
        self.assertEqual(len(frame), 48)
        self._assert_no_timedelta_deprecation(caught)

    def test_henex_parsing_emits_no_generic_unit_deprecation(self) -> None:
        rows = [
            {
                "DDAY": "2026-01-15",
                "SORT": sort,
                "DELIVERY_DURATION": 15,
                "MCP": price,
                "VER": 1,
                "ASSET_DESCR": "LOAD",
            }
            for sort, price in [(1, -3.0), (2, 20.0), (3, 50.0), (4, 90.0)]
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "20260115_EL-DAM_Results_EN_v01.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, sheet_name="Results")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                frame = parse_henex_results(path, retrieved_at_utc="2026-01-14T12:00Z")
        self.assertEqual(len(frame), 4)
        self._assert_no_timedelta_deprecation(caught)

    def test_entsoe_chunking_emits_no_generic_unit_deprecation(self) -> None:
        client = EntsoeClient(token="test-token")
        response = mock.MagicMock()
        response.read.return_value = SAMPLE_XML
        response.__enter__.return_value = response
        opener = mock.Mock(return_value=response)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with mock.patch("urllib.request.urlopen", opener):
                client.fetch_prices("2026-01-01T00:00Z", "2026-01-03T00:00Z", chunk_days=1)
        self.assertEqual(opener.call_count, 2)
        self._assert_no_timedelta_deprecation(caught)


class WarningPolicyTests(unittest.TestCase):
    """The policy the suite actually runs under, exercised against the live filters."""

    def test_a_warning_from_project_code_fails_the_suite(self) -> None:
        with self.assertRaises(DeprecationWarning):
            warnings.warn_explicit(
                "policy probe",
                DeprecationWarning,
                "probe.py",
                1,
                module="greek_bess.data.synthetic",
                registry={},
            )

    def test_a_warning_from_test_code_fails_the_suite(self) -> None:
        with self.assertRaises(FutureWarning):
            warnings.warn_explicit(
                "policy probe",
                FutureWarning,
                "probe.py",
                1,
                module="tests.test_annual",
                registry={},
            )

    def test_a_dependency_warning_stays_visible_without_failing(self) -> None:
        # Dependencies are installed from ranges, so an upstream deprecation must be
        # reported rather than allowed to decide when validation breaks.
        with warnings.catch_warnings(record=True) as caught:
            warnings.warn_explicit(
                "policy probe",
                DeprecationWarning,
                "probe.py",
                1,
                module="pandas.core.tools.timedeltas",
                registry={},
            )
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)

    def test_the_configured_policy_is_scoped_to_project_modules(self) -> None:
        filters = _pytest_filterwarnings()
        self.assertEqual(filters, ["error:::greek_bess", "error:::tests"])

    def test_the_configured_policy_promotes_no_warning_globally(self) -> None:
        # A bare "error" entry would fail the suite on any dependency warning.
        for entry in _pytest_filterwarnings():
            action, _, _, module, *_ = f"{entry}::::".split(":")
            if action == "error":
                self.assertNotEqual(module, "", f"unscoped error filter: {entry!r}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
