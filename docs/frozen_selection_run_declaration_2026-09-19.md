# Frozen-selection ageing and cost experiment — 19 September 2026

## Question and review status

Does the previously accepted validation-margin selection advantage persist when the same frozen
forecasts are dispatched through separate physical-ageing states and illustrative operating costs?
The hypothesis is a positive margin-selection-minus-RMSE-selection difference in historical cash
margin and NPV in the declared cost case. Report each sign separately; a positive cash difference
does not imply a positive NPV difference or profitable project. Result sign is never an acceptance
criterion. No new forecast family, fit, selection rule or market is introduced.

Integration PR #83 merged as `d57125eca16f6cdbdae19ffe5eb29d5c98d1ef89`.
Merge CI `35316480803` passed on Python 3.12 and 3.13. This declaration is the next review unit on
`codex/frozen-selection-run-declaration`. It prepares an experiment; it records no authorization,
new official result or public deployment. Review its final commit, CI and whole-document SHA-256
before authorizing the two private runs below. Stage 10 publication remains separate and open.

## Accepted evidence and unchanged calendar

Use history run `33483975614`, verified against the existing
[custody record](custody/greek-dam-official-history.json) before prices are consumed. Use original
Stage 9 run `34623616511`, source commit `1fdd81628951c02c185b3b806318385038a5137a`, and its
accepted `selection-comparison-private` bundle. Its exact identity, seal and forecast digest are
fixed below and in the [accepted result](selection_benchmark_2026-09-11.md). Retained local copies
may be used only after the same identity and custody verification. Missing or changed evidence
fails; neither fresh retrieval nor a replacement acceptance record is part of this experiment.

The full price calendar is 1 November 2020–25 August 2026. Source validation is 1 October
2024–30 September 2025; evaluation remains 1 October 2025–25 August 2026: 329 complete market
days and 31,584 native quarter-hour intervals. Preserve the 100-interval autumn and 92-interval
spring days, UTC keys, zero and negative prices. No interpolation, shortened window or exclusions.

Replay `ridge_alpha_1` for validation RMSE and `gradient_lr_005_leaf_15` for validation settled
margin. Preserve the original forecast columns, including their original resolution-transition
behavior. Do not invoke candidate generation, refitting or selection. The adapter verifies all
indexed files, frozen selection, canonical actuals, source labels and calendars. Hashes establish
identity; causal construction is inherited from the upstream accepted training protocol.

## Fixed cases and assumptions

Run the committed zero-fade configuration first. Only after its reproduction gate passes, run
the committed ageing/cost configuration. Both contain the same two strategies in the same order:
`validation-rmse-selection`, then `validation-margin-selection`. Each owns its battery state.

Both cases retain 50 MW charge/discharge and grid limits, 100 MWh initial energy capacity,
5–95% SOC, 50% initial and daily terminal SOC, 94% efficiency each way, 1.5 daily grid-discharge
equivalent cycles, full availability, no self-discharge, zero trading fees and zero non-cash
dispatch wear adder. Solve strategy is `relaxation_first`, relative MIP gap `1e-7`, no solver time
limit, and complete market days are required. Physical fade scales power with exponent 1.

| Assumption | Zero-fade reproduction | Ageing and costs |
| --- | ---: | ---: |
| Calendar capacity fade per year | 0 | 1.5% |
| Capacity fade per cell-based equivalent cycle | 0 | 0.004% |
| Fixed OPEX per year | EUR 0 | EUR 600,000 |
| Insurance per year | EUR 0 | EUR 150,000 |
| Asset management per year | EUR 0 | EUR 100,000 |
| Variable OPEX per MWh grid discharge | EUR 0 | EUR 0.50 |

