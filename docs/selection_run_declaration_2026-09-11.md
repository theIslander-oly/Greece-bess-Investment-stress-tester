# Stage 9 official-run declaration — 11 September 2026

Prepared before the Stage 9 official comparison is run. This document specifies a reviewable
run; it does not record operator authorization, a completed run or a result. Dispatch requires
operator approval of this declaration and its SHA-256. Publication is a separate gate.

## Fixed comparison

Reuse accepted history run `33483975614`, verified against its existing custody record before
reading prices. No retrieval, replacement custody record, features from external sources or new
model family is needed. Refuse expired/missing artifacts; use the documented custody recovery
process separately instead of silently changing the source run.

Training history begins 2020-11-01. Validation is 2024-10-01 through 2025-09-30 (365 days);
evaluation is 2025-10-01 through 2026-08-25 (329 days). These are the existing benchmark split
and accepted history end, chosen for continuity rather than observed Stage 9 performance.
All dates are market-clock delivery days; DST-aware native intervals are preserved.
Any missing day or incomplete interval coverage fails the run, without filling or shortening it.

Both objectives use the existing six candidates, in this exact tie-break order:

| Index | Candidate | Overrides |
| --- | --- | --- |
| 0 | ridge_alpha_1 | ridge_alpha=1 |
| 1 | ridge_alpha_10 | ridge_alpha=10 |
| 2 | ridge_alpha_100 | ridge_alpha=100 |
| 3 | gradient_lr_005_leaf_15 | gradient_learning_rate=0.05; gradient_max_leaf_nodes=15 |
| 4 | gradient_lr_010_leaf_31 | gradient_learning_rate=0.10; gradient_max_leaf_nodes=31 |
| 5 | gradient_lr_020_leaf_7 | gradient_learning_rate=0.20; gradient_max_leaf_nodes=7 |

Shared price-only causal features: 28-day window, 7-day refit cadence, 28 minimum training days,
expanding training window, seed 42. Other fitting settings are the pinned `MLForecastConfig`
defaults: gradient_max_iter=150 and gradient_l2_regularization=1.0. The candidate overrides
above take precedence. Fits can use earlier evaluation days as they become history; the selected
candidate identity is frozen once and never reselected. Tolerances remain 1e-9 EUR/MWh for RMSE
and 1e-6 EUR for margin. The pinned design defines the full settlement and reporting protocol.

Use `examples/battery_50mw_100mwh.json` unchanged: 50 MW / 100 MWh, 5–95% SOC, initial and
terminal SOC 50%, each-way efficiency 94%, 1.5 daily equivalent cycles, zero fees and monetary
wear penalty. No physical degradation or finance is added to this comparison.

## Interpretation and retention

Evidence class is **retrospective_supplementary**: this history has already been inspected.
Hourly validation precedes quarter-hour evaluation, so this measures transfer between regimes
as well as performance on one window. It supports no confirmatory or probability claim.

Retain the signed margin-selection-minus-RMSE-selection difference whatever its sign, including
zero when both objectives choose the same candidate. Retain all candidate scoreboards, forecasts,
the frozen record, input/output digests, runtime versions and private command diagnostics.
A completed bundle requires `evidence_index.json`; diagnostics without that index are a failed
attempt, not a result. GitHub artifact retention is 90 days and is not independent durable custody.

The workflow writes no research numbers to ordinary logs or the job summary, commits no data,
and publishes no report. The evidence index is a workflow provenance record, not a generic
run manifest: Stage 9 has no registered renderer kind yet. Rendering belongs to the subsequent
reviewed release work. An eventual approved aggregate result must record an unfavourable result
as readily as a favourable one. Neither outcome changes the shipped selection policy.

## Machine-readable declaration

These byte digests pin the protocol, configuration, implementation and workflow. A change
requires a new reviewed document digest. The operator supplies the SHA-256 of this whole file;
it is deliberately not embedded in itself.

```json
{
  "history_run_id": "33483975614",
  "history_first_day": "2020-11-01",
  "history_last_day": "2026-08-25",
  "validation_first_day": "2024-10-01",
  "validation_last_day": "2025-09-30",
  "evaluation_first_day": "2025-10-01",
  "evaluation_last_day": "2026-08-25",
  "evidence_class": "retrospective_supplementary",
  "input_sha256": {
    "examples/battery_50mw_100mwh.json": "c9156ef29f9e364d84cf1d74fb32c789c0ff612180b47d7a43f0c77d187079f2",
    "src/greek_bess/selection/candidates.py": "b48094e9c3ecb082007992d96a11de083035dd3a8443439d197464176c164865",
    "src/greek_bess/selection/experiment.py": "89a817d2662b04f520dcd6bf87edc7645c3a365383bd63591b5b8394eea84345",
    "src/greek_bess/forecast/ml.py": "72a691f5674f54d0b53f01065d34c121ad61759fb0c3d6a5b8a83a7db76004ae",
    "src/greek_bess/cli/selection.py": "7a195c0a7fdc13eb0671a020237fd81693b5082a69a095d614cc0515941b998a",
    "docs/value_based_selection_design.md": "51203e4e76ecb03729ea95b47e3440a7343fd9b05eec3586f5c4db39592d9293",
    "docs/custody/greek-dam-official-history.json": "4a68737b9dd53881c4b183926fd857f5a885158110a4909bfe4a6e8cb0de3a96",
    ".github/workflows/benchmark-selection.yml": "10c9eac99c45253bc117881706edc727a0ba88afd089aae4020a01212f486f5b",
    ".github/scripts/selection_run.py": "c8c760fb10dfea7431478229192e3574102ac6723f4c71005c4f053ecdcb3ab4"
  }
}
```

## Dispatch after approval

Workflow: `Compare official selection objectives`. Inputs: `history_run_id=33483975614`
and `declaration_document_sha256` from `sha256sum docs/selection_run_declaration_2026-09-11.md`.
Review the workflow commit and CI before dispatch. A merged workflow is not authorization
to publish its output or to change a model-selection default.
