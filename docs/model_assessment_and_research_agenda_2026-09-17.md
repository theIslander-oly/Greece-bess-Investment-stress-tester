# Model assessment and research agenda — 17 September 2026

## Decision and scope

Complete the current declared Stage 10 study before introducing a new model or market.
The instruction to continue the study authorizes one private retry of the repaired
17 September declaration after successful merged-commit CI. Record the model assessment
and proposed extensions now; they do not alter that experiment or authorize public deployment.

The present methods are appropriate baselines for transparent historical research. No
comparison establishes that they are the best available models for Greece, and no result
establishes expected revenue, investment value or a bankable project forecast.

## Evidence already available for presentation

These are accepted results from separate experiments, not new calculations or one combined
ranking. Their windows and physical bases must remain attached to their figures.

- The [weather benchmark](fundamentals_benchmark_2026-09-11.md) improved RMSE in both matched
  model families, but changed settled margin by +EUR 4,899.71 for ridge and -EUR 6,843.46 for
  histogram gradient boosting over 320 common days. More accurate prices did not consistently
  yield more battery margin. This does not establish that weather is useless or reliably valuable.
- The [selection benchmark](selection_benchmark_2026-09-11.md) recorded +EUR 12,639.14 for
  validation-margin selection over validation-RMSE selection across 329 days, with 489.95
  versus 487.69 equivalent full cycles. Physical degradation and monetary wear were excluded;
  whether that advantage survives them remains unanswered. The evidence is retrospective
  supplementary, and candidate identities differ by model family as well as selected objective.
- The [annual decomposition](official_annual_decomposition_2026-08-28.md) shows that the
  ensemble led rolling mean on common days in 2025 (87.49% versus 86.49% capture), whereas
  rolling mean led in partial 2026 (75.86% versus 72.81%). These are 356 and 235 common days
  respectively. The ranking changed; this does not identify its cause or predict a future winner.
- The same decomposition records fixed-battery daily-composed perfect-foresight ceilings of
  EUR 1,960,658 in 2021, EUR 5,859,178 in 2022 and EUR 3,577,481 in 2023. Historical opportunity
  depends strongly on the period. These ceilings are not expected earnings, and partial-year
  totals and hourly/quarter-hour negative-price interval counts are not directly comparable.

The presentation conclusion is that price accuracy, settled trading value and net economic
value are distinct. The accepted experiments establish the first distinction; the integrated
study develops the link to ageing and cash flows. It does not make a lifetime viability claim.

## Assessment of the mathematical models

| Component | Current approach | Assessment and material limitation |
| --- | --- | --- |
| Dispatch | Mixed-integer optimization with an admissible relaxation shortcut | Retain this formulation for the declared dispatch problem. Numerical solutions are subject to solver tolerances. An optimum under assumed efficiency, price-taking and terminal SOC is not proof that the assumptions represent actual operation. |
| Forecasts | Persistence, rolling mean, ensemble, ridge and histogram gradient boosting | Credible baselines. Two ML families and a small grid cannot establish a universally best model. Performance must be compared on new data using battery value as well as price error. |
| Degradation | Separate cohorts with additive calendar and equivalent-cycle fade | Transparent sensitivity model; not a calibrated electrochemical lifetime prediction. It does not explicitly resolve temperature, cycle-depth and SOC-exposure effects. |
| Operating policy | Daily optimization followed by state evolution | Myopic with respect to future capacity and lifetime throughput. It does not optimize lifetime value. A policy can spend its last permitted cycle on a small spread before a much larger opportunity. |
| Finance | Dated cash flows, NPV and qualified IRR | Appropriate arithmetic framework. Credibility depends on cost, residual-value, horizon and revenue assumptions; replacing formulas does not fix uncertain inputs. |
| Scenarios | Seasonal block resampling and declared transformations | Suitable for conditional stress questions. They are not calibrated probabilities of future prices, loss or profitability. |

The daily-policy limitation is demonstrated by the existing EUR 1 versus EUR 100 two-day
counterexample in [Methodology section 5.1](../METHODOLOGY.md). Daily optimality is not lifetime
optimality. Future work may value remaining energy capacity and cycle life in today's decision,
but estimates must use information available at that decision time. Realized future prices
would define another perfect-foresight diagnostic, not an executable policy.

