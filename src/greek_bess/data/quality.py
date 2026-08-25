"""Auditable quality checks and official-source comparisons."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import numpy as np
import pandas as pd

from .schema import CanonicalSchemaError, ensure_canonical
from .timezones import UTC, market_day_starts


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    count: int = 1
    sample: tuple[str, ...] = ()


@dataclass
class QualityReport:
    row_count: int
    first_interval_utc: str | None
    last_interval_utc: str | None
    negative_price_count: int
    zero_price_count: int
    missing_price_count: int
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["is_valid"] = self.is_valid
        return payload


def assess_quality(
    frame: pd.DataFrame,
    *,
    require_complete_days: bool = True,
) -> QualityReport:
    """Assess schema, duplicates, prices, resolution and daily completeness."""

    issues: list[QualityIssue] = []
    try:
        data = ensure_canonical(frame)
    except CanonicalSchemaError as exc:
        return QualityReport(
            row_count=len(frame),
            first_interval_utc=None,
            last_interval_utc=None,
            negative_price_count=0,
            zero_price_count=0,
            missing_price_count=0,
            issues=[QualityIssue("error", "canonical_schema", str(exc))],
        )

    if data.empty:
        return QualityReport(
            row_count=0,
            first_interval_utc=None,
            last_interval_utc=None,
            negative_price_count=0,
            zero_price_count=0,
            missing_price_count=0,
            issues=[QualityIssue("error", "empty_dataset", "Dataset contains no intervals")],
        )

    duplicate_mask = data.duplicated(
        subset=["delivery_start_utc", "bidding_zone"], keep=False
    )
    if duplicate_mask.any():
        samples = tuple(
            data.loc[duplicate_mask, "delivery_start_utc"].astype(str).head(5).tolist()
        )
        issues.append(
            QualityIssue(
                "error",
                "duplicate_interval",
                "Multiple rows exist for the same UTC delivery interval",
                int(duplicate_mask.sum()),
                samples,
            )
        )

    if len(data) > 1:
        expected_next = data["delivery_end_utc"].iloc[:-1].reset_index(drop=True)
        actual_next = data["delivery_start_utc"].iloc[1:].reset_index(drop=True)
        discontinuity = ~actual_next.eq(expected_next)
        if discontinuity.any():
            sample_positions = np.flatnonzero(discontinuity.to_numpy())[:5]
            samples = tuple(
                f"{expected_next.iloc[position]} -> {actual_next.iloc[position]}"
                for position in sample_positions
            )
            issues.append(
                QualityIssue(
                    "error",
                    "non_contiguous_horizon",
                    "Consecutive UTC delivery intervals contain a gap or overlap",
                    int(discontinuity.sum()),
                    samples,
                )
            )
    missing_price = data["price_eur_per_mwh"].isna()
    if missing_price.any():
        issues.append(
            QualityIssue(
                "error",
                "missing_price",
                "Intervals with missing prices must not be optimized",
                int(missing_price.sum()),
                tuple(data.loc[missing_price, "delivery_start_utc"].astype(str).head(5)),
            )
        )

    interval_hours = (
        data["delivery_end_utc"] - data["delivery_start_utc"]
    ).dt.total_seconds() / 3600
    duration_mismatch = ~interval_hours.round(9).eq(data["duration_hours"].round(9))
    if duration_mismatch.any():
        issues.append(
            QualityIssue(
                "error",
                "duration_mismatch",
                "Timestamp duration differs from duration_hours",
                int(duration_mismatch.sum()),
            )
        )

    data = data.assign(market_day=data["delivery_start_market"].dt.date)
    for delivery_day, day_frame in data.groupby("market_day", sort=True):
        durations = sorted(day_frame["duration_hours"].unique().tolist())
        if len(durations) != 1:
            issues.append(
                QualityIssue(
                    "error",
                    "mixed_daily_resolution",
                    f"{delivery_day} contains multiple MTU durations: {durations}",
                    len(day_frame),
                )
            )
            continue
        if require_complete_days:
            duration_minutes = int(round(durations[0] * 60))
            expected_market = market_day_starts(delivery_day, duration_minutes)
            expected_utc = set(expected_market.tz_convert(UTC))
            actual_utc = set(day_frame["delivery_start_utc"])
            missing = sorted(expected_utc - actual_utc)
            unexpected = sorted(actual_utc - expected_utc)
            if missing:
                issues.append(
                    QualityIssue(
                        "error",
                        "incomplete_market_day",
                        f"{delivery_day} is missing {len(missing)} expected interval(s)",
                        len(missing),
                        tuple(str(item) for item in missing[:5]),
                    )
                )
            if unexpected:
                issues.append(
                    QualityIssue(
                        "error",
                        "unexpected_market_interval",
                        f"{delivery_day} contains {len(unexpected)} unexpected interval(s)",
                        len(unexpected),
                        tuple(str(item) for item in unexpected[:5]),
                    )
                )

    negative_count = int(data["price_eur_per_mwh"].lt(0).sum())
    zero_count = int(data["price_eur_per_mwh"].eq(0).sum())
    if negative_count:
        issues.append(
            QualityIssue(
                "info",
                "negative_prices_present",
                "Negative prices are valid and have been preserved",
                negative_count,
            )
        )

    return QualityReport(
        row_count=len(data),
        first_interval_utc=str(data["delivery_start_utc"].min()),
        last_interval_utc=str(data["delivery_start_utc"].max()),
        negative_price_count=negative_count,
        zero_price_count=zero_count,
        missing_price_count=int(missing_price.sum()),
        issues=issues,
    )


def compare_sources(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    tolerance_eur_per_mwh: float = 1e-6,
) -> pd.DataFrame:
    """Outer-join two normalized sources and classify interval-level agreement."""

    if tolerance_eur_per_mwh < 0:
        raise ValueError("tolerance_eur_per_mwh cannot be negative")
    left_data = ensure_canonical(left)
    right_data = ensure_canonical(right)
    if left_data.empty or right_data.empty:
        raise ValueError("Both sources must contain data")

    left_name = _single_source(left_data, "left")
    right_name = _single_source(right_data, "right")
    if left_name == right_name:
        raise ValueError("Cross-source comparison requires two different sources")
    keys = ["delivery_start_utc", "duration_hours"]
    left_view = left_data[keys + ["price_eur_per_mwh", "source_version"]].rename(
        columns={
            "price_eur_per_mwh": f"price_{left_name}",
            "source_version": f"version_{left_name}",
        }
    )
    right_view = right_data[keys + ["price_eur_per_mwh", "source_version"]].rename(
        columns={
            "price_eur_per_mwh": f"price_{right_name}",
            "source_version": f"version_{right_name}",
        }
    )
    merged = left_view.merge(right_view, on=keys, how="outer", validate="one_to_one")
    left_price = merged[f"price_{left_name}"]
    right_price = merged[f"price_{right_name}"]
    merged["difference_eur_per_mwh"] = right_price - left_price

    both = left_price.notna() & right_price.notna()
    merged["comparison_status"] = "match"
    merged.loc[left_price.isna(), "comparison_status"] = f"missing_{left_name}"
    merged.loc[right_price.isna(), "comparison_status"] = f"missing_{right_name}"
    mismatch = both & merged["difference_eur_per_mwh"].abs().gt(tolerance_eur_per_mwh)
    merged.loc[mismatch, "comparison_status"] = "price_mismatch"
    return merged.sort_values("delivery_start_utc", kind="stable").reset_index(drop=True)


def _single_source(frame: pd.DataFrame, side: str) -> str:
    sources = frame["source"].dropna().unique().tolist()
    if len(sources) != 1:
        raise ValueError(f"{side} frame must contain exactly one source, found {sources}")
    return str(sources[0])