Both retain the same illustrative EUR 50 million initial CAPEX: battery EUR 30 million,
conversion EUR 8 million, connection EUR 5 million, development/construction EUR 4 million,
other EUR 3 million. Discount rate is 8%, margin realization 100%, OPEX escalation 2% per year,
and residual/decommissioning values zero. Finance covers exactly the declared 329-day window;
the zero-fade case is zero operating cost, not zero CAPEX. There is no augmentation. Warranty
references remain 10 years, 70% retained capacity and 4,000 cell EFC, without enforcement of the
warranty throughput cap; retirement threshold is 60% capacity. These are illustrative inputs,
not calibrated LFP degradation or project cost estimates.

OPEX is applied after dispatch. It does not cause the optimizer to avoid a marginal trade.
This two-case comparison changes fade and operating costs together; it measures the combined
effect and does not identify their separate causal contributions. No cost sensitivity or model
retuning is selected after inspecting outcomes.

## Reproduction and acceptance gates

1. Verify the reviewed declaration digest, every pinned input and the complete package source
   tree using `scripts/verify_frozen_study_declaration.py`. The tree digest is SHA-256 of compact,
   key-sorted JSON mapping each repository-relative `src/greek_bess/**/*.py` and `py.typed` path
   to its exact-byte SHA-256. Added and deleted modules change it. This check is read-only and
   does not establish authorization or verify private data custody.
2. Verify history custody, all Stage 9 bundle files, source identities and the complete calendars.
   Pin the numerical runtime to the source record: Python 3.12.14, numpy 2.5.3, pandas 2.3.3,
   scipy 1.18.1 and scikit-learn 1.9.1. Retain platform and full installed-package inventory.
   If that environment cannot be provisioned, stop and review an amendment before measuring.
3. Run zero-fade replay. Independently dispatch each original selected evaluation column using
   the existing fixed-battery `_backtest_precomputed_forecast` path, without training or selection.
   Match every day's cash margin within absolute EUR `1e-6` and grid charge/discharge within
   absolute `1e-6` MWh, with relative tolerance zero. Match each aggregate to the original
   unrounded `selection.csv` evaluation row within `329e-6` in its corresponding unit. Do not
   compare to rounded public totals or relax tolerances after seeing a failure. Reconcile
   daily-to-total sums, constant capacity, terminal energy and zero operating costs.
4. Only after that gate passes, run the unchanged ageing/cost configuration. Verify both complete
   calendars, independent state paths, daily energy balance, capacity fade, limits and terminal
   SOC. Reconcile daily cash margins to summaries, cash flows and dated NPV independently.
   Stage 9 EFC uses grid discharge / nominal energy; integrated EFC uses cell discharge / initial
   nominal energy. Convert by the declared discharge efficiency when reconciling those measures;
   never treat their raw numbers as equal.
5. Verify both manifests and their exact input/source provenance. Re-render reports and compare
   bytes. Record the signed paired cash-margin, NPV, cell-EFC, final-capacity and undiscounted
   cash-flow differences already emitted by the results module. No shared evolving-state ceiling,
   annualization, significance claim, new ranking rule or lifetime extrapolation is added.

If any gate fails, retain the diagnostics and stop before the next case. An unfavorable but valid
outcome is retained as a completed result. Changes to source, runtime, window, forecasts, costs or
tolerances require a prospective amendment; do not repin this declaration retrospectively.

## Execution and private retention after approval

Use the existing `greek-bess run-integrated-study` command with the verified canonical price file,
`--selection-evidence-dir` pointing to the accepted Stage 9 bundle, `--study-config` set to each
declared configuration, separate ignored `private/` output directories, `--declared-inputs` and
`--report`. Do not dispatch the old Stage 10 workflow: its immutable declaration pins different
source and strategies. This unit prepares a local execution protocol, not a new GitHub workflow.

Additional declared inputs must record this document's SHA-256, exact executing commit,
`retrospective_supplementary` evidence class, both source run IDs, source archive identity and
custody-verification identity. Keep automatic CLI configuration, price and selection identities.
Retain commands and logs privately, without research numbers or raw data in ordinary logs.

