# Completed-v0.8 formal review — 2 September 2026

## Scope and outcome

The completed v0.8 scope was reviewed as delivered at v0.8.2: the versioned run manifest and
report contract, the deterministic report renderer, their CLI surfaces (`record-run-manifest`,
`verify-run-manifest`, `render-report`), the design of record in `docs/v0.8_design.md`, the
contract document, the regression suite and the project records.

The review found no defect in what the renderer *computes*, because it computes nothing, and no
way to get an official price series, an environment variable, a network read or a cross-basis
value into an export. It did find four defects at the doorway between a recorded manifest and a
rendered one, all of them in the same blind spot: the existing tests build every manifest with
`build_run_manifest` and then render it, so no test ever exercised a manifest that `read_run_manifest`
accepts but `build_run_manifest` would have refused — which is precisely the manifest a report
meets when a file travels.

All four are corrected in v0.8.3. None changes an analytical result: no dispatch, forecast,
stress, degradation, finance or data path is touched, no recorded figure changes value, the
manifest `schema_version` stays at 1, the renderer version stays at 2, and no report format or
index field changed.

## Defects found and corrected

**1. A verified manifest missing a guaranteed summary key crashed the renderer.** The contract
runs its guaranteed-key check when a manifest is built rather than when one is read — deliberately,
so that an ensemble manifest recorded before `path_ranges` existed still verifies and still
renders. `_render_manifest` nevertheless read a kind's guaranteed keys straight out of the
summary, so the manifest that design admits raised `KeyError` and, since `KeyError` is not among
the errors the CLI handles, `greek-bess render-report` exited on an unhandled traceback rather
than a refusal. The absence is now stated as not recorded, by the same route every other absent
value takes, and no figure is recorded for a value that is not there.

**2. The standing-claim cross-check ran only when a manifest was recorded.** A summary declaring
`is_probabilistic`, `is_forecast` or `is_investment_evidence` as anything but false is refused by
`build_run_manifest` by name, as a scope change requiring a recorded decision. The same summary,
arriving as a manifest file, was read and rendered — putting `is probabilistic: true` in a report
directly above the standing exclusion "not a probability-calibrated estimate". `read_run_manifest`
now applies the check.

**3. The scoped distributional-term refusal ran only when a manifest was recorded.** For a kind
declaring `forbids_distributional_terms`, the same asymmetry applied. The renderer's own
vocabulary check caught some of it by accident, because it captions top-level and composition keys,
but it is scoped to what the renderer says and was never the guarantee. `read_run_manifest` now
applies the contract's check, at every depth, for the kinds that declare it.

**4. One in-document anchor could serve two manifests.** Two distinct manifest IDs reducing to
the same readable anchor were disambiguated with a single positional suffix that was not itself
checked. Manifest IDs `A`, `A-2` and `a` are three distinct manifests that produced two anchors,
so the index link for one led to another manifest's block — in a document whose index exists to
say where each recorded run can be found. The suffix now advances until the anchor is unused.

A fifth item was documentation: the `greek_bess.reporting.render` module docstring claimed the
manifest doorway inherits the guaranteed-key check, and `docs/v0.8_design.md` claimed that no
verified manifest can carry a probability or percentile. Neither was true as written. Both now
state which checks reading applies and why the guaranteed-key check is deliberately not among
them.

## What the corrections deliberately did not do

The obvious symmetric fix — apply the guaranteed-key check on read as well — was rejected. That
check is a promise about what a producing module recorded at the time it recorded it, not a
property of the file, and enforcing it on read would refuse a manifest that was correct when
written and is still exactly what it says it is. It would also revoke the 1 September amendment's
explicit guarantee that an ensemble manifest predating `path_ranges` still verifies and renders.
The split between the two kinds of check is now recorded as a decision rather than left as an
accident of where the code happened to put each one.

Neither content check can refuse a manifest this project recorded, because building one already
applied both. What they refuse is a manifest that was hand-edited, truncated or produced
elsewhere — the case the design's "verified manifests, and only verified manifests" rule was
always about.

## Confirmed integrity boundaries

- The renderer computes nothing: every value in a rendered report is a `RenderedFigure` naming
  the manifest and the exact place in its summary the text came from, composition cells included.
- No figure of one basis is merged with a figure of another; the index that spans bases carries
  no figure at all.
- The renderer opens no file a manifest names in `declared_inputs`, reads no environment
  variable and makes no network request; official HEnEx and ENTSO-E interval series cannot enter
  an export.
- A label is read from the manifest and never re-declared, so it cannot drift from the sentence
  the producing module wrote; the label, the basis in words and the three standing exclusions sit
  adjacent to every figure.
- A manifest this build cannot honor refuses the whole report rather than being skipped.
- Recorded values are rendered as recorded — no rounding, unit conversion or re-reduction — and
  an absent value, a recorded null and an empty recorded table remain three distinct statements.
- Perfect foresight remains a labelled gross-margin upper bound, scenario ranges remain ranges
  across named judgments with no probability, percentile, expected value, ranking or central
  case, and the standing exclusions are asserted on every manifest.

## Observations that are not defects

`_verified_sources` reads each manifest file twice: once as bytes for the SHA-256 the report
records, and once through `read_run_manifest`. If the file changed between the two reads the
recorded digest would describe bytes other than those rendered. This is left as it is: the window
is a few microseconds inside one function, the report is rendered from local files the operator
supplied, and closing it means either hashing inside the contract's read path or adding a
parse-from-bytes entry point to the contract's public surface. It is recorded here so that a
future change to either function is made knowing the digest and the parse are two reads.

`ruff format --check` reports 46 files it would reformat. The declared gates are `ruff check`,
mypy, pytest and a wheel build; the formatter is not among them and is not run in CI, so this is
not a failure. Adopting it would be a repository-wide reformatting decision, not a review
correction.

## Validation evidence

Ruff passed, mypy passed over 43 source files, all 361 tests passed, and a clean isolated wheel
build produced the 0.8.3 wheel with the typed-package marker present. Six regression tests were
added: four pinning the refusals reading now applies, one pinning that a manifest missing a
guaranteed key still reads (the deliberate non-change), and one pinning that a report meeting
such a manifest states the absence instead of crashing; plus one pinning that a suffixed anchor
which is itself taken is advanced. Each of the six behavioral tests was confirmed to fail against
the v0.8.2 implementation before the corrections were applied.

The complete diff, generated-file set, official-data paths and secret patterns were reviewed
before commit; no generated research output, official dataset or secret enters the change.

## Roadmap consequence

v0.8 remains complete, with its completed scope now formally reviewed. The two operator items are
untouched and still open: a second custody copy under separate control does not exist, and
`ENTSOE_SECURITY_TOKEN` is not configured. Neither is a reporting-layer task. No later phase is
opened by this review, and the interactive-viewer decision of 1 September 2026 stands.
