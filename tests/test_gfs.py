"""The NOAA GFS client: byte-range retrieval, decoding and the facts the spike turned into rules.

Everything the archive does is injected here — a fetcher, a HEAD reader and a decoder — so the
suite exercises the client's own logic rather than the provider's uptime. Four things the source
assessment of 2 September 2026 established are pinned as behaviour: both key layouts are tried,
the hourly record starts at a named delivery day, radiation is de-averaged from two adjacent
steps by a stated rule, and every forecast step is fetched and checked on its own.

One test does reach a real dependency: the ecCodes binding is imported and asked for its library
version. That is deliberate. The spike proved the decoder on two locally built interpreters and
recorded the `actions/setup-python` images as its one open residual; this is what closes it, on
whatever interpreter CI happens to run.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from greek_bess.cli import main
from greek_bess.data.gfs import (
    ATMOS_LAYOUT_FROM_CYCLE_DAY,
    FIRST_HOURLY_DELIVERY_DAY,
    GFS_VARIABLES,
    MAXIMUM_HOURLY_FORECAST_STEP,
    NOAA_GFS_ALLOWED_HOSTS,
    Grib2Grid,
    Grib2Message,
    NoaaGfsClient,
    NoaaGfsError,
    bucket_start_step,
    deaverage_bucket_mean,
    decode_grib2_message,
    eccodes_library_version,
    grid_index,
    index_step_window,
    object_key_candidates,
    parse_gfs_index,
    required_forecast_steps,
    select_index_entry,
)
from greek_bess.data.http import OfficialDataDownloadError, validate_https_url
from greek_bess.data.point_in_time import SamplingGeography

GRID = Grib2Grid(
    ni=1440,
    nj=721,
    first_latitude=90.0,
    first_longitude=0.0,
    latitude_increment=0.25,
    longitude_increment=0.25,
)

GEOGRAPHY = SamplingGeography.from_dict(
    {
        "geography_id": "declared-for-tests",
        "area": "GR",
        "points": [
            {"point_id": "north", "latitude": 40.5, "longitude": 23.0, "weight": 0.25},
            {"point_id": "south", "latitude": 38.0, "longitude": 23.75, "weight": 0.75},
        ],
        "reference": "Declared for tests; the operator supplies the basis for the choice.",
    }
)

#: The four messages a step object holds, in the order the real sidecar lists them.
MESSAGE_ORDER = (
    ("TMP", "2 m above ground"),
    ("UGRD", "10 m above ground"),
    ("VGRD", "10 m above ground"),
    ("DSWRF", "surface"),
)
MESSAGE_BYTES = 1000


def _index_text(step: int) -> str:
    lines = []
    for number, (variable, level) in enumerate(MESSAGE_ORDER, start=1):
        description = (
            f"{bucket_start_step(step)}-{step} hour ave fcst"
            if variable == "DSWRF"
            else f"{step} hour fcst"
        )
        lines.append(
            f"{number}:{(number - 1) * MESSAGE_BYTES}:d=2026081900:{variable}:{level}:"
            f"{description}:"
        )
    return "\n".join(lines) + "\n"


def _payload(key: str, start: int) -> bytes:
    """Deterministic stand-in bytes for one message, framed as a GRIB2 message is.

    Bytes 4-8 carry the message's position in the object so that the fake decoder can tell which
    variable it was handed; the rest is a digest of the key, so two different messages never
    hash alike and the client's own digesting is exercised.
    """

    position = start // MESSAGE_BYTES
    filler = hashlib.sha256(f"{key}:{start}".encode()).digest()
    body = (filler * ((MESSAGE_BYTES // len(filler)) + 1))[: MESSAGE_BYTES - 12]
    return b"GRIB" + position.to_bytes(4, "big") + body + b"7777"


class _Archive:
    """A fake archive: the ``atmos/`` layout by default, four messages per step object."""

    def __init__(self, *, legacy_layout: bool = False, missing_steps: frozenset[int] = frozenset()):
        self.legacy_layout = legacy_layout
        self.missing_steps = missing_steps
        self.requested_keys: list[str] = []
        self.head_keys: list[str] = []

    def _known(self, key: str) -> bool:
        if "/atmos/" in key and self.legacy_layout:
            return False
        if "/atmos/" not in key and not self.legacy_layout:
            return False
        step = int(key.rsplit(".f", 1)[1][:3])
        return step not in self.missing_steps

    def head(self, url: str) -> dict[str, str]:
        key = url.split("amazonaws.com/", 1)[1]
        self.head_keys.append(key)
        if not self._known(key):
            raise NoaaGfsError(f"no such object: {key}")
        return {
            "Last-Modified": "Wed, 19 Aug 2026 03:52:00 GMT",
            "Content-Length": str(len(MESSAGE_ORDER) * MESSAGE_BYTES),
            "ETag": '"deadbeef"',
        }

    def fetch(self, url: str, byte_range: tuple[int, int] | None) -> bytes:
        if url.endswith(".idx"):
            key = url.split("amazonaws.com/", 1)[1][: -len(".idx")]
            self.requested_keys.append(key + ".idx")
            step = int(key.rsplit(".f", 1)[1][:3])
            return _index_text(step).encode("utf-8")
        key = url.split("amazonaws.com/", 1)[1]
        self.requested_keys.append(key)
        assert byte_range is not None
        return _payload(key, byte_range[0])


def _decoder(values: dict[str, float] | None = None) -> Any:
    """A decoder that reports a fixed value per variable, and the real grid geometry."""

    per_variable = values or {"TMP": 300.0, "UGRD": 3.0, "VGRD": 4.0, "DSWRF": 600.0}

    def decode(payload: bytes, indices: Any) -> Grib2Message:
        # The fake archive encodes the message's position in its bytes, so the decoder can tell
        # which message it was handed without the caller passing extra state.
        variable = MESSAGE_ORDER[int.from_bytes(payload[4:8], "big")][0]
        return Grib2Message(
            name=variable,
            units="declared",
            step_type="instant",
            start_step=0,
            end_step=0,
            grid=GRID,
            samples=tuple(float(per_variable[variable]) for _ in indices),
        )

    return decode


class KeyLayoutTests(unittest.TestCase):
    def test_both_layouts_are_offered_for_every_cycle_day(self) -> None:
        recent = object_key_candidates(date(2026, 8, 19), 24)
        early = object_key_candidates(date(2021, 3, 1), 24)
        self.assertEqual(len(recent), 2)
        self.assertEqual(len(early), 2)
        self.assertEqual({"/atmos/" in key for key in recent}, {True, False})
        self.assertEqual({"/atmos/" in key for key in early}, {True, False})

    def test_the_likelier_layout_is_tried_first_on_each_side_of_the_change(self) -> None:
        self.assertIn("/atmos/", object_key_candidates(ATMOS_LAYOUT_FROM_CYCLE_DAY, 24)[0])
        self.assertNotIn(
            "/atmos/",
            object_key_candidates(date(2021, 3, 1), 24)[0],
        )

    def test_the_legacy_layout_is_found_rather_than_returning_nothing(self) -> None:
        """A client that hard-codes ``atmos/`` reports the earliest usable days as empty."""

        archive = _Archive(legacy_layout=True)
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        head = client.head_step_object(date(2021, 3, 1), 24)
        self.assertNotIn("/atmos/", head.key)
        self.assertEqual(head.size_bytes, len(MESSAGE_ORDER) * MESSAGE_BYTES)

    def test_a_missing_object_is_named_and_no_earlier_cycle_is_substituted(self) -> None:
        archive = _Archive(missing_steps=frozenset({30}))
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        with self.assertRaisesRegex(NoaaGfsError, "excluded by name"):
            client.head_step_object(date(2026, 8, 19), 30)


class ForecastStepTests(unittest.TestCase):
    def test_the_step_set_is_derived_from_the_market_day_it_must_cover(self) -> None:
        summer = required_forecast_steps(date(2026, 8, 20))
        winter = required_forecast_steps(date(2026, 1, 20))
        self.assertEqual((summer[0], summer[-1]), (22, 46))
        self.assertEqual((winter[0], winter[-1]), (23, 47))

    def test_a_transition_day_gets_its_own_step_set(self) -> None:
        short_day = required_forecast_steps(date(2026, 3, 29))
        long_day = required_forecast_steps(date(2026, 10, 25))
        self.assertEqual(len(long_day), len(short_day) + 2)
        self.assertEqual(long_day[-1], 47)

    def test_every_market_day_of_the_usable_record_stays_inside_the_hourly_range(self) -> None:
        day = FIRST_HOURLY_DELIVERY_DAY
        widest = (99, 0)
        while day <= date(2035, 12, 31):
            steps = required_forecast_steps(day)
            widest = (min(widest[0], steps[0]), max(widest[1], steps[-1]))
            day += pd.Timedelta(1, unit="D").to_pytimedelta()
        self.assertGreaterEqual(widest[0], 1)
        self.assertLessEqual(widest[1], MAXIMUM_HOURLY_FORECAST_STEP)
        # The source assessment computed 21-46 on the Athens delivery day. This project's
        # market day is the CET/CEST day, which is one hour later, so the range it needs is
        # 22-47. The correction is recorded rather than the constant being carried across.
        self.assertEqual(widest, (22, 47))


class IndexTests(unittest.TestCase):
    def test_a_sidecar_resolves_each_message_to_an_inclusive_byte_range(self) -> None:
        entries = parse_gfs_index(_index_text(24), len(MESSAGE_ORDER) * MESSAGE_BYTES)
        self.assertEqual(len(entries), len(MESSAGE_ORDER))
        self.assertEqual(entries[0].start_byte, 0)
        self.assertEqual(entries[0].end_byte, MESSAGE_BYTES - 1)
        self.assertEqual(entries[-1].end_byte, len(MESSAGE_ORDER) * MESSAGE_BYTES - 1)
        self.assertEqual(entries[-1].byte_count, MESSAGE_BYTES)

    def test_the_last_message_runs_to_the_end_of_the_object_not_a_guess(self) -> None:
        entries = parse_gfs_index(_index_text(24), 4321)
        self.assertEqual(entries[-1].end_byte, 4320)

    def test_a_sidecar_that_does_not_describe_this_object_is_refused(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "not the same publication"):
            parse_gfs_index(_index_text(24), 10)

    def test_an_unparseable_line_is_named_by_line_number(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "Line 2"):
            parse_gfs_index(_index_text(24).replace("2:1000:", "rubbish"), 4000)

    def test_the_averaging_window_is_read_from_the_sidecar(self) -> None:
        entries = parse_gfs_index(_index_text(25), 4000)
        radiation = select_index_entry(entries, "DSWRF", "surface", 25)
        temperature = select_index_entry(entries, "TMP", "2 m above ground", 25)
        self.assertEqual(index_step_window(radiation), (24, 25, "ave"))
        self.assertEqual(index_step_window(temperature), (25, 25, "instant"))

    def test_a_message_the_sidecar_does_not_hold_is_refused(self) -> None:
        entries = parse_gfs_index(_index_text(24), 4000)
        with self.assertRaisesRegex(NoaaGfsError, "no DSWRF:surface message"):
            select_index_entry(entries, "DSWRF", "surface", 25)


class RadiationTests(unittest.TestCase):
    def test_the_bucket_boundaries_match_the_sidecar_windows(self) -> None:
        # The windows the source assessment quotes verbatim from real sidecars.
        self.assertEqual(bucket_start_step(21), 18)
        self.assertEqual(bucket_start_step(24), 18)
        self.assertEqual(bucket_start_step(25), 24)
        self.assertEqual(bucket_start_step(36), 30)
        self.assertEqual(bucket_start_step(37), 36)

    def test_the_first_step_of_a_bucket_needs_no_predecessor(self) -> None:
        self.assertEqual(deaverage_bucket_mean(25, 120.0, None), 120.0)
        self.assertEqual(deaverage_bucket_mean(37, 5.0, None), 5.0)

    def test_a_later_step_is_de_averaged_from_the_two_adjacent_means(self) -> None:
        # A_24 is the mean over [18, 24]; A_23 over [18, 23]. The hour (23, 24] is therefore
        # 6*A_24 - 5*A_23.
        self.assertAlmostEqual(deaverage_bucket_mean(24, 100.0, 90.0), 6 * 100.0 - 5 * 90.0)
        self.assertAlmostEqual(deaverage_bucket_mean(26, 100.0, 90.0), 2 * 100.0 - 1 * 90.0)

    def test_a_constant_bucket_de_averages_to_the_same_constant(self) -> None:
        for step in range(19, 25):
            with self.subTest(step=step):
                self.assertAlmostEqual(deaverage_bucket_mean(step, 250.0, 250.0), 250.0)

    def test_a_missing_predecessor_is_named_rather_than_assumed_zero(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "was not retrieved"):
            deaverage_bucket_mean(24, 100.0, None)


class GridSamplingTests(unittest.TestCase):
    def test_a_declared_node_resolves_to_the_index_the_library_would_find(self) -> None:
        # 38.0 N, 23.75 E on the 0.25 degree grid: row 208, column 95.
        self.assertEqual(grid_index(GRID, 38.0, 23.75), 208 * 1440 + 95)
        self.assertEqual(grid_index(GRID, 90.0, 0.0), 0)

    def test_a_negative_longitude_wraps_onto_the_grid(self) -> None:
        self.assertEqual(grid_index(GRID, 90.0, -0.25), 1439)

    def test_a_point_between_nodes_is_refused_rather_than_interpolated(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "no interpolation rule is declared"):
            grid_index(GRID, 38.1, 23.75)

    def test_a_point_outside_the_grid_is_refused(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "outside the decoded grid"):
            grid_index(GRID, -90.25, 0.0)


class DecoderTests(unittest.TestCase):
    def test_the_binding_reports_its_library_version(self) -> None:
        """The spike's one open residual, closed by CI running this on its own images."""

        version = eccodes_library_version()
        self.assertRegex(version, r"^\d+\.\d+")

    def test_bytes_that_are_not_a_framed_message_are_named_as_truncation(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "not one complete GRIB2 message"):
            decode_grib2_message(b"GRIB not framed", [0])
        with self.assertRaisesRegex(NoaaGfsError, "not one complete GRIB2 message"):
            decode_grib2_message(b"", [0])


