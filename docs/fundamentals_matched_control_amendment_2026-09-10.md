# Prospective amendment — matched-training control for the fundamentals ablation

**Date:** 10 September 2026
**Status:** Prospective. Recorded before any comparison outcome exists.
**Amends:** the v0.9 fundamentals ablation declared in `docs/v0.9_design.md` and
`docs/fundamentals_declarations_2026-09-03.md`.
**Execution-plan stage:** 6. **Review finding:** 8.

## Why this is recorded before the comparison runs

No fundamentals benchmark has been executed against official data. The retrieval of the declared
window has not completed, no feature table has been accepted, and no weather result exists in
this repository. This amendment is therefore prospective in fact and not only in name: it fixes
the comparison structure while its outcome is unknown to everyone, including whoever wrote it.

A control chosen after seeing which arm won is not a control. Recording this now is what makes
the resulting comparison evidence rather than a description of a choice already made.

## The defect in the declared ablation

The declared ablation compares two arms:

- a **control** of calendar and price-history features, trained on every day in the causal
  feature table;
- a **challenger** of those features plus the accepted point-in-time weather columns, trained
  only on days whose weather features are complete, because a missing feature excludes its day
  rather than being imputed.

Those two arms differ in **two** ways at once: the feature columns, and the training rows. A day
without accepted weather is in the control's training set and absent from the challenger's. Any
difference between them therefore confounds the value of the weather columns with the cost of
the training coverage lost to requiring them.

The direction of that confound is not knowable in advance. Fewer training rows would usually
hurt the challenger, which would understate weather value; but the excluded days are exactly the
days the weather source failed to cover, which need not be a random sample of the price
distribution. Either way the recorded number would not be what it claimed to be.

## The amendment

A third arm is added, and the existing arms are renamed so that no arm's role is implied by the
word "control" alone.

| Arm | Feature columns | Training rows |
| --- | --- | --- |
| `full_history_baseline` | calendar + price history | every day in the causal feature table |
| `matched_control` | calendar + price history | exactly the challenger's eligible days |
| `challenger` | those columns **plus** accepted weather | exactly the challenger's eligible days |

The naïve price-only forecasts remain as `baselines`, unchanged.

**What each comparison measures, declared now:**

- `challenger` − `matched_control` is attributable to the weather columns. Only the columns
  differ; the rows, targets, model families, hyperparameters, seed, refit cadence, refit dates
  and evaluation days are identical.
- `matched_control` − `full_history_baseline` is attributable to training coverage. Only the
  rows differ; the columns are identical.
- `challenger` − `full_history_baseline` confounds the two and **will not be reported as a
  weather effect**.

## What is held fixed

For the matched pair: model families, hyperparameters, random seed, refit cadence, refit dates,
minimum training days, training window, validation and test boundaries, and the declared
evaluation days. The source, decision cutoff, sampling geography and test boundary are unchanged
by this amendment and are not revised after any run.

All arms are settled on the same declared held-out days — the intersection of days complete for
every arm — and days excluded from that intersection remain recorded with their named cause
rather than disappearing.

## How the match is enforced rather than asserted

Each refit records a digest of its training row identities and a digest of its training targets,
computed independently of the feature columns read. The benchmark refuses to produce a result
unless every matched pair agrees on both digests at every refit.

This is deliberate: the claim "only the feature columns differ" is the whole basis for
attributing a difference to weather, and a claim that is only stated in prose stops being true
the first time either arm's row selection changes for an unrelated reason.

## Settlement into euro

The dispatch comparison pairs each challenger with its **matched control**, not with the
full-history baseline. Settling a challenger against the full-history baseline would carry the
training-coverage confound into the euro figures, where it would be harder to see and easier to
quote.

## What this amendment does not do

It launches no retrieval, accepts no feature table, and produces no benchmark outcome. It does
not change the declared source, cycle, geography, decision cutoff, feature set, evidence grades
or held-out period. It does not predict which arm will perform better, and it commits in advance
to recording the result whichever way it falls — including a result in which the weather columns
add nothing, or subtract.
