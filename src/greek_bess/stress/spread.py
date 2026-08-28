"""Deterministic spread-compression transformations for synthetic bootstrap paths.

A spread compression pulls every interval of a market day toward that day's reference level:

    compressed(t) = reference(d) + factor * (price(t) - reference(d))

where ``d`` is the CET/CEST market day containing interval ``t``. A factor of 1.0 is the
identity; a factor of 0.0 flattens the day onto its reference level. The transformation is a
declared judgmental scenario about spread, not an estimated price process, and carries no
probability.

This is the economically first-order stress for storage. A constant additive level shift
leaves every within-day spread unchanged and therefore alters arbitrage economics only through
round-trip efficiency losses and per-MWh fees; compressing the spread changes the quantity a
battery actually earns from.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from ._paths import validate_bootstrap_paths

REFERENCE_BASES = ("daily_mean", "daily_median")

SPREAD_COMPRESSION_POLICY = (
    "A spread compression pulls each market day's prices toward a declared daily reference "
    "level by a declared factor in [0, 1]. There is no default reference basis and no default "
    "factor: both are judgmental scenario inputs and must be stated. Compression preserves "
    "zero and negative prices as valid results and never clips them, so an interval's sign can "
    "change when it is pulled across the reference level; the count of such intervals is "
    "reported rather than suppressed. Spread widening (a factor above 1) is out of scope."
)


class SpreadCompressionInputError(ValueError):
    """Raised when a spread compression cannot be applied audibly and safely."""


@dataclass(frozen=True)
class SpreadCompressionConfig:
    """A declared compression of within-day spread about a declared daily reference level."""

    compression_factor: float
    reference_basis: str
    transformation_id: str

    def __post_init__(self) -> None:
        if isinstance(self.compression_factor, bool) or not isinstance(
            self.compression_factor, (int, float)
        ):
            raise SpreadCompressionInputError("compression_factor must be a finite number")
        factor = float(self.compression_factor)
        if not math.isfinite(factor):
            raise SpreadCompressionInputError("compression_factor must be a finite number")
        if not 0.0 <= factor <= 1.0:
            raise SpreadCompressionInputError(
                "compression_factor must be between 0.0 and 1.0 inclusive; "
                "spread widening is out of scope"
            )
        if self.reference_basis not in REFERENCE_BASES:
            raise SpreadCompressionInputError(
                "reference_basis must be declared as one of: " + ", ".join(REFERENCE_BASES)
            )
        if not isinstance(self.transformation_id, str) or not self.transformation_id.strip():
            raise SpreadCompressionInputError("transformation_id must be a non-empty string")
        if self.transformation_id != self.transformation_id.strip():
            raise SpreadCompressionInputError(
                "transformation_id must not have surrounding whitespace"
            )

    @classmethod
    def from_dict(cls, payload: object) -> SpreadCompressionConfig:
        """Parse a strict JSON-compatible configuration object."""

        if not isinstance(payload, dict):
            raise SpreadCompressionInputError("Spread compression config must contain one object")
        required = {"compression_factor", "reference_basis", "transformation_id"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise SpreadCompressionInputError(
                f"Unknown spread compression config fields: {', '.join(unknown)}"
            )
        if missing:
            raise SpreadCompressionInputError(
                f"Missing spread compression config fields: {', '.join(missing)}"
            )
        return cls(**payload)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SpreadCompressionResult:
    """Compressed canonical paths, interval audit trail and method summary."""

    paths: pd.DataFrame
    provenance: pd.DataFrame
    summary: dict[str, object]


def apply_spread_compression(
    bootstrap_paths: pd.DataFrame, config: SpreadCompressionConfig
) -> SpreadCompressionResult:
    """Compress within-day spread about each market day's declared reference level.

    Zero and negative results are preserved: values are neither clipped nor floored, so an
    interval pulled across its day's reference level changes sign. That is a real consequence
    of the transformation and is counted in the summary rather than suppressed. The
    transformation has no random component, so identical input and configuration produce
    identical output and interval provenance.
    """

    paths = validate_bootstrap_paths(bootstrap_paths, SpreadCompressionInputError)
    original = paths["price_eur_per_mwh"].astype(float)
    if original.isna().any():
        raise SpreadCompressionInputError(
            "Bootstrap path prices must not be missing; a missing price would propagate "
            "through its market day's reference level"
        )
    if not original.map(math.isfinite).all():
        raise SpreadCompressionInputError("Bootstrap path prices must all be finite")

    factor = float(config.compression_factor)
    market_day = paths["delivery_start_market"].dt.date
    grouped = original.groupby([paths["path_id"], market_day])
    reference = (
        grouped.transform("mean")
        if config.reference_basis == "daily_mean"
        else grouped.transform("median")
    )
    compressed = reference + factor * (original - reference)
    if not compressed.map(math.isfinite).all():
        raise SpreadCompressionInputError("Compressed prices must all be finite")

    result = paths.copy()
    result["price_eur_per_mwh"] = compressed
    result["source_version"] = (
        result["source_version"]
        .astype(str)
        .map(lambda value: f"{value}|spread_compression:{config.transformation_id}")
    )
    result["quality_flags"] = result["quality_flags"].map(
        lambda flags: sorted(set(flags) | {"spread_compression", "synthetic_not_forecast"})
    )

    provenance = pd.DataFrame(
        {
            "path_id": paths["path_id"],
            "delivery_start_utc": paths["delivery_start_utc"],
            "market_day": market_day.astype(str),
            "transformation_id": config.transformation_id,
            "method": "spread_compression_about_daily_reference",
            "compression_factor": factor,
            "reference_basis": config.reference_basis,
            "reference_level_eur_per_mwh": reference,
            "original_price_eur_per_mwh": original,
            "compressed_price_eur_per_mwh": compressed,
            "input_source": paths["source"],
            "input_source_version": paths["source_version"],
        }
    )
    summary = _summary(paths, original, compressed, reference, market_day, config)
    return SpreadCompressionResult(result, provenance, summary)


def _summary(
    paths: pd.DataFrame,
    original: pd.Series,
    compressed: pd.Series,
    reference: pd.Series,
    market_day: pd.Series,
    config: SpreadCompressionConfig,
) -> dict[str, object]:
    """Aggregate the evidence a reader needs to judge what the compression did."""

    keys = [paths["path_id"], market_day]
    before = original.groupby(keys)
    after = compressed.groupby(keys)
    range_before = before.max() - before.min()
    range_after = after.max() - after.min()
    mean_before = before.mean()
    mean_after = after.mean()

    crossed_down = (original > 0) & (compressed < 0)
    crossed_up = (original < 0) & (compressed > 0)
    sign_changes = int(crossed_down.sum() + crossed_up.sum())
    return {
        "result_label": (
            "synthetic spread-compressed bootstrap paths; not forecasts, probabilities or "
            "investment evidence"
        ),
        "method": "deterministic spread compression about a declared daily reference level",
        "policy": SPREAD_COMPRESSION_POLICY,
        "configuration": config.to_dict(),
        "path_count": int(paths["path_id"].nunique()),
        "interval_count": int(len(paths)),
        "market_day_count": int(market_day.nunique()),
        "path_market_day_count": int(len(range_before)),
        "provenance_row_count": int(len(paths)),
        "mean_daily_range_before_eur_per_mwh": float(range_before.mean()),
        "mean_daily_range_after_eur_per_mwh": float(range_after.mean()),
        "max_daily_range_before_eur_per_mwh": float(range_before.max()),
        "max_daily_range_after_eur_per_mwh": float(range_after.max()),
        "max_absolute_daily_mean_shift_eur_per_mwh": float((mean_after - mean_before).abs().max()),
        "negative_interval_count_before": int((original < 0).sum()),
        "negative_interval_count_after": int((compressed < 0).sum()),
        "zero_interval_count_before": int((original == 0).sum()),
        "zero_interval_count_after": int((compressed == 0).sum()),
        "sign_change_interval_count": sign_changes,
        "reference_level_min_eur_per_mwh": float(reference.min()),
        "reference_level_max_eur_per_mwh": float(reference.max()),
    }
