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
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from unittest import mock

import pandas as pd

from greek_bess.cli import main
from greek_bess.data.gfs import (
    ATMOS_LAYOUT_FROM_CYCLE_DAY,
    FIRST_HOURLY_DELIVERY_DAY,
    GFS_FEATURE_SEMANTICS_VERSION,
    GFS_VARIABLES,
    MAXIMUM_HOURLY_FORECAST_STEP,
    MISSING_OBJECT,
    NOAA_GFS_ALLOWED_HOSTS,
    SIDECAR_OBJECT_MISMATCH,
    SOURCE_CONDITION_CAUSES,
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
from greek_bess.data.http import (
    ABSENT,
    SERVER_ERROR,
    OfficialDataDownloadError,
    validate_https_url,
)
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


def _index_text(step: int, *, cycle: str = "2026081900", offset_shift: int = 0) -> str:
    lines = []
    for number, (variable, level) in enumerate(MESSAGE_ORDER, start=1):
        description = (
            f"{bucket_start_step(step)}-{step} hour ave fcst"
            if variable == "DSWRF"
            else f"{step} hour fcst"
        )
        offset = (number - 1) * MESSAGE_BYTES + offset_shift
        lines.append(
            f"{number}:{offset}:d={cycle}:{variable}:{level}:{description}:"
        )
    return "\n".join(lines) + "\n"


def _payload(key: str, start: int) -> bytes:
    """Deterministic stand-in bytes for one message, framed as a GRIB2 message is.

    Bytes 4-8 carry the message's position in the object so that the fake decoder can tell which
    variable it was handed; the rest is a digest of the key, so two different messages never
    hash alike and the client's own digesting is exercised.
    """

    position = start // MESSAGE_BYTES
    step = int(key.rsplit(".f", 1)[1][:3])
    cycle_day = key.split("/", 1)[0].removeprefix("gfs.")
    filler = hashlib.sha256(f"{key}:{start}".encode()).digest()
    header = (
        b"GRIB"
        + position.to_bytes(4, "big")
        + step.to_bytes(4, "big")
        + cycle_day.encode("ascii")
    )
    body = (filler * ((MESSAGE_BYTES // len(filler)) + 1))[
        : MESSAGE_BYTES - len(header) - 4
    ]
    return header + body + b"7777"


class _Archive:
    """A fake archive: the ``atmos/`` layout by default, four messages per step object.

    It answers the way an object store answers, because the client's rules are about the
    difference between those answers: a key it does not hold gets a ``404``, and a step listed in
    ``unanswered_steps`` gets a ``503``, which is not an answer about the object at all.
    """

    def __init__(
        self,
        *,
        legacy_layout: bool = False,
        missing_steps: frozenset[int] = frozenset(),
        unanswered_steps: frozenset[int] = frozenset(),
        mismatched_sidecar_steps: frozenset[int] = frozenset(),
        missing_cycles: frozenset[str] = frozenset(),
        unanswered_cycles: frozenset[str] = frozenset(),
        mismatched_sidecar_cycles: frozenset[str] = frozenset(),
    ):
        self.legacy_layout = legacy_layout
        self.missing_steps = missing_steps
        self.unanswered_steps = unanswered_steps
        self.mismatched_sidecar_steps = mismatched_sidecar_steps
        # The step numbers a market day needs repeat from cycle to cycle, so a condition that
        # must strike one delivery day and not its neighbours is keyed by the cycle day.
        self.missing_cycles = missing_cycles
        self.unanswered_cycles = unanswered_cycles
        self.mismatched_sidecar_cycles = mismatched_sidecar_cycles
        self.requested_keys: list[str] = []
        self.head_keys: list[str] = []

    @staticmethod
    def _cycle(key: str) -> str:
        return key.split("/", 1)[0].removeprefix("gfs.")

    def _known(self, key: str) -> bool:
        if "/atmos/" in key and self.legacy_layout:
            return False
        if "/atmos/" not in key and not self.legacy_layout:
            return False
        if self._cycle(key) in self.missing_cycles:
            return False
        step = int(key.rsplit(".f", 1)[1][:3])
        return step not in self.missing_steps

    def head(self, url: str) -> dict[str, str]:
        key = url.split("amazonaws.com/", 1)[1]
        self.head_keys.append(key)
        step = int(key.rsplit(".f", 1)[1][:3])
        if step in self.unanswered_steps or self._cycle(key) in self.unanswered_cycles:
            raise OfficialDataDownloadError(
                "Official-data server returned HTTP 503; the answer says nothing about whether "
                "the object exists",
                kind=SERVER_ERROR,
                status=503,
            )
        if not self._known(key):
            raise OfficialDataDownloadError(
                f"Official-data server returned HTTP 404; the object is not at this location "
                f"({key})",
                kind=ABSENT,
                status=404,
            )
        # Published at 03:52 UTC of the cycle day the key names, so a multi-day window keeps the
        # publication instant after the cycle that produced it, as the schema requires.
        published = datetime.strptime(self._cycle(key), "%Y%m%d").replace(
            hour=3, minute=52, tzinfo=UTC
        )
        return {
            "Last-Modified": format_datetime(published, usegmt=True),
            "Content-Length": str(len(MESSAGE_ORDER) * MESSAGE_BYTES),
            "ETag": '"deadbeef"',
        }

    def fetch(self, url: str, byte_range: tuple[int, int] | None) -> bytes:
        if url.endswith(".idx"):
            key = url.split("amazonaws.com/", 1)[1][: -len(".idx")]
            self.requested_keys.append(key + ".idx")
            step = int(key.rsplit(".f", 1)[1][:3])
            if (
                step in self.mismatched_sidecar_steps
                or self._cycle(key) in self.mismatched_sidecar_cycles
            ):
                # A sidecar left over from a different publication of the same key: its last
                # message starts past the end of the object the HEAD just measured.
                return _index_text(
                    step,
                    cycle=f"{self._cycle(key)}00",
                    offset_shift=len(MESSAGE_ORDER) * MESSAGE_BYTES,
                ).encode(
                    "utf-8"
                )
            return _index_text(step, cycle=f"{self._cycle(key)}00").encode("utf-8")
        key = url.split("amazonaws.com/", 1)[1]
        self.requested_keys.append(key)
        assert byte_range is not None
        return _payload(key, byte_range[0])


def _decoder(values: dict[str, float | tuple[float, ...]] | None = None) -> Any:
    """A decoder that reports a fixed value per variable, and the real grid geometry."""

    per_variable = values or {"TMP": 300.0, "UGRD": 3.0, "VGRD": 4.0, "DSWRF": 600.0}

    def decode(payload: bytes, indices: Any) -> Grib2Message:
        # The fake archive encodes the message's position in its bytes, so the decoder can tell
        # which message it was handed without the caller passing extra state.
        variable = MESSAGE_ORDER[int.from_bytes(payload[4:8], "big")][0]
        step = int.from_bytes(payload[8:12], "big")
        cycle_day = payload[12:20].decode("ascii")
        cycle = datetime.strptime(cycle_day, "%Y%m%d").replace(tzinfo=UTC)
        valid = cycle + timedelta(hours=step)
        metadata = {
            "TMP": ("2t", "2 metre temperature", "K", "heightAboveGround", 2.0),
            "UGRD": (
                "10u",
                "10 metre U wind component",
                "m s**-1",
                "heightAboveGround",
                10.0,
            ),
            "VGRD": (
                "10v",
                "10 metre V wind component",
                "m s**-1",
                "heightAboveGround",
                10.0,
            ),
            "DSWRF": (
                "sdswrf",
                "Surface downward short-wave radiation flux",
                "W m**-2",
                "surface",
                0.0,
            ),
        }
        short_name, name, units, type_of_level, level = metadata[variable]
        declared = per_variable[variable]
        samples = (
            tuple(float(value) for value in declared)
            if isinstance(declared, tuple)
            else tuple(float(declared) for _ in indices)
        )
        if isinstance(declared, tuple) and indices and len(samples) != len(indices):
            raise AssertionError("A fake decoder sample tuple must match the requested points")
        return Grib2Message(
            short_name=short_name,
            name=name,
            units=units,
            type_of_level=type_of_level,
            level=level,
            step_type="avg" if variable == "DSWRF" else "instant",
            start_step=bucket_start_step(step) if variable == "DSWRF" else step,
            end_step=step,
            step_units=1,
            data_date=int(cycle.strftime("%Y%m%d")),
            data_time=int(cycle.strftime("%H%M")),
            validity_date=int(valid.strftime("%Y%m%d")),
            validity_time=int(valid.strftime("%H%M")),
            grid=GRID,
            samples=samples,
        )

    return decode


def _generated_temperature_grib2() -> bytes:
    """Build a tiny real GRIB2 message with ecCodes; no implementation decoder is injected."""

    import eccodes

    handle = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib2")
    try:
        for key, value in {
            "shortName": "2t",
            "dataDate": 20260819,
            "dataTime": 0,
            "stepType": "instant",
            "step": 25,
            "typeOfLevel": "heightAboveGround",
            "level": 2,
            "Ni": 2,
            "Nj": 2,
            "latitudeOfFirstGridPointInDegrees": 40.5,
            "latitudeOfLastGridPointInDegrees": 40.25,
            "longitudeOfFirstGridPointInDegrees": 23.0,
            "longitudeOfLastGridPointInDegrees": 23.25,
            "iDirectionIncrementInDegrees": 0.25,
            "jDirectionIncrementInDegrees": 0.25,
        }.items():
            eccodes.codes_set(handle, key, value)
        eccodes.codes_set_values(handle, [300.0, 301.0, 302.0, 303.0])
        return bytes(eccodes.codes_get_message(handle))
    finally:
        eccodes.codes_release(handle)


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
        with self.assertRaisesRegex(NoaaGfsError, "excluded by name") as caught:
            client.head_step_object(date(2026, 8, 19), 30)
        # Both layouts were asked, and both answered that they hold nothing. That is an answer,
        # so the refusal carries the cause a retrieval excludes the delivery day by.
        self.assertEqual(caught.exception.cause, MISSING_OBJECT)
        self.assertEqual(len(archive.head_keys), 2)


class UnansweredRequestTests(unittest.TestCase):
    """A store that does not answer has not said the object is absent.

    Before this distinction existed, ``head_step_object`` caught every failure from either key
    layout and moved on, so a 503 or a reset arrived at the operator as "no 0.25 degree object
    ... both archive key layouts were tried" — a finding about the provider, recorded against a
    delivery day that the provider had in fact published. Nothing downstream could tell the two
    apart, which is why this is checked here rather than left to the retrieval to notice.
    """

    def test_a_server_error_is_not_read_as_a_missing_object(self) -> None:
        archive = _Archive(unanswered_steps=frozenset({30}))
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        with self.assertRaises(NoaaGfsError) as caught:
            client.head_step_object(date(2026, 8, 19), 30)
        self.assertIn("did not answer whether", str(caught.exception))
        self.assertNotIn("excluded by name", str(caught.exception))
        self.assertIsNone(caught.exception.cause)
        self.assertNotIn(caught.exception.cause, SOURCE_CONDITION_CAUSES)

    def test_an_unreadable_sidecar_beside_a_present_object_is_named_without_a_cause(
        self,
    ) -> None:
        archive = _Archive()
        absent = OfficialDataDownloadError(
            "Official-data server returned HTTP 404; the object is not at this location",
            kind=ABSENT,
            status=404,
        )

        def fetch(url: str, byte_range: tuple[int, int] | None) -> bytes:
            if url.endswith(".idx"):
                raise absent
            return archive.fetch(url, byte_range)

        client = NoaaGfsClient(fetcher=fetch, head_reader=archive.head)
        head = client.head_step_object(date(2026, 8, 19), 24)
        with self.assertRaises(NoaaGfsError) as caught:
            client.read_index(head)
        self.assertIn("could not be read", str(caught.exception))
        self.assertIsNone(caught.exception.cause)

    def test_the_other_key_layout_is_not_tried_after_an_unanswered_request(self) -> None:
        """The second layout would answer 404, and two answers would read as absence."""

        archive = _Archive(unanswered_steps=frozenset({30}))
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        with self.assertRaises(NoaaGfsError):
            client.head_step_object(date(2026, 8, 19), 30)
        self.assertEqual(len(archive.head_keys), 1)


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
        with self.assertRaisesRegex(NoaaGfsError, "not the same publication") as caught:
            parse_gfs_index(_index_text(24), 10)
        # A sidecar and an object that are different publications of one key is a condition of
        # the delivery day that needs them, so it carries the cause the day is excluded by.
        self.assertEqual(caught.exception.cause, SIDECAR_OBJECT_MISMATCH)

    def test_an_unparseable_line_is_named_by_line_number(self) -> None:
        with self.assertRaisesRegex(NoaaGfsError, "Line 2") as caught:
            parse_gfs_index(_index_text(24).replace("2:1000:", "rubbish"), 4000)
        # A sidecar line this client cannot read is as likely to be a gap in this parser as a
        # fact about the provider, so it carries no cause and stops the retrieval.
        self.assertIsNone(caught.exception.cause)

    def test_an_unknown_source_condition_cause_cannot_be_invented(self) -> None:
        with self.assertRaises(ValueError):
            NoaaGfsError("refused", cause="looked_wrong")

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

    def test_a_generated_grib_message_is_decoded_with_its_full_semantics(self) -> None:
        decoded = decode_grib2_message(_generated_temperature_grib2(), [0, 3])

        self.assertEqual(decoded.short_name, "2t")
        self.assertEqual(decoded.name, "2 metre temperature")
        self.assertEqual(decoded.units, "K")
        self.assertEqual((decoded.type_of_level, decoded.level), ("heightAboveGround", 2.0))
        self.assertEqual(
            (decoded.step_type, decoded.start_step, decoded.end_step, decoded.step_units),
            ("instant", 25, 25, 1),
        )
        self.assertEqual((decoded.data_date, decoded.data_time), (20260819, 0))
        self.assertEqual((decoded.validity_date, decoded.validity_time), (20260820, 100))
        self.assertEqual(decoded.samples, (300.0, 303.0))


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

    def test_wind_speed_is_calculated_locally_before_geographic_weighting(self) -> None:
        archive = _Archive()
        decoder = _decoder({"TMP": 300.0, "UGRD": (12.0, -4.0), "VGRD": (0.0, 0.0), "DSWRF": 0.0})
        client = NoaaGfsClient(
            fetcher=archive.fetch, head_reader=archive.head, decoder=decoder
        )

        built = client.build_delivery_day_features(
            date(2026, 8, 20), geography=GEOGRAPHY, variables=["wind_speed_10m"]
        )

        self.assertTrue((built.features["value"].round(9) == 6.0).all())

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
        self.assertEqual(
            built.summary["feature_semantics_version"], GFS_FEATURE_SEMANTICS_VERSION
        )
        self.assertEqual(built.summary["geography"], GEOGRAPHY.to_dict())
        contract = built.summary["decoded_message_contract"]["temperature_2m"]
        self.assertEqual(contract["messages"][0]["short_name"], "2t")

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


class DecodedMetadataRefusalTests(unittest.TestCase):
    def _assert_refused(self, pattern: str, **overrides: Any) -> None:
        archive = _Archive()
        baseline = _decoder()

        def decode(payload: bytes, indices: Any) -> Grib2Message:
            return replace(baseline(payload, indices), **overrides)

        client = NoaaGfsClient(
            fetcher=archive.fetch, head_reader=archive.head, decoder=decode
        )
        with self.assertRaisesRegex(NoaaGfsError, pattern):
            client.build_delivery_day_features(
                date(2026, 8, 20), geography=GEOGRAPHY, variables=["temperature_2m"]
            )

    def test_a_wrong_parameter_identity_is_refused_by_name(self) -> None:
        self._assert_refused("parameter identity", short_name="10u")

    def test_wrong_units_are_refused_without_conversion(self) -> None:
        self._assert_refused("Decoded units", units="deg C")

    def test_a_wrong_level_is_refused_by_name(self) -> None:
        self._assert_refused("Decoded level", level=10.0)

    def test_a_wrong_source_cycle_is_refused_by_name(self) -> None:
        self._assert_refused("Decoded cycle", data_date=20260818)

    def test_a_wrong_valid_time_is_refused_by_name(self) -> None:
        self._assert_refused("Decoded valid time", validity_time=2300)

    def test_wrong_forecast_and_averaging_semantics_are_refused(self) -> None:
        self._assert_refused("Decoded forecast semantics", step_type="avg")

    def test_a_wrong_forecast_step_is_refused(self) -> None:
        self._assert_refused("Decoded forecast semantics", end_step=999)


class SidecarSemanticsTests(unittest.TestCase):
    def _assert_mutated_sidecar_is_refused(self, old: bytes, new: bytes, pattern: str) -> None:
        class _MutatedSidecar(_Archive):
            def fetch(self, url: str, byte_range: tuple[int, int] | None) -> bytes:
                payload = super().fetch(url, byte_range)
                return payload.replace(old, new) if url.endswith(".idx") else payload

        archive = _MutatedSidecar()
        client = NoaaGfsClient(
            fetcher=archive.fetch, head_reader=archive.head, decoder=_decoder()
        )
        with self.assertRaisesRegex(NoaaGfsError, pattern):
            client.build_delivery_day_features(
                date(2026, 8, 20), geography=GEOGRAPHY, variables=["dswrf_surface"]
            )

    def test_a_sidecar_from_another_cycle_is_refused(self) -> None:
        self._assert_mutated_sidecar_is_refused(
            b"d=2026081900", b"d=2026081800", "declares cycle"
        )

    def test_accumulation_is_not_accepted_as_the_declared_radiation_average(self) -> None:
        self._assert_mutated_sidecar_is_refused(
            b"hour ave fcst", b"hour acc fcst", "forecast semantics"
        )


class GridConsistencyTests(unittest.TestCase):
    """A step on a different grid is refused, not sampled at the right index of a wrong array."""

    def test_a_message_on_another_grid_refuses_the_whole_day(self) -> None:
        other = Grib2Grid(
            ni=720,
            nj=361,
            first_latitude=90.0,
            first_longitude=0.0,
            latitude_increment=0.5,
            longitude_increment=0.5,
        )
        calls: list[int] = []
        baseline = _decoder()

        def decode(payload: bytes, indices: Any) -> Grib2Message:
            calls.append(1)
            return replace(
                baseline(payload, indices),
                grid=GRID if len(calls) < 4 else other,
            )

        archive = _Archive()
        client = NoaaGfsClient(
            fetcher=archive.fetch, head_reader=archive.head, decoder=decode
        )
        with self.assertRaisesRegex(NoaaGfsError, "different grid"):
            client.build_delivery_day_features(
                date(2026, 8, 20), geography=GEOGRAPHY, variables=["temperature_2m"]
            )


class PublicationInstantTests(unittest.TestCase):
    """The object's Last-Modified is the provider-declared availability instant."""

    def test_an_http_date_is_read_as_an_aware_utc_instant(self) -> None:
        archive = _Archive()
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        head = client.head_step_object(date(2026, 8, 19), 24)
        self.assertEqual(head.last_modified_utc.isoformat(), "2026-08-19T03:52:00+00:00")

    def test_an_object_without_a_publication_instant_is_refused(self) -> None:
        class _NoInstant(_Archive):
            def head(self, url: str) -> dict[str, str]:
                headers = super().head(url)
                del headers["Last-Modified"]
                return headers

        archive = _NoInstant()
        client = NoaaGfsClient(fetcher=archive.fetch, head_reader=archive.head)
        # An object that exists but carries no publication instant is a different fact from an
        # object that is not there, so it is named rather than retried under the other layout:
        # availability inferred from anything but the datum is the quarantined grade, and the
        # client does not manufacture one.
        with self.assertRaisesRegex(NoaaGfsError, "does not manufacture one"):
            client.head_step_object(date(2026, 8, 19), 24)


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


class NamedExclusionTests(unittest.TestCase):
    """A source condition excludes its delivery day by name; nothing else does.

    The refusals for a missing object and for a mismatched sidecar have always said the delivery
    day "is excluded by name", but the exception left ``run_fetch_fundamentals`` and killed the
    whole window: only days before the hourly product were ever recorded as exclusions. On the
    declared v0.9 window that cost a 90-day slice per unpublished object.

    The other half of the rule matters just as much. A day is excluded only on a condition the
    provider stated. A request the archive did not answer, and any refusal about how a value
    would be built, still stops the retrieval, because an excluded day is recorded as a provider
    non-publication and neither of those is one.
    """

    def _run(self, directory: Path, archive: _Archive, *, end_day: str) -> tuple[int, str]:
        geography = directory / "geography.json"
        geography.write_text(json.dumps(GEOGRAPHY.to_dict()), encoding="utf-8")

        def factory() -> NoaaGfsClient:
            return NoaaGfsClient(
                fetcher=archive.fetch, head_reader=archive.head, decoder=_decoder()
            )

        stderr = io.StringIO()
        with mock.patch("greek_bess.cli.fundamentals.NoaaGfsClient", factory):
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
                        "2026-08-20",
                        "--end-day",
                        end_day,
                        "--output",
                        str(directory / "features.csv"),
                    ]
                )
        return code, stderr.getvalue()

    def _summary(self, directory: Path) -> dict[str, Any]:
        text = (directory / "features.summary.json").read_text(encoding="utf-8")
        return dict(json.loads(text))

    def test_a_missing_object_excludes_its_day_and_the_window_still_completes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            # The 00 UTC cycle of 20 August covers the 21 August delivery day, and no other.
            archive = _Archive(missing_cycles=frozenset({"20260820"}))
            code, stderr = self._run(directory, archive, end_day="2026-08-22")
            self.assertEqual(code, 0, stderr)
            summary = self._summary(directory)
            self.assertEqual(summary["built_day_count"], 2)
            self.assertEqual(summary["excluded_day_count"], 1)
            self.assertEqual(summary["excluded_day_count_by_cause"], {"missing_object": 1})
            self.assertEqual(
                [entry["market_day"] for entry in summary["excluded_days_by_cause"]],
                ["2026-08-21"],
            )
            self.assertEqual(
                sorted(
                    str(day["delivery_day"]) for day in summary["per_delivery_day"]
                ),
                ["2026-08-20", "2026-08-22"],
            )
            features = pd.read_csv(directory / "features.csv")
            self.assertEqual(
                sorted(set(features["market_day"])), ["2026-08-20", "2026-08-22"]
            )

    def test_a_sidecar_indexing_another_publication_excludes_its_day_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            archive = _Archive(mismatched_sidecar_cycles=frozenset({"20260820"}))
            code, stderr = self._run(directory, archive, end_day="2026-08-22")
            self.assertEqual(code, 0, stderr)
            summary = self._summary(directory)
            self.assertEqual(
                summary["excluded_day_count_by_cause"], {"sidecar_object_mismatch": 1}
            )
            self.assertEqual(summary["built_day_count"], 2)

    def test_an_unanswered_request_stops_the_retrieval_rather_than_excluding_a_day(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            archive = _Archive(unanswered_cycles=frozenset({"20260820"}))
            code, stderr = self._run(directory, archive, end_day="2026-08-22")
            self.assertEqual(code, 1)
            self.assertIn("did not answer whether", stderr)
            self.assertFalse((directory / "features.csv").exists())
            self.assertFalse((directory / "features.summary.json").exists())

    def test_a_refusal_about_building_a_value_still_stops_the_retrieval(self) -> None:
        """A grid change is an integrity refusal, not a provider non-publication."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            geography = directory / "geography.json"
            geography.write_text(json.dumps(GEOGRAPHY.to_dict()), encoding="utf-8")
            archive = _Archive()
            calls: list[int] = []
            baseline = _decoder()

            def decode(payload: bytes, indices: Any) -> Grib2Message:
                calls.append(1)
                return replace(
                    baseline(payload, indices),
                    grid=GRID
                    if len(calls) < 4
                    else Grib2Grid(720, 361, 90.0, 0.0, 0.5, 0.5),
                )

            def factory() -> NoaaGfsClient:
                return NoaaGfsClient(
                    fetcher=archive.fetch, head_reader=archive.head, decoder=decode
                )

            stderr = io.StringIO()
            with mock.patch("greek_bess.cli.fundamentals.NoaaGfsClient", factory):
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
                            "2026-08-20",
                            "--end-day",
                            "2026-08-22",
                            "--output",
                            str(directory / "features.csv"),
                        ]
                    )
            self.assertEqual(code, 1)
            self.assertIn("different grid", stderr.getvalue())
            self.assertFalse((directory / "features.csv").exists())

    def test_a_window_excluded_entirely_by_name_is_refused_rather_than_written_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            archive = _Archive(missing_cycles=frozenset({"20260819", "20260820"}))
            code, stderr = self._run(directory, archive, end_day="2026-08-21")
            self.assertEqual(code, 1)
            self.assertIn("refused rather than written", stderr)
            self.assertIn("missing_object", stderr)
            self.assertFalse((directory / "features.csv").exists())


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
