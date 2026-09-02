# Implementation report v0.8.1 — Multi-run composition

**Date:** 1 September 2026

## Scope

The second milestone of v0.8: composition across many verified run manifests. It adds an index
across every manifest a report carries, side-by-side presentation of a scenario ensemble with its
per-path ranges and per-scenario provenance, and explicit rendering of the equivalent-basis
evidence the ensemble records. The design of record is `docs/v0.8_design.md`, amended the same day
by a dated decision entry described below.

Composition is layout only. Nothing is computed across manifests, no figure of one basis is merged
with a figure of another, and no runtime dependency, server, environment read or network read is
added. AI-generated explanations remain outside v0.8 entirely, and v0.8.2 — whether an interactive
viewer is added on top of the static renderer — remains a separate dated decision that this
milestone does not assume or prejudge.

No dispatch mode, forecast method, stress transformation, degradation model, finance treatment or
data-ingestion behaviour changes, and no accepted figure moves.

## The design tension this milestone opened, and how it was resolved

v0.8.1 requires a scenario ensemble to be shown with its per-path ranges. Those ranges lived in
the CSV `report-scenario-ensemble` writes, not in the run summary a manifest carries. The summary
held the scenario list, the equivalent basis, the path count and four extreme aggregates — the
lowest and highest margin across every scenario and path, and the widest and narrowest path
spread — but not the range of each path.

The manifest is the sole doorway. Reading the CSV was therefore never an option: it would have
broken the one sentence the whole layer rests on, and a figure lifted out of a CSV arrives
stripped of the label the manifest carries, which is precisely what `PROMPT.md` requires an
output to retain through downstream analysis. That left two honest routes.

**The route not taken** was to render only what the summary records and say so. It is defensible,
and it is cheap. It was rejected because of what it does to a reader: a report showing the widest
and the narrowest path spread but not the ranges between them tells someone that the evidence
exists and is elsewhere. They then open a spreadsheet, which is the exact failure the reporting
layer exists to remove, and the figure they read there has no label beside it.

**The route taken** is that the producing module records what a report may show, rather than the
report reaching past the manifest for it. `report_scenario_ensemble` now records `path_ranges` in
its own summary, and `scenario_ensemble_range` guarantees `scenarios`, `equivalent_basis`,
`path_count` and `path_ranges` alongside the keys it already guaranteed. This is recorded as a
dated decision entry, *"Record the ensemble's per-path ranges in its summary, rather than reading
its CSV"*, with a matching amendment in `docs/v0.8_design.md` and `docs/run_manifest_contract.md`.

Recording is not computing. The recorded rows are a projection of the same reduced frame the CSV
is written from, taken in the same path order, with nothing rounded, converted or re-reduced; a
test asserts every recorded cell equals the frame's cell, and another asserts the widest recorded
spread is the aggregate the summary already reported. The producing module stays the one source of
truth for its own numbers, which is what the contract has always required. The renderer was given
no new permission at all: it still reads manifests and nothing else.

Two costs are part of the decision rather than side effects of it. An ensemble manifest grows with
the path count — bounded by the `path_count` the ensemble already declares — which is why
per-scenario provenance is recorded once under `scenarios` and joined by scenario name, rather
than repeated on every path row as the CSV repeats it; the manifest grows with the paths, not with
the paths times the fields, and the CSV is unchanged. And because the guaranteed-key check runs
when a manifest is built rather than when one is read, an ensemble manifest recorded before this
change still verifies and still renders. The report states plainly that such a manifest records no
per-path ranges instead of filling them in — the route not taken, kept for the manifests that
predate the change.

## The index across manifests, and why it carries no figure

A multi-manifest report creates exactly one temptation the single-manifest report did not: a
summary table spanning the whole document. That table is the first place a perfect-foresight
ceiling would sit in a column beside a settled backtest and a synthetic scenario range. The second
step — adding, differencing or ratioing them — is a short one, and it produces a number whose
basis is none of the five the contract defines.

So the index names and links; it does not report. Grouped by basis in the contract's declared
order, it gives each manifest's ID, result kind, recorded label, producing command, recorded time
and SHA-256 digest, and links to the block that holds its figures. Every number stays inside its
own manifest's block, beside the label that says what it is and what it is not. The rule is
executable rather than stated: a test asserts that every cell of the index is one of the
manifest's identity, label or provenance fields, so a figure cannot appear there even by accident.

The index also names the bases the report does **not** cover. A reader cannot otherwise tell a
basis this report happens not to include from a question the project cannot answer, and a report
that reads as the whole of what the tool can record is a report that misleads by omission.

## The scenario ensemble, side by side

Three sections, in the order a reader needs them, all read from one manifest:

- **Scenarios side by side.** One column per named scenario, in the order the scenarios were
  declared, with the recorded run, the transformation method, identifier and parameters, the
  declared availability, the source era, the bootstrap configuration and the path count. There is
  no baseline column: an untransformed replay is a named scenario like any other, because a
  scenario the report supplied itself would be a judgment the reader never made.
