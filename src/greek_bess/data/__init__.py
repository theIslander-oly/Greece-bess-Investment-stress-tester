"""Official Greek Day-Ahead Market data ingestion and validation."""

from .schema import CANONICAL_COLUMNS, ensure_canonical

__all__ = ["CANONICAL_COLUMNS", "ensure_canonical"]

