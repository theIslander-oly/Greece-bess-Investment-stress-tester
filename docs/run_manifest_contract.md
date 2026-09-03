# Run manifest and report contract — 31 August 2026

## The problem this contract exists to solve

The completed-v0.7 review found the domain APIs interface-ready, with one qualification: their
result summaries are "dictionaries rather than a versioned presentation schema, so a future
interface should first define a versioned run manifest and report contract instead of coupling
UI callbacks directly to incidental summary keys."

Sixteen modules emit summaries across twenty-seven CLI commands. Before this contract, exactly
one artifact in the codebase carried a `schema_version` — the retrieval manifest. Anything
reading a result had to know which module produced it and which keys that module happens to use.

`PROMPT.md` also requires that "model outputs must retain their source and limitation labels
through downstream analysis". That was a convention, kept by fifteen of the sixteen modules and
enforced by nothing. A consumer could drop the label and no check would notice.

## What the contract is, and what it deliberately is not

It is a thin, versioned wrapper. It does **not** reshape, recompute or reinterpret a result. The
producing module's summary is carried verbatim, and the contract adds a stable projection over
it:

| Field | Guarantee |
|---|---|
| `schema_version` | Refused on read when it is not a version this build understands. |
| `result_kind` | A member of a closed registry. |
| `basis` | What the number describes, from `RESULT_BASES`. |
| `result_label` | Required and non-empty, carried from the summary. |
| `produced_by`, `manifest_id` | Required, non-empty, declared by the caller. |
| `project_version` | The version of the code that produced the result. |
| `standing_exclusions` | The project's three standing negative claims, on every manifest. |
| `declared_inputs` | Caller-declared input provenance. |
| `summary` | The producing module's own summary, unchanged. |

The label is carried from the summary rather than re-declared in the registry. Re-declaring it
would create two sources of truth that could drift; carrying it makes drift impossible.

## The basis is the discriminator

The same euro figure means something different depending on what produced it, so a consumer
needs one field that says which:

- `historical_replay_upper_bound` — perfect foresight over real history; a ceiling, not revenue.
- `historical_forecast_backtest` — a causal forecast settled at realized prices.
- `synthetic_scenario` — bootstrap paths and declared transformations; not history and not a
  forecast.
- `screening_arithmetic` — finance and degradation arithmetic over a supplied operating path.
- `data_acceptance_evidence` — evidence about data, such as publication timing.

## Why the distributional-term check is scoped, not universal

`FORBIDDEN_REPORT_TERMS` bans claims about the **distribution of outcomes**. It is not a ban on
the words themselves, and the contract applies it only to result kinds that declare
`forbids_distributional_terms` — today, `scenario_ensemble_range` alone, exactly matching the
behaviour the ensemble already enforced.

This scoping is load-bearing, not a loophole. The perfect-foresight optimizer's real summary
contains `average_charge_price_eur_per_mwh` — a settled input price, not a claim about
outcomes. A forecast benchmark reports a mean absolute error, which is an accuracy statistic
about a model. The publication-timing audit reports a median lead time, which is a statistic
about a publisher. A blanket ban would refuse all three, and a check that refuses honest
arithmetic teaches its readers to route around it.

There is a regression test asserting that a genuine optimizer summary carries such a term, so
the reason for the scoping stays visible rather than being "simplified" away later.

## The standing claims are verified, not merely asserted

Every manifest asserts the three standing exclusions. Where a summary declares them itself —
only the scenario ensemble does today, via `is_probabilistic`, `is_forecast` and
`is_investment_evidence` — the contract cross-checks rather than ignores them. A module that
began reporting a genuinely probabilistic result would otherwise be recorded under a manifest
still asserting the opposite. Such a result is a scope change requiring a recorded decision, so
the contract refuses it by name.

## The registry is closed on purpose

An unknown `result_kind` is refused with the known kinds listed. A consumer can only rely on a
registry that cannot grow by accident: a new kind is a deliberate, reviewable addition that
states its basis and the summary keys it guarantees.

Required keys beyond `result_label` are declared only where they have been verified against a
real summary. The registry is expected to tighten as consumers need firmer guarantees; it starts
honest rather than aspirational.

## Using it

```bash
greek-bess optimize-perfect-foresight prices.csv --config battery.json --output dispatch.csv

greek-bess record-run-manifest dispatch.summary.json \
  --result-kind perfect_foresight_dispatch \
  --manifest-id 2026-08-31-replay \
  --produced-by optimize-perfect-foresight \
  --declared-inputs inputs.json \
  --output dispatch.manifest.json

greek-bess verify-run-manifest dispatch.manifest.json
```

`record-run-manifest` refuses a summary that lacks its label or its kind's guaranteed keys.
`verify-run-manifest` refuses a manifest from an unknown schema version or result kind, one
whose declared basis disagrees with its kind, one whose summary contradicts a standing exclusion
or carries distributional vocabulary its kind forbids, and one whose `declared_inputs` is not an
object. See the 2 September 2026 amendment for why the guaranteed-key check is not among them.

## Amendment, 1 September 2026 (v0.8.1)