- **The basis every scenario shared.** The `equivalent_basis` the ensemble recorded, group by
  group — battery parameters, terminal-energy basis, source era, path identity — presented as
  what it is: the properties every scenario was required to share before the ensemble would place
  them in one range at all. A difference in any of them is refused and named by the ensemble
  rather than reconciled, and rendering the evidence makes that check visible instead of implied.
- **Range per bootstrap path.** One row per path: the lowest and highest margin any named scenario
  produced for that path, which scenario attained each end, and the spread. The scenario name
  joins these rows to the provenance above. Nothing is totalled across paths, and the rows keep
  the recorded path order.

A key a composition section lays out is not also rendered as a generic headline or detail row, so
one recorded value appears in exactly one place — laid out rather than dumped as a JSON blob.

## What is refused rather than approximated

- **A recorded per-path range table with ragged rows.** Rows declaring different columns are
  refused rather than padded: a blank cell in a range table reads as a value rather than as an
  absence.
- **A composition entry that is not an object.** The report renders the table a manifest recorded
  and cannot render a row it cannot read.
- **Distributional vocabulary in a nested key**, for the kinds that forbid it. The contract's
  check now reaches every key name at any depth, because a report renders a nested key as a
  visible column heading; a top-level scan would have cleared a per-path table whose headings
  claimed a percentile. The scoping to those kinds is unchanged and still load-bearing for the
  reason recorded in v0.8.0: the standing exclusions themselves contain two of the terms.
- **A figure in the index**, as above.
- **Everything v0.8.0 already refused**, unchanged: a manifest this build cannot honor refuses the
  whole report, two inputs declaring one manifest ID are refused, a non-`.html` output is refused,
  a path named in `declared_inputs` is displayed and never opened.

## Determinism and auditability

Identical inputs still render byte-identical documents. Composition adds no ordering of its own:
scenarios render in their recorded declaration order and path ranges in their recorded path order,
both of which the ensemble already normalises, and manifests are still ordered by basis, then
kind, then manifest ID rather than by input order.

`RenderedFigure` now carries `summary_path`, the exact place in a manifest's summary a value was
read from — `("interval_count",)` for a top-level figure, `("path_ranges", 3, "spread_...")` for
one cell of a composition table. This is what keeps "nothing was computed while rendering"
checkable rather than asserted once layout reaches inside a summary: every rendered cell can be
walked back to the recorded value it came from, and a test does exactly that for a fixture and for
a summary a real ensemble produced.

The machine-readable index is at renderer version 2 and gains `bases_absent`, `manifests_by_basis`
and, per manifest, the `composition_sections` rendered and the `rendered_summary_keys` it
contributed — the key named once even when a composition table rendered many cells from it. The
manifest schema version is unchanged at 1: the envelope did not change.

## Test and validation evidence

The suite grows from 326 to 355 tests.

`tests/test_report_render.py` adds the index tests — every manifest named, grouping by basis in
the declared order, label and digest present, links resolving to real blocks, absent bases named,
the machine-readable grouping, and the index carrying no figure — and the ensemble composition
tests: every recorded range row rendered, every composition cell walked back to the manifest, no
total across paths and no reordering of them, the scenarios placed side by side with their
provenance, the equivalent-basis evidence rendered group by group, a composition key rendered once
and not also as a generic row, a manifest recording no per-path ranges saying so, ragged rows
refused, an empty recorded table distinguished from an absent one, and the label and standing
exclusions still adjacent to the composition.

One is an integration test rather than a fixture test: a real `report_scenario_ensemble` result is
recorded as a manifest and rendered, and every rendered range cell is checked against the frame
the CSV would have been written from. `tests/test_scenario_ensemble.py` adds the recording tests —
one row per path in frame order, every cell equal to the frame's cell, plain JSON values, no
probability vocabulary in the recorded columns, provenance recorded once rather than per path, and
no reported aggregate changed. `tests/test_report_contract.py` adds the deepened
distributional-term check in both directions and the new guaranteed keys.
`tests/test_cli.py` extends the end-to-end ensemble run through `record-run-manifest` and
`render-report`, asserting the summary's recorded ranges match the CSV and reach the document.

Ruff, mypy over 43 source files, all 355 tests and a clean wheel build pass on Python 3.12,
without secrets or official data.

## Roadmap consequence

`PLAN.md` records v0.8.1 as complete. The only item left in v0.8 is v0.8.2, which is a decision
rather than an implementation: whether a local interactive viewer is added on top of the static
renderer. It would be a new runtime dependency and a new rendering surface, it is not needed for
exportable reports, and it is not assumed. If it is declined, v0.8 completes with the static
renderer. AI-generated explanations remain outside v0.8 either way.

The two operator items are untouched by this milestone and remain open: a second custody copy
under separate control does not exist, and `ENTSOE_SECURITY_TOKEN` is not configured. Acceptance
against real recorded runs is performed inside GitHub Actions where the accepted artifacts live,
following the standing operating constraint that live evidence steps are workflow dispatches.
