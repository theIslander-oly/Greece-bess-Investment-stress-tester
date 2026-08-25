"""Canonical interval schema shared by all market-data sources."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


CANONICAL_COLUMNS = [
    "delivery_start_utc",
    "delivery_end_utc",
    "delivery_start_market",
    "delivery_start_greece",
    "duration_hours",
    "price_eur_per_mwh",
    "bidding_zone",
    "source",
    "source_version",
    "retrieved_at_utc",
    "raw_sha256",
    "quality_flags",
]

SUPPORTED_SOURCES = frozenset({"entsoe", "henex", "synthetic"})
SUPPORTED_DURATIONS_HOURS = frozenset({0.25, 1.0})


class CanonicalSchemaError(ValueError):
    """Raised when normalized market data violates the canonical schema."""


def empty_canonical_frame() -> pd.DataFrame:
    """Return an empty frame with all required canonical columns."""

    return pd.DataFrame(columns=CANONICAL_COLUMNS)


def ensure_canonical(frame: pd.DataFrame, *, allow_empty: bool = True) -> pd.DataFrame:
    """Validate, normalize and deterministically order a canonical data frame.

    The function returns a copy. It never silently removes duplicates or fills
    missing prices; those decisions belong in the quality layer.
    """

    missing = [column for column in CANONICAL_COLUMNS if column not in frame.columns]
    if missing:
        raise CanonicalSchemaError(f"Missing canonical columns: {', '.join(missing)}")

    result = frame.loc[:, CANONICAL_COLUMNS].copy()
    if result.empty:
        if allow_empty:
            return result
        raise CanonicalSchemaError("Canonical frame is empty")

    result["delivery_start_utc"] = _as_utc(result["delivery_start_utc"], "delivery_start_utc")
    result["delivery_end_utc"] = _as_utc(result["delivery_end_utc"], "delivery_end_utc")
    result["retrieved_at_utc"] = _as_utc(result["retrieved_at_utc"], "retrieved_at_utc")

    for column in ("delivery_start_market", "delivery_start_greece"):
        if not isinstance(result[column].dtype, pd.DatetimeTZDtype):
            raise CanonicalSchemaError(f"{column} must be timezone-aware")

    result["duration_hours"] = pd.to_numeric(result["duration_hours"], errors="raise")
    result["price_eur_per_mwh"] = pd.to_numeric(result["price_eur_per_mwh"], errors="coerce")

    invalid_duration = ~result["duration_hours"].isin(SUPPORTED_DURATIONS_HOURS)
    if invalid_duration.any():
        values = sorted(result.loc[invalid_duration, "duration_hours"].unique().tolist())
        raise CanonicalSchemaError(f"Unsupported interval durations: {values}")

    non_positive = result["delivery_end_utc"] <= result["delivery_start_utc"]
    if non_positive.any():
        raise CanonicalSchemaError("Every delivery interval must have a positive duration")

    calculated_duration = (
        result["delivery_end_utc"] - result["delivery_start_utc"]
    ).dt.total_seconds() / 3600
    if not calculated_duration.round(9).equals(result["duration_hours"].round(9)):
        raise CanonicalSchemaError("duration_hours disagrees with interval timestamps")

    invalid_sources = sorted(set(result["source"].dropna()) - SUPPORTED_SOURCES)
    if invalid_sources:
        raise CanonicalSchemaError(f"Unsupported sources: {invalid_sources}")

    if not result["bidding_zone"].eq("GR").all():
        raise CanonicalSchemaError("The MVP accepts only the Greek bidding zone GR")

    result["quality_flags"] = result["quality_flags"].map(_normalize_flags)
    return result.sort_values("delivery_start_utc", kind="stable").reset_index(drop=True)


def _as_utc(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, utc=True, errors="coerce")
    if parsed.isna().any():
        raise CanonicalSchemaError(f"{name} contains invalid timestamps")
    return parsed


def _normalize_flags(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Iterable):
        return sorted({str(item) for item in value if str(item)})
    return [str(value)]

