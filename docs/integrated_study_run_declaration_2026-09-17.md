# Stage 10 official integrated-study declaration after resolution repair — 17 September 2026

This prospective declaration preserves the evidence, window, strategies, configurations,
degradation and illustrative finance assumptions in the 14 September declaration. Authorized
run `35191734263` failed before producing either study because the existing rolling mean had no
exact historical matches for the `:15`, `:30` and `:45` intervals on the first quarter-hour day.
Custody and the complete accepted-history calendar passed before that failure.

The repaired naïve forecaster applies one explicit resolution rule: a coarser historical price
may be broadcast to a finer target interval that it contains. It does not interpolate, fill a
missing native interval or aggregate finer observations into a coarser target. This is the same
containment direction already accepted for point-in-time features. It changes forecasts at the
hourly-to-quarter-hour transition, so the failed declaration is not silently reused.

This document specifies a new reviewable run. It does not record operator authorization, a
completed run, a result or permission to publish. Dispatch requires approval of this document
and its SHA-256 after the repair merges and final-head CI succeeds. Publication remains a
separate gate.

## Fixed evidence and horizon

Reuse accepted history run `33483975614`, verified against the existing committed custody record
before prices are read. No retrieval, replacement custody record, fundamentals feature or new
model family is part of this run. Refuse an expired or missing artifact rather than changing the
source run.

The retained history must be the complete market-day calendar from 1 November 2020 through
25 August 2026. The study horizon is 1 October 2025 through 25 August 2026, 329 market-clock
delivery days. Native quarter-hour intervals, including the 92-interval spring DST day, are
preserved. A missing or incomplete day fails the run; nothing is filled, shortened or treated as
a no-trade day.

This window has already been inspected. The evidence class is
`retrospective_aggregate_release`; it is not confirmatory evidence, a forecast, expected revenue
or an investment conclusion.

## Fixed strategies

Each configuration runs these strategies in this order:

1. `perfect-foresight-own-state`: plans on realized delivery-day prices. It is a daily
   perfect-foresight policy under its own evolving state, not a ceiling over the other strategies
   or a lifetime optimum.
2. `rolling-mean`: the repaired 28-day causal rolling-mean forecast, using only price history
   before the delivery day and the declared coarser-to-finer containment rule, settled against
   realized prices.
3. `forecast-ensemble`: the repaired causal naïve ensemble under the same information and
   settlement rule.

`daily_persistence` is not silently excluded after seeing a result. It is not declared because
the day after the 23-hour spring transition has no same-position observation on the preceding
day. The integrated-study contract refuses an incomplete forecast and forbids inventing that
interval. The rolling mean and ensemble preserve complete native calendars under this window.
On 1 October 2025 their historical hourly inputs are broadcast by containment to the quarter-hour
targets; from then onward native quarter-hour observations enter causally after each delivery day.

Every strategy starts with the same declared battery within a configuration, owns a separate
degradation and stored-energy state, restores 50% SOC at every day end, and is financed over
exactly the study horizon. Once states diverge, no shared conditional ceiling exists or is
reported.

## Preregistered configuration sensitivity

Run both committed configurations on the same prices, window, strategies, degradation rates and
illustrative finance assumptions:

| Configuration | Power | Energy | Daily cycle limit | Grid limits |
| --- | ---: | ---: | ---: | ---: |
| `official-integrated-study-50mw-100mwh` | 50 MW | 100 MWh | 1.5 EFC | 50 MW import/export |
| `official-integrated-study-25mw-100mwh` | 25 MW | 100 MWh | 1.0 EFC | 25 MW import/export |

Both retain the committed 5–95% SOC bounds, 50% initial/terminal SOC, 94% each-way efficiency,
zero fees, zero monetary wear adder and complete-day requirement. Physical degradation is the
same illustrative 1.5% calendar fade per year plus 0.004% per equivalent cycle, with no
augmentation event in this short historical window.

Finance is deliberately identical between configurations so this is a controlled physical-
configuration sensitivity, not a cost-optimisation exercise: EUR 50 million initial capex in
the committed category breakdown, 8% discount rate, full realization of the simulated market
cash margin, the same fixed and variable operating costs, and zero residual or decommissioning
value at the short horizon. Holding PCS cost fixed while power changes is an illustrative
sensitivity convention, not a cost estimate. The comparison is not evidence of an optimal
battery size, project design, profitability or bankability.

