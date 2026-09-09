"""NOAA GFS 0.25° forecast vintages: the one v0.9 fundamentals source, read point in time.

The source was chosen on 2 September 2026 after a spike against the live public archive
(`docs/fundamentals_source_assessment_2026-09-02.md`). This client implements exactly what that
spike established, and refuses the cases it found rather than working around them.

**The decision-time cycle is the 00 UTC cycle of D-1, and only that cycle.** The 06 UTC cycle was
observed publishing a step after a midday cutoff, so it cannot support a day-ahead decision. A
later cycle is a separate decision with its own evidence, not a fallback this module may reach
for when a 00 UTC object is missing: a missing cycle makes the day incomplete and it is excluded
by name.

**Both archive key layouts are tried, and only absence moves on to the next.** The 0.25° product
moved under an ``atmos/`` segment on 23 March 2021. A client that hard-codes the current layout
returns nothing — silently, as an empty listing rather than an error — for the earliest usable
delivery days. Trying both layouts means asking the store twice, so the two answers have to be
told apart: a ``404`` means the object is not at that key and the other layout is tried, while a
5xx or a transport fault means the store did not answer and the retrieval stops there. Reading
the second as the first would report a network blip as a provider non-publication, which is a
finding about the source that nothing downstream could detect as false.

**A source condition names the delivery day, and only that day.** A genuinely missing object and
a ``.idx`` sidecar that does not describe the object beside it are conditions of one delivery
day. They carry a named cause (:data:`MISSING_OBJECT`, :data:`SIDECAR_OBJECT_MISMATCH`) so the
retrieval can exclude that day by name and continue, which is what the refusals here have always
said happens. Every other refusal in this module is an integrity refusal about how a value would
be built, and still stops the retrieval.

**Every forecast step is checked on its own.** Upload order is not monotone in step: a later step
of one cycle was observed appearing before an earlier one. One step's availability therefore says
nothing about another's, and no step is inferred from a neighbour.

**Only the hourly record is used.** Before 26 February 2021 the product is 3-hourly, so the first
delivery day that can carry an hourly feature is 27 February 2021. Earlier days are refused by
name. A coarser feature is not broadcast over them: that would make one column mean a one-hour
mean after February 2021 and a three-hour mean before it.

**Radiation is a bucket mean that resets every six hours** and is de-averaged from two adjacent
steps by a stated arithmetic rule (:func:`deaverage_bucket_mean`). Temperature and the wind
components are instantaneous and need no such treatment.

**Nothing here grades availability against a cutoff.** The client records the provider's
publication instant (the object's ``Last-Modified``) as ``provider_declared`` evidence and this
project's own retrieval instant beside it. Whether those instants clear a particular delivery
day's cutoff is a question only a declared cutoff answers, and
:mod:`greek_bess.data.availability_audit` answers it.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .http import (
    DEFAULT_RETRY_POLICY,
    OfficialDataDownloadError,
    RetryPolicy,
    fetch_https_bytes,
    head_https_headers,
)
from .point_in_time import (
    PROVIDER_DECLARED,
    VARIABLE_UNITS,
    SamplingGeography,
    ensure_point_in_time,
)
from .provenance import (
    RetrievalRecord,
    atomic_write_bytes,
    sha256_bytes,
    utc_now_iso,
    write_retrieval_manifest,
)
from .timezones import UTC, market_day_starts

NOAA_GFS_HOST = "noaa-gfs-bdp-pds.s3.amazonaws.com"
NOAA_GFS_BASE_URL = f"https://{NOAA_GFS_HOST}"
NOAA_GFS_ALLOWED_HOSTS = frozenset({NOAA_GFS_HOST})

NOAA_GFS_SOURCE = "noaa_gfs"
NOAA_GFS_DATASET = "gfs.0p25"

#: The provider's licence obligations, captured verbatim from the AWS Open Data registry entry
#: by the source spike. They are carried in every retrieval manifest so that the obligation
#: travels with the evidence rather than living only in a document.
NOAA_GFS_ATTRIBUTION = (
    "NOAA Global Forecast System (GFS) 0.25 degree product, retrieved from the NOAA Open Data "
    "Dissemination archive on Amazon S3. Values reported by this project are derived from that "
    "product and are not unaltered NOAA data; NOAA does not endorse this project or its results."
)

#: The one cycle that can support a day-ahead decision (source assessment section 4.3).
DECISION_CYCLE_HOUR = 0

#: The first delivery day that can carry an hourly feature. Before 26 February 2021 the product
#: is 3-hourly; the 00 UTC cycle of 26 February 2021 is the first hourly cycle, so 27 February
#: 2021 is the first delivery day it covers.
FIRST_HOURLY_DELIVERY_DAY = date(2021, 2, 27)

#: The cycle day from which the ``atmos/`` key segment is present. Both layouts are always tried;
#: this only decides which is tried first.
ATMOS_LAYOUT_FROM_CYCLE_DAY = date(2021, 3, 23)

#: The archive publishes hourly steps out to f120. A market day needs steps well inside that,
#: but the bound is asserted rather than assumed.
MAXIMUM_HOURLY_FORECAST_STEP = 120

#: The bucket length of the accumulated/averaged fields, in forecast hours.
RADIATION_BUCKET_HOURS = 6

#: Incremented when decoded-message validation or feature-value construction changes. Existing
#: tables built under an earlier value are not equivalent inputs and must be rebuilt.
GFS_FEATURE_SEMANTICS_VERSION = 2

_INDEX_LINE = re.compile(
    r"^(?P<message>\d+):(?P<offset>\d+):d=(?P<cycle>\d{10}):"
    r"(?P<variable>[^:]+):(?P<level>[^:]+):(?P<step>[^:]*):"
)
_INSTANT_STEP = re.compile(r"^(?P<step>\d+) hour fcst$")
_WINDOW_STEP = re.compile(r"^(?P<start>\d+)-(?P<end>\d+) hour (?P<kind>ave|acc) fcst$")


#: The 00 UTC cycle published no object for a forecast step this delivery day needs, at either
#: archive key layout, and the store said so rather than failing to answer.
MISSING_OBJECT = "missing_object"

#: The ``.idx`` sidecar beside a step object does not describe that object — it indexes a
#: different publication — so no message byte range can be resolved from it.
SIDECAR_OBJECT_MISMATCH = "sidecar_object_mismatch"

#: The causes that are conditions of one delivery day rather than of the retrieval. A retrieval
#: excludes such a day by name and continues; every other :class:`NoaaGfsError` stops it, because
#: every other one is a refusal about how a value would be built rather than about whether the
#: provider published it.
SOURCE_CONDITION_CAUSES = (MISSING_OBJECT, SIDECAR_OBJECT_MISMATCH)


class NoaaGfsError(RuntimeError):
    """Raised when a NOAA GFS retrieval or decode cannot be performed exactly as declared.

    ``cause`` is set only for the source conditions above. It is ``None`` for every integrity
    refusal, and a caller deciding whether to exclude a day must read it rather than the message
    text: an excluded day is recorded as a provider non-publication, and a refusal about grids,
    units, decoding or declarations is not that.
    """

    def __init__(self, message: str, *, cause: str | None = None) -> None:
        super().__init__(message)
        if cause is not None and cause not in SOURCE_CONDITION_CAUSES:
            raise ValueError(f"Unknown NOAA GFS source-condition cause: {cause!r}")
        self.cause = cause


@dataclass(frozen=True)
class GfsMessageSpec:
    """The sidecar and decoded GRIB identity required for one source message."""

    index_variable: str
    index_level: str
    short_name: str
    name: str
    units: str
    type_of_level: str
    level: float


@dataclass(frozen=True)
class GfsVariable:
    """One feature variable, the GRIB2 messages behind it and how they combine."""

    feature_variable: str
    messages: tuple[GfsMessageSpec, ...]
    aggregation: str

    def __post_init__(self) -> None:
        if self.feature_variable not in VARIABLE_UNITS:
            raise NoaaGfsError(
                f"{self.feature_variable!r} is not in the point-in-time variable registry"
            )
        if self.aggregation not in ("instant", "bucket_mean"):
            raise NoaaGfsError(f"Unknown aggregation {self.aggregation!r}")


#: The three feature variables this source supplies, and the four GRIB2 messages behind them.
#: Wind speed is derived from the two 10 m components rather than stored as components, because
#: the component signs are a coordinate convention and the speed is the physical quantity a
#: forecast uses.
GFS_VARIABLES: dict[str, GfsVariable] = {
    "dswrf_surface": GfsVariable(
        "dswrf_surface",
        (
            GfsMessageSpec(
                "DSWRF",
                "surface",
                "sdswrf",
                "Surface downward short-wave radiation flux",
                "W m**-2",
                "surface",
                0.0,
            ),
        ),
        "bucket_mean",
    ),
    "temperature_2m": GfsVariable(
        "temperature_2m",
        (
            GfsMessageSpec(
                "TMP",
                "2 m above ground",
                "2t",
                "2 metre temperature",
                "K",
                "heightAboveGround",
                2.0,
            ),
        ),
        "instant",
    ),
    "wind_speed_10m": GfsVariable(
        "wind_speed_10m",
        (
            GfsMessageSpec(
                "UGRD",
                "10 m above ground",
                "10u",
                "10 metre U wind component",
                "m s**-1",
                "heightAboveGround",
                10.0,
            ),
            GfsMessageSpec(
                "VGRD",
                "10 m above ground",
                "10v",
                "10 metre V wind component",
                "m s**-1",
                "heightAboveGround",
                10.0,
            ),
        ),
        "instant",
    ),
}


@dataclass(frozen=True)
class GfsObjectHead:
    """What a ``HEAD`` on one forecast-step object reports."""

    key: str
    url: str
    last_modified_utc: pd.Timestamp
    size_bytes: int
    etag: str | None


@dataclass(frozen=True)
class GfsIndexEntry:
    """One line of a ``.idx`` sidecar: a message, its byte range and what it holds."""

    message_number: int
    start_byte: int
    end_byte: int
    cycle: str
    variable: str
    level: str
    step_description: str

    @property
    def byte_count(self) -> int:
        return self.end_byte - self.start_byte + 1


@dataclass(frozen=True)
class Grib2Grid:
    """The regular latitude/longitude grid a decoded message is defined on."""

    ni: int
    nj: int
    first_latitude: float
    first_longitude: float
    latitude_increment: float
    longitude_increment: float


@dataclass(frozen=True)
class Grib2Message:
    """A decoded GRIB2 message, sampled at the grid indices the caller asked for."""

    short_name: str
    name: str
    units: str
    type_of_level: str
    level: float
    step_type: str
    start_step: int
    end_step: int
    step_units: int
    data_date: int
    data_time: int
    validity_date: int
    validity_time: int
    grid: Grib2Grid
    samples: tuple[float, ...]


#: What a decoder must do: read one self-framing GRIB2 message and return the values at the
#: requested grid indices. Injectable so that the client is testable without a real message.
Decoder = Callable[[bytes, Sequence[int]], Grib2Message]


def eccodes_library_version() -> str:
    """Return the ecCodes C library version the binding is bound to.

    This exists to be called by a test. The source spike proved the decoder on two locally built
    interpreters but not on the ``actions/setup-python`` images, and that residual closes only
    when CI itself imports the binding and gets an answer.
    """

    import eccodes

    return str(eccodes.codes_get_api_version())


def decode_grib2_message(payload: bytes, indices: Sequence[int]) -> Grib2Message:
    """Decode one GRIB2 message and read the values at ``indices``.

    The message is required to be self-framing — ``GRIB`` at the front, ``7777`` at the back —
    before it reaches the decoder, so a truncated byte range is named as truncation rather than
    surfacing as a library error about a corrupt field.
    """

    import eccodes

    if len(payload) < 8 or payload[:4] != b"GRIB" or payload[-4:] != b"7777":
        raise NoaaGfsError(
            f"Retrieved {len(payload)} bytes that are not one complete GRIB2 message: a message "
            "starts with 'GRIB' and ends with '7777', so the byte range was truncated or the "
            "sidecar offsets do not describe this object"
        )
    handle = eccodes.codes_new_from_message(payload)
    try:
        grid_type = str(eccodes.codes_get(handle, "gridType"))
        if grid_type != "regular_ll":
            raise NoaaGfsError(
                f"Message is on a {grid_type!r} grid; this client samples regular_ll grids only"
            )
        for name, expected in (
            ("iScansNegatively", 0),
            ("jScansPositively", 0),
            ("jPointsAreConsecutive", 0),
        ):
            if int(eccodes.codes_get(handle, name)) != expected:
                raise NoaaGfsError(
                    f"Message declares {name}={eccodes.codes_get(handle, name)}; the grid index "
                    "arithmetic this client uses assumes the archive's north-to-south, "
                    "west-to-east scanning order and refuses rather than mis-sampling"
                )
        grid = Grib2Grid(
            ni=int(eccodes.codes_get(handle, "Ni")),
            nj=int(eccodes.codes_get(handle, "Nj")),
            first_latitude=float(
                eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees")
            ),
            first_longitude=float(
                eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees")
            ),
            latitude_increment=float(
                eccodes.codes_get(handle, "jDirectionIncrementInDegrees")
            ),
            longitude_increment=float(
                eccodes.codes_get(handle, "iDirectionIncrementInDegrees")
            ),
        )
        samples = tuple(
            float(eccodes.codes_get_double_element(handle, "values", int(index)))
            for index in indices
        )
        return Grib2Message(
            short_name=str(eccodes.codes_get(handle, "shortName")),
            name=str(eccodes.codes_get(handle, "name")),
            units=str(eccodes.codes_get(handle, "units")),
            type_of_level=str(eccodes.codes_get(handle, "typeOfLevel")),
            level=float(eccodes.codes_get(handle, "level")),
            step_type=str(eccodes.codes_get(handle, "stepType")),
            start_step=int(eccodes.codes_get(handle, "startStep")),
            end_step=int(eccodes.codes_get(handle, "endStep")),
            step_units=int(eccodes.codes_get(handle, "stepUnits")),
            data_date=int(eccodes.codes_get(handle, "dataDate")),
            data_time=int(eccodes.codes_get(handle, "dataTime")),
            validity_date=int(eccodes.codes_get(handle, "validityDate")),
            validity_time=int(eccodes.codes_get(handle, "validityTime")),
            grid=grid,
            samples=samples,
        )
    finally:
        eccodes.codes_release(handle)


def grid_index(grid: Grib2Grid, latitude: float, longitude: float) -> int:
    """Return the flat index of a declared point, refusing a point that is not a grid node.

    A declared point that falls between nodes would have to be interpolated, and this project
    does not interpolate silently. The refusal names the nearest node so the operator can adjust
    the declaration deliberately.
    """

    normalized_longitude = (float(longitude) - grid.first_longitude) % 360.0
    row = (grid.first_latitude - float(latitude)) / grid.latitude_increment
    column = normalized_longitude / grid.longitude_increment
    for name, value, increment, origin in (
        ("latitude", row, grid.latitude_increment, grid.first_latitude),
        ("longitude", column, grid.longitude_increment, grid.first_longitude),
    ):
        if not math.isclose(value, round(value), rel_tol=0.0, abs_tol=1e-6):
            nearest = origin - round(value) * increment if name == "latitude" else (
                origin + round(value) * increment
            )
            raise NoaaGfsError(
                f"Declared {name} does not fall on a grid node of this {increment}° grid; the "
                f"nearest node is {nearest}. A point between nodes would have to be "
                "interpolated, and no interpolation rule is declared"
            )
    row_index = int(round(row))
    column_index = int(round(column))
    if not 0 <= row_index < grid.nj or not 0 <= column_index < grid.ni:
        raise NoaaGfsError("Declared point lies outside the decoded grid")
    return row_index * grid.ni + column_index


def bucket_start_step(step: int) -> int:
    """Return the forecast hour the averaging bucket containing ``step`` started at.

    The sidecar states the window directly — ``f025`` is ``24-25 hour ave fcst`` — and this
    reproduces it: buckets reset every six hours, so a step is in the bucket that began at the
    largest multiple of six strictly below it.
    """

    if step < 1:
        raise NoaaGfsError("A bucket-mean field has no window at forecast step 0")
    return RADIATION_BUCKET_HOURS * ((step - 1) // RADIATION_BUCKET_HOURS)


def deaverage_bucket_mean(
    step: int, value_at_step: float, previous_value: float | None
) -> float:
    """Return the one-hour mean over ``(step-1, step]`` from two adjacent bucket means.

    For a step ``f`` in the bucket that began at ``b``, the message holds the mean over
    ``[b, f]``. The hourly mean over ``(f-1, f]`` is therefore
    ``A_f·(f-b) - A_(f-1)·(f-1-b)``, which reduces to ``A_f`` at the first step of a bucket.
    """

    bucket = bucket_start_step(step)
    span = step - bucket
    previous_span = step - 1 - bucket
    if previous_span == 0:
        return float(value_at_step)
    if previous_value is None:
        raise NoaaGfsError(
            f"Step {step} is {previous_span} hour(s) into its averaging bucket, so the hourly "
            f"mean needs step {step - 1} of the same bucket; it was not retrieved"
        )
    return float(value_at_step) * span - float(previous_value) * previous_span


def object_key_candidates(cycle_day: date, step: int) -> tuple[str, ...]:
    """Return both archive key layouts for one cycle and step, likeliest first."""

    stamp = cycle_day.strftime("%Y%m%d")
    hour = f"{DECISION_CYCLE_HOUR:02d}"
    tail = f"gfs.t{hour}z.pgrb2.0p25.f{step:03d}"
    with_atmos = f"gfs.{stamp}/{hour}/atmos/{tail}"
    without_atmos = f"gfs.{stamp}/{hour}/{tail}"
    if cycle_day >= ATMOS_LAYOUT_FROM_CYCLE_DAY:
        return (with_atmos, without_atmos)
    return (without_atmos, with_atmos)


def cycle_instant_utc(cycle_day: date) -> pd.Timestamp:
    """Return the UTC instant of the 00 UTC cycle on ``cycle_day``."""

    return pd.Timestamp(datetime.combine(cycle_day, datetime.min.time()), tz=UTC)


def delivery_interval_starts_utc(delivery_day: date) -> pd.DatetimeIndex:
    """Return every hourly delivery-interval start of one CET/CEST market day, in UTC."""

    return market_day_starts(delivery_day, 60).tz_convert(UTC)


def required_forecast_steps(delivery_day: date) -> tuple[int, ...]:
    """Return every forecast step the 00 UTC cycle of D-1 must supply for one market day.

    The range is derived from the market day rather than declared as a constant, so a 23- or
    25-hour day, and either clock offset, produce their own step set instead of being trimmed to
    fit a number written down once. The bucket-mean fields need the step one hour past the last
    interval start, and the predecessor step of each of those, which is why the set is wider than
    the interval count.
    """

    cycle = cycle_instant_utc(delivery_day - timedelta(days=1))
    steps: set[int] = set()
    for start in delivery_interval_starts_utc(delivery_day):
        offset = int((start - cycle).total_seconds() // 3600)
        steps.add(offset)
        end_step = offset + 1
        steps.add(end_step)
        if end_step - 1 > bucket_start_step(end_step):
            steps.add(end_step - 1)
    ordered = tuple(sorted(steps))
    if ordered[0] < 1 or ordered[-1] > MAXIMUM_HOURLY_FORECAST_STEP:
        raise NoaaGfsError(
            f"Delivery day {delivery_day.isoformat()} needs forecast steps "
            f"{ordered[0]}-{ordered[-1]}, outside the hourly range this product publishes"
        )
    return ordered


def parse_gfs_index(text: str, object_size_bytes: int) -> tuple[GfsIndexEntry, ...]:
    """Parse a ``.idx`` sidecar into byte-ranged message entries.

    Each line gives a message's start offset; the end is the next message's start minus one, and
    the last message runs to the end of the object. The object size therefore has to come from
    the ``HEAD``, not be guessed, or the final message would be requested short.
    """

    entries: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _INDEX_LINE.match(line)
        if match is None:
            raise NoaaGfsError(
                f"Line {number} of the .idx sidecar is not a message record: {line[:80]!r}"
            )
        entries.append(match.groupdict())
    if not entries:
        raise NoaaGfsError("The .idx sidecar is empty; no message byte ranges can be resolved")

    offsets = [int(entry["offset"]) for entry in entries]
    if offsets != sorted(offsets):
        raise NoaaGfsError("The .idx sidecar lists message offsets out of order")
    if offsets[-1] >= object_size_bytes:
        raise NoaaGfsError(
            "The .idx sidecar describes an offset past the end of the object it indexes; the "
            "sidecar and the object are not the same publication",
            cause=SIDECAR_OBJECT_MISMATCH,
        )
    parsed: list[GfsIndexEntry] = []
    for position, entry in enumerate(entries):
        start = offsets[position]
        end = (
            offsets[position + 1] - 1
            if position + 1 < len(offsets)
            else object_size_bytes - 1
        )
        parsed.append(
            GfsIndexEntry(
                message_number=int(entry["message"]),
                start_byte=start,
                end_byte=end,
                cycle=str(entry["cycle"]),
                variable=str(entry["variable"]),
                level=str(entry["level"]),
                step_description=str(entry["step"]),
            )
        )
    return tuple(parsed)


def index_step_window(entry: GfsIndexEntry) -> tuple[int, int, str]:
    """Return ``(start_step, end_step, kind)`` from a sidecar step description."""

    instant = _INSTANT_STEP.match(entry.step_description)
    if instant is not None:
        step = int(instant.group("step"))
        return step, step, "instant"
    window = _WINDOW_STEP.match(entry.step_description)
    if window is not None:
        return int(window.group("start")), int(window.group("end")), window.group("kind")
    raise NoaaGfsError(
        f"Unrecognised forecast-step description {entry.step_description!r} for "
        f"{entry.variable}:{entry.level}; the averaging window cannot be read from the sidecar"
    )


def select_index_entry(
    entries: Sequence[GfsIndexEntry], variable: str, level: str, step: int
) -> GfsIndexEntry:
    """Return the one sidecar entry for a variable, level and forecast step."""

    matches = [
        entry
        for entry in entries
        if entry.variable == variable
        and entry.level == level
        and index_step_window(entry)[1] == step
    ]
    if not matches:
        raise NoaaGfsError(
            f"The sidecar holds no {variable}:{level} message ending at forecast step {step}"
        )
    if len(matches) > 1:
        raise NoaaGfsError(
            f"The sidecar holds {len(matches)} {variable}:{level} messages ending at forecast "
            f"step {step}; the message a value came from would be ambiguous"
        )
    return matches[0]


@dataclass(frozen=True)
class GfsDeliveryDayFeatures:
    """One delivery day's feature rows, the documents behind them and what was retrieved."""

    features: pd.DataFrame
    records: tuple[RetrievalRecord, ...]
    summary: dict[str, Any]


