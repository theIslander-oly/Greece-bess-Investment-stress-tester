# Project status

**Version:** 0.9.7
**Updated:** 15 September 2026
**Validation:** [Current CI](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/workflows/tests.yml) runs Python 3.12 and 3.13. Dated implementation reports record suite counts.

This page states where the work stands today. The dated record of how it got here is in
[`docs/history/status_log_through_2026-09-11.md`](docs/history/status_log_through_2026-09-11.md);
the stage tracker and what happens next are in [`PLAN.md`](PLAN.md).

## Readiness audit — 15 September 2026

[The Stages 1–9 audit](docs/history/implementation_report_stages1-9_audit_2026-09-15.md)
checks retained official artifacts and reproduces a Stage 9 library-input defect: RMSE trusted
a copied actual-price column while settlement used canonical prices. The repair refuses
inconsistent copies; the retained official table agrees exactly and its result is unaffected.
The maintenance branch is `codex/audit-stages1-9`, stacked on the release preparation.
Review this repair and its prospective declaration before completing release review.

Price and feature custody verify, Stage 7 manifests verify, all 200 matched refit pairs agree,
and the latest witness covers all three variables. Current-code feature reconstruction matches
the accepted feature and audit digests and all 2,124 daily coverage records. All 807 tests,
Ruff, mypy and a clean wheel build pass locally. Stage 8 is implementation-complete;
its original official-history acceptance check is still pending under Stage 10. Historical
benchmark reproduction also requires recorded dependencies, not this workstation's defaults.

## Where the work stands

Stages 1–7 and 9 have recorded completion evidence. Stage 8 has completed implementation and
synthetic validation; its official-history acceptance check remains open under Stage 10. Stage 9 result PR #77 merged
as `abfac6a`; CI run `34824236600` passed on Python 3.12 and 3.13. Stage 10 is in progress on
`release-integrated-research-study`. Nothing is renumbered.

The Stage 10 release layer now lets one configuration declare deterministic synthetic generation,
run the integrated study and render its verified manifest in one command. Repeated runs of the
committed demonstration produced byte-identical daily, strategy, cash-flow and summary artifacts.
The renderer now presents every recorded strategy field side by side without deriving a ranking,
cross-configuration figure or shared ceiling.

The [official Stage 10 declaration](docs/integrated_study_run_declaration_2026-09-14.md)
preregisters a 329-day accepted-history study and a controlled 50 MW/100 MWh versus
25 MW/100 MWh configuration sensitivity. The prepared workflow checks the declaration digest
and existing custody before prices are read, runs both fixed configurations, renders only their
verified manifests and seals a private evidence bundle. It performs no publication. The next
action is review, validation and merge of that workflow change; an official dispatch and any
publication remain separately gated.

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

The [official Stage 9 result](docs/selection_benchmark_2026-09-11.md), run `34623616511`,
records EUR 12,639.14 more settled margin for validation-margin selection over validation-RMSE
selection on 329 complete evaluation days, under the declared 50 MW / 100 MWh battery.
The margin-selected candidate also cycled more. This is retrospective supplementary evidence
on one inspected window; it changes no shipped selection policy. Existing custody, declaration
digests, complete calendars and the frozen selection record verified, and private evidence is
retained independently of result sign.

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
| Stage 9 official selection comparison | [`docs/selection_benchmark_2026-09-11.md`](docs/selection_benchmark_2026-09-11.md) |

The earlier fundamentals benchmark remains mixed by model family: `ridge_fundamentals`
earned EUR 4,899.71 more settled margin
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
