# Stage 9 official result record — 11 September 2026

## Change and evidence

PR #76 merged as `1fdd81628951c02c185b3b806318385038a5137a`, with a tree identical to the
reviewed head. CI run `34622953345` passed on Python 3.12 and 3.13. The operator then approved
the unchanged declaration and one official dispatch.

Comparison run `34623616511`, attempt 1, succeeded using accepted history `33483975614`.
Custody verified before prices were consumed. Independent checks verified all declaration and
evidence digests, exact calendars including DST, all-candidate coverage, forecast price-error
metrics, validation-only picks and tie breaks, frozen selection and summary reconciliation.
The retained ZIP matched GitHub's digest and all extracted bytes matched that archive.
Numerical command output was absent from the ordinary workflow log.

The operator reviewed the private aggregate proposal and authorized its publication in a
reviewable PR. The [result record](../selection_benchmark_2026-09-11.md) transcribes approved
metrics and provenance. Validation-margin selection settled EUR 12,639.14 more on the declared
evaluation window, with more cycling. This is retrospective supplementary evidence only.
No analytical code, selection policy, pinned declaration input or accepted earlier result changes.

README, changelog, status, plan and decision records now identify the official measurement.
Stage 9 is in Review pending this result PR's review and merge; Stage 10 remains Pending.
README and limitations claims predating the accepted fundamentals benchmark are corrected while
that earlier result remains unchanged. A documentation regression checks that the result's
declaration link and recorded SHA-256 identify the same committed text, without placing official
data in tests.

## Validation

The result table and all published digests were checked against the privately retained evidence
and the approved proposal. Local validation on Python 3.13.7 passed: Ruff reported no findings,
mypy reported no issues across 75 source files, all 792 pytest tests passed, and an isolated
wheel build produced `greek_bess_investment_stress_tester-0.9.7-py3-none-any.whl`. PR CI repeats
the gates on Python 3.12 and 3.13.

## Remaining gates and limitations

Review and merge the result PR, then decide whether to proceed to Stage 10. No report deployment
or change to the shipped model-selection policy is authorized by this result. The Stage 9 index
is not a registered renderer manifest. GitHub retains the private artifact until 10 December
2026; a local exact archive is also retained outside Git, and neither establishes independent
durable custody. One inspected historical window supports no confirmatory, probability or
expected-revenue claim.
