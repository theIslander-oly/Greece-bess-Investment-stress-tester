# Implementation plan

What happens next, and the gate each step has to pass. Where the work stands today is in
[`STATUS.md`](STATUS.md); the handoffs and completed-milestone records that used to live here are
in [`docs/history/plan_log_through_2026-09-11.md`](docs/history/plan_log_through_2026-09-11.md).

The staged plan in [`Greek_BESS_Execution_Plan.md`](Greek_BESS_Execution_Plan.md) is active and
authoritative. Only one stage moves at a time, and no stage is renumbered.

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
| 8 | Complete | `greek_bess.study` and `run-integrated-study` merged as PR #69, with the cash and stored-energy conventions corrected in PR #71 (`docs/integrated_study_design.md` sections 4.5, 5.3, 5.4) |
| 9 | **In progress** | Design (`docs/value_based_selection_design.md`), `greek_bess.selection` and `compare-selection-objectives` implemented and validated, with the synthetic divergence case committed. No official-history result yet; see below |
| 10 | Pending | Branch `release-integrated-research-study`; see below |

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

**Next gate: approve the declaration and dispatch the official-history run.** Branch
`stage9-official-selection-workflow` prepares `Compare official selection objectives` and
[`selection_run_declaration_2026-09-11.md`](docs/selection_run_declaration_2026-09-11.md).
The workflow checks the declaration digest, verifies existing custody before reading prices,
refuses incomplete calendars and retains private evidence for any result sign. No official result
exists; Stage 9 remains in progress. Review the declaration and CI before authorizing dispatch.
Publication and a change to the shipped selection policy remain separate gates.

## Stage 10 — deliver the portfolio release

Use the existing renderer. Produce a reproducible synthetic demonstration and an aggregate
official-history study with traceable inputs, under the existing custody and publication gates.
Verify the actual published report before calling publication complete.

Its acceptance check requires a `STATUS.md` and a `PLAN.md` that make no contradictory
current-state claims.

## Reassess model additions only afterwards

Identify the largest measured source of decision uncertainty, and consider a new degradation,
dispatch or forecast family only if the current model demonstrably fails a relevant test and the
data exist. Require a declared hypothesis, baseline, validation method and acceptance criterion
first. Adding models is not progress.

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
