# Project status

**Version:** 0.9.7
**Updated:** 11 September 2026
**Validation:** [Current CI](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/workflows/tests.yml) runs Python 3.12 and 3.13. Dated implementation reports record suite counts.

This page states where the work stands today. The dated record of how it got here is in
[`docs/history/status_log_through_2026-09-11.md`](docs/history/status_log_through_2026-09-11.md);
the stage tracker and what happens next are in [`PLAN.md`](PLAN.md).

## Where the work stands

Stages 1 through 8 of `Greek_BESS_Execution_Plan.md` are complete. Stage 9 is in progress: it
has a predeclared protocol, a working implementation and its synthetic proof, and no
official-history measurement yet. Nothing is renumbered.

The tool retrieves an official Greek DAM price history, records and renders it under custody and
manifest gates, optimizes perfect-foresight dispatch against it, backtests naive and ML forecasts
settled at realized prices, ages a battery under a cohort degradation model, evaluates unlevered
project finance, applies deterministic stress scenarios, and runs all of that end to end for
several competing strategies through one integrated study command.

The most recent substantive work is Stage 9's method. `greek_bess.selection` and
`compare-selection-objectives` compare selecting a forecast by validation RMSE against selecting
it by validation settled margin: one declared candidate grid, both objectives scored on the same
validation days under one battery configuration, each pick frozen and hashed before any
evaluation day is settled, ties broken by declared order and recorded. The protocol is
predeclared in [the Stage 9 design](docs/value_based_selection_design.md).

What exists is a method and a synthetic proof that the two objectives can select differently — a
forecast wrong by a constant preserves every intraday ordering and dispatches at the ceiling,
while one that is right almost everywhere but moves the cheapest hour has the better RMSE and
settles less. What does not exist is a measurement on official data. The manual workflow
`Compare official selection objectives` and its [dated declaration](docs/selection_run_declaration_2026-09-11.md)
are prepared for operator review. It verifies existing custody, fixes the complete calendar and
retains private evidence irrespective of outcome. Approval of the declaration and dispatch remain
the next gate, so Stage 9 makes no empirical claim today.

Before that, a numerical and accounting repair (#71) and its impact assessment (#72) corrected
IRR certification, partial-horizon break-even weighting, cash-versus-shadow-cost treatment and
cohort stored-energy accounting, and extended those conventions to the Stage 8 integrated study
runner that merged while the repair was open.

## What the repair did and did not move

No accepted official result changed, and nothing is stale. The
[impact register](docs/repair_impact_register_2026-09-11.md) compared every result-producing code
path across the pre-repair and post-repair revisions, frame by frame and column by column. The
perfect-foresight schedule, all four forecast backtests, all three annual decomposition tables and
fade-only degradation dispatch are bit-exact, so the annual ceilings, the EUR 24,974,729.59
accepted-history total, the capture ratios and the fundamentals ablation stand as recorded.

One figure moved anywhere in the repository: the synthetic demonstration's break-even average
annual margin, from EUR 53,908,552.74 to EUR 51,903,102.77. `docs/sample_report.html` was
regenerated inside the repair commit, so the committed file already carries it. No official rerun
is required.

Only a capacity change moves a degradation result. Fade alone does not: with terminal SOC equal to
initial SOC, carried energy scales exactly with usable capacity.

## The evidence produced so far

| Result | Where it is recorded |
| --- | --- |
| Accepted official price history and its custody | [`docs/official_history_acceptance_2026-08-26.md`](docs/official_history_acceptance_2026-08-26.md), [`docs/official_artifact_custody.md`](docs/official_artifact_custody.md) |
| Multi-year operational acceptance and cross-source reconciliation | [`docs/official_multiyear_operational_acceptance_2026-08-27.md`](docs/official_multiyear_operational_acceptance_2026-08-27.md), [`docs/official_source_reconciliation_2026-08-27.md`](docs/official_source_reconciliation_2026-08-27.md) |
| Per-delivery-year decomposition of the accepted replay | [`docs/official_annual_decomposition_2026-08-28.md`](docs/official_annual_decomposition_2026-08-28.md) |
| The pre-run declarations the operator approved on 3 September 2026 | [`docs/fundamentals_declarations_2026-09-03.md`](docs/fundamentals_declarations_2026-09-03.md) |
| Point-in-time fundamentals feature table, accepted by digest | [`docs/fundamentals_acceptance_2026-09-10.md`](docs/fundamentals_acceptance_2026-09-10.md) |
| The fundamentals benchmark result, mixed and recorded as mixed | [`docs/fundamentals_benchmark_2026-09-11.md`](docs/fundamentals_benchmark_2026-09-11.md) |
| What the accounting repair moved | [`docs/repair_impact_register_2026-09-11.md`](docs/repair_impact_register_2026-09-11.md) |

The fundamentals benchmark is the one place where a model comparison reached official data, and
its result is mixed by model family: `ridge_fundamentals` earned EUR 4,899.71 more settled margin
than its matched control and `hist_gradient_boosting_fundamentals` earned EUR 6,843.46 less, over
320 common held-out days. Favourable performance was never an acceptance criterion.

## Open gates

These are outstanding because something outside this repository has to happen first.

- **Public deployment of the accepted-replay report.** Render run `33609809770` produced the
  private report artifact and passed the custody and manifest gates; the Pages job landed
  afterward, so publication needs a new dispatch against decomposition run `33147448666`. This is
  the last mile of a delivered feature: no source behaviour, contract or report format changes.
- **A second custody copy under separate control.** Both encrypted copies are on one release, and
  one release is one failure domain. Nothing in this repository can perform or verify that
  placement.
- **`ENTSOE_SECURITY_TOKEN` is no longer configured**, so `Reconcile HEnEx and ENTSO-E prices`
  refuses at its guard step. The accepted evidence is safe in the custody copy; only regeneration
  is blocked.

## What this tool is not

Research and pre-feasibility only. Perfect foresight is a labelled gross-margin upper bound, never
expected revenue. Synthetic demonstrations are labelled as such and cannot support an investment
conclusion. Intraday, balancing, reserves, capacity payments, taxes, subsidies, grid feasibility
and revenue stacking remain excluded. See [`LIMITATIONS.md`](LIMITATIONS.md).
