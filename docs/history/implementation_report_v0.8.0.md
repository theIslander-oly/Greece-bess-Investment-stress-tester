# Implementation report v0.8.0 — Report rendering foundation

**Date:** 1 September 2026

## Scope

Adds `greek_bess.reporting.render` and the `render-report` CLI command, the first milestone of
the v0.8 research interface and exportable reports opened on 1 September 2026 by explicit user
approval. The design of record is `docs/v0.8_design.md`; this report describes what was built
against it.

No dispatch mode, forecast method, stress transformation, degradation model, finance treatment or
data-ingestion behaviour changes, and no accepted figure moves. No runtime dependency is added:
the renderer uses the standard library and the manifest contract. Nothing listens on a port.

## The problem

The completed-v0.7 review found the domain APIs interface-ready once a versioned run manifest and
report contract existed, and that contract landed as v0.7.11. What was still missing was a way to
get a recorded result out of the repository and in front of a reader without the reader having to
know which of sixteen modules produced it, what its basis was, or what it is not.

An export is the artifact most likely to travel beyond someone who knows this project's limits.
That makes a rendering surface the place where interpretation rules are most likely to erode: a
figure copied out of a summary loses its label, two figures of different bases end up in one
table row, and a page rendered before anything is declared quietly becomes the default.

## What was built

A presentation layer that is thin by construction rather than by discipline. One sentence governs
it:

> A report renders verified manifests, and only verified manifests.

`read_run_manifest` is the sole doorway. Every integrity property the contract enforces — the
schema-version check, the closed kind registry, the basis cross-check, the guaranteed-key check
and the scoped distributional-term refusal — is therefore **inherited** here, not restated. A
number that never passed through the contract cannot appear in a report, because the manifest
list is the renderer's only numeric input and there is no side channel.

`render-report` writes one self-contained HTML file — no scripts, no external stylesheets, fonts
or images, no network fetches — and a machine-readable index beside it. Reports and indexes are
generated research outputs and stay outside Git, like every other CLI output.

### The landing state is the declaration checklist

Every judgmental input in this project has no default by recorded decision: the bootstrap source
era (2026-08-27), the spread-compression factor and reference basis (2026-08-28), the
availability baseline (2026-08-31), the negative-price event list (2026-08-31) and the scenario
set of an ensemble (2026-08-31). An interface must render *something* before any of them is
declared, and whatever it renders becomes the de facto default.

Invoked with no manifests, `render-report` produces the declaration checklist: each default-free
input, what must be declared about it, the dated decision that made it default-free, and the
command that records a result once the declaration is made. It contains no figures, no example
numbers and no synthetic demonstration. A blank page would be unhelpful; a demo with implied
defaults would silently settle every trade-off the decision log refused to settle; a refusal with
instructions is the honest third option.

A regression test strips the decision dates from the page and asserts not one digit remains, so
"no example number" is checked rather than intended.

### Every figure carries its label beside it

Each figure renders inside a block that displays, adjacent to the figure and not in a global
footer, the manifest's `result_label`, its `basis` in reader-facing words, and the three standing
exclusions the manifest carries. All of it is read from the manifest; the renderer never
re-declares a label, so it cannot drift from the sentence the producing module wrote — the same
one-source-of-truth rule the contract itself follows.

The report is organised by basis in the order the contract declares them, so a reader meets the
ceiling/backtest/scenario distinction as the structure of the document rather than as a footnote.
Kinds with guaranteed summary keys beyond `result_label` render those keys as their headline; the
headline keys are read from the registry rather than listed again here, so a kind that tightens
its guarantees changes its headline without touching the renderer. Everything else in a summary
renders as the recorded key-value detail it is.

## What is refused rather than approximated

- **A manifest this build cannot honor refuses the whole report**, with the contract's own error.
  There is no partial render, and the CLI writes no file: a report that silently omitted a
  failing manifest would present the remainder as the whole.
- **Two inputs declaring one manifest ID.** A manifest ID names one recorded run, and a report
  listing it twice would present one run as two.
- **Renderer vocabulary that reads as a claim about a distribution**, for kinds that declare
  `forbids_distributional_terms`. See the scoping note below.
