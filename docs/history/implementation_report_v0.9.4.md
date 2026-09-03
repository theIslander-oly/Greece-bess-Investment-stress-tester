# Implementation report v0.9.4 — settled fundamentals dispatch comparison

**Date:** 3 September 2026

## Scope and result

v0.9.4 adds the surface the v0.9 design names as the milestone's primary measure:
`backtest/fundamentals_dispatch.py` and the `benchmark-fundamentals-dispatch` command, plus the
`fundamentals_dispatch_benchmark` manifest kind and the paired-difference artifact. It answers in
euro the question v0.9.3 answered in price error — on the same delivery days, under the same
battery and the same realized prices, did the fundamentals-augmented model settle more value than
the identical model on price history alone?

Like v0.9.1 through v0.9.3, it is built and tested exclusively against synthetic fixtures.
`config/decision_cutoff.json`, `config/decision_lead_minutes.txt` and
`config/fundamentals_geography.json` do not exist, so no accepted feature table exists, so no
settled figure, manifest or acceptance document was produced. No declaration was invented,
defaulted or inferred, and no accepted price-history figure changed.

## The comparison contract

**The module is thin on purpose.** Planning and settlement go through
`ml_dispatch._backtest_precomputed_forecast`, the accepted path the ML dispatch benchmark already
uses. An arm run through the new surface is therefore the accepted computation with a different
forecast column and nothing else, and a test asserts that: the control arm and the naive
baselines reproduce `backtest_ml_dispatch_benchmark`'s realized margin, ceiling, regret, capture
ratio, planned margin and turnover figure for figure on the synthetic suite. What the module adds
is the comparison discipline around that path, not a second dispatch implementation.

**The days are the ablation's own, and a gap is a contradiction rather than an exclusion.** The
evaluation set is the held-out subset of the days the forecast benchmark recorded as common to
every baseline and both arms. The module never widens that set and never re-derives it. Where
every other stage excludes an unusable day by named cause — correctly, because there the
exclusion is a property of the data — an exclusion here would give two arms different calendars
while every label still claimed they shared one. A missing forecast on a recorded common day is
therefore refused by naming the method and the count, and so is a forecast table whose held-out
common day count disagrees with its own summary. Both refusals say the table and the summary
disagree; the fix is upstream.

**Equivalence is asserted and written down.** One `BatteryDispatchConfig` plans every arm, and
`_backtest_precomputed_forecast` already refuses a terminal SOC that differs from the initial
SOC, so every day starts and ends in the same energy state. One realized price series settles
every arm. The perfect-foresight ceiling is checked identical across arms to an absolute 1e-6
EUR, and a wider spread is refused by naming the two arms and their ceilings rather than
reconciled. `equivalent_basis` records what was shared, in the groups a reader has to check
separately: the battery parameters, the terminal-energy convention, the settled interval range,
the common-day identity and its digest, the shared ceiling with the tolerance that proved it, and
the feature-set identity carried from the ablation.

**Every challenger is settled beside its own control.** `--methods` is required with no default,
because a comparison states which arms it settled. A challenger named without its control is
refused: comparing it against anything but the identical model on price history alone is not the
ablation. Naming baselines as well produces a second, separately recorded set of incremental rows
rather than mixing the two comparisons.

**The incremental figure is recorded here, never derived downstream.** The difference between two
recorded margins is itself a result, and results belong to the module that owns the basis. A
renderer that subtracted one figure from another would be computing, and would be doing so
without any way to check the two were comparable. `incremental_realized_margin_eur` is therefore
a guaranteed key of the new manifest kind, recorded together with `equivalent_basis`.

**The paired differences are published; nothing is derived from them.** One row per comparison
and delivery day carries both settled margins, their difference, the interval count and that
day's ceiling. The summary records the sign counts, the total and the largest daily gain and
shortfall. No dispersion, interval or significance statistic is computed. A moving-block
bootstrap of the differences or a Diebold-Mariano-style comparison would be a statement about the
sampling variability of a statistic rather than a market probability, and adopting either is a
separate decision with its own wording (decision entries 2026-08-27 and 2026-09-03).

