"""Shared validation of synthetic bootstrap-path frames.

Every path transformation validates its input the same way: canonical schema, per-path
quality assessment requiring complete market days, no duplicate intervals and non-negative
integer path identifiers. Sharing the contract keeps two transformations from drifting apart
on what counts as an acceptable path.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from greek_bess.data.quality import assess_quality
from greek_bess.data.schema import CANONICAL_COLUMNS, ensure_canonical


def validate_bootstrap_paths(
    frame: pd.DataFrame, error: Callable[[str], Exception]
) -> pd.DataFrame:
    """Return canonical, per-path validated bootstrap paths or raise ``error(message)``.

    ``error`` builds the caller's own input-error type, so a failure names the transformation
    the operator actually invoked rather than a shared helper.
    """

    required = ["path_id", *CANONICAL_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise error(f"Missing bootstrap path columns: {', '.join(missing)}")
    paths = frame.loc[:, required].copy()
    if paths.empty:
        raise error("Bootstrap paths must not be empty")
    if paths["path_id"].isna().any() or not pd.api.types.is_integer_dtype(paths["path_id"]):
        raise error("path_id must contain non-negative integers")
    if (paths["path_id"] < 0).any():
        raise error("path_id must contain non-negative integers")
    if paths.duplicated(["path_id", "delivery_start_utc"]).any():
        raise error("Duplicate path_id and delivery_start_utc intervals")

    validated: list[pd.DataFrame] = []
    for path_id, path in paths.groupby("path_id", sort=True):
        canonical = ensure_canonical(path.loc[:, CANONICAL_COLUMNS], allow_empty=False)
        report = assess_quality(canonical, require_complete_days=True)
        if not report.is_valid:
            errors = ", ".join(issue.code for issue in report.issues if issue.severity == "error")
            raise error(f"Path {path_id} failed quality validation: {errors}")
        canonical.insert(0, "path_id", path_id)
        validated.append(canonical)
    return pd.concat(validated, ignore_index=True)
