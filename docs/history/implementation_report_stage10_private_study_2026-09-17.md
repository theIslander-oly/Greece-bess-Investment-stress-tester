# Stage 10 private official study and research agenda — 17 September 2026

## Outcome

The unchanged repaired official study completed successfully and its retained private results
independently reconcile. This satisfies Stage 8's outstanding official-history acceptance.
Stage 10 moves to review: numerical result publication is not authorized and the deployed-report
check remains open. No new numerical study outcome is published in this record.

Record the [model assessment and ordered research agenda](../model_assessment_and_research_agenda_2026-09-17.md)
requested with the continuation. It summarizes already accepted findings, assesses dispatch,
forecasting, degradation, lifetime policy, finance and stress methods, and records primary
research references. The proposed extensions remain backlog; no model or active declaration changes.

## Authorization and execution identity

- Repair PR #81 merged as `76d48d5aea505fefe51ca948cc901d6fbda594a0`.
- Merge CI `35251110866` passed on Python 3.12 and 3.13 before dispatch.
- After reviewing the proposed continuation, the operator instructed continuation of the current
  study and recording of the model assessment. This authorized one private retry, not publication.
- The local declaration guard passed, the remote main SHA was checked, and the dispatched run's
  resolved SHA was checked again. No later commit was silently substituted.
- [Official run 35252229873](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/35252229873),
  attempt 1, succeeded using accepted history `33483975614` and declaration SHA-256
  `007c90444aedf17135601035c3b46a9731b7117a531692f92e4173f28cdcbe79`.
- Runtime: Python 3.12.14, NumPy 2.5.3, pandas 2.3.3, SciPy 1.18.1, project 0.9.7.

## Retention and independent review

Artifact `integrated-study-private`, ID `10510326086`, expires 16 December 2026 at 17:21:26 UTC.
The original ZIP is retained at `private/stage10-35252229873.zip`; its SHA-256 matches GitHub:
`9aaa06804b7baf3079c24d76ee7b8dbce45264f85b7dddb5f387a7d11c20f4a9`.
Every extracted file matches its original archive member. The evidence-index SHA-256 is
`214a4caaf52d16f9bd7cb508eb9334f94bfa3a98696cc4820b89eec612daf938`.
All 18 indexed file hashes and every declaration input pin match. The custody receipt reports
six verified source files and zero differences. The declaration is unchanged byte for byte.

Private evidence is at `private/stage10-35252229873/`. Independent reconciliation code and its
machine-readable result are retained privately as `private/audit_stage10_result.py` and
`private/stage10-35252229873-independent-audit.json`. This is an audit of the recorded outputs,
not a second official scientific run. A local copy and a GitHub artifact are not independent
durable custody; the separate custody issue remains open.

Both configurations contain three strategies, each with all 329 market days and 31,584 native
quarter-hour intervals. Every day agrees with the accepted source calendar. Each strategy's
daily margin, initial/terminal SOC, cell versus grid discharge, daily grid-cycle constraint,
energy continuity, cohort fade and final capacity independently reconcile. Finance reads the
recorded cash margin and applies fixed/variable operating costs once; independent dated NPV
and IRR residual calculations agree with the summaries. These checks retain the distinction
between cell-based reported EFC and grid-based daily dispatch limits.

The workflow rendered two verified manifests. Local re-rendering reproduces the exact HTML
SHA-256 `5fb8ccc56b083d9f2cc3a1fdf05b0252c86a4599da1cec29913d3bbb9bdbd342`.
The renderer continues to report every strategy's own state and does not invent a common ceiling,
cross-configuration difference or lifetime interpretation.

## Acceptance matrix

| Check | Evidence | Disposition |
| --- | --- | --- |
| 1. One declared command/configuration produces a study | Existing synthetic command tests and completed official workflow, both configurations | Pass |
| 2. Zero-fade equivalence | `CheckTwoZeroFadeReproduction` in `tests/test_integrated_study.py` compares to fixed-battery dispatch | Pass in current suite |
| 3. Separate state and order invariance | Synthetic state/order tests plus independent cohort reconstruction for all six official paths | Pass |
| 4. Causality | Future-price mutation regression in the current suite; official configuration retains declared causal planners | Pass |
| 5. Energy, fees and cash reconciliation | Synthetic augmentation/nonzero-cost tests plus independent official daily and finance identities | Pass |
| 6. Missing days refused | Existing incomplete-window and forecast regressions; official calendars agree exactly | Pass |
| 7. Reproducibility | Synthetic repeated-execution tests; official archive and indexed hashes verified; report re-render byte-identical | Pass; no claim of a second full official replay |
| 8. No shared evolving-state ceiling | Existing contract tests and both recorded summaries/manifests | Pass |
| 9. Provenance, configuration sensitivity and horizon labels | Declaration pins, source SHA, custody, runtime and report index verified; costs and finite horizon retained | Pass |
| 10. Release review, consistent current notes and publication | README, STATUS, PLAN and LIMITATIONS updated; private result and findings brief prepared | Review; public publication authorization and deployed-byte verification still open |

Synthetic unit tests are evidence of implementation properties, not official investment evidence.
The official run supplies the missing real-history execution check; it does not validate OEM
parameters, future prices, actual market acceptance or a lifetime forecast.

## Validation and change scope

- Ruff passed; mypy passed for 75 source files.
- All 812 tests passed locally in 186.38 seconds with numerical-library thread counts set to one.
- An isolated wheel build from a fresh archive of the reviewed producing commit succeeded.
  Subsequent changes are documentation only; no package code, dependency or experiment pin changed.
- Existing regression coverage is reused: no new analytical behavior was introduced that would
  justify a mirrored or prose-only test. Official reconciliation is retained as private run evidence.
- Review includes whitespace, local Markdown links, generated-file and secret checks, and the
  contributor-neutral attribution convention. Only documentation is intended for this PR.

## Handoff

Continuation branch: `codex/stage10-study-results`, based on the reviewed producing commit.
The private findings brief is `outputs/integrated-study-findings-2026-09-17.md`; the original
verified report remains inside the private evidence bundle. No numerical result or provider
data is staged for Git. Existing accepted benchmark aggregates in the model-assessment note
are already published records, not the new integrated result.

Next single action: operator review of the completed private aggregate for publication
authorization. After approval, publish through the approved route and verify the deployed
bytes before completing Stage 10. Do not start a new model experiment in the meantime.
