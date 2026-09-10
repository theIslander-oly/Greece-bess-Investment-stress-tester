# Implementation report — matched-training control

**Date:** 10 September 2026
**Execution-plan stage:** 6
**Review finding:** 8

## Scope

This stage adds a third ablation arm so that one comparison varies only the feature columns. It
changes no declared source, cycle, geography, decision cutoff, feature set, evidence grade or
held-out period, launches no retrieval or acceptance workflow, and produces no benchmark
outcome.

## Ordering

The prospective amendment was recorded first, as its own commit, before this implementation and
before any comparison outcome exists
(`docs/fundamentals_matched_control_amendment_2026-09-10.md`). That ordering is real rather than
presentational: no fundamentals benchmark has been run against official data, the declared window
has not been retrieved and no feature table has been accepted, so the comparison structure was
fixed while its outcome was unknown.

## The defect

The declared ablation compared two arms whose training sets are not the same. The control trained
on every day in the causal feature table. The challenger trained only on days whose accepted
weather features are complete, because a missing feature excludes its day rather than acquiring
an imputed value.

The two arms therefore differed in the feature columns **and** in the training rows, and any
difference between them confounded the value of the weather columns with the cost of the training
coverage lost to requiring them. The direction of that confound is not knowable in advance:
fewer training rows would usually hurt the challenger, understating weather value, but the
excluded days are exactly the days the weather source failed to cover, which need not be a random
sample of the price distribution.

## The three arms

| Arm | Feature columns | Training rows |
| --- | --- | --- |
| `full_history_baseline` | calendar and price history | every day in the causal feature table |
| `matched_control` | calendar and price history | exactly the challenger's eligible days |
| `challenger` | those columns plus accepted weather | exactly the challenger's eligible days |

The naïve forecasts remain as `baselines`. The arm previously named `control` is renamed
`full_history_baseline`: leaving the name `control` on it would have kept implying it was the
challenger's comparator, which is precisely the error being corrected.

The summary records an `attribution` sentence naming what each difference measures, so a reader
of the recorded result does not have to reconstruct it.

## Enforcing the match

Each refit now records `training_row_digest` — a digest of its training row identities — and
`training_target_digest`, both computed independently of the feature columns the fit reads. The
benchmark refuses to produce a result unless every matched pair agrees on both at every refit,
and reports which refit disagreed.

This is the substantive part of the stage. "Only the feature columns differ" is the entire basis
for attributing a difference to weather, and a claim carried only in prose stops being true the
first time either arm's row selection changes for an unrelated reason. The digests exclude
feature columns deliberately: a digest that moved when the columns changed would answer a
different question.

## Settlement

`fundamentals_dispatch` pairs each challenger with its matched control rather than the
full-history baseline, and refuses a challenger named without it. Settling a challenger against
the full-history baseline would have carried the training-coverage confound into the euro
figures, where it is harder to see and easier to quote.

The settled-arm record names all four groups separately.

## What is preserved

The full-history baseline remains the accepted computation, bit for bit. That is asserted by
test, and it matters: its comparison with the matched control is the measurement of training
coverage, which is only meaningful if the baseline is unchanged.

A test that previously asserted the *control* reproduced the accepted ML dispatch benchmark now
asserts it of the full-history arm. The matched control deliberately does **not** reproduce it —
it trains on fewer rows, and reproducing the accepted benchmark would mean the match had failed.

## Validation

- Ruff
- mypy (65 source files)
- pytest: 684 passed, up from 677
- isolated wheel build

New regression tests cover: the three arms recorded and named, with the matched control reading
the baseline's columns; every matched refit agreeing on training row and target digests and on
interval counts; a synthetic fixture with missing weather days proving both matched arms drop the
same rows while the full-history arm does not; a matched pair with differing row digests being
refused; the full-history baseline still reproducing the accepted computation; every arm
producing a value on every common day with excluded days still recorded by cause; and the matched
control being selected on validation only.

Nothing here accepts a feature table, admits a source or produces a benchmark figure.