class DeliveryDayTests(unittest.TestCase):
    def _client(self, archive: _Archive) -> NoaaGfsClient:
        return NoaaGfsClient(
            fetcher=archive.fetch, head_reader=archive.head, decoder=_decoder()
        )

    def test_a_day_before_the_hourly_record_carries_no_feature(self) -> None:
        archive = _Archive()
        with self.assertRaisesRegex(NoaaGfsError, "3-hourly"):
            self._client(archive).build_delivery_day_features(
                date(2021, 2, 26), geography=GEOGRAPHY, variables=["temperature_2m"]
            )

    def test_a_complete_day_yields_one_row_per_interval_per_variable(self) -> None:
        archive = _Archive()
        built = self._client(archive).build_delivery_day_features(
            date(2026, 8, 20),
            geography=GEOGRAPHY,
            variables=["temperature_2m", "wind_speed_10m"],
            retrieved_at_utc="2026-08-19T06:00:00+00:00",
        )
        features = built.features
        self.assertEqual(len(features), 48)
        self.assertEqual(set(features["variable"]), {"temperature_2m", "wind_speed_10m"})
        self.assertEqual(features["source"].unique().tolist(), ["noaa_gfs"])
        self.assertEqual(
            sorted(features["market_day"].unique().tolist()), [date(2026, 8, 20)]
        )

    def test_wind_speed_is_the_magnitude_of_the_two_declared_components(self) -> None:
        archive = _Archive()
        built = self._client(archive).build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["wind_speed_10m"]
        )
        # The stub decoder reports 3 and 4 for the two components at every point.
        self.assertTrue((built.features["value"].round(9) == 5.0).all())
        self.assertEqual(built.features["unit"].unique().tolist(), ["m/s"])

    def test_a_derived_value_names_every_document_behind_it(self) -> None:
        archive = _Archive()
        built = self._client(archive).build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["dswrf_surface"]
        )
        documents = built.features["source_document_id"]
        # A de-averaged hour inside a bucket is built from two adjacent step objects, and both
        # are named; the first hour of a bucket is built from one.
        self.assertTrue(any("+" in value for value in documents))
        self.assertTrue(any("+" not in value for value in documents))

    def test_every_required_step_is_fetched_on_its_own(self) -> None:
        archive = _Archive()
        self._client(archive).build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["temperature_2m"]
        )
        steps = required_forecast_steps(date(2026, 8, 20))
        self.assertEqual(len(archive.head_keys), len(steps))
        self.assertEqual(
            sorted({key.rsplit(".f", 1)[1] for key in archive.head_keys}),
            sorted(f"{step:03d}" for step in steps),
        )

    def test_the_provider_publication_instant_becomes_provider_declared_evidence(self) -> None:
        archive = _Archive()
        built = self._client(archive).build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["temperature_2m"]
        )
        self.assertEqual(
            built.features["availability_evidence_grade"].unique().tolist(),
            ["provider_declared"],
        )
        self.assertEqual(
            built.features["published_at_utc"].unique().tolist(),
            [pd.Timestamp("2026-08-19T03:52:00+00:00")],
        )

    def test_the_summary_carries_the_provider_attribution(self) -> None:
        archive = _Archive()
        built = self._client(archive).build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["temperature_2m"]
        )
        self.assertIn("not unaltered NOAA data", built.summary["attribution"])
        self.assertEqual(built.summary["cycle_hour_utc"], 0)
        self.assertEqual(built.summary["cycle_day"], "2026-08-19")

    def test_a_variable_this_source_does_not_supply_is_refused_by_name(self) -> None:
        archive = _Archive()
        with self.assertRaisesRegex(NoaaGfsError, "does not supply"):
            self._client(archive).build_delivery_day_features(
                date(2026, 8, 20), geography=GEOGRAPHY, variables=["load_forecast"]
            )

    def test_the_registered_variables_are_the_three_the_decision_names(self) -> None:
        self.assertEqual(
            sorted(GFS_VARIABLES), ["dswrf_surface", "temperature_2m", "wind_speed_10m"]
        )


