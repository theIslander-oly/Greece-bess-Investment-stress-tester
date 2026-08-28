"""Deterministic synthetic prices for public demos and automated tests only."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .schema import ensure_canonical
from .timezones import GREECE_TZ, UTC, market_day_starts


def generate_synthetic_prices(
    start_day: date,
    end_day: date,
    *,
    resolution_minutes: int = 60,
    seed: int = 42,
    negative_price_share: float = 0.02,
) -> pd.DataFrame:
    """Generate a labelled, non-official Greek-shaped DAM series.

    `end_day` is exclusive. The generator preserves real CET/CEST market-day
    lengths but does not reproduce or estimate any specific official prices.
    """

    if end_day <= start_day:
        raise ValueError("end_day must be later than start_day")
    if resolution_minutes not in (15, 60):
        raise ValueError("resolution_minutes must be 15 or 60")
    if not 0 <= negative_price_share <= 0.25:
        raise ValueError("negative_price_share must be between 0 and 0.25")

    rng = np.random.default_rng(seed)
    market_starts: list[pd.Timestamp] = []
    cursor = start_day
    while cursor < end_day:
        market_starts.extend(market_day_starts(cursor, resolution_minutes).tolist())
        cursor += timedelta(days=1)

    starts = pd.DatetimeIndex(market_starts)
    hour = starts.hour.to_numpy(dtype=float) + starts.minute.to_numpy(dtype=float) / 60
    weekday = starts.dayofweek.to_numpy()
    evening_peak = 34 * np.exp(-0.5 * ((hour - 19.5) / 2.2) ** 2)
    morning_peak = 14 * np.exp(-0.5 * ((hour - 8.5) / 2.8) ** 2)
    solar_dip = 23 * np.exp(-0.5 * ((hour - 13.5) / 2.4) ** 2)
    weekend = np.where(weekday >= 5, -8.0, 0.0)
    noise = rng.normal(0, 7, len(starts))
    prices = 68 + evening_peak + morning_peak - solar_dip + weekend + noise

    negative_count = int(round(len(prices) * negative_price_share))
    if negative_count:
        lowest = np.argpartition(prices, negative_count - 1)[:negative_count]
        prices[lowest] = -rng.uniform(1, 35, negative_count)

    starts_utc = starts.tz_convert(UTC)
    duration = pd.Timedelta(resolution_minutes, unit="min")
    retrieved = pd.Timestamp.now(tz=UTC)
    frame = pd.DataFrame(
        {
            "delivery_start_utc": starts_utc,
            "delivery_end_utc": starts_utc + duration,
            "delivery_start_market": starts,
            "delivery_start_greece": starts_utc.tz_convert(GREECE_TZ),
            "duration_hours": resolution_minutes / 60,
            "price_eur_per_mwh": prices.round(6),
            "bidding_zone": "GR",
            "source": "synthetic",
            "source_version": f"generator-v1-seed-{seed}",
            "retrieved_at_utc": retrieved,
            "raw_sha256": "synthetic-no-official-source",
            "quality_flags": [["synthetic_demo_data"] for _ in range(len(starts))],
        }
    )
    return ensure_canonical(frame)
