# Implementation report — feature shard reconciliation

**Date:** 10 September 2026
**Execution-plan stage:** 3, second of two units
**Review finding:** 7

## Scope

This unit makes a shard's combined coverage checkable against what its shards actually hold. It
changes no declared source, cycle, geography, decision cutoff, feature set, held-out period or
feature value, and it launches no retrieval, acceptance or benchmark workflow. It builds on the
observation-time correction of the first unit, which is already on `main`.

## The defect

`combine_feature_shards` checked two things: that the shards shared one retrieval identity, and
that their **declared** `start_day`/`end_day` ranges tiled a window without overlap or gap. It
then concatenated their CSVs.

Nothing checked those declarations against the shards' contents. A shard whose feature table
lost a delivery day still declared its original window, still listed that day among the days its
`per_delivery_day` records said it built, and still reported zero exclusions — and the combiner
repeated all three claims in the combined summary. The combined `built_day_count` was the length
of the concatenated `per_delivery_day` lists, so it counted days the table did not contain.

Downstream, a delivery day missing this way is indistinguishable from a delivery day the
provider never published. That is the one distinction this project records by name and never
infers, so the failure could not be detected later.

## The correction

Every shard is now reconciled before any of it is concatenated. For each shard:

- the days its frame actually holds are read from the frame;
- days it claims to have built but holds no row for are refused;
- days it holds rows for but records no build for are refused;
- rows outside its declared window are refused;
- a day recorded as both built and excluded is refused;
- days accounted for outside its declared window are refused;
- each built day must hold one row per requested variable per delivery interval, where the
  interval count is the market day's own — 23, 24 or 25 across a DST boundary — and the
  resolution is read from the day's own rows rather than assumed to be hourly. A day storing two
  resolutions is refused, because what it owes has no single answer.

The combined `built_day_count` is now the reconciled count: every day it counts was proved to
hold rows in its shard and to be recorded as built by that shard's own retrieval.

### Why the partition is checked by count, not by set

The plan requires built days and explicitly excluded days to partition the declared window
exactly. The first implementation of this checked it as a set difference and was wrong: a shard
caps the day-by-day exclusion list it writes but reports its counts in full, so a shard that hit
its cap legitimately lists fewer excluded days than it excluded. The set check refused a correct
shard, and the existing capped-list test caught it.

The partition is therefore established by arithmetic — a shard declaring an *n*-day window and
recording *b* built days must report exactly *n − b* exclusions — which holds whether or not the
list is capped. The listed entries are still checked for every claim they do make: overlap with
built days, and days outside the declared window. This preserves the v0.9.7 rule that counts
reconcile even when a summary displays only a capped sample.

## Official-mode provenance

`combine_feature_shards` previously skipped a shard that had no retrieval manifest. It now takes
an `official` flag, exposed as `--official` on `combine-feature-tables` and set in the retrieval
workflow, which additionally requires:

- every shard to carry a retrieval manifest, and that manifest to record at least one message;
- every record to name both a local path and a digest;
- two records naming one local path to agree on its digest — disagreement means two different
  byte sequences under one name, and no later stage could tell which produced a row;
- each shard's reported `document_count` to match the records its manifest holds, so a manifest
  cannot be silently shorter than the retrieval it describes.

The flag is off by default because a synthetic fixture legitimately has no provenance to record.
It is on for the retrieval workflow, whose combination feeds the availability audit and, through
it, an acceptance document.

## A second fixture-versus-producer drift

The shard test fixture wrote its `per_delivery_day` entries keyed on `market_day`. The retrieval
writes them keyed on `delivery_day`; `market_day` is the key the *exclusion* entries use. The
fixture had drifted from the producer on this key, and nothing detected it because no test read
the field until this unit did.

This is the second such drift found in two units, after the renamed `retrieved_at_utc` the first
unit's own recombination read. Both were invisible for the same reason: a hand-written fixture
that stands in for a producer stops matching it silently. The retrieval-to-combination
integration tests added in the first unit remain the guard against this class of defect, and the
fixture is now corrected to the producer's key.

## Fixture correction

`_synthetic_day` built every fixture day as 24 hourly intervals with one fixed receipt instant.
It therefore could not represent a 23- or 25-hour market day at all, which is the case the
interval check exists for. It now derives its intervals from `market_day_starts`, as the
production path does, and derives its receipt from its publication instant. Ordinary days are
unchanged at 24 intervals.

## Preserved behavior

A valid tiling still reproduces the equivalent unsplit table exactly, asserted by frame equality
against a single-shard combination of the same days. Content digests and the combined table's
schema are unchanged.

## Validation

- Ruff
- mypy (65 source files)
- pytest: 664 passed, up from 650
- isolated wheel build

New regression tests cover: a two-day shard losing one day's rows without changing its records;
a stored day no record claims; rows outside the declared window; a day recorded as both built
and excluded; an exclusion count that does not close the window; a capped exclusion list still
reconciling; a day short by one interval; a shard with no coverage records; a reconciled tiling
still reproducing the unsplit table; a 25-hour DST day complete at 25 intervals per variable and
short at 24, proving the count follows the market day rather than a fixed 24; and, in official
mode, a missing manifest, contradictory
digests for one document, a manifest shorter than its reported document count, and agreeing
provenance combining successfully.
