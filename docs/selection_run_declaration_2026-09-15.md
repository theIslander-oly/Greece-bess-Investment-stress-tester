# Stage 9 run declaration after input-validation repair — 15 September 2026

## Scope

This prospective declaration retains the complete protocol of the
[11 September declaration](selection_run_declaration_2026-09-11.md): identical accepted history,
validation/evaluation windows, six candidates, fitting settings, battery, selection objectives,
tie rules and retrospective interpretation. That original document remains unchanged and
continues to identify the accepted result from run `34623616511`.

The sole analytical-code change refuses a candidate table whose copied actual prices are
missing or disagree with the settlement price file on any interval (absolute tolerance
1e-9 EUR/MWh, zero relative tolerance). Without the check, RMSE could select using different
actuals from those used by dispatch. The retained official forecast table has zero discrepancy;
its recorded result is unaffected by this refusal-only change.

The workflow helper now reads this document. The two changed implementation identities are
pinned below; all other pins are retained. No run has been performed under this declaration.
Review and merge the repair before authorizing any fresh official dispatch. Existing evidence
can be checked without a new benchmark; reproducing the original declaration requires its
historical implementation. No publication or selection-policy change is authorized here.

## Machine-readable declaration

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
    "src/greek_bess/selection/experiment.py": "124adeefbb852cd8c7ed6cf304b0fc8e128c23d28579fd19ed698f6debe1ff89",
    "src/greek_bess/forecast/ml.py": "72a691f5674f54d0b53f01065d34c121ad61759fb0c3d6a5b8a83a7db76004ae",
    "src/greek_bess/cli/selection.py": "7a195c0a7fdc13eb0671a020237fd81693b5082a69a095d614cc0515941b998a",
    "docs/value_based_selection_design.md": "51203e4e76ecb03729ea95b47e3440a7343fd9b05eec3586f5c4db39592d9293",
    "docs/custody/greek-dam-official-history.json": "4a68737b9dd53881c4b183926fd857f5a885158110a4909bfe4a6e8cb0de3a96",
    ".github/workflows/benchmark-selection.yml": "10c9eac99c45253bc117881706edc727a0ba88afd089aae4020a01212f486f5b",
    ".github/scripts/selection_run.py": "2e55dc3b9cf6386fafa4a196c86fb38996e16f469e691b3e90ff3bdeff56d9b6"
  }
}
```
