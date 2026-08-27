# Bootstrap source-era and resolution policy — 27 August 2026

## The problem this policy exists to solve

The seasonal block bootstrap samples contiguous historical blocks and maps them onto target
market days. Mapping requires a single delivery resolution: a block of hourly days cannot be
laid onto quarter-hour target days without inventing or discarding intervals, which the
project's rules forbid.

The accepted official history does not have a single resolution. The Greek DAM moved from
hourly to quarter-hour delivery on **1 October 2025**, so the accepted 1 November 2020 to
25 August 2026 history contains two regimes. Before this policy, the bootstrap simply refused
such a history with "Historical prices must use one interval resolution", which left the
operator to slice the CSV by hand. That slice would then be the single most consequential
assumption behind every generated path, and it would exist nowhere in the record.

The sampled regime must therefore be a declared decision, not a by-product of which file was
passed in.

## What a source era is

A **source era** is a maximal contiguous run of market days sharing one delivery resolution.
A resolution change ends an era. A gap in market days also ends one, because a block sampled
across a gap would not be a contiguous run. In practice the bootstrap's quality gate already
refuses a non-contiguous history, so for a real accepted history eras are separated by
resolution alone; the gap rule is what makes the definition complete rather than a case that
arises.

The accepted history contains exactly two:

| Era | Resolution | Window | Market days | Season occurrences |
|---|---|---|---:|---|
| 1 | 60 min | 2020-11-01 .. 2025-09-30 | 1,795 | 5 winters, 5 springs, 5 summers, 6 autumns |
| 2 | 15 min | 2025-10-01 .. 2026-08-25 | 329 | 1 of each |

The split is not merely computed here; it reconciles exactly with figures recorded
independently by `docs/official_multiyear_operational_acceptance_2026-08-27.md`, which counted
market-day lengths without reference to any era concept:

| Check | From the era split | From the acceptance report |
|---|---:|---:|
| Hourly market days | 1,795 | 23 × 5 + 24 × 1,786 + 25 × 4 = 1,795 |
| Hourly intervals | 43,079 | 43,079 |
| Quarter-hour market days | 329 | 92 × 1 + 96 × 327 + 100 × 1 = 329 |
| Quarter-hour intervals | 31,584 | 31,584 |
| Total market days | 2,124 | 2,124 |
| Total intervals | 74,663 | 74,663 |

The era boundary therefore falls exactly where the accepted history's resolution regimes change,
with no day unaccounted for on either side.

## The policy

1. **A history with one era needs no declaration.** The bootstrap uses it and records that no
   declaration was made. This keeps synthetic single-resolution demonstrations unchanged.
2. **A history with more than one era must declare which.** `source_resolution_minutes`
   selects the era; `source_start_day` and `source_end_day` narrow it further, and are
   required when a declaration would otherwise match more than one era. There is **no
   default**, and in particular no "use the most recent" rule: a default would restore the
   accident this policy removes.
3. **The refusal names the choices.** When no era is declared, the error lists every available
   era with its resolution and window, so the operator chooses from what the history actually
   contains rather than guessing.
4. **The choice is recorded, not just applied.** The run summary carries the era policy text,
   every available era, the selected era, and whether a declaration was made. Every sampled
   block additionally records the era's resolution and window in the provenance table, so a
   path cannot be read without knowing which regime it came from.
5. **Sampling is confined to the selected era.** Days outside it are absent from the candidate
   search, so no block can straddle a regime boundary.
6. **Candidate scarcity is reported, not smoothed.** The summary records the minimum and median
   candidate count across sampled blocks. A minimum of 1 means every path repeats the same
   source block at that position, which is a property of the era, not of the seed.

## Choosing an era, and what each choice costs

Neither era is the right answer. The trade-off is explicit and the tool refuses to make it.

**The quarter-hour era (2025-10-01 .. 2026-08-25)** is the delivery regime the market actually
operates under, and the only one whose interval structure matches a forward-looking
quarter-hour scenario. Its cost is severe: it contains **exactly one occurrence of each
meteorological season**. Seasonal block bootstrap over it recombines the within-season shape of
a single year and therefore expresses **no inter-annual variation at all**. Its autumn is also
only 61 days, so autumn blocks are drawn from the thinnest candidate set of the four.

**The hourly era (2020-11-01 .. 2025-09-30)** contains five or six occurrences of every season
and is the only era in which resampling can express variation between years. Its cost is that
it is a **superseded delivery regime**: it ends the day before quarter-hour delivery began, and
its 60-minute blocks can only be mapped onto 60-minute target days. Paths generated from it
describe a market structure that no longer exists.

There is a further limitation both eras share, already recorded in `LIMITATIONS.md`: the
replayed history predates operating battery competition in the Greek DAM, which began in April
2026. Resampling either era carries that forward.

## What the policy deliberately does not do

- It does not resample one resolution into another, aggregate quarter-hour prices to hourly, or
  disaggregate hourly prices to quarter-hour. Each of those is a modelling assumption that
  would need its own justification and acceptance, and none is in scope.
- It does not weight, blend or stitch the two eras. A path drawn from two regimes would have no
  single interpretation.
- It does not attach any probability, percentile or likelihood to an era or to a path drawn
  from it. Choosing an era is a judgment about relevance, not an estimate of anything.
- It does not decide for the operator. A declared era that is a poor fit for a question is a
  recorded decision that can be argued with, which is the point.

## Configuration

```json
{
  "start_day": "2027-01-01",
  "end_day": "2027-04-01",
  "path_count": 20,
  "block_days": 7,
  "random_seed": 42,
  "source_resolution_minutes": 15,
  "source_start_day": "2025-10-01",
  "source_end_day": "2026-08-26"
}
```

`source_end_day` is exclusive, matching `end_day`. `source_start_day` and `source_end_day` may
be omitted when `source_resolution_minutes` already selects exactly one era; supplying them
records the intended window explicitly, which is worth doing when the history may later be
extended.

`greek_bess.stress.detect_source_eras` and `select_source_era` are public, so an operator can
list the eras in a history before deciding.
