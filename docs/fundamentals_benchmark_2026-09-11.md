# Fundamentals forecast-dispatch benchmark — 11 September 2026

## Scope and interpretation

- This document records the result of Stage 7, steps 6–7 of `Greek_BESS_Execution_Plan.md`:
  the forecast and dispatch benchmarks run against the accepted feature-set digest, including
  the matched controls, committed **regardless of whether weather improves or worsens
  performance**.
- This is a **historical research result**: held-out price error and settled gross margin on
  one declared period, using price-taking planned quantities. It is **not** a forecast, expected
  revenue, financial advice, a bankable forecast, or an investment-grade study. Perfect
  foresight is a gross-margin upper bound, not an achievable outcome.
- The comparison structure (three arms, matched by training rows) was fixed prospectively in
  `docs/fundamentals_matched_control_amendment_2026-09-10.md`, before this run existed. Nothing
  in that structure was revised after seeing this result.

## Workflow run and identity

| Field | Evidence |
| --- | --- |
| Workflow | `Benchmark point-in-time fundamentals`, run [`34524611285`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34524611285) at commit `a76f809`, branch `claude/nice-mendel-mmrv8f`; all 16 steps succeeded |
| Prior failed attempt | Run [`34522951370`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34522951370) at commit `c17242e` failed at the dispatch step: the workflow's `--methods` list named the challenger arms without their matched controls, which `benchmark-fundamentals-dispatch` correctly refused to settle. Fixed in `a76f809` by adding `ridge_matched` and `hist_gradient_boosting_matched`; no data, digest, or acceptance was touched by that fix. |
| Accepted feature set | `a718f46265678cf1e37c31fca439b9f2f03479901fe8f0ac126766431b99aefc`, named by `docs/fundamentals_acceptance_2026-09-10.md` (SHA-256 `43e04df9639de7e14762c79a112897d0569ddd13932cd34c9e2cd6aa1cd9f84a`) |
| History run / feature run | `33483975614` (accepted official price history) / `34503398871` (accepted feature table) — both re-verified by custody digest before use |
| Decision cutoff / lead | `greek-dam-gate-closure-2026-09-10`; 0 minutes |
| Evidence grades admitted | `witnessed`, `provider_declared` |
| Private evidence artifact | `fundamentals-acceptance-and-benchmark-private`, artifact ID `10171792538`, SHA-256 `66af40f4dbc8ad492ae912c7b1b9d4fc77713b4b3410e2e3e23c6b2077d663b9`; expires 9 December 2026. Contains the interval tables, refit-by-refit training-row/target digests, both benchmark summaries, the manifests and the rendered generic report. Kept private per the existing procedure; not attached to this document. |
| Battery | `examples/battery_50mw_100mwh.json` (`c9156ef29f9e364d84cf1d74fb32c789c0ff612180b47d7a43f0c77d187079f2`) |

## Ablation arms

Per the matched-control amendment, each model family runs as three arms, held to identical
model families, hyperparameters, seed (42), refit cadence (7 days) and refit dates. Each refit's
training-row and training-target digests were checked to agree between every matched pair at
every refit; none disagreed.

| Arm | Feature columns | Training rows |
| --- | --- | --- |
| `ridge` / `hist_gradient_boosting` (full-history baseline) | calendar + price history | every day in the causal feature table |
| `ridge_matched` / `hist_gradient_boosting_matched` (matched control) | calendar + price history | exactly the challenger's eligible days |
| `ridge_fundamentals` / `hist_gradient_boosting_fundamentals` (challenger) | matched-control columns + accepted weather | exactly the challenger's eligible days |

## Coverage and classification

| Item | Value |
| --- | --- |
| Common evaluation window | 320 days, 2025-10-08 to 2026-08-25 (30,720 quarter-hour intervals) |
| Exploratory causes | none carried from the forecast ablation |
| **Exploratory** | **false** — carried verbatim from the accepted preflight's DJF 2025-26 coverage classification, decided before this result existed |

## Result: forecast error (RMSE, EUR/MWh, lower is better)

| Method | RMSE | MAE | Correlation |
| --- | ---: | ---: | ---: |
| `ridge` | 31.894 | 22.319 | 0.8484 |
| `ridge_matched` | 31.899 | 22.360 | 0.8484 |
| `ridge_fundamentals` | 31.350 | 22.179 | 0.8549 |
| `hist_gradient_boosting` | 31.276 | 21.644 | 0.8543 |
| `hist_gradient_boosting_matched` | 31.347 | 21.623 | 0.8536 |
| `hist_gradient_boosting_fundamentals` | **30.603** | 21.304 | 0.8611 |

## Result: settled dispatch (EUR, common 320 days; perfect-foresight ceiling EUR 4,626,011.14)

| Method | Realized margin (EUR) | Capture ratio |
| --- | ---: | ---: |
| `ridge` | 3,528,123.63 | 0.76267 |
| `ridge_matched` | 3,529,075.61 | 0.76288 |
| `ridge_fundamentals` | 3,533,975.32 | 0.76394 |
| `hist_gradient_boosting` | 3,537,095.83 | 0.76461 |
| `hist_gradient_boosting_matched` | **3,550,080.94** | **0.76742** |
| `hist_gradient_boosting_fundamentals` | 3,543,237.47 | 0.76594 |

## The comparison that isolates weather (challenger vs. its own matched control)

| Comparison | Incremental margin (EUR) | Days challenger higher | Days control higher | Days equal |
| --- | ---: | ---: | ---: | ---: |
| `ridge_fundamentals` − `ridge_matched` | **+4,899.71** | 154 | 162 | 4 |
| `hist_gradient_boosting_fundamentals` − `hist_gradient_boosting_matched` | **−6,843.46** | 150 | 170 | 0 |

**The result is mixed, and it is committed as mixed.** Adding the accepted point-in-time
weather columns to a ridge model, holding rows fixed, settled EUR 4,899.71 more over 320 days
(a 0.14% relative gain against the matched control's realized margin). Adding the same columns
to a histogram gradient-boosting model, holding rows fixed, settled EUR 6,843.46 *less*
(a 0.19% relative loss). Both differences are small compared to the day-to-day range recorded in
`largest_daily_gain_eur`/`largest_daily_shortfall_eur` (up to ~EUR 4,847 and −EUR 3,285
respectively) — this is not a large or uniform effect, and it is not reported as one.

The `challenger − full_history_baseline` comparison is **not reported as a weather effect** and
is not computed here, per the amendment: it would confound the weather columns with the
training-row difference between the full-history and matched-control arms.

## What this result does not establish

- It does not establish investment value, expected revenue, or a bankable forecast.
- It does not generalize beyond the declared window, the declared cutoff/lead, the
  wind-weighted geography (applied uniformly to irradiance and temperature; see the acceptance
  document's recorded limitation), or the hourly-to-quarter-hour broadcast regime in force after
  2025-10-01.
- A small, sign-mixed effect across two model families is not evidence that weather features
  are useless or that they reliably help; it is exactly the honestly-labelled outcome the
  predeclared, matched-control design was built to produce, whichever way it fell.

## Labels carried through the report contract

`is_forecast: false`; `is_probabilistic: false`; `is_investment_evidence: false`;
`establishes_only_historical_settled_value: true` (dispatch) /
`establishes_only_price_error: true` (forecast). Both manifests were recorded, verified, and
rendered through the existing generic report renderer (`render-report`) into the private
evidence bundle; no bespoke rendering path was used.
