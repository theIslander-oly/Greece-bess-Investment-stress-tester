# Official HEnEx Data Acceptance — 25 August 2026

## Purpose

This acceptance check tests the released v0.4.0 production CLI against legitimately
downloaded official HEnEx Day-Ahead Market workbooks. It is an ingestion and data-quality
test, not a revenue study, price forecast or investment conclusion.

Official raw workbooks and normalized market outputs are deliberately excluded from the
repository. This report retains only the minimum provenance and aggregate evidence needed
to reproduce and audit the check, subject to the source's terms of use.

## Accepted sources

| Delivery day | Official filename | Version | SHA-256 |
| --- | --- | --- | --- |
| 2026-08-24 | `20260824_EL-DAM_Results_EN_v01.xlsx` | v01 | `7fe79629bb8afcaa64bdb22b8de600f5659cd92a942b71b3d91f5411bac97970` |
| 2026-08-25 | `20260825_EL-DAM_Results_EN_v01.xlsx` | v01 | `b1e6d44eb504a6acd01f4d187bfc7aa8fcde8ceae085a033e90b0159c0f5abf1` |

Source: HEnEx Day-Ahead Market publications. Retrieval and acceptance date:
25 August 2026.

## Production command exercised

```bash
greek-bess parse-henex \
  path/to/YYYYMMDD_EL-DAM_Results_EN_v01.xlsx \
  --output path/to/henex_YYYYMMDD.csv
```

The command was run independently for each unmodified workbook with complete-day checks
enabled. Both executions returned exit code `0`. The check was then repeated through an
isolated installation of the built v0.4.0 wheel; both wheel executions also returned exit
code `0` with the same interval counts, UTC boundaries and quality results.

## Results

| Check | 2026-08-24 | 2026-08-25 | Combined |
| --- | ---: | ---: | ---: |
| Parsed intervals | 96 | 96 | 192 |
| Resolution | 15 minutes | 15 minutes | 15 minutes |
| Missing prices | 0 | 0 | 0 |
| Negative prices | 0 | 0 | 0 |
| Zero prices | 0 | 0 | 0 |
| Quality errors | 0 | 0 | 0 |

Combined UTC coverage begins at `2026-08-23T22:00:00Z`. The last interval starts at
`2026-08-25T21:45:00Z` and ends at `2026-08-25T22:00:00Z`.

The 24 August series ends at exactly `2026-08-24T22:00:00Z`, which is the start of the
25 August series. Therefore the two official market days contain no UTC gap or overlap.

The combined observed price range was EUR 83.44/MWh to EUR 265.29/MWh. These descriptive
values only verify numeric parsing; they are not retained as an investment result.

## Acceptance decision

**Passed.** The v0.4.0 HEnEx parser successfully handled current production
`EL-DAM_Results_EN` workbook structure, publication versioning, repeated result rows,
quarter-hour delivery intervals, timestamp reconstruction and complete-day validation
without a code change.

## Remaining official-data acceptance work

1. Exercise the ENTSO-E A44 client using a private user token.
2. Fetch the same delivery days from ENTSO-E.
3. Reconcile HEnEx and ENTSO-E interval timestamps and prices.
4. Validate a spring and autumn DST transition using official workbooks.
5. Run the forecast and dispatch benchmark over a complete official multi-year history.

Until those checks and the later degradation, finance and probabilistic layers are
complete, the tool remains a transparent research and pre-feasibility system—not an
investment-grade forecast or financial recommendation.
