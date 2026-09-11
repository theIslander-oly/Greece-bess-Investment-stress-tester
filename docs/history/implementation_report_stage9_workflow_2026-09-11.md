# Stage 9 official-run workflow — 11 September 2026

## Change and evidence

Baseline `b8114aa` had no Stage 9 official workflow or result. CI run 176 succeeded and no
PR was open at inspection. The comparison CLI prints result figures, so the new manual workflow
captures its output and diagnostics in the restricted artifact instead of ordinary logs.

The dated declaration pins the existing candidate, fitting, battery, protocol, custody and
workflow bytes. Before download it checks the operator-supplied document digest and source run;
after download it requires the existing custody record to verify, never generating a replacement.
Calendar checks refuse missing, extra and incomplete delivery days. Result checks enforce the
full declared validation/evaluation windows and the frozen selection digest. The evidence index
records file hashes, declared inputs, source commit, workflow attempt and runtime package versions.
Retention is independent of the signed result; failed attempts retain diagnostics without a
completed evidence index. No analytical source module changes.

The status head-SHA line becomes a live CI link, avoiding a new stale SHA on every merge.
Stage 9 remains in progress and Stage 10 remains pending.

## Validation

Local Python 3.12: 21 existing selection tests and nine new workflow tests pass through unittest,
including a synthetic CLI-to-evidence-index round trip and retention of negative, zero and
positive headline values. No official prices were downloaded or inspected.
Development dependency installation was blocked by the execution environment's network approval;
Ruff, mypy, the full pytest suite and wheel build are therefore delegated to the PR CI matrix
on Python 3.12 and 3.13. Their outcome must be verified before this milestone is accepted.

## Remaining gate

Review CI and the dated declaration before approving merge and official dispatch. The declaration
records no operator authorization. No official run, result, publication or selection-policy change
was performed. The private workflow index is not a generic renderer manifest; a Stage 9 renderer
kind remains release work. Artifact retention is 90 days, not independent durable custody.
