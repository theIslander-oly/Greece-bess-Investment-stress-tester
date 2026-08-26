# Greek Battery Investment Stress Tester — Implementation Report v0.6.1

**Date:** 26 August 2026  
**Status:** Official multi-year acquisition pipeline implemented; live full-history run pending  
**Scope:** Greek Day-Ahead Market evidence track only

## Outcome

Version 0.6.1 hardens the official-data path before probabilistic modeling. It can retrieve the
reviewed HEnEx 2020-2025 annual archives, discover unarchived daily HEnEx results, normalize many
revisions into one canonical series, and retrieve ADMIE files with delivery and publication-time
provenance.

No official file is bundled or committed. The milestone changes data acquisition and auditability,
not dispatch, forecast, degradation or finance arithmetic.

## HEnEx annual archives

The source register pins the official annual result ZIP URLs linked from HEnEx's DAM/IDM archive.
The 2020 archive is labeled from 1 November, the start of the current Greek DAM. Unsupported years
are rejected rather than guessed.

Extraction enforces relative member paths, a workbook size limit and the exact English
`YYYYMMDD_EL-DAM_Results_EN_v##.xlsx` filename contract. Each annual ZIP and extracted workbook is
hashed. Workbook records retain the parent archive hash.

After parsing, the greatest `VER` is retained per UTC delivery interval. If two files claim the
same latest revision but disagree on MCP, the run stops. Missing prices are not repaired.

## HEnEx incremental daily retrieval

The unarchived-year client reads the official HEnEx results asset catalog, filters the requested
delivery range, chooses the greatest visible revision per day, resolves the document download and
requires an XLSX ZIP signature before writing it.

This catalog is a website interface, not a documented API. Layout changes therefore produce an
explicit failure. A successful catalog download still passes through the normal parser and data
quality layer.

## ADMIE/IPTO retrieval

The ADMIE client implements the provider-documented public JSON endpoints for filetype discovery
and date-range overlap search. It validates the response schema, source host, coverage dates and
publication time. The default keeps the latest publication per filetype and coverage period;
revision-history audits may keep all publications.

Candidate day-ahead load and RES files are labeled `requires_pre_auction_timing_validation`. They
do not enter v0.4 features in this milestone. Publication time is stored separately from delivery
coverage to support the later leakage audit.

## Retrieval manifests and security

Each file record includes:

- provider and dataset;
- exact source URL;
- relative private raw-data path;
- UTC retrieval time;
- SHA-256 and byte size;
- delivery coverage;
- provider publication time and UTC conversion when available;
- revision;
- parent archive hash where applicable; and
- availability/leakage classification.

Only HTTPS URLs from exact HEnEx or ADMIE host allowlists are accepted. URL credentials and
foreign hosts are rejected. Writes use sibling temporary files and atomic replacement.

## GitHub workflow

The manual `fetch-official-history.yml` workflow installs the package in a clean Python 3.12
runner, retrieves the selected annual range and optionally an incremental daily range, then
uploads normalized CSVs, manifests and quality reports as a private seven-day artifact. Raw
archives and workbooks are not uploaded or committed.

## Verification

The clean GitHub Actions suite passed Ruff, mypy, all 68 tests and a wheel build. This is eight
more tests than v0.6. Coverage includes:

- annual ZIP extraction and parent/child manifest records;
- path traversal rejection;
- unsupported archive-year rejection;
- later HEnEx revision selection;
- incremental catalog revision selection and XLSX download;
- ADMIE query construction, publication-time conversion and latest-revision selection;
- ADMIE foreign-host rejection; and
- generic HTTPS, credential and host validation.

## Remaining acceptance work

- Run all annual archives live in GitHub and inspect annual row counts, DST days, gaps and format
  regimes.
- Run 2026 incremental retrieval live and reconcile its coverage with the archive boundary.
- Cross-check overlapping HEnEx prices against ENTSO-E A44 with a private token.
- Accept ADMIE workbook formats and prove target-day pre-auction availability before feature use.
- Run optimizer and forecast backtests across the accepted official history.

Until those steps finish, v0.6.1 is an implemented acquisition system, not evidence of historical
profitability.
