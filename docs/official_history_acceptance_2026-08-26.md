# Official HEnEx annual-history acceptance — 26 August 2026

## Scope and interpretation

This report records a live acceptance run of the official HEnEx annual Greek Day-Ahead Market
results archives from 1 November 2020 through 31 December 2025. It validates ingestion evidence;
it does not estimate battery revenue, forecast future prices or support an investment decision.

Official ZIPs, workbooks and normalized prices remain outside Git. Only source identifiers,
hashes and aggregate validation evidence are recorded here.

## Initial workflow failure

GitHub Actions run `32940463180` failed on 26 August 2026 while parsing 16 December 2020. HEnEx
published v01, v02 and v03 workbooks for that day. The superseded v01/v02 files contain conflicting
MCP rows, while the latest v03 publication is internally consistent. The pipeline parsed obsolete
files before selecting v03.

A second acceptance defect was found locally: the 2021 annual download stores the DAM archive as
`2021_EL-DAM_Results.zip` inside the outer ZIP. The original extractor did not recurse and the
quality layer correctly rejected the resulting one-year gap.

## Accepted resolution rules

- Select the greatest `YYYYMMDD_EL-DAM_Results_EN_v##.xlsx` revision per delivery day before
  parsing.
- Permit one nested, size-limited `YYYY_EL-DAM_Results.zip` and record both archive hashes.
- Reject deeper nested archives and unsafe paths.
- Require repeated MCP rows to agree exactly, except when a unique strict majority differs from
  at most two rows and the complete price spread is no more than EUR 0.011/MWh.
- Label every bounded consensus interval `henex_mcp_rounding_consensus`.
- Reject ties, larger differences and non-majority disagreements.

The 980 bounded cases in this history all have an exact EUR 0.01/MWh spread, a majority fraction
of at least 85.7%, no more than two outlier rows, and outliers only on Greek-border import/export
assets. The rule does not interpolate, average or replace missing intervals.

## Archive evidence

| Delivery year | Archive bytes | SHA-256 | Workbooks, all revisions | Accepted intervals | Negative intervals | Rounding flags |
|---:|---:|---|---:|---:|---:|---:|
| 2020 (from 1 Nov) | 5,039,023 | `2aa69b20e963d810bfa7e793947088bf5450f8666842b27c88525cb85cd04b00` | 64 | 1,464 | 2 | 5 |
| 2021 | 15,805,523 | `ac7a8681511933346dba05f4a376917ba76778ff463fbbde800f474393d58128` | 365 | 8,760 | 5 | 83 |
| 2022 | 17,104,211 | `84f3a38ae67c1145cf19cac37e93c81e1759c61ebf36aa412901036661cad3d5` | 366 | 8,760 | 1 | 158 |
| 2023 | 17,068,727 | `082adec9ce1b83abf8bcc7e8e92340d44f7c0d4a14f3f9c9e3f0e4341db77eb0` | 366 | 8,760 | 0 | 222 |
| 2024 | 17,232,180 | `6892cb6ec7aa3bef7bd774ed233ababb533a3149b574af15265e6e408e3720d7` | 367 | 8,784 | 11 | 284 |
| 2025 | 26,688,090 | `8c6ab55032fdd2b89b00aac8ce58df9aa622c1d13f2c47df0c85bb069de431d9` | 365 | 15,387 | 177 | 228 |
| **Total** | **98,937,754** | — | **1,893** | **51,915** | **196** | **980** |

## Quality result

- Coverage: market day 1 November 2020 through 31 December 2025.
- Canonical UTC keys: 51,915 unique intervals.
- Missing prices: 0.
- Duplicate intervals: 0.
- Gaps or overlaps: 0.
- Hourly/quarter-hour duration mismatches: 0.
- Negative-price intervals preserved: 196.
- Hourly spring/fall DST days validated against 23/25 intervals.
- The 2025 quarter-hour autumn DST day validated against 100 intervals.
- All annual and extracted-file provenance records include SHA-256 values.
- Overall deterministic quality status: valid, with negative-price and bounded MCP-consensus
  information notices only.

## Still pending

- Confirm the corrected clean GitHub workflow and inspect its private seven-day artifact.
- Retrieve and accept the unarchived 2026 daily range.
- Reconcile overlapping HEnEx intervals against ENTSO-E A44 after a private token is configured.
- Keep ADMIE variables quarantined until pre-auction publication timing is proven.