## Reporting and retention

Each study writes its daily table, strategy table, cash flows, summary and verified manifest.
The existing renderer consumes only the two manifests and renders every recorded strategy field
beside its result label, basis, declared inputs and standing exclusions. It computes no
cross-configuration difference, ranking or combined ceiling.

Retain the full signed outputs whatever their ordering or NPV sign. A completed private bundle
requires `evidence_index.json`, exact input/output digests, runtime versions, the declaration,
custody verification and the aggregate report index. GitHub artifact retention is 90 days and is
not independent durable custody. The workflow writes no research result to ordinary logs or the
job summary. The report is not publicly deployed by this workflow; publication requires review
of the private aggregate and separate authorization, followed by verification of the deployed
bytes.

## Machine-readable declaration

```json
{
  "history_run_id": "33483975614",
  "history_first_day": "2020-11-01",
  "history_last_day": "2026-08-25",
  "study_first_day": "2025-10-01",
  "study_last_day": "2026-08-25",
  "study_day_count": 329,
  "evidence_class": "retrospective_aggregate_release",
  "strategy_ids": [
    "perfect-foresight-own-state",
    "rolling-mean",
    "forecast-ensemble"
  ],
  "studies": [
    {
      "study_id": "official-integrated-study-50mw-100mwh",
      "power_mw": 50.0,
      "energy_mwh": 100.0,
      "max_daily_equivalent_cycles": 1.5
    },
    {
      "study_id": "official-integrated-study-25mw-100mwh",
      "power_mw": 25.0,
      "energy_mwh": 100.0,
      "max_daily_equivalent_cycles": 1.0
    }
  ],
  "input_sha256": {
    "config/integrated_study_official_50mw_100mwh.json": "cf4274b144d0b829a5461e2d8fd663c060828d70bbaa31498decf230f741f662",
    "config/integrated_study_official_25mw_100mwh.json": "9f213b5462898056f63395c943e4718e4a1b0eab29483115d719c0075bda7a5c",
    "src/greek_bess/cli/study.py": "41c3641af1d3f05d99875b4e4c8578ee99dcea02fd2e36148107557dd43f83f9",
    "src/greek_bess/forecast/naive.py": "31e1b424f0aafcdbdf7eee56667b1ba9bbc4ce5329ef3c83eab7c9e06d4747ee",
    "src/greek_bess/study/config.py": "2d80638f4a37b38be29da48d3fece67e8c31f32f71e6b0a059c7bc78ec9c4ef1",
    "src/greek_bess/study/runner.py": "97da44b5e4387944c54de5dbcf6ba95a45d0af418f1d70bb3f81e4ea201b0524",
    "src/greek_bess/study/results.py": "c07c59e14640c4c17ec02a814d61379944774cf199d39f1b15d48ae8a10f3d4d",
    "src/greek_bess/reporting/contract.py": "bc91046bfc7777d36e79997ea817a8e85d0abd37e11c56628a86cdd8a8a5d63a",
    "src/greek_bess/reporting/render.py": "1c8cfd0a73e7ce5a5018f3900d783a3d768390a0a082269d5f70a6af2e44bbfe",
    "docs/integrated_study_design.md": "e75df7ba59c0d77fc557fb78032144dc09158906a29c315915492ce7169f620c",
    "docs/custody/greek-dam-official-history.json": "4a68737b9dd53881c4b183926fd857f5a885158110a4909bfe4a6e8cb0de3a96",
    ".github/workflows/run-integrated-study.yml": "97e94ab2b557818360b0d5d7f33a0242a5d28b5093859dc6f959f14be5f6fd08",
    ".github/scripts/integrated_study_run.py": "f345f53616a37eda5c4217fbfae1f1fc16093c40af1baaef7b1cf1d6e7816337"
  }
}
```

## Dispatch after approval

Workflow: `Run the declared official integrated study`. Inputs:
`history_run_id=33483975614` and `declaration_document_sha256` equal to the SHA-256 of this whole
file. Review the repair commit and CI before dispatch. A merged repair does not authorize a run,
publication, or a change to any selection policy.
