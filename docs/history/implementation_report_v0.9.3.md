# Implementation report v0.9.3 — fundamentals forecast ablation

**Date:** 2 September 2026

## Scope and result

v0.9.3 adds the two-arm forecast ablation the v0.9 design names as its analytical core:
`forecast/fundamentals.py` and the `benchmark-fundamentals-forecast` command, plus the one
parameter in `forecast/ml.py` that makes an ablation possible without a second walk-forward loop,
the `fundamentals_forecast_benchmark` manifest kind, and one renderer checklist entry.

Like v0.9.1 and v0.9.2, it is built and tested exclusively against synthetic fixtures.
`config/decision_cutoff.json`, `config/decision_lead_minutes.txt` and
`config/fundamentals_geography.json` do not exist, so no accepted feature table exists, so no
benchmark figure, manifest or acceptance document was produced. No declaration was invented,
defaulted or inferred. No accepted price-history figure changed, and the regression that proves it
is in the test suite rather than in this sentence.

## The ablation contract

**One thing varies.** The control arm is the accepted ML benchmark unchanged: `ridge` and
`hist_gradient_boosting` on `FEATURE_COLUMNS`. The challenger arm is the same two families, the
same fixed hyperparameters, the same `random_seed`, the same refit cadence and the same
walk-forward loop, with the accepted point-in-time columns appended and named
`ridge_fundamentals` and `hist_gradient_boosting_fundamentals`. Both arms iterate the same target
days, so both refit on the same days even where the challenger has no rows to predict.

**`ml.py` changed by one parameter, and the change is proved inert.** `_walk_forward_predict`
gains `feature_columns`, defaulting to `FEATURE_COLUMNS`, and `require_non_null`, naming columns
that must be complete wherever the model reads them. `generate_ml_forecasts` is untouched. A
regression asserts the control arm's predictions and refit logs equal `generate_ml_forecasts`
bit for bit on the same prices and config.

**A missing feature excludes its day.** The pipeline's `SimpleImputer` exists for the price-lag
warm-up gaps and must never invent an exogenous value; `require_non_null` makes the loop refuse
rather than impute, at fit and at predict. A day the join excluded is dropped from the
challenger's training rows, the dropped-interval count is recorded, and the day is excluded from
every arm's evaluation by the join's own named cause.

**Both arms are measured on one calendar.** The evaluation set is the intersection of days
complete for every naive baseline, for the control and for the challenger. The control's metrics
on its own unreduced calendar are recorded alongside, so the size of the reduction is visible
rather than implied.

**Inputs are identified, not described.** `join_point_in_time_features` now records
`feature_set_sha256` over the joined interval frame. The benchmark declares that digest, the
cutoff schedule identity, the decision lead and the admitted evidence grades, and refuses to run
unless every one equals what the join recorded and the frame supplied hashes to the digest its
own summary states. The digest survives the CSV round trip between the two commands, and a test
runs both commands through files to prove it.

**Selection is on validation only.** Within each arm the reported model is the lower validation
RMSE on the common days. Test metrics never select. The recorded policy also states that the
feature set, the split and the cutoff are never revised after a test run.

**Slices are declared.** Accuracy on the held-out common days is additionally reported by
delivery year, by market-clock interval of day, by declared price regime and by resolution era.
`--price-regime-bands` is required, has no default, and is recorded with the run; the renderer's
landing checklist gains an entry naming it, following the project's convention that a judgmental
input with no default appears there.

**The exploratory rule is executable.** A run is exploratory when the join recorded itself as
exploratory, when the quarantined `assumed` grade is admitted, or when the common held-out days
do not cover a complete meteorological season of quarter-hour deliveries. A season counts only
when every one of its calendar days is present: any weaker threshold would be a judgmental
default, and the project's convention is to err toward the exploratory label rather than invent
one. The causes are recorded and the label carries the suffix.

## Contract and renderer

`fundamentals_forecast_benchmark` is registered on the `historical_forecast_backtest` basis with
the eleven guaranteed summary keys the design names. `forbids_distributional_terms` is left
unset, for the reason the contract module already gives: a mean error and a median absolute error
are statistics about a model, not claims about a distribution of outcomes. The summary instead
declares `is_probabilistic`, `is_forecast` and `is_investment_evidence` as `false`, which the
contract cross-checks.

One new check joins the two the contract already applies on record and on read: a summary that
admits the quarantined `assumed` availability grade while declaring `is_exploratory` anything but
`true` is refused. It runs on read because a hand-edited manifest is exactly the case it exists
for, and the renderer reads through that doorway, so such a manifest refuses the whole report.

The renderer needs nothing else: its generic path renders a nested summary as recorded detail,
and it computes nothing.

## Synthetic verification

Twenty-nine tests cover the design cases assigned to this phase and the ones its own refusals
add: the control arm's bit-for-bit reproduction of the accepted benchmark; both arms on identical
common days; repeated runs bit-identical; held-out label mutation leaving validation metrics and
both selections unchanged; a day without an accepted feature leaving every arm by named cause
with its training rows dropped; the NaN-at-fit refusal and the refusal of a completeness
requirement over a column that is not a model input; refusals for a frame that is not the
declared feature set, a benchmark naming another feature set, a summary with no digest, a cutoff
or lead or grade set differing from the join's, a feature frame built from other prices, absent
or non-ascending price bands, and a feature column with no recorded provenance; the season gate,
including that a single missing day disqualifies a season and that winter is named for the year
its January falls in; provenance covering the closed variable registry; manifest recording and
reading, a missing guaranteed key, and both hand-edited refusals; and both commands run through
files so the feature-set digest is proved to survive the CSV round trip.

## Interpretation

Nothing here is accepted and nothing here is a figure. What the milestone establishes is that the
comparison, if it is ever run on an accepted feature table, will vary one thing and will refuse
to run on inputs it cannot identify. Price error remains the secondary measure; realized settled
dispatch value is primary and is v0.9.4's surface. Perfect foresight remains a historical
gross-margin upper bound, and ADMIE-originated forecasts remain excluded by every route.

The scheduled witness workflow still has no declarations with which to pass its guard, and every
refused target day permanently costs one witnessed day.

## Verification record

Ruff passed, mypy passed over 63 source files, all 556 tests passed, and a clean wheel build
succeeded on Python 3.12. The declared project version moved to 0.9.3 in `pyproject.toml`,
`greek_bess.__version__` and the README release line, and `docs/sample_report.html` was
regenerated for that version; its diff is the version string and the manifest digests that follow
from it, with no analytical value changed. The complete diff was reviewed for generated output,
official data, secrets and ignored-artifact leakage; build products were removed before commit.
