# Release notes — v0.6.2

Version 0.6.2 fixes the live HEnEx annual-history acceptance defects found by the first GitHub
retrieval run.

## Fixed

- Latest daily workbook revisions are selected before obsolete publications are parsed.
- The official nested 2021 DAM archive is extracted with bounded depth, size and hash provenance.
- One-cent MCP differences confined to at most two cross-border rows use a tightly bounded,
  explicitly flagged consensus rule.
- Material, tied or non-majority MCP conflicts continue to fail.

## Live evidence

The official 2020-2025 annual archives produce 51,915 contiguous canonical intervals with no
missing prices, duplicates, gaps or overlaps. The complete evidence and archive hashes are in
`docs/official_history_acceptance_2026-08-26.md`.

The normalized data and source workbooks are not included in the package or repository.
