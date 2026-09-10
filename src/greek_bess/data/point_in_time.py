"""The typed point-in-time feature table: one row per value, carrying how it was available.

A canonical price row says what a price was. A point-in-time feature row has to say something
harder: what a value was, **and** that a bidder could have had it before the moment they had to
decide. Section 5 of `docs/v0.9_design.md` specifies the columns that make the second claim
checkable rather than asserted, and this module is that specification in code.

Four properties are load-bearing.

**Availability travels with the value.** Every row carries the instant the provider published
the datum, the instant this project retrieved it, the document and revision it came from, and a
SHA-256 of the exact bytes it was decoded from. A value whose publication instant is unknown
cannot enter an accepted table at all; it is admitted only into an explicitly quarantined table
under :data:`ASSUMED`, which no accepted run may read.

**Every revision is stored; none is selected here.** The table holds each publication of a
datum, including revisions published after any cutoff. Selecting the decision-time revision is
the join's job (v0.9.2). The storage layer must not discard the evidence that a revision was
superseded — that is the ``--all-revisions`` lesson of the ADMIE timing policy, applied to
values rather than files.

**A missing value is an absent row, never ``NaN``.** Coverage is reported by counting rows
against the delivery intervals a market day actually has. Nothing is forward-filled,
interpolated or imputed, and a broadcast of a coarser feature over finer price intervals is a
relation the join records, not a value this module invents.

**The evidence grade may be demoted downstream, never promoted.** A row's
``availability_evidence_grade`` records the strongest evidence the *retrieval* had: ``witnessed``
when this project observed the datum contemporaneously, ``provider_declared`` when a provider
instant attached to the datum is all there is. Whether that evidence clears a particular
delivery day's cutoff is a question only a declared cutoff can answer, so
:mod:`greek_bess.data.availability_audit` re-derives the effective grade per delivery day and
may lower it. It never raises it.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .schema import CANONICAL_TIME_UNIT
from .timezones import MARKET_TZ

#: Every column of the table, in canonical order. A frame is validated against this list, so a
#: column that is not here cannot ride along unnoticed into a feature set.
POINT_IN_TIME_COLUMNS = (
    "delivery_start_utc",
    "delivery_end_utc",
    "market_day",
    "source",
    "dataset",
    "variable",
    "area",
    "unit",
    "resolution_minutes",
    "value",
    "published_at_utc",
    "retrieved_at_utc",
    "source_document_id",
    "source_revision",
    "raw_sha256",
    "forecast_issue_time_utc",
    "forecast_horizon_minutes",
    "availability_evidence_grade",
    "availability_evidence_detail",
)

#: Columns that may hold a null. Everything else is required in every row of an accepted table.
#: ``published_at_utc`` is required unless the caller explicitly asks for a quarantine table.
OPTIONAL_POINT_IN_TIME_COLUMNS = frozenset(
    {
        "source_revision",
        "forecast_issue_time_utc",
        "forecast_horizon_minutes",
        "availability_evidence_detail",
    }
)

#: Closed source set, extended only by a reviewed change, exactly as ``SUPPORTED_SOURCES`` is.
#: ``noaa_gfs`` is the one source chosen for v0.9 (decision entry 2026-09-02). ``eex_auction``
#: and ``entsoe_fundamentals`` are named but **unassessed**: neither has had a source-selection
#: spike, and naming a value here admits nothing.
SUPPORTED_FEATURE_SOURCES = frozenset(
    {"noaa_gfs", "eex_auction", "entsoe_fundamentals", "synthetic"}
)

#: The closed variable registry and the unit each variable is stated in. A row whose ``unit``
#: differs from the registry is refused: there is no silent conversion anywhere in this project,
#: and a feature silently rescaled by a factor of a thousand would be indistinguishable from a
#: feature that simply does not help.
VARIABLE_UNITS: dict[str, str] = {
    "dswrf_surface": "W/m2",
    "wind_speed_10m": "m/s",
    "temperature_2m": "K",
}

WITNESSED = "witnessed"
PROVIDER_DECLARED = "provider_declared"
ASSUMED = "assumed"
UNAVAILABLE = "unavailable"

#: All four grades of design section 4.4, in descending strength.
EVIDENCE_GRADES = (WITNESSED, PROVIDER_DECLARED, ASSUMED, UNAVAILABLE)

#: The grades an accepted run may admit. ``assumed`` is quarantined by decision, not by
#: oversight: the source spike found one genuinely late NOAA run that a nominal-latency
#: assumption would have admitted and been wrong about.
ADMISSIBLE_EVIDENCE_GRADES = (WITNESSED, PROVIDER_DECLARED)

#: Native resolutions a feature may be stated at.
SUPPORTED_FEATURE_RESOLUTIONS = frozenset({15, 60, 180, 1440})

#: The uniqueness key. Two rows sharing it are the same observation; if they disagree in any
#: other respect the table is refused rather than de-duplicated to whichever was read first.
UNIQUENESS_KEY = (
    "source",
    "dataset",
    "variable",
    "area",
    "delivery_start_utc",
    "source_document_id",
    "source_revision",
)

#: ``source_revision`` is normalized to a nullable string, because it is an *identity* and not a
#: quantity: nothing arithmetic is done with it, and storing it as a number would make an absent
#: revision read back from CSV as ``NaN`` rather than as absent. Ordering by it is therefore
#: lexicographic, which is only ever a tie-break: the decision-time revision is selected by
#: publication instant first, and two revisions of one datum published at the same instant to
#: the sub-second is not a case any observed source produces.
_REVISION_COLUMN = "source_revision"

#: Fields that must agree for two rows with the same uniqueness key to be one observation.
_IDENTITY_FIELDS = ("value", "raw_sha256", "published_at_utc")

#: Canonical ordering, applied on validation so that a table compares equal regardless of the
#: order its rows were retrieved or concatenated in.
_ORDERING = (
    "delivery_start_utc",
    "variable",
    "area",
    "published_at_utc",
    "source_document_id",
    "source_revision",
)

_TIMESTAMP_COLUMNS = (
    "delivery_start_utc",
    "delivery_end_utc",
    "published_at_utc",
    "retrieved_at_utc",
    "forecast_issue_time_utc",
)


class PointInTimeSchemaError(ValueError):
    """Raised when a point-in-time feature table violates the feature contract."""


def empty_point_in_time_frame() -> pd.DataFrame:
    """Return an empty frame carrying every point-in-time column."""

    return pd.DataFrame(columns=list(POINT_IN_TIME_COLUMNS))


def ensure_point_in_time(
    frame: pd.DataFrame,
    *,
    allow_empty: bool = True,
    require_publication_time: bool = True,
) -> pd.DataFrame:
    """Validate, normalize, de-duplicate and deterministically order a feature table.

    Returns a copy. ``require_publication_time=False`` builds the quarantine table of design
    section 4.5: rows without a publication instant are retained, and every such row must carry
    the :data:`ASSUMED` grade so that nothing downstream can mistake it for evidence.
    """

    missing = [column for column in POINT_IN_TIME_COLUMNS if column not in frame.columns]
    if missing:
        raise PointInTimeSchemaError(
            f"Missing point-in-time columns: {', '.join(missing)}"
        )
    unknown = [column for column in frame.columns if column not in POINT_IN_TIME_COLUMNS]
    if unknown:
        raise PointInTimeSchemaError(
            f"Unknown point-in-time columns: {', '.join(sorted(unknown))}; the feature table is "
            "a closed schema so that an unreviewed column cannot enter a feature set"
        )

    result = frame.loc[:, list(POINT_IN_TIME_COLUMNS)].copy()
    if result.empty:
        if allow_empty:
            return result
        raise PointInTimeSchemaError("Point-in-time feature table is empty")

    for column in _TIMESTAMP_COLUMNS:
        optional = column in ("forecast_issue_time_utc",) or (
            column == "published_at_utc" and not require_publication_time
        )
        result[column] = _as_utc(result[column], column, optional=optional)

    result[_REVISION_COLUMN] = _normalize_revisions(result[_REVISION_COLUMN])
    _validate_strings(result)
    _validate_values(result)
    _validate_intervals(result)
    _validate_units(result)
    _validate_publication_order(result, require_publication_time=require_publication_time)
    _validate_forecast_provenance(result)
    result["market_day"] = _market_days(result)
    result = _deduplicate(result)
    return _order(result)


def read_point_in_time_csv(path: Path, *, require_publication_time: bool = True) -> pd.DataFrame:
    """Read a written feature table back into a validated frame."""

    # `float_precision="round_trip"` rather than the parser default. The default is accurate to
    # within one unit in the last place, which is far below anything meteorological or monetary
    # this project reports — but this table is identified downstream by a SHA-256 over its own
    # values, and a digest does not have a tolerance. Without the exact parser a feature table
    # written, read and written again digests differently from the one the retrieval produced,
    # which would make the v0.9 acceptance gate depend on how many times a table had been
    # copied rather than on what was retrieved.
    frame = pd.read_csv(path, float_precision="round_trip")
    for column in _TIMESTAMP_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
    if "market_day" in frame.columns:
        frame["market_day"] = frame["market_day"].map(_as_date)
    return ensure_point_in_time(frame, require_publication_time=require_publication_time)


def write_point_in_time_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a validated feature table deterministically, via a temporary sibling."""

    if path.suffix.lower() != ".csv":
        raise PointInTimeSchemaError("A point-in-time feature table is written as .csv")
    export = frame.copy()
    export["market_day"] = export["market_day"].map(
        lambda value: value.isoformat() if isinstance(value, date) else value
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    export.to_csv(temporary, index=False)
    temporary.replace(path)


def feature_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Count stored rows per (variable, area, market day, revision-bearing document).

    Coverage is a count of what is present. It never states what is missing as a value: a day
    the provider did not publish and a day this project did not retrieve look identical here and
    are separated by the availability audit, which knows the window that was requested.
    """

    if frame.empty:
        return pd.DataFrame(
            columns=["variable", "area", "market_day", "row_count", "distinct_interval_count"]
        )
    grouped = (
        frame.groupby(["variable", "area", "market_day"], sort=True)
        .agg(
            row_count=("value", "size"),
            distinct_interval_count=("delivery_start_utc", "nunique"),
        )
        .reset_index()
    )
    grouped["market_day"] = grouped["market_day"].map(
        lambda value: value.isoformat() if isinstance(value, date) else value
    )
    return grouped


@dataclass(frozen=True)
class GeographyPoint:
    """One declared sampling point and the weight it carries in the declared aggregate."""

    point_id: str
    latitude: float
    longitude: float
    weight: float

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, str) or not self.point_id.strip():
            raise PointInTimeSchemaError("Every sampling point needs a non-empty point_id")
        for name, value in (("latitude", self.latitude), ("longitude", self.longitude)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PointInTimeSchemaError(f"{name} must be a number")
        if not -90.0 <= float(self.latitude) <= 90.0:
            raise PointInTimeSchemaError("latitude must lie between -90 and 90 degrees")
        if not -180.0 <= float(self.longitude) <= 360.0:
            raise PointInTimeSchemaError("longitude must lie between -180 and 360 degrees")
        if isinstance(self.weight, bool) or not isinstance(self.weight, (int, float)):
            raise PointInTimeSchemaError("weight must be a number")
        if float(self.weight) <= 0.0:
            raise PointInTimeSchemaError(
                f"Sampling point {self.point_id!r} declares a non-positive weight; a point that "
                "contributes nothing is removed from the declaration rather than weighted zero"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "latitude": float(self.latitude),
            "longitude": float(self.longitude),
            "weight": float(self.weight),
        }


@dataclass(frozen=True)
class SamplingGeography:
    """A declared set of sampling points, their weights and the basis for the choice.

    There is no default geography. A gridded variable has a value at every grid node, and which
    nodes represent "Greek demand" or "Greek wind" is a judgment about installed capacity,
    demand density or something else the operator must state. The tooling aggregates exactly as
    declared and cannot check that the declaration represents the bidding zone.
    """

    geography_id: str
    area: str
    points: tuple[GeographyPoint, ...]
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.geography_id, str) or not self.geography_id.strip():
            raise PointInTimeSchemaError("geography_id must be a non-empty string")
        if self.area != "GR":
            raise PointInTimeSchemaError(
                "The MVP samples the Greek bidding zone GR only"
            )
        if not self.points:
            raise PointInTimeSchemaError(
                "A sampling geography must declare at least one point; there is no default"
            )
        identifiers = [point.point_id for point in self.points]
        duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
        if duplicates:
            raise PointInTimeSchemaError(
                f"Duplicate sampling point_id: {', '.join(duplicates)}"
            )
        total = sum(float(point.weight) for point in self.points)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise PointInTimeSchemaError(
                f"Declared sampling weights sum to {total!r}, not 1. A weighted aggregate whose "
                "weights do not sum to one rescales the variable silently"
            )
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise PointInTimeSchemaError(
                "reference must state what the declared points and weights represent"
            )

    @classmethod
    def from_dict(cls, payload: object) -> SamplingGeography:
        if not isinstance(payload, Mapping):
            raise PointInTimeSchemaError("A sampling geography config must be one object")
        required = {"geography_id", "area", "points", "reference"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise PointInTimeSchemaError(f"Unknown geography fields: {', '.join(unknown)}")
        if missing:
            raise PointInTimeSchemaError(f"Missing geography fields: {', '.join(missing)}")
        declared = payload["points"]
        if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
            raise PointInTimeSchemaError("points must be a non-empty list")
        return cls(
            geography_id=str(payload["geography_id"]),
            area=str(payload["area"]),
            points=tuple(_point_from_dict(entry) for entry in declared),
            reference=str(payload["reference"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "geography_id": self.geography_id,
            "area": self.area,
            "points": [point.to_dict() for point in self.points],
            "reference": self.reference,
        }


def read_sampling_geography(path: Path) -> SamplingGeography:
    """Read a declared sampling geography, refusing the committed format example."""

    from .decision_cutoff import (
        EXAMPLE_PLACEHOLDER_IDENTIFIER,
        EXAMPLE_PLACEHOLDER_MARKER,
    )

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    geography = SamplingGeography.from_dict(payload)
    if geography.geography_id == EXAMPLE_PLACEHOLDER_IDENTIFIER:
        raise PointInTimeSchemaError(
            f"{path}: geography_id is still {EXAMPLE_PLACEHOLDER_IDENTIFIER!r}. This is the "
            "committed format example, not a declaration."
        )
    if EXAMPLE_PLACEHOLDER_MARKER in geography.reference:
        raise PointInTimeSchemaError(
            f"{path}: the reference still carries the {EXAMPLE_PLACEHOLDER_MARKER!r} "
            "placeholder. State what the points and weights represent, and the vintage of that "
            "basis; there is no default geography."
        )
    return geography


def _point_from_dict(payload: object) -> GeographyPoint:
    if not isinstance(payload, Mapping):
        raise PointInTimeSchemaError("Every sampling point must be an object")
    required = {"point_id", "latitude", "longitude", "weight"}
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown:
        raise PointInTimeSchemaError(f"Unknown sampling point fields: {', '.join(unknown)}")
    if missing:
        raise PointInTimeSchemaError(f"Missing sampling point fields: {', '.join(missing)}")
    return GeographyPoint(
        point_id=str(payload["point_id"]),
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        weight=float(payload["weight"]),
    )


def _as_utc(series: pd.Series, name: str, *, optional: bool) -> pd.Series:
    if series.isna().all() and optional:
        return pd.to_datetime(pd.Series([pd.NaT] * len(series), index=series.index), utc=True)
    naive = [
        value
        for value in series.dropna()
        if isinstance(value, pd.Timestamp) and value.tzinfo is None
    ]
    if naive:
        raise PointInTimeSchemaError(
            f"{name} must be timezone aware; a naive instant cannot be compared with a declared "
            "decision cutoff"
        )
    parsed = pd.to_datetime(series, utc=True, errors="coerce")
    invalid = parsed.isna() & series.notna()
    if invalid.any():
        raise PointInTimeSchemaError(f"{name} contains invalid timestamps")
    if not optional and parsed.isna().any():
        count = int(parsed.isna().sum())
        raise PointInTimeSchemaError(
            f"{name} is absent on {count} row(s). A value whose publication instant is unknown "
            "cannot enter an accepted feature table; build a quarantine table explicitly if the "
            "row is to be retained at all"
        )
    return parsed.dt.as_unit(CANONICAL_TIME_UNIT)


def _normalize_revisions(series: pd.Series) -> pd.Series:
    return pd.Series(
        [
            pd.NA
            if value is None or value is pd.NA or (isinstance(value, float) and math.isnan(value))
            else str(value)
            for value in series
        ],
        index=series.index,
        dtype="string",
    )


def _validate_strings(frame: pd.DataFrame) -> None:
    for column in ("source", "dataset", "variable", "area", "unit", "source_document_id",
                   "raw_sha256", "availability_evidence_grade"):
        if frame[column].isna().any():
            raise PointInTimeSchemaError(f"{column} is required on every row")
        frame[column] = frame[column].astype(str)
        blank = frame[column].str.strip() != frame[column]
        if blank.any() or (frame[column] == "").any():
            raise PointInTimeSchemaError(f"{column} must be a non-empty trimmed string")

    unsupported = sorted(set(frame["source"]) - SUPPORTED_FEATURE_SOURCES)
    if unsupported:
        raise PointInTimeSchemaError(f"Unsupported feature sources: {unsupported}")
    unregistered = sorted(set(frame["variable"]) - set(VARIABLE_UNITS))
    if unregistered:
        raise PointInTimeSchemaError(
            f"Unregistered feature variables: {unregistered}. The variable registry is closed, "
            "so a realized target-day quantity cannot be smuggled in under a new name"
        )
    grades = sorted(set(frame["availability_evidence_grade"]) - set(EVIDENCE_GRADES))
    if grades:
        raise PointInTimeSchemaError(f"Unknown availability evidence grades: {grades}")
    digests = frame["raw_sha256"].str.fullmatch(r"[0-9a-f]{64}")
    if not bool(digests.all()):
        raise PointInTimeSchemaError(
            "raw_sha256 must be a lowercase hexadecimal SHA-256 of the exact bytes the value "
            "was decoded from"
        )


def _validate_values(frame: pd.DataFrame) -> None:
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    if not bool(frame["value"].map(lambda value: bool(pd.notna(value))).all()):
        raise PointInTimeSchemaError(
            "value contains a missing entry. A missing feature value is an absent row, never a "
            "NaN: a NaN would reach a fit as a number-shaped hole"
        )
    if not bool(frame["value"].map(math.isfinite).all()):
        raise PointInTimeSchemaError("value must be finite")

    frame["resolution_minutes"] = pd.to_numeric(frame["resolution_minutes"], errors="raise")
    fractional = frame["resolution_minutes"].map(lambda value: float(value) != int(value))
    if bool(fractional.any()):
        raise PointInTimeSchemaError("resolution_minutes must be a whole number of minutes")
    unsupported = sorted(
        {int(value) for value in frame["resolution_minutes"]} - SUPPORTED_FEATURE_RESOLUTIONS
    )
    if unsupported:
        raise PointInTimeSchemaError(f"Unsupported feature resolutions: {unsupported}")
    frame["resolution_minutes"] = frame["resolution_minutes"].astype(int)


def _validate_intervals(frame: pd.DataFrame) -> None:
    non_positive = frame["delivery_end_utc"] <= frame["delivery_start_utc"]
    if bool(non_positive.any()):
        raise PointInTimeSchemaError("Every delivery interval must have a positive duration")
    declared = pd.to_timedelta(frame["resolution_minutes"], unit="min")
    measured = frame["delivery_end_utc"] - frame["delivery_start_utc"]
    if not bool(measured.eq(declared).all()):
        raise PointInTimeSchemaError(
            "resolution_minutes disagrees with the delivery interval it describes"
        )


def _validate_units(frame: pd.DataFrame) -> None:
    expected = frame["variable"].map(VARIABLE_UNITS)
    mismatched = frame.loc[expected != frame["unit"]]
    if not mismatched.empty:
        row = mismatched.iloc[0]
        raise PointInTimeSchemaError(
            f"Variable {row['variable']!r} is registered in {VARIABLE_UNITS[row['variable']]!r} "
            f"but the row for {row['delivery_start_utc']} declares {row['unit']!r}; there is no "
            "silent unit conversion"
        )


def _validate_publication_order(frame: pd.DataFrame, *, require_publication_time: bool) -> None:
    known = frame["published_at_utc"].notna()
    late = known & (frame["published_at_utc"] > frame["retrieved_at_utc"])
    if bool(late.any()):
        row = frame.loc[late].iloc[0]
        raise PointInTimeSchemaError(
            f"{row['source_document_id']}: published_at_utc {row['published_at_utc']} is later "
            f"than retrieved_at_utc {row['retrieved_at_utc']}; a datum cannot be retrieved "
            "before it was published"
        )
    if require_publication_time:
        return
    ungraded = frame.loc[~known & (frame["availability_evidence_grade"] != ASSUMED)]
    if not ungraded.empty:
        raise PointInTimeSchemaError(
            f"{len(ungraded)} quarantined row(s) have no publication instant but do not carry "
            f"the {ASSUMED!r} grade. Availability inferred rather than observed is graded as "
            "inferred, so nothing downstream can mistake it for evidence"
        )


def _validate_forecast_provenance(frame: pd.DataFrame) -> None:
    issued = frame["forecast_issue_time_utc"].notna()
    known = issued & frame["published_at_utc"].notna()
    after = known & (frame["forecast_issue_time_utc"] > frame["published_at_utc"])
    if bool(after.any()):
        raise PointInTimeSchemaError(
            "forecast_issue_time_utc must not be later than published_at_utc; a model cycle "
            "cannot run after the datum it produced was published"
        )
    expected = (
        (frame["delivery_start_utc"] - frame["forecast_issue_time_utc"]).dt.total_seconds() / 60.0
    )
    declared = pd.to_numeric(frame["forecast_horizon_minutes"], errors="coerce")
    supplied = declared.notna()
    disagreeing = issued & supplied & (declared != expected)
    if bool(disagreeing.any()):
        raise PointInTimeSchemaError(
            "forecast_horizon_minutes disagrees with delivery_start_utc minus "
            "forecast_issue_time_utc; it is derived and verified, never independently supplied"
        )
    orphaned = ~issued & supplied
    if bool(orphaned.any()):
        raise PointInTimeSchemaError(
            "forecast_horizon_minutes is recorded without a forecast_issue_time_utc to measure "
            "it from"
        )
    frame["forecast_horizon_minutes"] = expected.where(issued).astype("Float64")


def _market_days(frame: pd.DataFrame) -> pd.Series:
    derived = frame["delivery_start_utc"].dt.tz_convert(MARKET_TZ).dt.date
    supplied = frame["market_day"].map(_as_date)
    stated = supplied.notna()
    if bool(stated.any()) and not bool((supplied[stated] == derived[stated]).all()):
        raise PointInTimeSchemaError(
            "market_day disagrees with the CET/CEST date of delivery_start_utc; it is derived "
            "from the interval, then verified, and never supplied on its own"
        )
    return derived


def _as_date(value: object) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return pd.NA
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date()
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise PointInTimeSchemaError(f"market_day must be an ISO date, not {value!r}") from exc


def _deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    keys = [frame[column].astype(str) for column in UNIQUENESS_KEY]
    signature = pd.Series(list(zip(*keys, strict=True)), index=frame.index)
    identity = pd.Series(
        [
            tuple(str(frame.at[index, column]) for column in _IDENTITY_FIELDS)
            for index in frame.index
        ],
        index=frame.index,
    )
    conflicts: list[str] = []
    seen: dict[tuple[str, ...], tuple[str, ...]] = {}
    keep: list[Any] = []
    for index in frame.index:
        key = signature.at[index]
        incumbent = seen.get(key)
        if incumbent is None:
            seen[key] = identity.at[index]
            keep.append(index)
            continue
        if incumbent != identity.at[index]:
            conflicts.append(
                f"{key[2]} {key[4]} from {key[5]!r} revision {key[6]!r}: "
                f"{dict(zip(_IDENTITY_FIELDS, incumbent, strict=True))} and "
                f"{dict(zip(_IDENTITY_FIELDS, identity.at[index], strict=True))}"
            )
    if conflicts:
        raise PointInTimeSchemaError(
            "Two rows share a uniqueness key but disagree, so one of them is wrong and the "
            "table refuses to choose: " + "; ".join(conflicts[:5])
        )
    return frame.loc[keep]


def _order(frame: pd.DataFrame) -> pd.DataFrame:
    ordering = frame.copy()
    ordering["_revision_sort"] = ordering[_REVISION_COLUMN].fillna("")
    columns = [
        column if column != _REVISION_COLUMN else "_revision_sort" for column in _ORDERING
    ]
    ordered = ordering.sort_values(columns, kind="stable").drop(columns="_revision_sort")
    return ordered.reset_index(drop=True)
