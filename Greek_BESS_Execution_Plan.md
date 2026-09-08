# Greek BESS — fixed execution plan

Prepared 8 September 2026. Follow the stages in order; completion is determined by evidence, not by a target date.

**Goal:** deliver one reproducible Greek Day-Ahead Market study that connects causal forecasts, realized dispatch, battery ageing and dated cash flows, with an accepted report explaining what the results establish.

**Starting point:** [repository](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester), main commit `bf9ff4a3add31fc06921d56e0ae214af090b152a`, v0.9.6. PR #55 remains open at head `b06fa6b4b8a327cbbb5b577c1b2c7aa2a174e401`. The preceding review ran 599 passing tests, Ruff, mypy and a wheel build; it did not independently rerun the private accepted official-history datasets. Recheck these references when execution begins.

This is an execution plan, not a record of completed fixes. Creating it does not merge a PR, accept a dataset, change a research declaration or publish a report.

## Working rules

1. Work on one stage at a time. Begin from current main after the preceding stage is accepted and merged. Do not open speculative implementation branches for later stages.
2. Preserve `AGENTS.md`, `PROMPT.md` and existing methodology decisions. Adopt this sequence into the active portion of `PLAN.md` without erasing historical decisions. Record prospective methodological amendments explicitly.
3. Implement the smallest change that satisfies the stage. For a reported defect, reproduce it first. If current code already fixes it or evidence contradicts the review, document that disposition; do not manufacture a failing test or an unnecessary edit.
4. Use one feature branch and one focused PR per implementation unit. Stage 3 has two sequential units; stages 7–10 may require separate design, implementation and evidence PRs as specified. Each PR must remain independently reviewable.
5. A code milestone is complete only after meaningful regression tests, Ruff, mypy, the full test suite, a clean wheel build, complete diff review, required documentation updates and successful CI on the final PR head. A larger test count alone is not acceptance evidence.
6. Keep README, CHANGELOG, STATUS, DECISIONS and the implementation report consistent, as required by `AGENTS.md`. Summarize the present state briefly; link detailed evidence instead of duplicating long narratives across files.
7. Preserve the existing merge requirement: CI must pass and the user must have reviewed the first milestones. Prepare the complete PR and evidence before any approval request. Do not repeatedly request authorization already granted in the session.
8. Never shorten an evaluation window, change an admitted evidence grade, impute missing official data or alter test-period choices simply to obtain a successful or favorable result.
9. Keep official interval data, raw messages, tokens and generated research outputs outside Git. Commit code, small synthetic fixtures, aggregate findings and provenance references under the repository's existing rules.
10. A blocker receives an exact cause, the affected stage, evidence and one concrete resolution. An unavailable credential or declaration is not a reason to build additional scaffolding around the same blocker. Any sequence or scope change needs a dated, explicit amendment.

**Deferred throughout this plan:** additional markets, revenue stacking, debt/tax/subsidy models, profitability probabilities, additional weather providers, new model families, an interactive dashboard and AI explanations. Continue existing daily witnessing, but do not treat a successful workflow as proof that its evidence grade is correct.

## Entry gate — establish the executable baseline

- Confirm repository, main SHA, open PRs and their current CI state. Do not use the prior review's downloaded snapshot as a writable Git checkout.
- Read AGENTS, PROMPT, STATUS, PLAN, DECISIONS, METHODOLOGY, LIMITATIONS and the latest implementation report.
- In a proper authenticated checkout, run the required validation commands once and record dependency versions, interpreter and commit. Preserve unrelated working changes.
- Add the stage tracker below to the active plan when implementation begins. Keep a link to the review and a finding-to-stage mapping.

**Exit:** a reproducible baseline, a clean or isolated working area, and a confirmed PR #55 disposition. If remote access is missing, resolve access before creating replacement work.

## Stage 1 — finish the existing retrieval repair

**Branch:** reuse PR #55's branch where appropriate; do not duplicate its fixes. **Review finding:** 6.

