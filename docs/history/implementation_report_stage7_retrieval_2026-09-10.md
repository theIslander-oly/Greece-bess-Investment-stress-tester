# Implementation report — Stage 7 retrieval steps 1–3

**Date:** 10 September 2026
**Execution-plan stage:** 7, retrieval steps 1–3 only

## Retrieval

Smoke run `34476165832` rebuilt delivery days 18–19 April 2026 with corrected GFS feature
semantics and per-message receipt times. It produced 144 feature rows from 200 traced source
documents and evaluated no model skill.

Full run `34476720910` retrieved the unchanged declared window, 27 February 2021 through
25 August 2026, in 23 private shards on standard Ubuntu runners. Every retrieval job succeeded.
Raw GRIB2 messages were not retained; the manifests retain their digests and source identities.

## Defects found before acceptance

The workflow counted both `features_N.csv` and `features_N.coverage.csv` as feature tables. Its
guard therefore saw 46 files for 23 shards and stopped before combination. Discovery now matches
only numbered feature tables.

Local reproduction then found that interval validation used dtype-sensitive `Series.equals`.
CSV-loaded delivery intervals were stored as `timedelta64[us]`, while declared resolutions were
stored as `timedelta64[s]`; every duration was equal by value, but the dtype mismatch caused a
refusal. Validation now uses elementwise duration equality. A regression test fixes that boundary
while the existing unequal-duration refusal remains.

## Combination and timing audit

The corrected official combiner reconciled all 23 shards as an exact tiling with 2,005 built
days, 144,357 feature rows and 200,496 traced source documents. The audit covered all 2,006
declared days. Each variable has 2,002 days classified
`provider_declared_before_cutoff`; 2021-03-23, 2021-06-15 and 2022-01-18 are
`incomplete_before_cutoff`, and 2022-12-01 is `no_publication`. The minimum declared lead among
accepted observations is 196.17 minutes. No observation is classified as witnessed in this
historic retrieval, and no missing day is filled or imputed.

## Interpretation

This completes retrieval, shard reconciliation and publication/receipt timing audit only. It is
availability evidence, not feature-value acceptance, forecast skill, expected revenue, financial
advice or investment evidence. Custody, acceptance preflight, a dated acceptance decision and all
benchmarks remain outside this report.
