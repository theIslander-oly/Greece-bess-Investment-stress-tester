# Implementation report v0.7.11 — Run manifest and report contract

**Date:** 31 August 2026

## Scope

Adds `greek_bess.reporting` (`contract.py`), the `record-run-manifest` and
`verify-run-manifest` CLI commands, `docs/run_manifest_contract.md`, and a `result_label` on the
ADMIE publication-timing summary.

No dispatch mode, forecast method, stress transformation, degradation model, finance treatment
or data-ingestion behaviour changes. No interface, dashboard, exporter, rendering surface or
dependency is added. **This does not open v0.8.**

## The problem

The completed-v0.7 review found the domain APIs interface-ready with one qualification: result
summaries are "dictionaries rather than a versioned presentation schema, so a future interface
should first define a versioned run manifest and report contract instead of coupling UI
callbacks directly to incidental summary keys."

Two facts made that concrete. Sixteen modules emit summaries across twenty-seven CLI commands,
and exactly one artifact in the codebase carried a `schema_version` — the retrieval manifest. And
`PROMPT.md` requires that "model outputs must retain their source and limitation labels through
downstream analysis", a requirement fifteen of the sixteen modules honoured by convention and
nothing enforced.

## What was built

A thin, versioned wrapper. The producing module's summary is carried **verbatim** — the contract
adds a projection over a result, it does not reshape, recompute or reinterpret one. The
projection is what a consumer reads instead of incidental keys: `schema_version`, `result_kind`
from a closed registry, the `basis` that kind reports on, the required non-empty `result_label`,
`produced_by`, `manifest_id`, `project_version`, `declared_inputs` and the standing exclusions.

The label is carried from the summary rather than re-declared in the registry. Re-declaring it
would create two sources of truth that could drift; carrying it makes drift impossible.

`basis` is the discriminator a consumer needs before rendering anything: the same euro figure
means something different as a historical replay upper bound, a historical forecast backtest, a
synthetic scenario, screening arithmetic, or data-acceptance evidence.

## Why the distributional-term check is scoped

`FORBIDDEN_REPORT_TERMS` is applied only to result kinds declaring
`forbids_distributional_terms` — today `scenario_ensemble_range` alone, exactly matching the
behaviour the ensemble already enforced.

The list bans claims about the distribution of **outcomes**, not the words themselves. The
perfect-foresight optimizer's real summary contains `average_charge_price_eur_per_mwh`, a settled
input price. A forecast benchmark reports a mean absolute error, an accuracy statistic about a
model. The publication-timing audit reports a median lead time, a statistic about a publisher. A
blanket check would refuse all three, and a check that refuses honest arithmetic teaches its
readers to route around it — a worse outcome than no check.

This was verified against real output rather than reasoned about: a regression test runs the
optimizer and asserts its genuine summary carries such a term, so the reason for the scoping
stays visible instead of being tidied away later.

## The standing claims are verified where they are declared

Every manifest asserts the three standing exclusions. Where a summary declares them itself —
only the scenario ensemble does today, via `is_probabilistic`, `is_forecast` and
`is_investment_evidence` — the contract cross-checks and refuses any value but false. A module
that began reporting a genuinely probabilistic result would otherwise be recorded under a
manifest still asserting the opposite; that is a scope change requiring a recorded decision.

## What is refused rather than approximated

- A summary with no `result_label`, an empty or whitespace label, or missing a key its kind
  guarantees.
- An unknown `result_kind`, refused with the closed registry listed.
- A blank or untrimmed `manifest_id` or `produced_by`, a non-mapping summary or declared inputs.
- On read: a `schema_version` this build does not understand, an unknown result kind, a declared
  `basis` disagreeing with its kind, missing required fields, or a non-object summary.

## Test and validation evidence

`tests/test_report_contract.py` adds 22 tests covering the registry's internal consistency and
basis coverage, verbatim summary carriage, every refusal above, the scoping of the distributional
check in both directions, the standing-claim cross-check, a full write/read round trip, and the
CLI's `0` and `1` exit codes.

Two of those tests are integration rather than fixture tests: they run the perfect-foresight
optimizer and build a manifest from the summary it genuinely produces. A registry can otherwise
be satisfied by a fixture that no real summary satisfies. The command path was also exercised end
to end on synthetic prices before the tests were written.

Ruff, mypy, the complete pytest suite and a clean wheel build pass.

## Roadmap consequence

`PLAN.md` records the prerequisite as met and keeps v0.8 open, with the design questions it must
answer named: the landing state when no judgmental input has been declared (every one has no
default by recorded decision, and an interface must render something), how a rendered figure
carries its label and exclusions, and what an export refuses to contain. The same entry records
the 2026-08-31 reevaluation finding that v0.8 appears in the suggested branch sequence but not in
`PROMPT.md`'s approved scope, so opening it is a scope change rather than the next milestone.
