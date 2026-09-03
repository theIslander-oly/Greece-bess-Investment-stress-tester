# Fundamentals data acceptance — <YYYY-MM-DD>

> **Template:** copy to `docs/fundamentals_acceptance_<YYYY-MM-DD>.md` only from actual workflow evidence. Do not include interval-level official data.

## Scope and interpretation

- Acceptance verdict: `<accepted/refused>`
- Scope: suitability of the declared point-in-time feature table for the registered benchmark only.
- This acceptance establishes data suitability only. It establishes neither forecast skill, investment value, expected revenue, future format stability, financial advice, a bankable forecast, nor an investment-grade study.

## Workflow run and artifact identity

| Field | Evidence |
| --- | --- |
| Workflow / run ID / source commit | `<...>` |
| Private artifact name / published artifact digest | `<...>` |
| Retrieval window / parser version | `<...>` |

## Identity digests

| Input | SHA-256 or stable identifier |
| --- | --- |
| Accepted official price history | `<...>` |
| Accepted feature table / feature set | `<...>` |
| Decision-cutoff schedule | `<...>` |
| Sampling geography | `<...>` |
| Complete benchmark configuration | `<...>` |

## Acceptance findings

Record a verdict, evidence reference, counts, and every exception for each item. Never replace an exception with interpolation or a silent exclusion.

| Check | Verdict | Aggregate finding / evidence |
| --- | --- | --- |
| Retrieval and parser | `<...>` | `<...>` |
| Schema and provenance | `<...>` | `<...>` |
| Revisions and decision-time selection | `<...>` | `<...>` |
| Completeness and duplicates | `<...>` | `<...>` |
| Units and ranges | `<...>` | `<...>` |
| UTC, Greece/market views and DST (23/25-hour; 92/100-quarter-hour days) | `<...>` | `<...>` |
| Native resolution and hourly-to-quarter-hour broadcast | `<...>` | `<...>` |
| Publication time and strict cutoff | `<...>` | `<...>` |
| Availability grade and quarantine | `<...>` | `<...>` |
| Exclusions | `<...>` | `<...>` |
| Custody record, verification and encrypted copy | `<...>` | `<...>` |

## Availability-grade counts

| Grade | Observation count | Delivery-day count | Admitted? |
| --- | ---: | ---: | --- |
| `witnessed` | `<...>` | `<...>` | yes |
| `provider_declared` | `<...>` | `<...>` | yes |
| `assumed` | `<...>` | `<...>` | no; quarantine unless explicitly exploratory |

## Structured exclusions

| Named cause | Day count | Observation count | Affected span | Disposition |
| --- | ---: | ---: | --- | --- |
| `missing_observation` | `<...>` | `<...>` | `<...>` | `<refused/excluded>` |
| `late_publication` | `<...>` | `<...>` | `<...>` | `<refused/excluded>` |
| `inadmissible_grade` | `<...>` | `<...>` | `<...>` | `<refused/excluded>` |
| `revision_conflict` | `<...>` | `<...>` | `<...>` | `<refused>` |
| `duplicate_conflict` | `<...>` | `<...>` | `<...>` | `<refused>` |
| `unit_or_range_failure` | `<...>` | `<...>` | `<...>` | `<refused>` |
| `resolution_or_dst_failure` | `<...>` | `<...>` | `<...>` | `<refused>` |

## Custody conclusion

`<record/verification outcome and encrypted-copy identity; do not include private contents>`

## Reproduction

```bash
# Exact workflow dispatch command, source commit, inputs and artifact verification commands.
<commands from the completed run>
```