**A negative result is recorded as it stands.** A challenger that settles less than its control
produces a negative incremental margin under the same labels, and a test asserts that path
explicitly rather than only the favourable one.

## Contract and renderer

`fundamentals_dispatch_benchmark` is registered on the `historical_forecast_backtest` basis,
guaranteeing `result_label`, `comparison_methods`, `common_backtest_day_count`,
`perfect_foresight_margin_eur`, `equivalent_basis`, `dispatch_ranking`,
`incremental_realized_margin_eur` and `is_exploratory`. `REPORT_CONTRACT_VERSION` stays 1 and the
envelope is unchanged, so every older manifest still reads and still renders.

`forbids_distributional_terms` is left unset, and the reason is sharper here than for the
forecast benchmark: `dispatch_ranking` would trip the term list on the word "rank" alone. An
ordering of named methods by a recorded euro amount is an ordering of results, not a claim about
a distribution of outcomes, and a check that refused it would teach a reader the check is noise.
The summary instead declares `is_probabilistic`, `is_forecast` and `is_investment_evidence` as
`false`, which the contract cross-checks on record and on read; and because the summary carries
`evidence_grades_admitted`, the quarantined-`assumed` check added in v0.9.3 applies to this kind
too.

The renderer needs no change. The decision cutoff and lead already have a checklist entry, this
milestone introduces no new judgmental input with a default to refuse, and no composition section
is registered for the kind — `equivalent_basis` renders through the generic path. An ablation
layout remains a v0.9.5 option, and if it is built the producing module will still record the
rows.

## Synthetic verification

`tests/test_fundamentals_dispatch.py` adds 25 tests over five groups. The settled-comparison
group runs the full chain on a synthetic fixture whose exogenous feature is a deliberately
constructed pre-cutoff predictor, so that the non-zero incremental path is tested rather than
assumed; the fixture used by the v0.9.3 suite carries a feature uncorrelated with price, which
settles identically in both arms and therefore cannot exercise it. Neither fixture is evidence
about any real variable.

That group covers the reproduction of `backtest_ml_dispatch_benchmark`, the recorded equivalence,
the agreement between the summary's incremental margin and the sum of the paired daily
differences, a challenger whose plan and margin actually move, bit-identical repeated runs, and
adversarial case 17 — mutating realized prices after planning leaves every planned MW identical
while changing both the settled margin and the ceiling.

The refusal group covers an unpaired challenger, an unknown method, an empty and a repeated
method list, a summary that does not identify its ablation, a gap on a recorded common day, a day
count disagreeing with the summary, a table with no common held-out day, a terminal SOC differing
from the initial SOC, and adversarial case 18 — two batteries producing two ceilings, refused by
name.

The arithmetic group checks the recorded increments against a closed-form two-day case in both
directions rather than trusting the implementation, and the manifest and command groups cover
recording under the new kind, a hand-edited manifest refused on read, a summary missing a
guaranteed key, and the command writing its four artifacts and refusing an unpaired challenger
through the CLI.

## Interpretation

Nothing here is accepted and nothing here is a figure. What the milestone establishes is that the
comparison, if it is ever run on an accepted feature table, will settle both arms on one basis
and will refuse to run when that basis does not hold. An incremental margin from it would be a
historical outcome on one period, under one battery, against a market history that almost
entirely predates operating battery competition — not expected revenue, not a rate, and not
transferable to another battery, cutoff or period.

The remaining v0.9 surface is v0.9.5: manifest and report integration and the official acceptance
run, which still cannot start. The scheduled witness workflow has no declarations with which to
pass its guard, and every refused target day permanently costs one witnessed day.

## Verification record

Ruff passed, mypy passed over 64 source files, all 582 tests passed, and a clean wheel build
succeeded on Python 3.12. The declared project version moved to 0.9.4 in `pyproject.toml`,
`greek_bess.__version__` and the README release line, and `docs/sample_report.html` was
regenerated for that version; its diff is the version string and the manifest digests that follow
from it, with no analytical value changed. The complete diff was reviewed for generated output,
official data, secrets and ignored-artifact leakage; build products were removed before commit.
