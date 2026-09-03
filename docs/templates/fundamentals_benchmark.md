# Fundamentals benchmark — <YYYY-MM-DD>

> **Template:** acceptance must be committed first. This document records a historical research output whether positive, negative, null, or exploratory.

## Scope, acceptance link and interpretation

- Acceptance document: `docs/fundamentals_acceptance_<YYYY-MM-DD>.md`
- Accepted feature-set SHA-256: `<exact digest already accepted there>`
- `is_exploratory`: `<true/false>`
- These are historical research outputs, not expected revenue, financial advice, a bankable forecast, or an investment-grade study.
- Perfect foresight is only a gross-margin upper bound, never expected revenue.

## Fixed design

| Declaration | Fixed value |
| --- | --- |
| Training | `2021-03-27` through `2024-09-30`; entirely hourly |
| Validation | `2024-10-01` through `2025-09-30`; entirely hourly |
| Test | starts `2025-10-01`; entirely quarter-hour |
| Structural price bands (EUR/MWh) | `0 50 100 200` |
| Decision lead | `0` minutes |
| Features | `dswrf_surface`, `temperature_2m`, `wind_speed_10m` |
| Battery | unchanged `examples/battery_50mw_100mwh.json` |

**Training and validation are entirely hourly while test is entirely quarter-hour.** Native hourly GFS features are broadcast unchanged over four quarter-hour test intervals; this is explicit coarser-feature broadcast, not interpolation.

## Workflow and artifact identity

| Field | Evidence |
| --- | --- |
| Workflow / run ID / source commit | `<...>` |
| Private artifact / digest | `<...>` |
| Price history / feature set / cutoff / geography / configuration digests | `<...>` |

## Common-day basis and exclusions

| Split | Candidate days | Common days | Resolution | Named exclusions |
| --- | ---: | ---: | --- | --- |
| Training | `<...>` | `<...>` | hourly | `<...>` |
| Validation | `<...>` | `<...>` | hourly | `<...>` |
| Test | `<...>` | `<...>` | quarter-hour | `<...>` |

Complete meteorological season present in common held-out quarter-hour days: `<season/none>`. The `is_exploratory` value above must be true unless every day of at least one complete season is present.

## Forecast arms and recorded results

Record every control, challenger and baseline under identical common days, model families, hyperparameters, seed and refit cadence. Record negative and null results under exactly the same labels and table structure as positive results.

| Arm / method | Information set | Validation selection record | Test metrics and structural-band slices |
| --- | --- | --- | --- |
| `<...>` | `<...>` | `<...>` | `<recorded producer output>` |

## Settled dispatch under equivalent constraints

Every schedule is forecast-planned and settled against the same realized prices. Record the common calendar, physical battery parameters, terminal-energy constraint and producer-recorded incremental margin; this document and renderer compute nothing.

| Method / comparison | Settled realized margin | Perfect-foresight gross-margin upper bound | Producer-recorded incremental margin | Paired-day artifact |
| --- | ---: | ---: | ---: | --- |
| `<...>` | `<...>` | `<...>` | `<positive/negative/null>` | `<...>` |

## Reproduction

```bash
# Exact workflow dispatch command, source commit, accepted digest and verification commands.
<commands from the completed run>
```
