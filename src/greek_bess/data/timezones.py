"""Timezone and market-interval helpers.

UTC is canonical. Europe/Brussels represents the CET/CEST market clock used
by coupled-market publications; Europe/Athens is retained for Greek display.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd


UTC = ZoneInfo("UTC")
MARKET_TZ = ZoneInfo("Europe/Brussels")
GREECE_TZ = ZoneInfo("Europe/Athens")

_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_iso_duration(value: str) -> timedelta:
    """Parse the day/hour/minute/second subset used by ENTSO-E resolutions."""

    match = _DURATION_RE.fullmatch(value.strip().upper())
    if not match:
        raise ValueError(f"Unsupported ISO-8601 duration: {value!r}")
    parts = {name: int(raw or 0) for name, raw in match.groupdict().items()}
    duration = timedelta(**parts)
    if duration <= timedelta(0):
        raise ValueError(f"Duration must be positive: {value!r}")
    return duration


def as_utc_timestamp(value: datetime | str | pd.Timestamp) -> pd.Timestamp:
    """Convert a timezone-aware value to a pandas UTC timestamp."""

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return timestamp.tz_convert(UTC)


def market_day_starts(delivery_day: date, duration_minutes: int) -> pd.DatetimeIndex:
    """Return every real MTU start for a CET/CEST market day.

    Building the range between two localized midnights naturally yields 23/25
    hourly intervals and 92/100 quarter-hour intervals at DST transitions.
    """

    if duration_minutes not in (15, 60):
        raise ValueError("Only 15-minute and 60-minute MTUs are supported")
    start = pd.Timestamp(delivery_day).tz_localize(MARKET_TZ)
    end = pd.Timestamp(delivery_day + timedelta(days=1)).tz_localize(MARKET_TZ)
    return pd.date_range(start=start, end=end, freq=f"{duration_minutes}min", inclusive="left")


def expected_interval_count(delivery_day: date, duration_minutes: int) -> int:
    return len(market_day_starts(delivery_day, duration_minutes))


def local_views(starts_utc: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Produce market-clock and Greek-local views from canonical UTC starts."""

    utc = pd.to_datetime(starts_utc, utc=True)
    return utc.dt.tz_convert(MARKET_TZ), utc.dt.tz_convert(GREECE_TZ)

