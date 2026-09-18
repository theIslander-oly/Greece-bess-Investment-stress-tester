# Implementation plan

What happens next, and the gate each step has to pass. Where the work stands today is in
[`STATUS.md`](STATUS.md); the handoffs and completed-milestone records that used to live here are
in [`docs/history/plan_log_through_2026-09-11.md`](docs/history/plan_log_through_2026-09-11.md).

The staged plan in [`Greek_BESS_Execution_Plan.md`](Greek_BESS_Execution_Plan.md) is active and
authoritative. Only one stage moves at a time, and no stage is renumbered.

**18 September continuation:** the operator confirmed the Stage 10 report was not published
and instructed continuation of the next research unit. Stage 10 remains in publication review;
the sole active development unit is frozen ML selection integration below. The original ten
stages are not renumbered or retrospectively marked published.

## GitHub milestone workflow

Every new milestone uses a feature branch, validation, diff review and one pull request. The
v0.1-v0.6 implementation predates the connected repository and entered through the truthful
`repository-foundation-v0.6-import` snapshot; earlier Git history will not be fabricated.

## Fixed execution-plan tracker

| Stage | Status | Evidence or next gate |
| --- | --- | --- |
| Entry | Complete | Cross-platform baseline validated and merged in PR #56 (`84ec878`) |
| 1 | Complete | Retrieval repair merged as `f149f61`; tree matches reviewed PR #55 head |
| 2 | Complete | GFS value semantics and identity guards merged as `316e9f5` (PR #57) |
| 3 | Complete | Unit 1 merged as `8dc72e3`, unit 2 as `61afae0` |
| 4 | Complete | Dated cash-flow NPV and IRR merged as `d5f0ca1` |
| 5 | Complete | Degradation result basis merged as `df7ffec` |
| 6 | Complete | Matched-training control merged as `196a5c1` (amendment `cba04f0`) |
| 7 | Complete | Acceptance (`docs/fundamentals_acceptance_2026-09-10.md`) and benchmark result (`docs/fundamentals_benchmark_2026-09-11.md`, run `34524611285`) both committed; the result is mixed by model family and recorded as such |
| 8 | Complete | Implementation and synthetic checks supplemented by independently reconciled official run `35252229873`; see the 17 September continuation report |
| 9 | Complete | Result PR #77 merged as `abfac6a`; CI run `34824236600` passed on Python 3.12 and 3.13 |
| 10 | **Review** | Branch `codex/stage10-study-results`; official private study verified; publication authorization and deployed-report verification outstanding |

## Readiness maintenance — 15 September 2026

Review the [Stages 1–9 audit](docs/history/implementation_report_stages1-9_audit_2026-09-15.md)
and the refusal repair on `codex/audit-stages1-9` before finishing the release PR. The official
Stage 9 result is unchanged; a future run uses the prospective 15 September declaration.
Stage 8's original acceptance includes an official study; the completed Stage 10 retry now
satisfies that check, as recorded in the 17 September continuation report.
Preserve expiring accepted inputs and witnesses and verify the documented restore path.

## Stage 9 — evaluate selection by battery value

Compare validation-RMSE selection against validation-settled-margin selection on the same model
families and candidate configurations, with deterministic tie-breaking and an explicit selection
schedule. Freeze the selected policy before its evaluation period. Include the synthetic case
where better RMSE earns less margin.

The existing benchmark is not changed retrospectively. Already inspected historical periods are
labelled retrospective supplementary evidence; any confirmatory claim needs a newly predeclared
untouched or prospective period. An unfavourable result is retained and reported as one.

**Done.** The protocol is predeclared in
[`docs/value_based_selection_design.md`](docs/value_based_selection_design.md). `greek_bess.selection`
scores one declared candidate grid by both objectives on validation days, freezes and hashes each
pick before settling any evaluation day, breaks ties by declared order and records them, and
reports held-out margin, regret against perfect foresight and against the retrospective best
candidate, cycling, capacity and price errors. The synthetic divergence case is committed and
passing, so the two objectives are known to be capable of selecting differently.

**Official measurement recorded.** Run `34623616511` reused accepted history `33483975614`
under the approved [declaration](docs/selection_run_declaration_2026-09-11.md), with existing
custody verified before prices were consumed. The [aggregate result](docs/selection_benchmark_2026-09-11.md)
records a positive signed difference, with complete calendars, frozen selections and private
evidence verified. Publication of the prepared aggregate record was separately authorized.

**Complete.** Result PR #77 merged as `abfac6a`, with CI run `34824236600` passing on Python 3.12
and 3.13. The result did not change the shipped selection policy.

## Stage 10 — deliver the portfolio release

Use the existing renderer. Produce a reproducible synthetic demonstration and an aggregate
official-history study with traceable inputs, under the existing custody and publication gates.
Verify the actual published report before calling publication complete.

**In review.** One declared synthetic configuration can now generate its own deterministic
price history, run the integrated study and render its verified manifest in one command. The
renderer lays every recorded strategy field out side by side without deriving a ranking or a
shared ceiling. The [official run declaration](docs/integrated_study_run_declaration_2026-09-14.md)
preregisters the accepted-history window and the 50 MW/100 MWh versus 25 MW/100 MWh
configuration sensitivity; the prepared workflow verifies the declaration and existing custody,
runs both configurations, renders their manifests, seals private evidence and does not publish.

Authorized run `35191734263` passed declaration, custody and calendar gates but failed before
producing a result at the hourly-to-quarter-hour transition. The failure is retained. The
[17 September declaration](docs/integrated_study_run_declaration_2026-09-17.md) preserves all
experiment settings and pins an explicit coarser-to-finer forecast-alignment repair.

Repair PR #81 merged as `76d48d5`; merge CI `35251110866` passed. The operator's instruction
to continue authorized one private retry of the unchanged 17 September declaration. Run
`35252229873` resolves to that merged commit. Continuation records use
`codex/stage10-study-results`.

Run `35252229873` succeeded. The [continuation report](docs/history/implementation_report_stage10_private_study_2026-09-17.md)
records independent reconciliation of all six paths, artifact identity, manifest figures and
byte-identical report re-rendering, together with the synthetic acceptance tests.

**Publication action outstanding: operator review of the completed private aggregate.**
The private report and findings brief are retained locally. After authorization, publish through
the applicable approved route and verify the deployed bytes before calling Stage 10 complete.
No new numerical study outcome is included in this documentation change.

## Active research unit — integrate frozen ML selection with ageing and costs

Branch: `codex/integrate-frozen-ml-policies`. The [design](docs/frozen_selection_study_design.md)
connects both existing Stage 9 selections to the integrated runner without refitting, retuning
or replacing the original forecasts. The accepted source index pins every consumed file.
Regression checks compare zero-fade replay to fixed-battery dispatch and preserve separate
ageing states, causal information, complete calendars and manifest provenance.

Two configurations are prepared: a zero-fade/zero-operating-cost reproduction baseline and
the same frozen policies with the existing illustrative physical-fade and operating-cost inputs.
This implementation does not create a new official empirical result. The original inspected
window remains retrospective supplementary evidence.

**Next action: review the integration and its final-head CI, then prepare the digest-pinned
official experiment declaration.** Do not rerun candidate training or select a different pair
because of an observed outcome. The separate Stage 10 publication action stays open.

## Reassess model additions only afterwards

Identify the largest measured source of decision uncertainty, and consider a new degradation,
dispatch or forecast family only if the current model demonstrably fails a relevant test and the
data exist. Require a declared hypothesis, baseline, validation method and acceptance criterion
first. Adding models is not progress.

The [dated model assessment](docs/model_assessment_and_research_agenda_2026-09-17.md) records
the proposed order: couple existing ML selection to ageing/costs, test the opportunity cost of
remaining battery life, and compare a limited forecast challenger set on untouched or prospective
data. Assess a calibrated LFP degradation model only with suitable validation data. Additional
markets require independent data and settlement validation. These remain backlog items;
The first item is now the active unit above; Stage 10's experiment remains unchanged and its
public release remains in review. Remaining items stay in the backlog.

## Open gates

The three items waiting on something outside this repository are listed under **Open gates** in
[`STATUS.md`](STATUS.md) and are not repeated here.

## Operating constraint on live retrieval

The development environment's egress policy refuses `www.admie.gr`, so ADMIE catalog queries, file
retrieval and timing audits are performed by dispatching the relevant workflow and reading its
uploaded evidence, never from a working checkout. That constraint is per host and not universal:
the v0.9 spike of 2 September 2026 reached `noaa-gfs-bdp-pds.s3.amazonaws.com`, `pypi.org` and
`raw.githubusercontent.com` from a checkout, while the same policy refused `www.eex.com`,
`eur-lex.europa.eu`, `data.ecmwf.int`, `archive-api.open-meteo.com` and `registry.opendata.aws`.
Check the host before assuming a live step must be a workflow run, and plan it as one whenever the
host is refused.
