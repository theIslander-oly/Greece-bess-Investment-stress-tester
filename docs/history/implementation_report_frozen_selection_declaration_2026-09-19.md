# Frozen-selection experiment preparation — 19 September 2026

## Outcome

PR #83 is merged as `d57125eca16f6cdbdae19ffe5eb29d5c98d1ef89`; merge CI `35316480803`
passed on Python 3.12 and 3.13. The continuation advances the next action in PLAN: prepare the
concrete official experiment declaration. No official dispatch, new empirical result, merge or
public report deployment is performed by this preparation.

The [declaration](../frozen_selection_run_declaration_2026-09-19.md) fixes the original accepted
Stage 9 selections and calendar, the existing two configurations, numerical runtime and
reproduction tolerances. Its complete-document SHA-256 is
`178ed1903a6072acc3a7c0ca95b62aedbeb46e5ac6878ecd9e92c1e9c468819f`.
The complete package tree, including added or removed modules, and each relevant configuration
and evidence record are pinned. No analytical package file or completed declaration changes.

## Review choices

Zero-fade replay must reproduce daily fixed-battery cash margins and grid flows and reconcile
with the original unrounded evaluation aggregates before the ageing/cost case can run. Daily
absolute tolerances are `1e-6` EUR and MWh respectively; aggregate tolerance is `329e-6` in each
unit, with zero relative tolerance. Changed outcomes cannot justify relaxed tolerances.

The source's grid-based EFC and the integrated model's cell-based EFC retain separate definitions.
The combined fade/OPEX comparison does not attribute changes separately to each assumption.
Both signed cash-margin and NPV differences are reported; their signs need not agree and neither
sign determines acceptance. The short finance window is not a lifetime return estimate.

The execution protocol uses the existing local CLI and requires private custody verification,
baseline reproduction, independent accounting and retained evidence before publication review.
It does not reuse or alter the historical Stage 10 workflow. Stage 10 publication remains open.

## Validation

Seven new regressions check the configuration pair against the accepted battery, the exact
permitted differences, changed document/configuration/source refusal, added/deleted modules and
repository path containment. Fixtures are synthetic and generated in disposable test directories.
The read-only declaration verifier passes against the current source. A separate read-only
check confirms the retained accepted selection index, all indexed files, source commit/run,
selection seal and candidate-forecast identity. It runs no optimizer.

Ruff, mypy and a clean isolated wheel build pass. Full-suite and cross-platform validation are
required review gates; private local logs and final-head PR checks retain their outcomes.
The complete diff review checks whitespace, documentation links, credential
patterns, contributor-neutral content and generated/private-file exclusions.

## Next gate

Review the declaration and final-head CI, then authorize the exact document digest before the
private experiment. Preserve all valid outcomes and diagnostics. Any source, runtime, assumption
or tolerance change requires a prospective amendment. Public publication is separately gated.
