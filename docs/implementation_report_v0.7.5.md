# Greek Battery Investment Stress Tester — Implementation Report v0.7.5

**Date:** 27 August 2026
**Scope:** Explicit bootstrap source-era and resolution policy

## Why this milestone exists

The seasonal block bootstrap maps sampled historical blocks onto target market days, which
requires one delivery resolution. The accepted history does not have one: the Greek DAM moved
from hourly to quarter-hour delivery on 1 October 2025, so the 1 November 2020 to 25 August 2026
history holds two regimes.

The previous behaviour refused such a history with "Historical prices must use one interval
resolution". That is a correct refusal and a poor one: it left the operator to slice the CSV by
hand, making the sampled regime — the single most consequential assumption behind every generated
path — a by-product of which file was passed in, recorded nowhere. This milestone makes the era a
declared decision. It is a prerequisite for the availability/outage integration, which must not
be built on an undeclared sampling regime.

## Delivered policy

A **source era** is a maximal contiguous run of market days sharing one delivery resolution. A
resolution change ends an era; so does a gap in market days, because a block sampled across a gap
would not be a contiguous run. In practice the bootstrap's quality gate already refuses a
non-contiguous history, so for a real accepted history eras are separated by resolution alone;
the gap rule completes the definition rather than describing a case that arises.

`BootstrapConfig` gains `source_resolution_minutes`, `source_start_day` and `source_end_day`,
all optional and all round-tripping through the strict JSON config. `detect_source_eras` and
`select_source_era` are public, so an operator can list a history's eras before deciding.

The rules are:

- a history with one era needs no declaration, which leaves synthetic single-resolution
  demonstrations unchanged;
- a history with several must declare one, with **no default and no "most recent" rule**, since
  either would restore the accident the policy removes;
- a declaration matching more than one era must be narrowed by the source window;
- the refusal lists every available era with its resolution and window;
- sampling is confined to the selected era, so days outside it are absent from the candidate
  search and no block can straddle a regime boundary.

## What is recorded

The run summary carries the policy text, every available era, the available-era count, the
selected era, and whether a declaration was made. Every provenance row additionally carries the
era's resolution and its effective first and last day, so a path cannot be read without knowing
which regime produced it.

The summary also reports the minimum and median block-candidate counts. This is the honesty
metric for a short era: a minimum of 1 means every path repeats the same source block at that
position, which is a property of the era rather than of the seed.

## The two eras of the accepted history

| Era | Resolution | Window | Market days | Season occurrences |
|---|---|---|---:|---|
| 1 | 60 min | 2020-11-01 .. 2025-09-30 | 1,795 | 5 winters, 5 springs, 5 summers, 6 autumns |
| 2 | 15 min | 2025-10-01 .. 2026-08-25 | 329 | 1 of each |

The counts sum to the accepted 2,124 market days. Neither era is the right answer, and the tool
refuses to choose. The quarter-hour era is the regime the market actually operates under and the
only one whose interval structure matches a quarter-hour scenario, but it holds exactly one
occurrence of each meteorological season, so resampling it expresses no inter-annual variation at
all, and its autumn is only 61 days. The hourly era is the only one in which resampling can
express variation between years, but it is a superseded delivery regime that ends the day before
quarter-hour delivery began.

## Validation and limitations

Ruff, mypy, 156 tests and a clean wheel build pass, up from 142. Fourteen new deterministic
synthetic tests cover era detection as maximal contiguous single-resolution runs, a gap ending an
era, the refusal to choose implicitly and the eras it names, a declared era bounding every
sampled block and the resulting path resolution, the quarter-hour declaration changing the
sampled regime, an ambiguous declaration requiring narrowing, source-window narrowing inside an
era, a single-era history needing no declaration, a declared era absent from the history, the
generator still refusing a non-contiguous history, a market day mixing resolutions, config
validation of the new fields and their JSON round trip.

Resampling one resolution into another, aggregating quarter-hour prices to hourly, disaggregating
hourly prices to quarter-hour, weighting or stitching the two eras, and attaching any probability,
percentile or likelihood to an era or to a path drawn from it all remain excluded. Choosing an era
is a judgment about relevance, not an estimate. The limitation both eras share is unchanged: the
replayed history predates operating battery competition in the Greek DAM, which began in April
2026.