- **An output path that is not `.html`.** A report is a self-contained document, not a format the
  renderer silently converts to.
- **Any figure not reachable from a verified manifest**, by construction: the manifest list is
  the only numeric input.
- **Interval-level official price series**, also by construction. A manifest carries the
  producing module's summary, and the summary is all the renderer ever sees. A path a manifest
  names in `declared_inputs` is displayed, never opened — a test writes a price CSV, names it in
  a manifest and asserts the price does not reach the document. This keeps the redistribution
  question that forced encrypted custody entirely out of the export path.
- **A value computed across manifests or across bases.** Nothing in the renderer performs
  arithmetic; such a number's basis would be none of the five the contract defines.

## Why the distributional-term check is scoped to renderer vocabulary

The check covers the headings and captions the renderer itself emits for a block whose kind
forbids the terms. Text carried verbatim from the manifest is exempt, and that exemption is
load-bearing rather than a loophole.

The project's standing exclusions read "not a probability-calibrated estimate" and "not expected
or forecast investment revenue". They contain `probability` and `expected`, both on
`FORBIDDEN_REPORT_TERMS`. The design requires those exclusions beside **every** figure, including
a scenario ensemble's. A blanket scan of the rendered text would therefore refuse to render the
disclaimer the design exists to guarantee — the check would fire on the very sentence that makes
the claim safe.

The manifest's own keys need no second check: the contract already cleared them for that kind on
build. So the renderer checks what the renderer adds. Two tests pin this in both directions: one
patches a kind description containing "Expected value" and asserts the render is refused, and one
asserts the standing exclusions still render intact beside an ensemble, after first asserting
that those exclusions do contain exactly the two forbidden terms — so a future reader meets the
reason rather than a bare exemption.

## Determinism and auditability

Identical manifest inputs produce byte-identical documents. Manifests are ordered by basis, then
kind, then manifest ID — never by the order they were supplied — and the only timestamp the
renderer adds is `rendered_at_utc`, which lives in the index rather than the document. A test
renders the whole registry in both directions and compares the documents, the figures and the
index entries.

The index names every manifest rendered with its kind, basis, label, `produced_by`, recorded
time, the keys rendered from it, and the SHA-256 digest of the exact bytes read, so a report is
auditable back to the exact manifests behind it. A manifest is identified by ID and digest and
**not** by its path on the machine that rendered it: an export travels, and the operator's
directory layout is not part of the evidence.

Recorded values are formatted as the JSON they were recorded as. No display rounding, unit
conversion or thousands grouping happens between the manifest and the page, because each of those
is a transformation, and this layer transforms nothing.

## Test and validation evidence

`tests/test_report_render.py` adds 25 tests: the landing state and its absence of any number, the
declaration checklist naming every default-free input with its decision and command, a manifest
rendered for **every** kind in the registry with its label, basis wording and standing exclusions
asserted inside that kind's own block, headline-versus-detail placement, the refusals above,
the scoping of the distributional check in both directions, byte-determinism across input orders
and across rendering times, basis grouping in the declared order, self-containment, and the CLI's
`0` and `1` exit codes including the guarantee that a refused manifest leaves no file behind.

Two are integration rather than fixture tests. One runs the perfect-foresight optimizer and
renders a manifest built from the summary it genuinely produces, because a renderer can otherwise
be satisfied by fixtures no real summary matches. One asserts every rendered figure equals the
value its manifest recorded, which is what makes "nothing was computed while rendering" checkable
rather than asserted.

Ruff, mypy over 43 source files, the complete pytest suite and a clean wheel build pass on
Python 3.12 without secrets or official data.

## Roadmap consequence

`PLAN.md` records v0.8.0 as complete. v0.8.1, multi-run composition, and v0.8.2, a separate dated
decision on whether an interactive viewer is added on top of the static renderer, remain open.
AI-generated explanations remain outside v0.8 either way. Acceptance against real recorded runs
is performed inside GitHub Actions where the accepted artifacts live, following the standing
operating constraint that live evidence steps are workflow dispatches.