Two changes, both recorded in `DECISIONS.md` under *"Record the ensemble's per-path ranges in its
summary, rather than reading its CSV"*.

**`scenario_ensemble_range` guarantees more.** Its required summary keys are now `result_label`,
`scenario_count`, `scenario_names`, `scenarios`, `equivalent_basis`, `path_count` and
`path_ranges`. A report renders verified manifests and nothing else, so a range the ensemble did
not record in its summary is a range no report can show; `report_scenario_ensemble` therefore
records its per-path ranges as well as the four extreme aggregates. The envelope is unchanged, so
`schema_version` stays at 1 and an ensemble manifest recorded before this amendment still reads
and still renders — the guaranteed-key check runs when a manifest is built, not when one is read,
and the report says plainly that such a manifest records no per-path ranges.

**The distributional-term check reaches nested keys.** For the kinds that declare
`forbids_distributional_terms`, every key name at any depth of the summary is checked, not only
the top-level names. The scoping to those kinds is unchanged and still load-bearing for the
reasons above; the depth changed because a report renders a nested key as a visible column
heading, and a top-level scan would clear a per-path table whose headings claimed a percentile.

## Amendment, 2 September 2026 (v0.8.3)

The completed-v0.8 review found that two of the contract's checks ran only when a manifest was
built. Recorded in `DECISIONS.md` under *"Check recorded content on read, and guaranteed keys
only on record"*.

**Reading now applies every check that is a property of the recorded content.** In addition to
the schema version, the closed registry and the basis cross-check, `read_run_manifest` applies
the standing-claim cross-check and, for a kind that declares it, the distributional-term
refusal — and refuses a `declared_inputs` that is not an object, which previously raised an
unhandled error. A manifest travels, and a reader has only the file: a summary declaring
`is_probabilistic` was refused when recorded yet read and rendered, placing that claim in a
report directly above the standing exclusion "not a probability-calibrated estimate". Neither
check can refuse a manifest this project recorded, because building one already applied both.

**The guaranteed-key check stays a record-time check.** It is a promise about what a producing
module recorded at the time it recorded it, not a property of the file, and the 1 September
amendment above depends on it staying that way: an ensemble manifest written before
`path_ranges` existed still verifies and still renders. Because a report may therefore meet a
manifest without one of its kind's guaranteed keys, the renderer states that key as not recorded
by the same route it states any other absent value. It previously read the key straight out of
the summary and raised `KeyError`.

The envelope is unchanged, so `schema_version` stays at 1 and every manifest recorded earlier
still reads and still renders.

## What this does not do

It does not open v0.8. No interface, dashboard, exporter or rendering surface is added, and no
dependency is introduced. The contract is the prerequisite the v0.7 review named; whether a
research interface is built on it remains a separate decision requiring explicit approval.

## Renderer contract amendment, 2 September 2026 (renderer version 3)

The manifest envelope and `REPORT_CONTRACT_VERSION` remain unchanged at 1. Renderer version 3
adds deterministic inline SVG for the per-path values a `scenario_ensemble_range` manifest has
already recorded under `path_ranges`. The chart is a second rendering of those values, not a new
manifest field and not a new result: it reports no derived quantity and its visible value labels
retain the recorded text without rounding or conversion.

The chart dispatcher is closed by result kind and summary key. It receives only the verified
manifest already being rendered; it cannot accept another source, open a manifest-declared path,
read environment or network state, or combine manifests or bases. Missing, empty and structurally
unusable chart fields are stated as unavailable. The chart remains inside the same labelled
figure block as the existing tables and therefore carries that manifest's `result_label`, basis
wording and standing exclusions. The HTML remains self-contained and script-free.

## Amendment, 2 September 2026 (v0.9.3)

The registry gains `fundamentals_forecast_benchmark` on the `historical_forecast_backtest` basis,
guaranteeing `result_label`, `ablation_arms`, `feature_set_sha256`, `decision_cutoff_schedule_id`,
`decision_lead_minutes`, `evidence_grades_admitted`, `common_day_count`, `excluded_days_by_cause`,
`metrics`, `selected_challenger` and `is_exploratory`. The envelope is unchanged and
`REPORT_CONTRACT_VERSION` stays 1, so every older manifest still reads.

`forbids_distributional_terms` is deliberately left unset, for the reason the module already
gives: a mean error and a median absolute error are statistics about a model, not claims about a
distribution of investment outcomes. The summary instead declares `is_probabilistic`,
`is_forecast` and `is_investment_evidence` as `false`, which the standing-claim cross-check
verifies rather than ignores.

**A third check runs on record and on read.** A summary that admits the quarantined `assumed`
availability grade while declaring `is_exploratory` anything but `true` is refused. Availability
inferred from a regulatory deadline or a nominal latency, rather than from the datum, is usable
only in an explicitly labelled exploratory run and never as accepted evidence (decision entry
2 September 2026). The check runs on read for the same reason the other two do: a manifest
travels, a hand-edited summary is exactly the case it exists for, and the renderer reads through
that doorway — so such a manifest refuses the whole report rather than one block of it.
