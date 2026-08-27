"""Deterministic additive price-level shocks for synthetic bootstrap paths."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import CANONICAL_COLUMNS, ensure_canonical


class PriceLevelShockInputError(ValueError):
    """Raised when a price-level shock cannot be applied audibly and safely."""


@dataclass(frozen=True)
class PriceLevelShockConfig:
    """An additive, constant EUR/MWh shift applied to every path interval."""

    shift_eur_per_mwh: float
    transformation_id: str

    def __post_init__(self) -> None:
        if isinstance(self.shift_eur_per_mwh, bool) or not isinstance(
            self.shift_eur_per_mwh, (int, float)
        ):
            raise PriceLevelShockInputError("shift_eur_per_mwh must be a finite number")
        if not math.isfinite(float(self.shift_eur_per_mwh)):
            raise PriceLevelShockInputError("shift_eur_per_mwh must be a finite number")
        if not isinstance(self.transformation_id, str) or not self.transformation_id.strip():
            raise PriceLevelShockInputError("transformation_id must be a non-empty string")
        if self.transformation_id != self.transformation_id.strip():
            raise PriceLevelShockInputError(
                "transformation_id must not have surrounding whitespace"
            )

    @classmethod
    def from_dict(cls, payload: object) -> PriceLevelShockConfig:
        """Parse a strict JSON-compatible configuration object."""

        if not isinstance(payload, dict):
            raise PriceLevelShockInputError("Price-level shock config must contain one object")
        required = {"shift_eur_per_mwh", "transformation_id"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise PriceLevelShockInputError(
                f"Unknown price-level shock config fields: {', '.join(unknown)}"
            )
        if missing:
            raise PriceLevelShockInputError(
                f"Missing price-level shock config fields: {', '.join(missing)}"
            )
        return cls(**payload)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PriceLevelShockResult:
    """Shocked canonical paths, interval audit trail and method summary."""

    paths: pd.DataFrame
    provenance: pd.DataFrame
    summary: dict[str, object]


def apply_price_level_shock(
    bootstrap_paths: pd.DataFrame, config: PriceLevelShockConfig
) -> PriceLevelShockResult:
    """Add one configured constant to every validated bootstrap-path price.

    This intentionally preserves zero and negative *results*: values are neither clipped nor
    floored. The transformation has no random component, so identical input and configuration
    produce identical output and interval provenance.
    """

    paths = _validated_paths(bootstrap_paths)
    original = paths["price_eur_per_mwh"].astype(float)
    shocked = original + float(config.shift_eur_per_mwh)
    if not shocked.map(math.isfinite).all():
        raise PriceLevelShockInputError("Shocked prices must all be finite")

    result = paths.copy()
    result["price_eur_per_mwh"] = shocked
    result["source_version"] = (
        result["source_version"]
        .astype(str)
        .map(lambda value: f"{value}|price_level:{config.transformation_id}")
    )
    result["quality_flags"] = result["quality_flags"].map(
        lambda flags: sorted(set(flags) | {"additive_price_level_shock", "synthetic_not_forecast"})
    )

    provenance = pd.DataFrame(
        {
            "path_id": result["path_id"],
            "delivery_start_utc": result["delivery_start_utc"],
            "transformation_id": config.transformation_id,
            "method": "additive_constant_eur_per_mwh",
            "shift_eur_per_mwh": float(config.shift_eur_per_mwh),
            "original_price_eur_per_mwh": original,
            "shocked_price_eur_per_mwh": shocked,
            "input_source": paths["source"],
            "input_source_version": paths["source_version"],
        }
    )
    summary: dict[str, object] = {
        "result_label": "synthetic shocked bootstrap paths; not forecasts or investment evidence",
        "method": "additive constant price-level transformation",
        "configuration": config.to_dict(),
        "path_count": int(result["path_id"].nunique()),
        "interval_count": len(result),
        "provenance_row_count": len(provenance),
    }
    return PriceLevelShockResult(result, provenance, summary)


def _validated_paths(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["path_id", *CANONICAL_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise PriceLevelShockInputError(f"Missing bootstrap path columns: {', '.join(missing)}")
    paths = frame.loc[:, required].copy()
    if paths.empty:
        raise PriceLevelShockInputError("Bootstrap paths must not be empty")
    if paths["path_id"].isna().any() or not pd.api.types.is_integer_dtype(paths["path_id"]):
        raise PriceLevelShockInputError("path_id must contain non-negative integers")
    if (paths["path_id"] < 0).any():
        raise PriceLevelShockInputError("path_id must contain non-negative integers")
    if paths.duplicated(["path_id", "delivery_start_utc"]).any():
        raise PriceLevelShockInputError("Duplicate path_id and delivery_start_utc intervals")

    validated: list[pd.DataFrame] = []
    for path_id, path in paths.groupby("path_id", sort=True):
        canonical = ensure_canonical(path.loc[:, CANONICAL_COLUMNS], allow_empty=False)
        report = assess_quality(canonical, require_complete_days=True)
        if not report.is_valid:
            errors = ", ".join(issue.code for issue in report.issues if issue.severity == "error")
            raise PriceLevelShockInputError(f"Path {path_id} failed quality validation: {errors}")
        canonical.insert(0, "path_id", path_id)
        validated.append(canonical)
    return pd.concat(validated, ignore_index=True)