## Ordered research agenda after Stage 10

1. **Does the observed selection gain survive ageing and costs?** Connect the existing frozen
   ML policies to the integrated runner, preserving causal refits and separate degradation
   states. First reconcile the zero-fade, zero-cost case to the corresponding fixed-battery
   benchmark. Do not imply the current naive-only integrated planners already answer this.
2. **Does valuing remaining battery life improve the operating policy?** Compare a declared
   opportunity-cost or multi-period policy against the existing daily policy under equivalent
   starting conditions, terminal-energy rules, information sets and physical constraints.
   Separate physical fade, a dispatch shadow penalty and actual cash costs; avoid counting wear
   twice. Calibrate assumptions where data exist and otherwise label them as sensitivities.
3. **Which forecast improvements survive a new evaluation?** Preregister a limited challenger
   set, including consideration of an electricity-specific LEAR model and alternative training
   windows. LEAR means LASSO Estimated AutoRegressive. Preserve the current baselines; compare
   settled value, cycling and price error. Neural networks and probabilistic forecasts are
   candidate methods, not presumptively superior replacements.
4. **Only then consider another market.** First establish accessible official data, decision
   timing, eligibility, settlement and joint physical constraints. Do not add an independent
   revenue estimate to DAM margin as though both schedules could always be delivered.

Before each experiment, declare a hypothesis, baseline, candidate grid, cutoff, evaluation
window, missing-data treatment, sensitivities and acceptance criteria. Retain adverse results.
Use demonstrably untouched history or a prospective period for confirmation; previously
inspected days remain retrospective. Method acceptance and scientific support for superiority
are different decisions. If sampling-variability analysis is adopted, predeclare a method that
respects serial dependence and explain that uncertainty about an estimated difference is not
a calibrated probability of future project profit.

This agenda is a backlog, not four newly active stages. Stage 10 remains the only active stage.
No ADMIE load or RES source is readmitted; all existing market exclusions remain in force.

## Research references and limits of transfer

- Lago, Marcjasz, De Schutter and Weron, *Forecasting day-ahead electricity prices: A review
  of state-of-the-art algorithms, best practices and an open-access benchmark* (2021):
  [author paper](https://arxiv.org/abs/2008.08004) and
  [benchmark documentation](https://epftoolbox.readthedocs.io/en/latest/index.html).
  The benchmark supplies LEAR and DNN comparisons and emphasizes reproducible evaluation.
  Neither its model names nor performance in other markets establish superiority in Greece.
- [BLAST-Lite documentation](https://github.com/NatLabRockies/BLAST-Lite) describes degradation
  dependent on temperature, SOC, depth of discharge and charge/discharge rate. A suitable
  calibrated LFP model could test the present approximation. Its authors caution that
  accelerated laboratory evidence spans limited time and does not capture every pack failure.
  Greater complexity without suitable cell/OEM validation is not demonstrated greater accuracy.
- García-Miguel et al., *Impact of risk measures and degradation cost on the optimal arbitrage
  schedule for battery energy storage systems* (2024),
  [paper](https://doi.org/10.1016/j.ijepes.2024.109883), found the tested risk-adjusted stochastic
  approaches inferior to a deterministic point-forecast strategy in its Iberian case study.
  This is evidence against assuming automatic gains from complexity, not proof that stochastic
  optimization is inferior in Greece.

## Stage 10 interpretation to preserve

The fixed 329-day study compares 50 MW/100 MWh at 1.5 daily cycles with 25 MW/100 MWh at
1.0 daily cycles. It is configuration sensitivity, not an isolated power or duration effect,
and not an optimal sizing study. Finance intentionally holds costs identical, including
EUR 50 million initial CAPEX, and uses zero residual value at the short horizon. Its NPV is
not a lifetime profitability verdict. No common evolving-state ceiling spans the strategies.

Source: [the unchanged repaired declaration](integrated_study_run_declaration_2026-09-17.md).
