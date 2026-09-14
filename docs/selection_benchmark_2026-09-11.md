# Stage 9 official selection comparison — 11 September 2026

Historical Greek DAM research and pre-feasibility evidence only; not financial advice,
expected revenue, a bankable forecast or an investment-grade study.

## Finding

Margin-based selection earned more settled margin on the declared evaluation window. The
recorded margin-selection minus RMSE-selection difference is **EUR 12,639.14**. The
margin-selected candidate also cycled more; this comparison includes no monetary wear cost.

| Evaluation metric | Validation-RMSE selection | Validation-settled-margin selection |
| --- | ---: | ---: |
| Frozen candidate | ridge_alpha_1 | gradient_lr_005_leaf_15 |
| Settled margin (EUR) | 3,651,359.54 | 3,663,998.68 |
| Market cash margin (EUR) | 3,651,359.54 | 3,663,998.68 |
| Perfect-foresight gross-margin upper bound (EUR) | 4,804,428.23 | 4,804,428.23 |
| Regret against perfect foresight (EUR) | 1,153,068.69 | 1,140,429.55 |
| Regret against retrospective best candidate (EUR) | 12,639.14 | 0.00 |
| Grid charge (MWh) | 55,193.80 | 55,449.49 |
| Grid discharge (MWh) | 48,769.25 | 48,995.17 |
| Equivalent full cycles | 487.69 | 489.95 |
| Price RMSE (EUR/MWh) | 32.48 | 31.74 |
| Price MAE (EUR/MWh) | 22.70 | 21.94 |
| Capture of perfect-foresight upper bound | 76.00% | 76.26% |

The headline and table transcribe the producing summary, rounded for display. The signed
difference is taken from its recorded field, not calculated from rounded displayed totals.

## Declared basis

The [dated declaration](selection_run_declaration_2026-09-11.md) and
[selection protocol](value_based_selection_design.md) fix the comparison:

- Six existing price-only candidates, in tie-break order: `ridge_alpha_1`, `ridge_alpha_10`,
  `ridge_alpha_100`, `gradient_lr_005_leaf_15`, `gradient_lr_010_leaf_31`,
  `gradient_lr_020_leaf_7`.
- 50 MW / 100 MWh; 50 MW grid import/export; 5–95% SOC; 50% initial and daily terminal SOC;
  94% efficiency each way; 1.5 daily equivalent cycles; full availability; zero fees,
  self-discharge and monetary wear penalty. No physical degradation or finance.
- Training history begins 1 November 2020. Validation: 1 October 2024–30 September 2025
  (365 complete market days). Evaluation: 1 October 2025–25 August 2026
  (329 complete market days).
- Shared causal price features: 28-day feature window; 28 minimum training days; seven-day
  refits; expanding training; seed 42. Gradient maximum iterations 150, L2 regularization 1.0;
  candidate-specific overrides are as declared.
- Candidate identities freeze once using validation only. Fits can use earlier evaluation
  days after they become history. Both arms settle against realized prices under equivalent
  physical and terminal-energy constraints.
- Evidence class: **retrospective_supplementary**. Hourly validation precedes quarter-hour
  evaluation; this measures regime transfer as well as performance over one inspected window.

## Validation and provenance

The operator approved the declaration and one dispatch after successful merged-commit CI,
then authorized publication of the prepared private aggregate record. These are separate
approvals; neither changes the shipped selection policy.

- Comparison: [run 34623616511](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34623616511), attempt 1; all workflow steps succeeded.
- Accepted history: run `33483975614`. Existing custody verified before prices were consumed;
  no replacement acceptance record or fresh retrieval.
- Source commit: `1fdd81628951c02c185b3b806318385038a5137a`.
- Declaration SHA-256: `78822530a6f9c1d2f0f45e50ea08d0864dffd4ebf23c989cc4cb5428751fc611`.
- Evidence-index SHA-256: `33e78be5952c1f3afd5632b6ec0709d73f99839537ada77ba3e2c3ad058c0bcc`.
- Frozen selection SHA-256: `47d8ba1281daa3e0f9529e241ebab4139df7d1fbebbc23023e8c300fc1bc2ccc`.
- Candidate forecast SHA-256: `9bbe2a36513d7fd5b4efcc7601e5f5603d8576084b969416142db9f917c0bca3`.
- Runtime: Python 3.12.14; numpy 2.5.3; pandas 2.3.3; scipy 1.18.1; scikit-learn 1.9.1;
  greek-bess-investment-stress-tester 0.9.7.
- Artifact: `selection-comparison-private` (ID `10274111580`), ZIP SHA-256
  `ecafeaa7c8cf44d13cd0e69d2bc752c50ba4dd5f66d66d1a7b9ca0df7bf8d01a`;
  expires 10 December 2026 at 16:43:18 UTC. An exact ZIP and extracted evidence are also
  retained locally outside Git.

Independent checks passed for all indexed file digests, declaration pins, input/output
identity, exact native calendars including DST, all-candidate coverage, retained forecast
price errors, validation-only picks and tie breaks, the selection seal, and summary/scoreboard
reconciliation. The archive matched GitHub's digest and every extracted file matched that
archive. Numerical command output was absent from the ordinary workflow log.

Private evidence is retained irrespective of result sign. Workflow timeout: 180 minutes;
GitHub artifact retention: 90 days. This is not independent durable custody. Reproduction
uses the recorded source commit, declaration, runtime and accepted source artifact; the
existing custody recovery procedure applies if that artifact expires. Any further official
dispatch requires its own authorization.

## Interpretation and remaining gates

This is one already inspected historical window, not a distribution, a confirmatory test or
evidence that the result sign will recur. The perfect-foresight figure is a gross-margin upper
bound, never expected revenue. The retrospective best candidate uses evaluation outcomes and
is a diagnostic ceiling, not an achievable selection policy.

Intraday, balancing, reserves, taxes, subsidies, grid feasibility and revenue stacking remain
excluded. Price-taking and full acceptance of planned quantities are assumed. The shipped
selection policy remains unchanged.

This record publishes approved aggregates and provenance only. Raw prices, interval forecasts
and private diagnostics remain outside Git. The evidence index is not a registered renderer
manifest; Stage 10 and any public report deployment remain separately gated.
