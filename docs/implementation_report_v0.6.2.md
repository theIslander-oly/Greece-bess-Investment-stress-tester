# Greek Battery Investment Stress Tester — Implementation Report v0.6.2

**Date:** 26 August 2026  
**Status:** Live 2020-2025 annual-history acceptance fix implemented  
**Scope:** Greek Day-Ahead Market data evidence only

## Failure-driven correction

The first merged official-history workflow failed on a genuine historical revision edge case.
Superseded 16 December 2020 v01/v02 workbooks contain conflicting MCP values that HEnEx corrected
in v03. The original normalization parsed every file before selecting the latest revision, so it
stopped on evidence that should have been superseded.

After correcting the selection order, the quality layer found that 2021 was absent. That official
annual download uniquely contains a nested DAM ZIP. The extractor now permits exactly one
name-matched, size-limited nested DAM archive, rejects deeper nesting and preserves both hashes.

## MCP row-consensus boundary

Latest HEnEx workbooks repeat the Greek-zone MCP across demand, supply and cross-border asset
rows. In 980 of 51,915 accepted intervals, one or two cross-border rows differ from all dominant
rows by exactly EUR 0.01/MWh. The parser accepts these only when:

- there is one unique strict majority;
- no more than two rows disagree; and
- the maximum-to-minimum spread is at most EUR 0.011/MWh.

Accepted intervals are labeled `henex_mcp_rounding_consensus`. Larger differences, ties and
non-majority disagreements remain errors. This rule was calibrated against the complete latest
2020-2025 publications, where the smallest majority share was 85.7% and every outlier belonged to
a Greek-border import/export asset.

## Verification

- Official archive coverage: 1 November 2020 through 31 December 2025.
- Canonical intervals: 51,915.
- Missing prices, duplicate UTC keys, gaps and overlaps: zero.
- Negative-price intervals preserved: 196.
- All hourly DST days and the 2025 quarter-hour autumn DST day passed expected-count checks.
- Outer annual, nested 2021 and workbook hashes remain in the private retrieval manifest.
- Regression tests cover superseded conflicting revisions, nested annual archives, safe rounding
  consensus and rejection of material majority disagreements.
- All 72 source tests and an offline clean wheel build pass locally; GitHub CI remains the clean
  environment gate.

The exact archive hashes and year-level counts are recorded in
`docs/official_history_acceptance_2026-08-26.md`. A corrected GitHub workflow run and its private
artifact remain the final PR acceptance gate.