Seal a private evidence index containing the declaration, configuration copies, runtime inventory,
custody/admission checks, reproduction comparison, independent reconciliation, and both studies'
daily/strategy/cash-flow tables, summary, manifest, report and report index. Hash every retained
file, record UTC execution times and commit, and set `publication_authorized` to false. Retain
failures and all valid outcome signs. Do not commit raw/processed prices, forecasts or generated
results. Artifact retention is not independent durable custody.

Public aggregate publication requires review and separate authorization. Research and
pre-feasibility only: not financial advice, expected revenue, a bankable forecast or investment
evidence. Intraday, balancing, reserves, taxes, subsidies, grid feasibility and revenue stacking
remain excluded. Price-taking full acceptance is assumed; forecasts are not executable bids.

## Machine-readable declaration

```json
{
  "evidence_class": "retrospective_supplementary",
  "implementation_commit": "d57125eca16f6cdbdae19ffe5eb29d5c98d1ef89",
  "history_run_id": "33483975614",
  "selection_run_id": "34623616511",
  "selection_source_commit": "1fdd81628951c02c185b3b806318385038a5137a",
  "selection_evidence_index_sha256": "33e78be5952c1f3afd5632b6ec0709d73f99839537ada77ba3e2c3ad058c0bcc",
  "frozen_selection_sha256": "47d8ba1281daa3e0f9529e241ebab4139df7d1fbebbc23023e8c300fc1bc2ccc",
  "candidate_forecast_sha256": "9bbe2a36513d7fd5b4efcc7601e5f5603d8576084b969416142db9f917c0bca3",
  "history_first_day": "2020-11-01",
  "history_last_day": "2026-08-25",
  "study_first_day": "2025-10-01",
  "study_last_day": "2026-08-25",
  "study_day_count": 329,
  "study_interval_count": 31584,
  "selected_candidates": {
    "frozen_validation_rmse": "ridge_alpha_1",
    "frozen_validation_margin": "gradient_lr_005_leaf_15"
  },
  "study_configs": [
    "config/integrated_study_frozen_selection_zero_fade.json",
    "config/integrated_study_frozen_selection_with_costs.json"
  ],
  "runtime": {
    "python": "3.12.14",
    "numpy": "2.5.3",
    "pandas": "2.3.3",
    "scipy": "1.18.1",
    "scikit-learn": "1.9.1"
  },
  "reproduction_tolerances": {
    "relative": 0.0,
    "daily_eur": 1e-06,
    "daily_mwh": 1e-06,
    "aggregate_eur": 0.000329,
    "aggregate_mwh": 0.000329
  },
  "source_tree_sha256": "6a66f845cd4913457c559a121c92c6c342145d3ecda94fae1c085b089ec9a4de",
  "input_sha256": {
    "config/integrated_study_frozen_selection_zero_fade.json": "2473f24da19195af68a612bf94d3888b893a760c7ca1e359ad15c81493cc61b4",
    "config/integrated_study_frozen_selection_with_costs.json": "6ccd33fe0cb4b49aacfb72bd5fe2e3fc95685191835d06da70826457b2c68cac",
    "examples/battery_50mw_100mwh.json": "c9156ef29f9e364d84cf1d74fb32c789c0ff612180b47d7a43f0c77d187079f2",
    "docs/custody/greek-dam-official-history.json": "4a68737b9dd53881c4b183926fd857f5a885158110a4909bfe4a6e8cb0de3a96",
    "docs/selection_benchmark_2026-09-11.md": "ee7771c218e36271f47acd0482d50206ae45581465e5756da7c429017a1d07ae",
    "docs/frozen_selection_study_design.md": "780c5eec866be7c4082afeedbb4bdf8b267eb8f13a4075a3306e18b702e5430d",
    "scripts/verify_frozen_study_declaration.py": "2b14374edc6132a72c03576a7572b1fb4500cc327b243a7aa08dbfd8d988d34e",
    "pyproject.toml": "ef5e7f8b1dbc841518ac703a843bf24ad3ffee3baa7291af3f36ff08686f707e"
  }
}
```