class SecretHygieneTests(unittest.TestCase):
    """Design section 11, case 24, for a source that has no credential at all."""

    def test_a_url_carrying_credentials_is_refused_before_a_request_is_made(self) -> None:
        with self.assertRaises(OfficialDataDownloadError) as caught:
            validate_https_url(
                f"https://user:s3cr3t@{next(iter(NOAA_GFS_ALLOWED_HOSTS))}/gfs.20260819/00/x",
                allowed_hosts=NOAA_GFS_ALLOWED_HOSTS,
            )
        self.assertNotIn("s3cr3t", str(caught.exception))

    def test_a_host_outside_the_allowlist_is_refused_and_not_echoed_with_a_query(self) -> None:
        with self.assertRaises(OfficialDataDownloadError) as caught:
            validate_https_url(
                "https://example.invalid/object?securityToken=s3cr3t",
                allowed_hosts=NOAA_GFS_ALLOWED_HOSTS,
            )
        self.assertNotIn("s3cr3t", str(caught.exception))

    def test_no_retrieval_url_the_client_builds_carries_a_query_string(self) -> None:
        for step in (22, 47):
            for key in object_key_candidates(date(2026, 8, 19), step):
                with self.subTest(key=key):
                    self.assertNotIn("?", key)


class CommandTests(unittest.TestCase):
    def test_the_committed_example_geography_is_refused_by_the_command(self) -> None:
        example = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "fundamentals_geography.example.json"
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                code = main(
                    [
                        "fetch-fundamentals",
                        "--source",
                        "noaa_gfs",
                        "--variables",
                        "temperature_2m",
                        "--geography",
                        str(example),
                        "--start-day",
                        "2026-08-20",
                        "--end-day",
                        "2026-08-20",
                        "--output",
                        str(directory / "features.csv"),
                    ]
                )
        self.assertEqual(code, 1)
        self.assertIn("not a declaration", stderr.getvalue())

    def test_a_window_entirely_before_the_hourly_record_is_refused_not_written_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            geography = directory / "geography.json"
            geography.write_text(json.dumps(GEOGRAPHY.to_dict()), encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                code = main(
                    [
                        "fetch-fundamentals",
                        "--source",
                        "noaa_gfs",
                        "--variables",
                        "temperature_2m",
                        "--geography",
                        str(geography),
                        "--start-day",
                        "2021-01-01",
                        "--end-day",
                        "2021-01-05",
                        "--output",
                        str(directory / "features.csv"),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("refused rather than written", stderr.getvalue())
            self.assertFalse((directory / "features.csv").exists())


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