Review the complete [PR #55](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/pull/55) diff against its current base. Check that absence, server errors and transport failures remain distinct; retries are bounded; incomplete reads are handled; only explicitly admitted source conditions exclude a day; and exclusions retain exact counts.

**Acceptance checks**

- A 404/410 is classified as absence; repeated 5xx or connection failures never become evidence that a source object was absent.
- Retry exhaustion stops with a transport/server cause. Deterministic data-integrity refusals are not silently retried into a different result.
- A permitted missing-source day is recorded and does not discard valid neighboring days.
- Unknown failures still stop retrieval. Counts reconcile even when a summary displays only a capped list of examples.
- CI passes on the reviewed final head; the existing merge/review gate is satisfied.

**Exit:** the reviewed repair is on main. This stage does not certify the full weather pipeline. Defer the expensive full retrieval until stage 7.

## Stage 2 — correct GFS feature values

**Branch:** `fix-gfs-feature-semantics`. **Review findings:** 3 and 4.

Validate decoded parameter identity, level, units, cycle, valid time, forecast step and averaging/accumulation semantics against the request and index. Extend decoded metadata where necessary. Calculate local wind speed before applying geographic weights. Retain the declared geography and source cycle; correcting aggregation does not authorize choosing new locations after seeing results.

**Acceptance checks**

- Wrong parameter, units, level, cycle or time semantics cause a named refusal.
- At two locations with weights 0.25/0.75 and opposite eastward winds +12/−4 m/s, the weighted local wind speed is 6 m/s, not zero.
- Radiation tests establish correct de-averaging across bucket resets and ordinary steps.
- Positive-path tests exercise the actual GRIB decoder using a small generated synthetic GRIB fixture, not only an injected decoder that mirrors the implementation.
- Record the changed feature semantics and identify any previously retrieved tables that require rebuilding. Do not silently reuse their old acceptance identities.

**Exit:** physically defined feature values and executable rejection of wrong message metadata.

## Stage 3 — make timing and shard evidence truthful

**Branches, sequentially:** `fix-feature-observation-times`, then `fix-feature-shard-reconciliation`. **Review findings:** 5 and 7.

First record successful receipt time per message, separately from run start. A derived feature inherits the latest receipt time among its contributing messages. Retain provider publication time as a separate field. Then reconcile each shard's actual coverage, source identity, per-day records, exclusions and provenance before combination.

**Acceptance checks**

- A request starting before cutoff and completing after cutoff is not witnessed-before-cutoff evidence.
- A receipt exactly at cutoff does not satisfy a strict-before rule. Retries use the successful receipt time.
- Removing one day from a two-day shard without changing its records causes refusal; the combiner cannot claim two built days and zero exclusions.
- Built days and explicitly excluded days partition the declared window exactly. Overlaps, outside-window rows and unaccounted gaps fail.
- Every required variable/interval is accounted for. Official-mode combination refuses missing or contradictory provenance records.
- Valid shards still reproduce the equivalent unsplit table and stable content digests.
- Review existing witness records affected by the timestamp semantics. Reclassify conservatively unless retained evidence proves timely observation; do not fabricate more precise historic receipt times.

**Exit:** both PRs accepted; witnesses and combined summaries describe what was actually observed.

## Stage 4 — align finance metrics

**Branch:** `fix-dated-cash-flow-irr`. **Review finding:** 2.

Use the same dated cash-flow series and documented end-of-day convention for NPV and IRR. Apply ambiguity checks to that series. Annual tables remain summaries and do not relocate cash receipts for IRR. Review related break-even outputs for inconsistent timing while keeping this PR limited to demonstrated timing defects.

**Acceptance checks**

- For EUR 1,000 paid initially and EUR 1,200 received evenly across 365 daily periods, the reported IRR agrees with an independent root calculation using the same dates: approximately 45.59% under the current 365.25-day convention.
- Evaluating the dated NPV at a calculated IRR leaves an absolute residual no larger than `1e-7 * max(1, initial_capex_eur)`.
- Test a partial year, leap-year dates, no sign change, and an intrayear sequence with multiple sign changes.
- Cash-flow totals, fees and augmentation costs are not changed or counted twice as a side effect.

**Exit:** all monetary metrics refer to the same declared cash-flow timing.

## Stage 5 — correct the degradation result's interpretation

**Branch:** `fix-degradation-result-basis`. **Review finding:** 1.

Retain the existing daily optimization policy, but identify the evolving-state aggregate as a day-by-day perfect-foresight simulation. Update the result kind, labels, downstream finance interpretation, reports and documentation so it cannot be mistaken for a lifetime optimum. Preserve genuine fixed-capacity upper bounds.

**Acceptance checks**

- A two-day, one-lifetime-cycle fixture reproduces EUR 1 for the daily policy and EUR 100 for a feasible policy that waits. Its aggregate is not labelled a lifetime upper bound.
- Labels and basis remain correct through manifest creation, serialization, rendering and finance.
- Existing stored outputs are either read with an explicit compatible interpretation or refused with an actionable migration message; they are never silently relabelled as different evidence.
- No new lifetime optimizer is introduced in this milestone.

**Exit:** the interpretation matches the optimization actually performed.

## Stage 6 — isolate the weather contribution

**Branch:** `benchmark-matched-training-control`. **Review finding:** 8.

Before producing new benchmark outcomes, record a prospective amendment adding a price-only control trained on exactly the weather challenger's eligible rows. Keep the original full-history control as a separately named baseline.

Compare three explicit arms: full-history price-only; matched-training price-only; matched-training price-plus-weather. Hold hyperparameters, model families, seed, refit dates and evaluation days fixed for the matched pair.

**Acceptance checks**

- Each matched refit records identical training-row identities and targets; only feature columns differ.
- A synthetic fixture with missing weather days proves that both matched arms exclude identical training rows.
- All compared arms settle on the same declared held-out days. Missing days remain visible.
- The original baseline remains reproducible. Its comparison with the matched control measures the effect of reduced training coverage, not weather value.
- The source, cutoff, geography and test boundary are not retuned using held-out outcomes.

**Exit:** the experiment can separate weather information from differences in training coverage.

## Stage 7 — complete the official weather experiment

**Work:** execute existing workflows; use separate evidence PRs for acceptance and results. **Review finding:** 6; prerequisites are stages 1–6.

Perform these steps in exactly this order:

1. Run a small live smoke retrieval with the corrected decoder and evidence logic. Include previously failing cases where available. Keep raw verification material private. Do not evaluate model skill in the smoke test.
2. Retrieve the declared full window, 27 February 2021–25 August 2026, with unchanged source declarations. Rebuild affected feature tables rather than mixing old and corrected feature semantics.
3. Combine and reconcile shards; audit publication and observation timing against the declared cutoff.
4. Record and verify custody of the required artifacts under the existing procedure. Run the acceptance preflight to obtain joined feature identity, coverage and exploratory classification. This is not a benchmark run.
5. Commit the dated acceptance document naming the accepted feature-set digest, evidence grades, exclusions, declarations and primary-source support.
6. Run the forecast and dispatch benchmarks against that accepted digest, including the matched controls.
7. Commit the aggregate result and run references regardless of whether weather improves or worsens performance. Render through the existing report contract.

**Exit:** one reproducible accepted dataset and one honestly labelled empirical result. An exploratory result is allowed when the predeclared rule requires that label; favorable performance is not an acceptance criterion. If required source evidence cannot be accepted, report the precise blocker and amend scope explicitly before proceeding—never substitute synthetic investment evidence.

## Stage 8 — build the integrated study runner

**Branches, sequentially:** `design-integrated-study`, then `build-integrated-study`. **Review finding:** 9.

**Design unit:** specify a single study configuration and contracts for forecast inputs, realized settlement, per-strategy degradation state, cash-flow timing, costs, coverage, terminal SOC, provenance and result labels. Adopt the design before implementation; the design PR is the reviewable decision, not a request to choose among vague architectures.

For the first version, require a declared continuous window with complete official prices and complete forecasts for every compared strategy. Refuse gaps. Do not invent a no-trade or fill policy to bridge missing days. Finance uses exactly that horizon; a shorter replay must not become a 20-year forecast.

**Implementation unit:** connect existing modules in this order for each strategy and delivery day:

1. Read only information available at the declared decision time.
2. Plan dispatch under that strategy's beginning-of-day physical state.
3. Settle the schedule against realized prices.
4. Update that strategy's state from its realized cell throughput and calendar ageing.
5. Generate dated operating cash flows and evaluate finance.
6. Record manifests and render the existing report.

**Acceptance checks**

- One command and one configuration produce a complete synthetic demonstration, then a declared official-history study.
- Zero-fade configurations reproduce the corresponding fixed-battery backtests within stated solver tolerances.
- Two strategies with different throughput evolve separately; neither borrows another strategy's degradation state.
- Modifying future information cannot change an earlier forecast or decision.
- Initial and terminal energy, augmentation and fees reconcile. Physical fade and any monetary degradation adder are explicitly distinguished; costs are not double-counted.
- Missing-day input fails clearly. Repeated execution preserves scientific results and content identity; run timestamps may legitimately differ.
- Comparisons use the same initial conditions and declared rules. Do not assert one shared conditional ceiling after strategy-specific degradation states diverge.

**Exit:** the study directly connects forecasting choices to ageing and cash flows without manual CSV manipulation.

## Stage 9 — evaluate selection by battery value

**Branch:** `benchmark-value-based-selection`. **Review finding:** 10.

Define a supplementary experiment comparing validation-RMSE selection with validation-settled-margin selection. Keep the same model families and candidate configurations. Set deterministic tie-breaking and an explicit selection schedule. Do not change the existing benchmark retrospectively.

**Acceptance checks**

- Selection uses validation data only, on common dates and equivalent physical assumptions.
- The selected policy is frozen before its evaluation period. Outcome-dependent switching is prohibited.
- A synthetic case where better RMSE earns less margin proves that the two selection objectives can select different policies.
- Report held-out settled margin, regret against a valid comparator, cycling and capacity, alongside price errors.
- Already inspected historical test periods are labelled retrospective supplementary evidence. Any confirmatory claim requires a newly predeclared untouched or prospective period.
- An unfavorable result is retained; a more complicated method is not automatically promoted.

**Exit:** evidence for which selection objective serves the battery study, without test-set tuning.

## Stage 10 — deliver the portfolio release

**Branch:** `release-integrated-research-study`; separate code changes from evidence/publication steps if needed.

Use the existing static report renderer. Produce a synthetic demonstration anyone can reproduce and an aggregate official-history study with traceable inputs. Keep public provider-data restrictions and the existing custody/publication gates.

**Acceptance checks**

- A fresh checkout can reproduce the synthetic study using documented commands and recorded dependency versions.
- The official report identifies the source window, commit, configuration, evidence grades, study horizon, strategy rules and limitations beside the results.
- Include one preregistered comparison of the existing 50 MW/100 MWh and 25 MW/100 MWh example configurations, retaining each configuration's explicit assumptions. Describe it as configuration sensitivity, not proof of an optimal battery size.
- Figures reconcile to producing manifests. Illustrative finance/OEM assumptions remain labelled. No statement implies calibrated profitability probabilities or a bankable forecast.
- README explains what was tested, what changed, the main empirical finding and how to reproduce it. STATUS and PLAN identify a single next step and contain no contradictory current-state claims.
- Review the final diff, run the required gates, and satisfy the existing merge and publication authorization requirements. Verify the actual published report before calling publication complete.

**Exit:** an accessible, reproducible research deliverable demonstrating the complete analytical chain. Correctness and honest conclusions define success; positive NPV or a weather-model win do not.

## Tracker

| Stage | Deliverable | Initial status | Evidence required to close |
| --- | --- | --- | --- |
| Entry | Verified working baseline | Pending execution | Main SHA, access, validation |
| 1 | PR #55 retrieval repair | Existing PR open | Reviewed merge and final CI |
| 2 | Correct GFS values | Pending | Metadata and wind counterexamples |
| 3 | Truthful timing and shards | Pending | Cutoff and coverage reconciliation tests |
| 4 | Consistent finance timing | Pending | Independent IRR and NPV residual |
| 5 | Honest degradation basis | Pending | Lifetime-budget counterexample and propagated labels |
| 6 | Matched-training controls | Pending | Equal training-row identities |
| 7 | Official weather result | Pending | Accepted digest, custody, run and result documents |
| 8 | Integrated study runner | Pending | Design, end-to-end tests and reproducible study |
| 9 | Value-based selection evidence | Pending | Frozen selection and labelled evaluation |
| 10 | Portfolio release | Pending | Reproducible demo and verified report |

Only one stage may be In progress. A stage moves Pending → In progress → Review → Complete, or In progress → Blocked. A blocked stage is not complete. Record its specific cause and resume it once resolved. New unrelated ideas go into a short backlog, not into the active stage.

## Session handoff

At the end of each implementation session, record: active stage; branch and commit; exact changes; counterexample/test evidence; CI/PR state; any specific blocker; and the next single action. At the next session, read this record and verify repository state before working.

The first implementation action is the Entry gate followed by review of PR #55. No full weather retrieval should be launched before stage 7, and no integrated feature development should begin before the preceding correctness and acceptance gates close.

## Source references

- [Contribution and validation requirements](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/blob/bf9ff4a/AGENTS.md)
- [Approved scope](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/blob/bf9ff4a/PROMPT.md)
- [Existing plan](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/blob/bf9ff4a/PLAN.md)
- [Declared weather experiment](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/blob/bf9ff4a/docs/fundamentals_declarations_2026-09-03.md)
- [Open retrieval repair](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/pull/55)
- [Failed full retrieval](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33843070945)

Stages beyond the existing repository scope are proposed future work under this plan; no benchmark outcome, new acceptance or completed milestone is asserted here.
