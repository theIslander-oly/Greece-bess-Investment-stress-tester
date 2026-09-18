# Frozen-selection study integration — 18 September 2026

## Outcome

The integrated runner can replay both previously accepted Stage 9 selections through separate
battery-ageing and finance states without retraining or selecting again. This supplies the
implementation needed to measure whether the historical selection gain survives ageing and
declared costs. No new official comparison has been run and no new superiority claim is made.

The operator requested continuation and confirmed that the Stage 10 report was not published.
PR #82 is merged as `a294ab2`, with successful merge CI `35254232678`. Stage 10 publication
remains open. The active branch is `codex/integrate-frozen-ml-policies`.

## Changes and evidence contract

The [design](../frozen_selection_study_design.md) was recorded before implementation. Two
planners replay the frozen validation-RMSE and validation-margin selections. A declared index
digest pins the original bundle. Every indexed file, selection seal, candidate identity,
evaluation calendar, UTC interval, source, duration and copied realized price is checked.
Selected forecasts must be finite; missing observations are refused, never interpolated.

Original forecasts are preserved: regenerating them with subsequently repaired forecasting
code would confound the experiment. The adapter handles the legacy producer's LF/CRLF semantic
checksum explicitly, without changing source bytes, values, precision or recorded hashes.
Hashes establish identity; causal construction rests on independent upstream acceptance.

The existing dispatch, settlement, physical fade and finance contracts are reused. Each
strategy owns its state. Summary and manifest provenance identify the source and selected
candidate. Signed paired differences report margin-selection minus RMSE-selection in cash
margin, NPV, cell-based EFC, final capacity and project cash flow. No shared evolving-state
upper bound is introduced. Existing studies need no new configuration field.

Two prepared configurations declare zero-fade reproduction and the existing illustrative
ageing/cost assumptions. They are experiment preparation, not recorded experiment outcomes.
The design also records the buy/sell optimization, round-trip-loss arithmetic, terminal SOC,
and the distinction between physical fade, dispatch wear penalties and post-dispatch costs.

## Validation

Nineteen new tests cover fixed-battery equivalence, independent state and order invariance,
zero/negative prices, hourly and quarter-hour DST, future-outcome mutation, UTC row ordering,
evidence refusal, provenance, report rendering and producer line endings. Synthetic fixtures
establish implementation properties only.

A read-only admission check of the retained original Stage 9 bundle passed: 31,584 evaluation
intervals, the original ridge and gradient selections, and the original LF semantic digest.
The evidence-index digest is
`33e78be5952c1f3afd5632b6ec0709d73f99839537ada77ba3e2c3ad058c0bcc`.
This check did not run dispatch or produce new official numerical findings.

The full regression run passed 830 tests and exposed one stale acceptance expectation: the
completed Stage 10 declaration intentionally refuses changed source bytes. Its original document
and hashes remain unchanged. The regression now verifies that historical refusal and separately
checks successful admission of matching bytes in a disposable prospective fixture. No official
declaration was repinned and the old workflow cannot silently rerun against changed code.
All six Stage 10 declaration tests pass after that correction; the suite now contains 832 tests.

Ruff and mypy pass (76 source files). A clean isolated wheel build from the staged source passes.
The complete change review includes whitespace, local documentation links, credential patterns,
generated-file exclusions and contributor-neutral content. Official data and generated results
remain outside Git. Final-head CI supplies the cross-platform regression check.

## Next measurement

After implementation review and successful final-head CI, prepare and review the concrete
official-run declaration. Use the original accepted forecasts and evaluation window. Establish
zero-fade reproduction first, then apply the declared ageing and costs and retain all outcomes.
The inspected historical period remains retrospective supplementary evidence. Subsequent
life-aware policy and new forecast-family work remain separate research units.