class NoaaGfsClient:
    """Read 0.25° forecast vintages by byte range and sample them at a declared geography.

    Three collaborators are injectable so the client can be exercised without the archive: a
    ``fetcher`` returning bytes for a URL and optional byte range, a ``head_reader`` returning
    response headers, and a ``decoder`` turning one GRIB2 message into sampled values. The
    defaults are the real HTTPS and ecCodes implementations; the seams exist for tests, not to
    admit an alternative source through the back door.

    ``retry_policy`` bounds how often the transport re-asks a request that failed in a way that
    says nothing about the object. It is a property of the client rather than a command-line
    knob: a retrieval accepted as evidence should talk to the provider the same way every time
    it runs.
    """

    def __init__(
        self,
        *,
        fetcher: Callable[[str, tuple[int, int] | None], bytes] | None = None,
        head_reader: Callable[[str], Mapping[str, str]] | None = None,
        decoder: Decoder | None = None,
        timeout_seconds: int = 60,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy
        self._fetcher = fetcher
        self._head_reader = head_reader
        self._decoder = decoder or decode_grib2_message

    def head_step_object(self, cycle_day: date, step: int) -> GfsObjectHead:
        """Return the ``HEAD`` of one forecast-step object, trying both key layouts.

        Only the store answering that a key holds nothing moves on to the other layout. A 5xx, a
        connection reset or a truncated answer is not an answer about the key, and is raised
        rather than absorbed: absorbing it would turn a network fault into the claim that the
        provider published no object, which is a finding this project records by name and which
        no later stage could distinguish from the real thing.

        An injected ``head_reader`` is held to the same contract — it signals absence with an
        :class:`~greek_bess.data.http.OfficialDataDownloadError` of kind ``absent`` — so a test
        exercises the same branch the archive does.
        """

        attempted: list[str] = []
        for key in object_key_candidates(cycle_day, step):
            url = f"{NOAA_GFS_BASE_URL}/{key}"
            attempted.append(key)
            try:
                headers = self._head(url)
            except OfficialDataDownloadError as exc:
                if not exc.is_absence:
                    raise NoaaGfsError(
                        f"The archive did not answer whether {key} exists ({exc}). The delivery "
                        "day is not excluded on this evidence: an unanswered request is not a "
                        "provider non-publication"
                    ) from exc
                continue
            return _object_head(key, url, headers)
        raise NoaaGfsError(
            f"No 0.25° object for the {DECISION_CYCLE_HOUR:02d} UTC cycle of "
            f"{cycle_day.isoformat()} at forecast step {step}; both archive key layouts were "
            f"tried ({', '.join(attempted)}) and the store answered that neither holds an "
            "object. A missing cycle or step makes the delivery day incomplete and it is "
            "excluded by name; an earlier cycle is not substituted",
            cause=MISSING_OBJECT,
        )

    def read_index(self, head: GfsObjectHead) -> tuple[GfsIndexEntry, ...]:
        """Read and parse the ``.idx`` sidecar beside one forecast-step object.

        A sidecar that is absent while its object is present carries no cause: it is neither the
        provider having published no object nor a sidecar describing a different one, and this
        client has no rule for reading an object's messages without it. The retrieval stops and
        names the key rather than excluding the delivery day on a condition nobody stated.
        """

        try:
            payload = self._get(f"{head.url}.idx", None)
        except OfficialDataDownloadError as exc:
            raise NoaaGfsError(
                f"The .idx sidecar beside {head.key} could not be read ({exc}). The object is "
                "present, so this is not a delivery day the provider did not publish, and the "
                "message byte ranges are not guessed"
            ) from exc
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NoaaGfsError(f"The sidecar for {head.key} is not UTF-8 text") from exc
        return parse_gfs_index(text, head.size_bytes)

    def fetch_message(self, head: GfsObjectHead, entry: GfsIndexEntry) -> bytes:
        """Retrieve exactly one GRIB2 message by the byte range its sidecar declares."""

        payload = self._get(head.url, (entry.start_byte, entry.end_byte))
        if len(payload) != entry.byte_count:
            raise NoaaGfsError(
                f"{head.key} message {entry.message_number}: asked for {entry.byte_count} bytes "
                f"and received {len(payload)}; the slice is not the message the sidecar declares"
            )
        return payload

    def build_delivery_day_features(
        self,
        delivery_day: date,
        *,
        geography: SamplingGeography,
        variables: Sequence[str],
        raw_dir: Path | None = None,
        retrieved_at_utc: str | None = None,
    ) -> GfsDeliveryDayFeatures:
        """Build every hourly feature row for one CET/CEST market day, with its provenance.

        A day is built completely or not at all. A missing object, an unreadable sidecar or a
        step whose message cannot be decoded raises, because a partly built day would reach the
        availability audit as a day with thin coverage rather than as a day with a named cause.
        """

        if delivery_day < FIRST_HOURLY_DELIVERY_DAY:
            raise NoaaGfsError(
                f"Delivery day {delivery_day.isoformat()} precedes "
                f"{FIRST_HOURLY_DELIVERY_DAY.isoformat()}, the first day the 0.25° product "
                "covers hourly. Before it the product is 3-hourly, and a 3-hour mean is not "
                "broadcast into an hourly column: the day carries no feature and is excluded"
            )
        requested = _validate_variables(variables)
        retrieved = retrieved_at_utc or utc_now_iso()
        cycle_day = delivery_day - timedelta(days=1)
        cycle = cycle_instant_utc(cycle_day)
        steps = required_forecast_steps(delivery_day)

        heads: dict[int, GfsObjectHead] = {}
        indexes: dict[int, tuple[GfsIndexEntry, ...]] = {}
        messages: dict[tuple[int, str, str], _MessagePayload] = {}
        records: list[RetrievalRecord] = []
        for step in steps:
            head = self.head_step_object(cycle_day, step)
            heads[step] = head
            indexes[step] = self.read_index(head)
        indices: dict[tuple[float, float], int] = {}
        grid: Grib2Grid | None = None

        for step in steps:
            head = heads[step]
            for variable in requested:
                variable_spec = GFS_VARIABLES[variable]
                for message_spec in variable_spec.messages:
                    name = message_spec.index_variable
                    level = message_spec.index_level
                    key = (step, name, level)
                    if key in messages:
                        continue
                    entry = select_index_entry(indexes[step], name, level, step)
                    _validate_index_semantics(
                        entry,
                        expected_cycle=cycle,
                        expected_step=step,
                        aggregation=variable_spec.aggregation,
                    )
                    payload = self.fetch_message(head, entry)
                    if grid is None:
                        # The declared points are resolved to flat indices once, from the first
                        # message's own grid header. Every later message is then checked against
                        # that grid rather than trusted: a step published on a different grid
                        # would be sampled at the right index of the wrong array, which is the
                        # one failure here that produces plausible numbers.
                        probe = self._decoder(payload, ())
                        _validate_decoded_message(
                            probe,
                            spec=message_spec,
                            entry=entry,
                            expected_cycle=cycle,
                        )
                        grid = probe.grid
                        indices = {
                            (point.latitude, point.longitude): grid_index(
                                grid, point.latitude, point.longitude
                            )
                            for point in geography.points
                        }
                    ordered_points = tuple(geography.points)
                    message = self._decoder(
                        payload,
                        [indices[(point.latitude, point.longitude)] for point in ordered_points],
                    )
                    _validate_decoded_message(
                        message,
                        spec=message_spec,
                        entry=entry,
                        expected_cycle=cycle,
                    )
                    if message.grid != grid:
                        raise NoaaGfsError(
                            f"{head.key} message {entry.message_number} is on a different grid "
                            f"({message.grid}) from the one the declared points were resolved "
                            f"against ({grid}); the day is refused rather than sampled at "
                            "indices that mean something else"
                        )
                    _validate_samples(message.samples, ordered_points)
                    digest = sha256_bytes(payload)
                    messages[key] = _MessagePayload(
                        head=head,
                        entry=entry,
                        digest=digest,
                        samples=message.samples,
                    )
                    if raw_dir is not None:
                        atomic_write_bytes(
                            Path(raw_dir) / f"{head.key}.m{entry.message_number:04d}.grib2",
                            payload,
                        )
                    records.append(
                        RetrievalRecord(
                            source=NOAA_GFS_SOURCE,
                            dataset=NOAA_GFS_DATASET,
                            source_url=f"{head.url}#bytes={entry.start_byte}-{entry.end_byte}",
                            local_path=f"{head.key}.m{entry.message_number:04d}.grib2",
                            retrieved_at_utc=retrieved,
                            sha256=digest,
                            size_bytes=len(payload),
                            coverage_start=delivery_day.isoformat(),
                            coverage_end=delivery_day.isoformat(),
                            published_at_source=head.last_modified_utc.isoformat(),
                            published_at_utc=head.last_modified_utc.isoformat(),
                            availability_classification=(
                                "requires_point_in_time_acceptance"
                            ),
                        )
                    )

        rows = _feature_rows(
            delivery_day=delivery_day,
            cycle=cycle,
            geography=geography,
            variables=requested,
            messages=messages,
            retrieved_at_utc=retrieved,
        )
        features = ensure_point_in_time(pd.DataFrame(rows))
        summary = {
            "delivery_day": delivery_day.isoformat(),
            "cycle_day": cycle_day.isoformat(),
            "cycle_hour_utc": DECISION_CYCLE_HOUR,
            "forecast_steps": list(steps),
            "requested_variables": list(requested),
            "geography_id": geography.geography_id,
            "geography": geography.to_dict(),
            "feature_semantics_version": GFS_FEATURE_SEMANTICS_VERSION,
            "decoded_message_contract": _decoded_message_contract(requested),
            "message_count": len(messages),
            "retrieved_byte_count": int(
                sum(payload.entry.byte_count for payload in messages.values())
            ),
            "feature_row_count": int(len(features)),
            "attribution": NOAA_GFS_ATTRIBUTION,
        }
        return GfsDeliveryDayFeatures(
            features=features, records=tuple(records), summary=summary
        )

    def _head(self, url: str) -> Mapping[str, str]:
        if self._head_reader is not None:
            return self._head_reader(url)
        return head_https_headers(
            url,
            allowed_hosts=NOAA_GFS_ALLOWED_HOSTS,
            timeout_seconds=self.timeout_seconds,
            retry_policy=self.retry_policy,
        )

    def _get(self, url: str, byte_range: tuple[int, int] | None) -> bytes:
        if self._fetcher is not None:
            return self._fetcher(url, byte_range)
        return fetch_https_bytes(
            url,
            allowed_hosts=NOAA_GFS_ALLOWED_HOSTS,
            timeout_seconds=self.timeout_seconds,
            byte_range=byte_range,
            retry_policy=self.retry_policy,
        )


def write_gfs_retrieval_manifest(
    path: Path, records: Sequence[RetrievalRecord], *, created_at_utc: str | None = None
) -> None:
    """Write the retrieval manifest for a NOAA GFS fetch."""

    write_retrieval_manifest(path, list(records), created_at_utc=created_at_utc)


@dataclass(frozen=True)
class _MessagePayload:
    head: GfsObjectHead
    entry: GfsIndexEntry
    digest: str
    samples: tuple[float, ...]


def _validate_index_semantics(
    entry: GfsIndexEntry,
    *,
    expected_cycle: pd.Timestamp,
    expected_step: int,
    aggregation: str,
) -> None:
    expected_cycle_text = expected_cycle.strftime("%Y%m%d%H")
    if entry.cycle != expected_cycle_text:
        raise NoaaGfsError(
            f"Sidecar message {entry.message_number} declares cycle {entry.cycle}, not the "
            f"requested {expected_cycle_text} cycle"
        )
    actual_window = index_step_window(entry)
    expected_window = (
        (expected_step, expected_step, "instant")
        if aggregation == "instant"
        else (bucket_start_step(expected_step), expected_step, "ave")
    )
    if actual_window != expected_window:
        raise NoaaGfsError(
            f"Sidecar message {entry.message_number} declares forecast semantics "
            f"{actual_window}, not the required {expected_window}"
        )


def _validate_decoded_message(
    message: Grib2Message,
    *,
    entry: GfsIndexEntry,
    spec: GfsMessageSpec,
    expected_cycle: pd.Timestamp,
) -> None:
    identity = (message.short_name, message.name)
    expected_identity = (spec.short_name, spec.name)
    if identity != expected_identity:
        raise NoaaGfsError(
            f"Decoded parameter identity {identity!r} does not match "
            f"{entry.variable}:{entry.level} ({expected_identity!r})"
        )
    if message.units != spec.units:
        raise NoaaGfsError(
            f"Decoded units {message.units!r} for {entry.variable}:{entry.level} do not match "
            f"the required {spec.units!r}; units are not converted silently"
        )
    if message.type_of_level != spec.type_of_level or not math.isclose(
        message.level, spec.level, rel_tol=0.0, abs_tol=1e-9
    ):
        raise NoaaGfsError(
            f"Decoded level {message.type_of_level}:{message.level:g} does not match "
            f"{entry.variable}:{entry.level} ({spec.type_of_level}:{spec.level:g})"
        )
    if message.step_units != 1:
        raise NoaaGfsError(
            f"Decoded forecast step unit code is {message.step_units}, not 1 (hours)"
        )
    sidecar_start, sidecar_end, sidecar_kind = index_step_window(entry)
    decoded_kind = {"instant": "instant", "ave": "avg", "acc": "accum"}[sidecar_kind]
    expected_window = (sidecar_start, sidecar_end, decoded_kind)
    decoded_window = (message.start_step, message.end_step, message.step_type)
    if decoded_window != expected_window:
        raise NoaaGfsError(
            f"Decoded forecast semantics {decoded_window} do not match sidecar semantics "
            f"{expected_window} for {entry.variable}:{entry.level}"
        )

    expected_data_date = int(expected_cycle.strftime("%Y%m%d"))
    expected_data_time = int(expected_cycle.strftime("%H%M"))
    if (message.data_date, message.data_time) != (expected_data_date, expected_data_time):
        raise NoaaGfsError(
            f"Decoded cycle {message.data_date:08d} {message.data_time:04d} does not match "
            f"requested cycle {expected_data_date:08d} {expected_data_time:04d}"
        )
    expected_valid = expected_cycle + pd.Timedelta(message.end_step, unit="h")
    expected_validity = (
        int(expected_valid.strftime("%Y%m%d")),
        int(expected_valid.strftime("%H%M")),
    )
    if (message.validity_date, message.validity_time) != expected_validity:
        raise NoaaGfsError(
            f"Decoded valid time {message.validity_date:08d} {message.validity_time:04d} does "
            f"not equal cycle plus forecast step, {expected_validity[0]:08d} "
            f"{expected_validity[1]:04d}"
        )


def _decoded_message_contract(variables: Sequence[str]) -> dict[str, Any]:
    return {
        variable: {
            "aggregation": GFS_VARIABLES[variable].aggregation,
            "messages": [
                {
                    "index_variable": message.index_variable,
                    "index_level": message.index_level,
                    "short_name": message.short_name,
                    "name": message.name,
                    "units": message.units,
                    "type_of_level": message.type_of_level,
                    "level": message.level,
                    "step_units": "hours",
                }
                for message in GFS_VARIABLES[variable].messages
            ],
        }
        for variable in variables
    }


def _validate_variables(variables: Sequence[str]) -> tuple[str, ...]:
    if isinstance(variables, (str, bytes)) or not isinstance(variables, Sequence):
        raise NoaaGfsError("variables must be a list of registered feature variable names")
    requested = [str(name) for name in variables]
    if not requested:
        raise NoaaGfsError(
            "At least one feature variable must be named; there is no default variable set"
        )
    unknown = sorted(set(requested) - set(GFS_VARIABLES))
    if unknown:
        raise NoaaGfsError(
            f"This source does not supply: {', '.join(unknown)}. It supplies "
            f"{', '.join(sorted(GFS_VARIABLES))}"
        )
    duplicated = sorted({name for name in requested if requested.count(name) > 1})
    if duplicated:
        raise NoaaGfsError(f"Duplicate variables requested: {', '.join(duplicated)}")
    return tuple(sorted(requested))


def _object_head(key: str, url: str, headers: Mapping[str, str]) -> GfsObjectHead:
    lowered = {str(name).lower(): str(value) for name, value in headers.items()}
    last_modified = lowered.get("last-modified")
    length = lowered.get("content-length")
    if last_modified is None:
        raise NoaaGfsError(
            f"{key}: the object carries no Last-Modified header, so it has no provider "
            "publication instant. Availability inferred from anything else is the quarantined "
            "'assumed' grade, and this client does not manufacture one"
        )
    if length is None:
        raise NoaaGfsError(f"{key}: the object carries no Content-Length header")
    # parsedate_to_datetime is the parser HTTP-dates are specified against and returns an aware
    # datetime; strptime with %Z accepts "GMT" but whether it attaches a timezone has varied, and
    # a publication instant that is silently naive is exactly what this schema refuses.
    try:
        parsed = parsedate_to_datetime(last_modified)
    except (TypeError, ValueError) as exc:
        raise NoaaGfsError(
            f"{key}: Last-Modified {last_modified!r} is not an HTTP-date"
        ) from exc
    if parsed.tzinfo is None:
        raise NoaaGfsError(
            f"{key}: Last-Modified {last_modified!r} carries no timezone, so it cannot be "
            "compared with a declared decision cutoff"
        )
    published = pd.Timestamp(parsed).tz_convert(UTC)
    return GfsObjectHead(
        key=key,
        url=url,
        last_modified_utc=published,
        size_bytes=int(length),
        etag=lowered.get("etag"),
    )


def _weighted_sample(samples: Sequence[float], points: Sequence[Any]) -> float:
    _validate_samples(samples, points)
    return sum(
        float(value) * float(point.weight)
        for value, point in zip(samples, points, strict=True)
    )


def _validate_samples(samples: Sequence[float], points: Sequence[Any]) -> None:
    if len(samples) != len(points):
        raise NoaaGfsError(
            f"The decoder returned {len(samples)} samples for {len(points)} declared points"
        )
    for value, point in zip(samples, points, strict=True):
        if not math.isfinite(float(value)):
            raise NoaaGfsError(
                f"Sampling point {point.point_id!r} decoded a non-finite value; a missing grid "
                "value is not averaged into a declared aggregate"
            )


def _feature_rows(
    *,
    delivery_day: date,
    cycle: pd.Timestamp,
    geography: SamplingGeography,
    variables: Sequence[str],
    messages: Mapping[tuple[int, str, str], _MessagePayload],
    retrieved_at_utc: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start in delivery_interval_starts_utc(delivery_day):
        offset = int((start - cycle).total_seconds() // 3600)
        for variable in variables:
            spec = GFS_VARIABLES[variable]
            if spec.aggregation == "instant":
                contributing = [
                    messages[(offset, message.index_variable, message.index_level)]
                    for message in spec.messages
                ]
                value = _combine_instant(variable, contributing, geography.points)
            else:
                end_step = offset + 1
                message_spec = spec.messages[0]
                message_key = (message_spec.index_variable, message_spec.index_level)
                current = messages[(end_step,) + message_key]
                previous = (
                    None
                    if end_step - 1 == bucket_start_step(end_step)
                    else messages[(end_step - 1,) + message_key]
                )
                contributing = [current] if previous is None else [current, previous]
                local_hourly_means = tuple(
                    deaverage_bucket_mean(
                        end_step,
                        current_value,
                        None if previous is None else previous.samples[position],
                    )
                    for position, current_value in enumerate(current.samples)
                )
                value = _weighted_sample(local_hourly_means, geography.points)
            rows.append(
                _feature_row(
                    start=start,
                    variable=variable,
                    area=geography.area,
                    value=value,
                    contributing=contributing,
                    cycle=cycle,
                    retrieved_at_utc=retrieved_at_utc,
                    geography=geography,
                )
            )
    return rows


def _combine_instant(
    variable: str, contributing: Sequence[_MessagePayload], points: Sequence[Any]
) -> float:
    if variable == "wind_speed_10m":
        eastward, northward = (payload.samples for payload in contributing)
        if len(eastward) != len(northward):
            raise NoaaGfsError(
                "The decoded eastward and northward wind components have different point counts"
            )
        local_speeds = tuple(
            math.hypot(east, north)
            for east, north in zip(eastward, northward, strict=True)
        )
        return _weighted_sample(local_speeds, points)
    if len(contributing) != 1:
        raise NoaaGfsError(
            f"{variable} is built from {len(contributing)} messages but declares no rule for "
            "combining them"
        )
    return _weighted_sample(contributing[0].samples, points)


def _feature_row(
    *,
    start: pd.Timestamp,
    variable: str,
    area: str,
    value: float,
    contributing: Sequence[_MessagePayload],
    cycle: pd.Timestamp,
    retrieved_at_utc: str,
    geography: SamplingGeography,
) -> dict[str, Any]:
    # A derived value is available only when its *last* input was, and it is traceable only
    # through all of them. So the publication instant is the latest contributing object's, the
    # document id names every contributing object, and the digest is taken over the contributing
    # message digests in a stated order rather than over one of them.
    ordered = sorted(
        contributing, key=lambda payload: (payload.head.key, payload.entry.message_number)
    )
    document_id = "+".join(
        f"{payload.head.key}#m{payload.entry.message_number}" for payload in ordered
    )
    digest = (
        ordered[0].digest
        if len(ordered) == 1
        else sha256_bytes("".join(payload.digest for payload in ordered).encode("ascii"))
    )
    published = max(payload.head.last_modified_utc for payload in ordered)
    return {
        "delivery_start_utc": start,
        "delivery_end_utc": start + pd.Timedelta(1, unit="h"),
        "market_day": None,
        "source": NOAA_GFS_SOURCE,
        "dataset": NOAA_GFS_DATASET,
        "variable": variable,
        "area": area,
        "unit": VARIABLE_UNITS[variable],
        "resolution_minutes": 60,
        "value": value,
        "published_at_utc": published,
        "retrieved_at_utc": pd.Timestamp(retrieved_at_utc),
        "source_document_id": document_id,
        "source_revision": None,
        "raw_sha256": digest,
        "forecast_issue_time_utc": cycle,
        "forecast_horizon_minutes": None,
        "availability_evidence_grade": PROVIDER_DECLARED,
        "availability_evidence_detail": (
            f"s3_last_modified; geography {geography.geography_id}"
        ),
    }
