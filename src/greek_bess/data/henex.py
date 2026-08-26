"""Parser for HEnEx `EL-DAM_Results_EN` workbooks."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .schema import ensure_canonical
from .timezones import GREECE_TZ, UTC, as_utc_timestamp, market_day_starts

REQUIRED_COLUMNS = {"DDAY", "SORT", "DELIVERY_DURATION", "MCP", "VER"}
_MCP_ROUNDING_TOLERANCE_EUR_PER_MWH = 0.011
_MAX_MCP_OUTLIER_ROWS = 2


class HenexParseError(ValueError):
    """Raised when a HEnEx workbook is missing or contradicts documented data."""


def parse_henex_results(
    path: str | Path,
    *,
    retrieved_at_utc: datetime | str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Parse a HEnEx DAM results workbook into one price per delivery MTU.

    HEnEx result workbooks contain repeated MCP values across asset and side
    rows. The parser normally requires one unique MCP per interval. A unique
    strict-majority value is accepted only when at most two provider rows differ
    by no more than one cent per MWh. The interval is explicitly flagged; larger
    disagreements, ties and non-majority values are rejected.
    """

    source_path = Path(path)
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    retrieved = (
        as_utc_timestamp(retrieved_at_utc)
        if retrieved_at_utc is not None
        else pd.Timestamp.now(tz=UTC)
    )

    try:
        sheets = pd.read_excel(
            source_path, sheet_name=None, header=None, engine="openpyxl"
        )
    except Exception as exc:
        raise HenexParseError(f"Could not read HEnEx workbook: {source_path.name}") from exc

    candidates: list[pd.DataFrame] = []
    for frame in sheets.values():
        candidate = _find_result_table(frame)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        raise HenexParseError(
            "No worksheet contains the documented HEnEx DAM result columns: "
            + ", ".join(sorted(REQUIRED_COLUMNS))
        )

    data = pd.concat(candidates, ignore_index=True)
    data = data.dropna(subset=list(REQUIRED_COLUMNS)).copy()
    if data.empty:
        raise HenexParseError("HEnEx workbook contains no complete DAM result rows")

    data["DDAY"] = pd.to_datetime(data["DDAY"], errors="coerce").dt.date
    data["SORT"] = pd.to_numeric(data["SORT"], errors="coerce")
    data["DELIVERY_DURATION"] = pd.to_numeric(data["DELIVERY_DURATION"], errors="coerce")
    data["MCP"] = pd.to_numeric(data["MCP"], errors="coerce")
    data["VER"] = pd.to_numeric(data["VER"], errors="coerce")
    if data[list(REQUIRED_COLUMNS)].isna().any().any():
        raise HenexParseError("HEnEx result columns contain unparseable values")

    data["SORT"] = data["SORT"].astype(int)
    data["DELIVERY_DURATION"] = data["DELIVERY_DURATION"].astype(int)
    data["VER"] = data["VER"].astype(int)
    if not data["DELIVERY_DURATION"].isin([15, 60]).all():
        durations = sorted(data["DELIVERY_DURATION"].unique().tolist())
        raise HenexParseError(f"Unsupported HEnEx delivery durations: {durations}")

    # A workbook or combined sheet can contain revisions. Use the latest
    # revision per delivery day while preserving the raw file and hash.
    latest = data.groupby("DDAY")["VER"].transform("max")
    data = data.loc[data["VER"].eq(latest)].copy()

    interval_keys = ["DDAY", "SORT", "DELIVERY_DURATION"]
    reduced_rows: list[dict[str, object]] = []
    for key, interval in data.groupby(interval_keys, dropna=False, sort=True):
        counts = interval["MCP"].value_counts(dropna=False)
        highest_count = int(counts.max())
        modes = counts[counts.eq(highest_count)].index.tolist()
        spread = float(interval["MCP"].max() - interval["MCP"].min())
        outlier_count = len(interval) - highest_count
        has_safe_rounding_consensus = (
            len(modes) == 1
            and highest_count > len(interval) / 2
            and spread <= _MCP_ROUNDING_TOLERANCE_EUR_PER_MWH
            and outlier_count <= _MAX_MCP_OUTLIER_ROWS
        )
        if len(counts) > 1 and not has_safe_rounding_consensus:
            raise HenexParseError(f"Conflicting MCP values for HEnEx interval {key}")
        flags = ["henex_mcp_rounding_consensus"] if len(counts) > 1 else []
        reduced_rows.append(
            {
                "DDAY": key[0],
                "SORT": key[1],
                "DELIVERY_DURATION": key[2],
                "MCP": modes[0],
                "VER": int(interval["VER"].max()),
                "QUALITY_FLAGS": flags,
            }
        )
    reduced = pd.DataFrame(reduced_rows).sort_values(interval_keys, kind="stable")

    rows: list[dict[str, object]] = []
    for record in reduced.itertuples(index=False):
        starts = market_day_starts(record.DDAY, record.DELIVERY_DURATION)
        if record.SORT < 1 or record.SORT > len(starts):
            raise HenexParseError(
                f"SORT={record.SORT} is invalid for {record.DDAY}; expected 1-{len(starts)}"
            )
        start_market = starts[record.SORT - 1]
        start_utc = start_market.tz_convert(UTC)
        duration = pd.Timedelta(minutes=record.DELIVERY_DURATION)
        rows.append(
            {
                "delivery_start_utc": start_utc,
                "delivery_end_utc": start_utc + duration,
                "delivery_start_market": start_market,
                "delivery_start_greece": start_utc.tz_convert(GREECE_TZ),
                "duration_hours": record.DELIVERY_DURATION / 60,
                "price_eur_per_mwh": float(record.MCP),
                "bidding_zone": "GR",
                "source": "henex",
                "source_version": f"v{record.VER:02d}",
                "retrieved_at_utc": retrieved,
                "raw_sha256": digest,
                "quality_flags": record.QUALITY_FLAGS,
            }
        )

    return ensure_canonical(pd.DataFrame(rows))


def _normalize_header(value: object) -> str:
    text = str(value).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def _find_result_table(raw: pd.DataFrame, max_header_rows: int = 30) -> pd.DataFrame | None:
    """Locate the documented result header below optional workbook preamble rows."""

    for row_number in range(min(max_header_rows, len(raw))):
        headers = [_normalize_header(value) for value in raw.iloc[row_number].tolist()]
        if REQUIRED_COLUMNS.issubset(headers):
            result = raw.iloc[row_number + 1 :].copy()
            result.columns = headers
            result = result.loc[:, [column for column in result.columns if column != "NAN"]]
            return result.dropna(how="all")
    return None
