# Implementation report v0.9.6 — the declared window becomes retrievable

**Date:** 3 September 2026

## What this milestone is

v0.9.5 completed the machinery for the official run and the declarations that unblock it. The
first thing that machinery was asked to do was retrieve the declared window, and it could not.
This milestone measures why, and removes the two obstacles, without changing what is retrieved,
how it is graded, or any analytical result.

## The measurement

`Fetch point-in-time fundamentals` had never been dispatched. Run `33760441164`, on 3 September
2026, retrieved delivery days 27 July to 25 August 2026 — 30 days — and its retrieval step took
**36 minutes 4 seconds**, or **72.1 seconds per delivery day**. The source is read as one HTTPS
round trip per forecast step per delivery day, and the retrieval is sequential by construction.
A local retrieval of two days measured **83 MB per delivery day** of GRIB2 messages.

Against the pre-registered window of **2,006 delivery days** (27 February 2021 to 25 August
2026, the first hourly-product day to the accepted price endpoint), those rates give:

| Quantity | Measured rate | Declared window | Ceiling |
| --- | ---: | ---: | ---: |
| Retrieval time | 72.1 s/day | **40.2 hours** | 6 h per job |
| Raw retention with `--raw-dir` | 83 MB/day | **163 GB** | ~14 GB free on a runner |

Both are hard failures rather than slow successes, and neither was visible before the workflow
was dispatched, because the surface had only ever been exercised on synthetic fixtures.

The window itself is not negotiable: the split, the boundary and the source are pre-registered
(`docs/fundamentals_declarations_2026-09-03.md`), and shortening the window to fit a runner
would be revising a declaration to fit an operational constraint.

## What was changed

**Raw retention.** The retrieval workflow no longer passes `--raw-dir`. The flag stays on the
command, where it is useful over a short window, but the retrieval manifest already records the
digest, byte count and source URL of every message each value was decoded from, so the messages
themselves are not what the evidence rests on. This removes the disk ceiling outright.

**Sharded retrieval.** The window is tiled into slices retrieved in parallel and recombined.
This is sound only because a delivery day is retrieved independently of every other: the client
reads that day's own forecast cycle and derives nothing from a neighbour. The retrieval client
is untouched — making it concurrent would change how an evidence path talks to the provider,
which is a change to the evidence, not to its schedule.

`combine-feature-tables` and `data/feature_shards.py` hold the invariant that makes the
recombination checkable rather than assumed: the slices must **tile** the window, covering every
delivery day exactly once. An overlap is refused rather than deduplicated, because two
retrievals of one day are two revisions of the same observation and choosing between them is the
point-in-time join's decision under a declared cutoff. A gap is refused by name. Slices that
disagree on source, variable set or declared geography are refused by naming the fields that
differ. The combined summary records every slice and its own retrieval instant, and the combined
manifest carries every document from every slice, so any one slice can be re-retrieved alone.

At 90 delivery days per slice the declared window is 23 slices of about 1 hour 50 minutes each.

**Round-trip float precision.** Combining exposed a defect that was already present. The feature
table is written exactly but was read back with pandas' default float parser, which is accurate
to within one unit in the last place. That is far below anything meteorological or monetary this
project reports — the observed relative difference was 2e-16 — but the feature set is identified
downstream by a SHA-256 over its own values, and **a digest has no tolerance**. A table written,
read and written again therefore digested differently from the one the retrieval produced, which
would have made the v0.9 acceptance gate depend on how many times a table had been copied. Both
readers that feed a digested frame now parse with round-trip precision. No analytical result
changes; one digest computation becomes stable that was not.

## What was validated

Ruff, mypy over 65 source files, **599 tests** and a clean wheel build pass. Seven new tests
cover the tiling property and every refusal, on synthetic fixtures. The equivalence was also
checked on real retrieved NOAA GFS data before the surface was adopted: two delivery days
retrieved separately and recombined are **exactly** the table one retrieval of both days wrote,
every float included, and the combined manifest carries the same 200 documents and the same
166,460,222 bytes.

## What this milestone does not do

It retrieves no accepted feature table, records no availability finding against official data,
writes no custody record, produces no acceptance document and computes no benchmark figure. It
makes the official run possible; it does not perform it. Perfect foresight remains a
gross-margin upper bound, and every result this repository reports still comes from the accepted
price history alone.
