# Implementation report v0.7.9 — Declared negative-price events

**Date:** 31 August 2026

## Scope

Adds `greek_bess.stress.apply_negative_price_events` and the
`apply-negative-price-events` CLI command for validated synthetic bootstrap paths. This is the
last approved v0.7 modeling item. No dispatch mode, forecast method, finance treatment,
availability behaviour, official-data workflow, research interface or exportable report is
added or changed.

The result is a deterministic synthetic scenario, not a forecast, probability-calibrated path,
expected revenue, investment conclusion or bankable study.

## Declared event unit and depth

One event is a sequence of whole delivery intervals selected by an inclusive UTC start and an
exclusive UTC end. Every covered interval on every bootstrap path is replaced by the event's
declared strictly negative absolute price in EUR/MWh. The event identifier, both boundaries,
depth and transformation identifier are all required and have no defaults. The `events` field is
also required; an explicitly empty list is the exact identity.

Whole delivery intervals are the smallest price unit the validated paths contain. A boundary
inside an interval is therefore refused rather than rounded or prorated. Rounding would change
the requested event, while proration would invent sub-interval prices and settlement arithmetic
the input does not support. A window covering no interval, reversed or equal boundaries,
overlapping windows, duplicate identifiers and naive timestamps are likewise refused.

An absolute negative price makes event depth explicit and executable. Zero is not accepted as
event depth because the milestone is specifically a negative-price event. Existing zero and
negative prices outside named windows remain unchanged; no transformed value is clipped or
floored.

## Occurrence is never sampled

The transformation contains no event-frequency mechanism. It does not draw, infer, fit, rank,
threshold-search or calibrate event occurrence, and strict configuration parsing rejects any
undeclared field rather than silently ignoring it. A frequency, rate, probability, likelihood,
percentile or expected count would claim evidence about occurrence that the non-stationary
uniform bootstrap cannot provide. This applies the same refusal principle that removed
percentiles on 27 August 2026 and made outage timing declarative on 31 August 2026.

Reproducibility follows from the recorded bootstrap seed and complete transformation
configuration: given identical ordered paths and the same declaration, paths, provenance and
summary are identical. The transformation adds no random state of its own.

## Distinction from existing transformations

An additive price-level shock changes every interval by one constant and preserves all absolute
spreads. Spread compression changes every interval relative to a daily reference and scales the
entire within-day range. A declared negative-price event instead changes only explicitly named
interval windows and assigns them absolute negative prices. This localized temporal replacement
is the content neither existing transformation expresses, and the distinction is stated in the
method summary.

The command does not compose transformations or infer their order. A caller can pass a validated
path produced elsewhere, whose source-version provenance is retained, but this command performs
only its declared interval replacement and records that fact.

## Provenance and summary evidence

The provenance table has exactly one row for every input path interval. Every row records path
ID, canonical UTC start, transformation ID, method, original and transformed price, input source
and source version. Covered rows also name the event and its declared price; untouched rows
explicitly record that no event applied.

The summary carries the result label, method, distinction from the level/spread transformations,
policy, complete configuration, path and interval counts, provenance count, declared event count,
covered interval count by event, and negative and zero interval counts before and after. The
negative count is evidence of what the declaration changed and is never suppressed.

## Refusal boundary

The public function and CLI refuse:

- missing or non-finite input prices;
- malformed, unknown or omitted configuration fields;
- non-finite, zero or positive event prices;
- naive, reversed or equal timestamps;
- duplicate identifiers, overlapping events and windows covering no interval;
- boundaries inside a delivery interval; and
- any bootstrap path that fails the shared canonical/DST-aware validation contract.

There is no interpolation, flooring, clipping, sub-interval approximation, frequency model,
dispatch integration or downstream commercial interpretation.

## Test and validation evidence

Tests cover hand-checked two-interval replacement arithmetic across two paths, exact identity,
preservation of unnamed zero and negative prices, every required field, invalid depths and
windows, missing prices, repeatability, one-to-one provenance, before/after negative counts and
the CLI sidecars. The milestone is validated with Ruff, mypy, the complete pytest suite and a
clean wheel build. Exact command results are recorded in the pull request.

## Roadmap consequence

The approved v0.7 deterministic modeling scope is complete. v0.8 remains gated until the
completed v0.7 scope is reviewed; this milestone does not implement, stub or prepare the research
interface or exportable reports.
