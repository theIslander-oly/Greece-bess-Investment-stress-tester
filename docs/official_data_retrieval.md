# Official multi-year data retrieval

**Reviewed:** 26 August 2026  
**Scope:** Reproducible private retrieval; no official dataset is committed

## HEnEx archive track

HEnEx's official DAM/IDM archive publishes annual ZIPs containing market-result workbooks. The
verified register in `henex_archive.py` covers 2020 through 2025. Current Greek DAM coverage
begins on 1 November 2020; the 2020 manifest therefore records that start rather than implying a
full calendar year.

`fetch-henex-archives`:

1. accepts only years present in the reviewed URL register;
2. downloads over HTTPS from an exact HEnEx host allowlist;
3. hashes and stores the annual ZIP below ignored raw-data paths;
4. rejects absolute and parent-traversal archive members;
5. extracts only `YYYYMMDD_EL-DAM_Results_EN_v##.xlsx` files;
6. hashes every extracted workbook and links it to its parent archive hash;
7. parses every workbook through the accepted HEnEx parser;
8. selects the greatest publication revision per delivery interval;
9. rejects conflicting prices within the selected revision; and
10. writes normalized prices plus deterministic quality evidence.

The 2026 annual archive does not yet exist. `fetch-henex-daily` uses the official results asset
catalog for a requested date range and retains the latest visible revision for each delivery day.
Because this is a web catalog rather than a documented API, a layout change is a hard error. Its
first complete 2026 run has been accepted; see
`docs/official_history_acceptance_2026-08-26.md`.

## ADMIE/IPTO file API track

ADMIE documents unauthenticated JSON endpoints for:

- the current filetype catalog;
- exact file coverage queries; and
- queries whose coverage overlaps a requested date range.

`fetch-admie-files` stores the source URL, filetype, coverage start/end, the provider's raw
publication timestamp, its Europe/Athens-to-UTC conversion, revision suffix, retrieval time,
SHA-256 and byte size. The default keeps the latest publication per filetype and coverage period;
`--all-revisions` is available for audits.

The retrieval client intentionally does not parse load, RES or availability values yet. ADMIE
formats and meanings must be accepted dataset by dataset. More importantly, an exogenous value
may enter a target-day forecast only after its publication timestamp is proven to precede the
relevant bid decision. Until then, files are historical explanatory inputs or lag candidates.

## Storage and artefact policy

- Raw HEnEx, ADMIE and ENTSO-E responses remain under ignored `data/raw/` paths.
- Normalized prices remain under ignored `data/processed/` or acceptance paths.
- Git stores clients, parsers, source URLs, schemas, tests, aggregate evidence and manifests
  without official file contents.
- The GitHub workflow runs when its own file first reaches `main` and may be rerun manually. It
  uploads normalized data and provenance as a private artifact with a seven-day retention period.
  Ordinary code pushes do not trigger it, and it does not commit or publish those files.
- Provider terms must be reviewed before redistribution or public hosting.

## Acceptance sequence

1. ~~Run 2020-2025 archive retrieval in the connected private repository.~~ Accepted.
2. ~~Run incremental 2026 retrieval and confirm every expected market day.~~ Accepted.
3. ~~Produce annual row counts, DST checks, gaps, duplicates, revisions and price-regime
   reports.~~ Accepted.
4. ~~Run the optimizer and forecast benchmarks across the official history.~~ Accepted; see
   `docs/official_multiyear_operational_acceptance_2026-08-27.md`.
5. Reconcile an overlapping period with ENTSO-E A44 using a private token.
6. Inventory ADMIE format regimes and publication timing before parsing forecast features.
