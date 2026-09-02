# Project status

**Version:** 0.9.2
**Updated:** 2 September 2026
**Status:** Official multi-year operational acceptance and HEnEx-to-ENTSO-E cross-source
reconciliation passed; encrypted custody copies published and the private key exercised;
per-delivery-year replay decomposition accepted against the official history;
bootstrap source-era policy, spread compression, non-probabilistic scenario-ensemble range
reporting, declared availability/outage paths and declared negative-price events landed,
completing the approved v0.7 modeling scope; the completed-v0.7 review passed after reconciling
one roadmap wording contradiction, and v0.8 was opened on 1 September 2026 by explicit user
approval, with the scope amended and the design recorded in `docs/v0.8_design.md`;
ADMIE load and RES forecasts are removed from scope and that quarantine is closed as never
accepted, with the retrieval client and timing audit retained and documented as unused; a
versioned run manifest and report contract now carries every recorded result, making label
retention executable; and v0.8.0, the report rendering foundation, and v0.8.1, multi-run
composition, have both landed — a deterministic `render-report` command that renders verified run
manifests, and only verified run manifests, into self-contained static reports, now composing
many of them into one indexed report that computes nothing across them; v0.8.2 has declined
an interactive viewer and completed v0.8 with that single deterministic presentation surface;
the completed-v0.8 review has passed after correcting four reporting-layer defects in
v0.8.3, none of which changes an analytical result; and render run `33609809770` accepted the first aggregate report from decomposition run `33147448666`; public Pages deployment remains outstanding because the required re-dispatch could not be started from the unauthenticated working environment; and an external review of
v0.8.3 has been answered on the engineering items it raised — a relaxation-first dispatch solve
that is exact by construction, property-based tests over the market calendar that found and fixed
a canonical timestamp-resolution defect, closed-form dispatch checks, a subcommand registry
replacing the CLI's 30-branch chain, a README quickstart, coverage measurement and a 3.12/3.13 CI
matrix, with no analytical result changed
(`docs/history/implementation_report_v0.8.3_review_response.md`); and v0.9 has been opened as a
point-in-time fundamentals forecast benchmark, with its design recorded, its two declaration
formats committed as refused examples and its source-selection spike run and recorded — NOAA GFS
0.25° forecast vintages chosen from the 00 UTC cycle of D-1 for delivery days from 27 February
2021, with 118 accepted delivery days carrying no feature and the EEX fallback not selected; and
v0.9.1 has landed the first v0.9 code — the declared decision cutoff in a neutral module, the
typed point-in-time feature schema, the NOAA GFS client reading single GRIB2 messages by byte
range, the per-delivery-interval availability audit, two commands, a fetch workflow, a daily
witness workflow and one new manifest kind, with `eccodes` as the single new dependency — while
accepting nothing and leaving every surface blocked on three operator declarations
(`docs/v0.9_design.md`, `docs/fundamentals_source_assessment_2026-09-02.md`,
`docs/point_in_time_feature_contract.md`, `docs/history/implementation_report_v0.9.1.md`);
and v0.9.2 now adds the revision-aware, whole-day-atomic as-of join and per-value provenance
audit, validated only on synthetic fixtures while the same declarations remain absent
(`docs/history/implementation_report_v0.9.2.md`); its completed review corrected grade admission
to occur after latest-revision selection and corrected the per-value supersession count, with no
real-data or analytical result affected
(`docs/history/implementation_report_v0.9.2_review.md`)

## v0.9.2 — point-in-time join complete on synthetic fixtures

The revision-aware as-of join and `build-point-in-time-features` command are implemented. For every delivery interval the join selects the latest revision published strictly before the declared effective cutoff, counts and excludes later revisions, and emits an audit row carrying the source document, revision and byte digest. Missing coverage excludes the whole day by named cause; nothing is forward-filled, interpolated or imputed. Equal and coarser-broadcast resolution relations are explicit, and a finer feature is refused without an aggregation rule. The implementation is tested entirely against synthetic fixtures.

The three operator declarations still do not exist. Consequently every real reader and workflow remains refusing, no real join result, model, manifest or acceptance document was produced, and the dispatched-run acceptance criterion remains outstanding for that reason and no other. The scheduled witness workflow cannot produce a witnessed day while its guard refuses; each refused scheduled target day is permanently lost from the witnessed subset. Exact run IDs and target days could not be verified from this unauthenticated checkout, so none are invented here.

## Documentation debt cleared from v0.8.x

The shared records now describe renderer version 3's deterministic manifest-local SVG charts and the rendered aggregate report capability, plus the attributable accepted-history timing and opt-in synthetic dispatch benchmark. The chart and engineering staging files are removed. The publication staging record remains deliberately pending because the required Pages deployment has not succeeded.


## v0.9.1 — ingestion and the availability audit are built; nothing runs yet

**The code is complete and tested; the declarations it needs do not exist.** v0.9.1 landed on
2 September 2026 and is the first v0.9 code
(`docs/history/implementation_report_v0.9.1.md`). It builds everything that can be built without
the operator declarations v0.9 waits on, and stops exactly where those begin.

**What landed.** `data/decision_cutoff.py` gives the declared gate-closure schedule a neutral
home, moved verbatim out of the retained-but-unused ADMIE timing module, which re-exports it — a
live feature path must not import its decision rule from a module whose own docstring says it is
unused, and `tests/test_admie_timing.py` passing untouched is the evidence the move changed
nothing. `data/point_in_time.py` is the typed feature schema: a closed column set, a closed
source set, a closed variable registry with its units, four evidence grades, and refusals for a
missing value that is not an absent row, a unit that is not the registry's, a naive instant, a
retrieval that precedes its publication, and two rows that share the uniqueness key and disagree.
`data/gfs.py` reads NOAA GFS 0.25° vintages from the 00 UTC cycle of D-1 through both archive key
layouts, parses the `.idx` sidecar into inclusive byte ranges, retrieves single GRIB2 messages,
decodes them through ecCodes, samples at declared grid nodes and de-averages bucketed radiation
by a stated two-step rule. `data/availability_audit.py` judges every delivery interval on its own
evidence. `cli/fundamentals.py` adds `fetch-fundamentals` and `audit-feature-availability`, the
latter exiting `2` on any unaccepted day with its evidence still written.
`fetch-fundamentals.yml` and `witness-fundamentals.yml` dispatch and schedule them.
`contract.py` gains the `point_in_time_availability_audit` kind and `render.py` gains the
checklist entries for the cutoff, the lead and the geography. The policy the code enforces is
`docs/point_in_time_feature_contract.md`. Ruff, mypy, 520 tests and the wheel build are green.

**What the phase corrected.** The source assessment computed the required forecast steps as 21-46
from the *Athens* delivery day; this project's delivery day is the CET/CEST market day, which
begins an hour later, so the range a market day needs is **22-47**. The client derives the step
set from each market day rather than carrying a constant, so a 23- or 25-hour day produces its
own, and a test asserts the widest range across the usable record. Separately, two of the three
variables are derived from more than one message, so for a derived value the publication instant
is the **latest** contributing object's — the value became available when its last input did —
the document identity names every contributing object, and the digest is taken over the
contributing digests in a stated order (decision entry 2026-09-02).

**What is blocked, and what that costs each day.** Three operator declarations have no default
and no fallback (gate G3): the decision-cutoff schedule with a real rulebook citation, the
decision lead in minutes, and the sampling geography with its weights and stated basis. Until all
three exist, `fetch-fundamentals` and `audit-feature-availability` refuse at their readers, both
workflows stop at their guard steps, and the phase's acceptance criteria that need a dispatched
run — a one-month window with its audit recorded, and a witness run producing a witnessed day —
stay outstanding for that reason and no other. **The witnessed subset is the part that does not
wait patiently:** a provider-declared publication instant can be read at any point in the future,
but a witnessed one exists only if a retrieval actually happened before that delivery day's
cutoff, so every day without the declarations is a witnessed day v0.9.5 can never recover.

**What it did not do.** No join, no model, no manifest recorded from real data, no acceptance
document, no `cfgrib` and no `xarray`. The client was exercised once end to end against the live
archive during development for a single delivery day; that is evidence the pipeline works, not an
accepted figure, and nothing from it is committed. ADMIE-originated forecasts were not reopened
by any route.

## v0.9 opened — point-in-time fundamentals forecast benchmark

**Design recorded, source chosen, nothing built.** v0.9 was opened on 2 September 2026 and
`docs/v0.9_design.md` is its design of record (decision entry 2026-09-02). It addresses the one
open analytic question the forecasting layer carries: every accepted forecast figure comes from
price history alone, because validated weather, demand, fuel, renewable and interconnector
forecasts are not included. The milestone asks whether an independently validated exogenous input
improves *realized settled dispatch value* — the accepted held-out evidence shows price error and
settled value disagreeing, so value is the primary metric and price error explains the mechanism
rather than deciding.

What landed today is documentation and configuration only: the design, the two declaration formats
(`config/decision_cutoff.example.json`, `config/fundamentals_geography.example.json`) with
placeholder references, and the test that keeps both parseable by the reader that will read the
real declaration and refused as declarations while the placeholders remain. No source code,
dependency, workflow or data source was added, and no accepted figure or analytical behaviour
changed.

What the design commits to, and what it refuses:

- **A declared decision cutoff and decision lead, with no defaults**, in the existing dated-regime
  schedule format. A feature is available for a delivery day only if its publication instant is
  strictly before the cutoff; a publication at the cutoff is late. This is the gate-closure
  refusal of 2026-08-31 applied to a live feature path rather than a quarantined one.
- **Graded availability evidence that never merges.** `witnessed` and `provider_declared` are
  admissible and reported separately; `assumed` — availability inferred from a regulatory deadline
  or a nominal latency rather than from the datum — is quarantined and usable only in a labelled
  exploratory run that is never recorded as accepted.
- **Leakage ruled out by construction.** Every revision stored, the decision-time revision being
  the latest published strictly before the cutoff, later revisions counted and excluded, every
  value traceable to a source document, revision and byte digest, days complete or excluded by
  named cause, nothing forward-filled or imputed, and realized target-day quantities refused by
  name as well as by timestamp.
- **Data acceptance before any model.** A dated acceptance document must precede any benchmark
  document, and no benchmark manifest may name a feature-set digest no acceptance document names.
- **A negative result recorded under the same labels**, with no re-splitting, re-tuning or cutoff
  change after seeing test results, and an exploratory label whenever accepted coverage is thinner
  than one full meteorological season of quarter-hour common test days.

**The source is now chosen and one thing still blocks the next phase.** The source-selection
spike ran the same day against the live public archive
(`docs/fundamentals_source_assessment_2026-09-02.md`) and the dated decision names **NOAA GFS
0.25° forecast vintages**, 00 UTC cycle of D-1, delivery days from 27 February 2021 onward. All
three checks passed, so G0 is not triggered and the EEX fallback is not selected and stays
unassessed. What remains open is the operator side: the decision cutoff, decision lead and
sampling geography are declarations the repository will not supply, and no v0.9 surface runs
without them. The ADMIE removal of 2026-09-01 is not reopened: ENTSO-E's Greek load and renewable
forecasts originate from ADMIE, are isolated as a separate track requiring its own dated decision,
and nothing in v0.9 depends on them
(`docs/history/implementation_report_v0.9.0.md`).

## v0.9 source chosen — NOAA GFS forecast vintages

The v0.9.0 spike is run and recorded (`docs/fundamentals_source_assessment_2026-09-02.md`,
decision entry 2026-09-02). It converts every external fact the design labelled an inference into
a verified fact or a recorded unknown with a named closing step.

**What passed.** The AWS Open Data archive serves anonymous byte-range reads through `.idx`
sidecars at a 157x reduction — 3.27 MiB rather than 514 MiB per forecast step, 85 MiB per delivery
day, 167 GiB across the usable history, against 25.6 TiB without subsetting. All four proposed
variables are present in every step inspected. A pip-installable ecCodes binding installs with no
system package or compiler and leaves Ruff, mypy, 403 tests and the wheel build green on 3.12 and
3.13, with the existing numpy, pandas, scipy and scikit-learn resolution undisturbed. The provider
licence text is captured verbatim; it requires attribution, forbids implying NOAA endorsement, and
forbids presenting derived values as unaltered NOAA data, all three of which the manifest and
provenance contract already satisfies. No credential is involved.

**What the spike corrected.** The usable hourly record begins at delivery day 27 February 2021,
not at the archive start: before 26 February 2021 the 0.25° product is 3-hourly, so **118 of the
accepted history's 2,131 delivery days carry no feature** and are excluded by named cause rather
than filled by a coarser broadcast. The decision-time cycle is fixed at 00 UTC of D-1, because the
06 UTC cycle's step-48 object was observed appearing after a midday cutoff, while the 00 UTC cycle
cleared the same illustrative cutoff on all 365 days of 2025 with a normal lag of 3 h 41 m to
4 h 10 m. Two ingestion facts became requirements: both archive key layouts must be tried for days
before April 2021, and availability must be checked per forecast step, because upload order is not
monotone in step.

**What is recorded rather than resolved.** Every object from 1 January to 25 February 2021 carries
a `Last-Modified` from March or April 2024 — G7, and safe in one direction only: an instant
written at upload time can be moved later by a re-upload but never earlier, so the
`provider_declared` grade can under-claim availability and cannot over-claim it. One genuinely
late run (14 June 2021, published 1 h 39 m after the illustrative cutoff) and one entirely missing
cycle (2 February 2021) are excluded by named cause. The late run is the concrete case that
justifies quarantining the `assumed` grade: a nominal-latency assumption would have admitted it
and been wrong.

**What is still open.** The decoder was proven on CPython 3.12.3 and 3.13.12 in the development
environment, not on the `actions/setup-python` images; v0.9.1's first CI run, where `eccodes` is
first declared, closes that residual, and a failure there returns the choice to the G0 branch. The
EEX fallback, the ECMWF and Open-Meteo alternatives, the ENTSO-E Track B candidates and the
Regulation (EU) 543/2013 deadlines are recorded unknowns: the egress policy refuses those hosts,
none of them is selected, and no part of v0.9 depends on any of them. Successful retrieval is
still not accepted use — the data-acceptance document of the design's Section 7 precedes any
benchmark document. Documentation only: no source code, no dependency, no workflow, no committed
provider content, and no accepted figure or analytical behaviour changed.

## One-command synthetic public demonstration

`greek-bess demo` now provides the shortest path from a clone to a complete, indexed output:
synthetic prices, daily-composed ceiling, declared spread compression, stressed ceiling,
illustrative finance screening, verified manifests and static rendering. The README links a
committed synthetic-only sample and the suite regenerates it byte for byte. This is presentation
and workflow integration, not new market evidence or an analytical-scope change
(`docs/history/implementation_report_demo_2026-09-02.md`).

## Documentation — accepted findings now lead the README

The repository landing page now opens with the recorded per-delivery-year official-history
findings and places the unchanged limitations immediately after them. The detailed command
catalogue is now `docs/command_reference.md`. This is a presentation-only change; no accepted
figure, analytical behavior, scope or dependency changed
(`docs/history/implementation_report_readme_findings_first_2026-09-02.md`).

**Standing position, 2 September 2026:** the approved `PROMPT.md` scope is implemented, v0.7
was re-verified on the unchanged v0.7.11 implementation (Ruff, mypy, 301 tests, clean wheel
build), and v0.8 is complete through v0.8.3, its completed scope formally reviewed. The interactive viewer was declined: it would add a
dependency, a server lifecycle and a second rendering surface without adding evidence. A future
proposal must identify a need the static report cannot meet and receive separate approval. The
artifact expiry is retired: run
`33483975614` produced a replacement official-history artifact on 1 September 2026 under the
90-day retention, expiring 30 November 2026 at 07:49 UTC, and its price series verifies as
identical to the accepted baseline, and the committed custody record now fingerprints it.
Encrypted copies of both accepted artifacts were published the same day and the private key was
exercised, so the accepted evidence is recoverable. The ADMIE forecast quarantine is closed by
removing ADMIE load and RES forecasts from scope (decision entry 2026-09-01).

Two operator items remain. A second custody copy under separate control does not exist, and one
release is one failure domain. `ENTSOE_SECURITY_TOKEN` is no longer configured, so the
reconciliation cannot be re-run; its accepted evidence is safe in the custody copy and only
regeneration is blocked. Live market endpoints are reachable only from GitHub Actions runners, so every
live acceptance step is a workflow dispatch rather than a command in a checkout. See `PLAN.md`.

## v0.8.0 landed — report rendering foundation

- `greek_bess.reporting.render` and the `render-report` command render verified run manifests,
  and only verified run manifests, into one self-contained static HTML report plus a
  machine-readable index (`docs/history/implementation_report_v0.8.0.md`).
- `read_run_manifest` is the sole doorway, so the schema-version check, the closed kind
  registry, the basis cross-check, the guaranteed-key check and the scoped distributional-term
  refusal are inherited by the presentation layer rather than restated in it. The renderer
  computes nothing, reads no environment variable and makes no network request. No runtime
  dependency was added and nothing listens on a port.
- The landing state is the declaration checklist. Rendered with no manifests, the report shows
  no figure and no example number: a regression test strips the decision dates and asserts not
  one digit remains. It lists each judgmental input with no default — bootstrap source era,
  spread-compression factor and reference basis, availability baseline, negative-price event
  list, ensemble scenario set — with the dated decision behind it and the command that records
  a result once it is declared.
- Every figure renders inside a block carrying its manifest's `result_label`, its basis in
  reader-facing words and the three standing exclusions, adjacent to the figure. A regression
  test renders a manifest for every kind in the registry and asserts all three appear inside
  that kind's own block. Figures are grouped by basis in the order the contract declares them.
- The refusals are executable: a manifest that fails verification refuses the whole report and
  the CLI writes no file; two inputs declaring one manifest ID are refused; renderer vocabulary
  reading as a distributional claim is refused where the kind forbids it; a non-`.html` output
  is refused. A path a manifest names in `declared_inputs` is displayed, never opened, so
  interval-level official prices cannot enter an export.
- Reports are deterministic: manifests are ordered by basis, then kind, then manifest ID, never
  by input order, and the only timestamp the renderer adds is `rendered_at_utc` in the index.
  Recorded values render exactly as recorded, with no display rounding or unit conversion.
- Every rendered value is recorded as a `RenderedFigure` naming the manifest and summary key it
  came from, so "nothing was computed while rendering" is checked rather than asserted.
- Reports and indexes are generated research outputs and stay outside Git.

## v0.8.1 landed — multi-run composition

- A report now composes many verified manifests, and composition is layout only: nothing is
  computed across manifests, and figures of different bases are never merged into one row, total
  or derived value (`docs/history/implementation_report_v0.8.1.md`).
- **An index across every manifest, grouped by basis**, naming each manifest by ID, result kind,
  recorded label, producing command, recorded time and SHA-256 digest, linking to the block that
  holds its figures, and naming the bases the report does *not* cover — a reader cannot otherwise
  tell an absent basis from an absent question.
- **The index carries no figure at all**, which is the point of it. A summary table spanning the
  whole report is the one place a perfect-foresight ceiling would sit in a column beside a
  settled backtest, and combining them is a short second step producing a number whose basis is
  none of the five the contract defines. A test asserts every cell of the index is one of the
  manifest's identity, label or provenance fields.
- **A scenario ensemble is laid out side by side**: one column per named scenario with its
  provenance, the equivalent-basis evidence the ensemble recorded — battery parameters,
  terminal-energy basis, source era and path identity, the properties every scenario was required
  to share — and one row per bootstrap path with the lowest and highest margin any named scenario
  produced for it, which scenario attained each end, and the spread. The scenario name joins the
  two tables, and nothing is totalled or reordered across paths.
- **The design tension the milestone opened was resolved by recording, not by routing around the
  manifest.** The per-path ranges lived only in the ranges CSV, and a report reads a verified
  manifest and nothing else. So `report_scenario_ensemble` now records `path_ranges` in its own
  summary — a projection of the same frame the CSV is written from, in the same order, nothing
  rounded or re-reduced — and `scenario_ensemble_range` guarantees `scenarios`,
  `equivalent_basis`, `path_count` and `path_ranges`. The renderer was given no permission to
  open any file a run wrote (decision entry 2026-09-01; amendment in `docs/v0.8_design.md`).
- What a manifest does not record is stated rather than filled in. An ensemble manifest recorded
  before its module carried a key renders an explicit "records no ..." note and still renders
  everything else; the manifest envelope is unchanged, so `schema_version` stays at 1 and older
  manifests still verify.
- Every composition cell is still a `RenderedFigure`, now naming the exact place in the summary
  it was read from, so "nothing was computed while rendering" stays checkable once layout reaches
  inside a summary. The contract's distributional-term check reaches nested key names for the
  kinds that declare it, because a report renders a nested key as a visible column heading.
- Ruff, mypy over 43 source files, 355 tests and a clean wheel build pass on Python 3.12.

## v0.8.2 complete — interactive viewer declined

- The dated v0.8.2 decision declines Streamlit or another local viewer and completes v0.8 with
  the indexed, self-contained static renderer (`docs/history/implementation_report_v0.8.2.md`).
- The decision is based on surface area rather than schedule: a viewer cannot add evidence under
  the approved read-only design. Controls that compute, open a manifest-declared file or combine
  manifests would violate that design; controls that do not merely duplicate the report's index
  and links while adding a dependency, server lifecycle and second place to enforce every label
  and refusal.
- No runtime dependency, command, manifest contract, report format or analytical behaviour
  changes. Version 0.8.2 records the completed milestone and closes v0.8.
- Interactivity is not prohibited forever. A future proposal must name a need the static report
  cannot meet, define any requested scope change, and preserve the verified-manifest-only doorway
  and export refusals under its own dated decision and milestone.

## Open — render the accepted replay, awaiting a dispatch

- The `Render a report from the accepted replay` workflow exists as of 2 September 2026. It takes
  a completed `Decompose the accepted replay by delivery year` run, refuses one whose custody
  verification did not pass, records that run's accepted summaries under the run-manifest
  contract, verifies each manifest and renders one indexed report as a private artifact.
- **No report has been rendered from the accepted official history yet.** The v0.8 renderer was
  validated on synthetic manifests and real module summaries; a dispatch against an accepted
  decomposition run is what turns that into evidence. Run `33147448666` is the accepted
  decomposition (2026-08-28); its artifact retention is 90 days from that run.
- Until a run happens, this is machinery, not evidence. The acceptance document for the first
  rendered report is not written, and this entry stays open.

## v0.8.3 landed — completed-v0.8 review corrections

- The formal review of the completed v0.8 scope covered the manifest contract, the renderer, the
  reporting CLI surfaces, the design of record and the project records
  (`docs/history/implementation_report_v0.8.2_review.md`).
- Confirmed: the renderer computes nothing, opens no file a manifest names, reads no environment
  or network variable, merges no figure across manifests or bases, re-declares no label, and
  refuses an unverifiable manifest rather than rendering the rest as the whole.
- Four defects found and corrected, none of which changes an analytical result or a recorded
  figure. A verified manifest missing one of its kind's guaranteed summary keys crashed
  `render-report` with an unhandled `KeyError`; the absence is now stated. The standing-claim
  cross-check and the scoped distributional-term refusal ran only when a manifest was recorded,
  so a summary declaring `is_probabilistic` was rendered above the standing exclusion denying it;
  both now run when one is read. A non-object `declared_inputs` raised an unhandled error rather
  than a contract refusal. Three distinct manifest IDs could reduce to two in-document anchors,
  sending one index link to another manifest's block.
- The split between the two kinds of check is now recorded and executable: reading applies every
  check that is a property of the recorded content, while the guaranteed-key check stays a
  record-time promise so a manifest written before its kind guaranteed a key still verifies
  (decision entry 2026-09-02).
- The manifest `schema_version` stays at 1, the renderer version stays at 2, and no report
  format or index field changed. Ruff, mypy over 43 source files, 361 tests and a clean wheel
  build pass on Python 3.12.

## v0.8 opened — research interface and exportable reports

- Opened on 1 September 2026 by explicit user approval, lifting the gate the completed-v0.7
  review set. `PROMPT.md` carries the amended scope bullet, and `docs/v0.8_design.md` is the
  design of record (decision entry 2026-09-01).
- The governing rule: a report renders verified run manifests, and only verified run manifests.
  The manifest contract's guarantees — closed kind registry, basis discriminator, executable
  label retention, scoped distributional-term refusal — are inherited by the presentation
  layer, never restated in it. The renderer computes nothing and reads no environment.
- The three gated design questions are answered. The landing state with no judgmental input
  declared is the declaration checklist itself, not a result and not a demo with implied
  defaults. Every rendered figure carries its `result_label`, basis and the standing
  exclusions adjacent to the figure, read from its manifest. An export refuses any figure not
  reachable from a verified manifest, interval-level official price series, distributional
  vocabulary where the kind forbids it, unlabeled figures, and any value computed across
  manifests or bases.
- The core is a deterministic `render-report` CLI producing self-contained static HTML plus a
  machine-readable index, with no new runtime dependency and no server. Milestones: v0.8.0
  report rendering foundation and v0.8.1 multi-run composition (both landed 1 September 2026),
  followed by v0.8.2's dated decision to decline an interactive viewer and complete v0.8.
- No dispatch, forecast, stress, degradation, finance or data behaviour changes in the plan
  itself; exports remain generated research outputs outside Git.

## Declared negative-price events

- `apply-negative-price-events` and `greek_bess.stress.apply_negative_price_events` replace
  prices only in explicit UTC windows, on every bootstrap path, with an absolute declared
  strictly negative price in EUR/MWh.
- The unit of an event is a sequence of whole market intervals selected by inclusive start and
  exclusive end. Timing and depth have no defaults. Events are declared, never sampled,
  inferred, fitted, ranked or found by a threshold search; an empty list is the exact identity.
- This is distinct from the horizon-wide additive level shift and daily spread scaling: it
  changes only named windows. Untouched zero and negative prices remain numerically unchanged,
  and transformed prices are never clipped or floored.
- Boundaries inside an interval, overlaps, windows covering no interval, duplicate identifiers,
  naive timestamps, non-negative/non-finite depths, missing prices and unknown or omitted fields
  are refused rather than approximated.
- Provenance is one-to-one with every path interval, including rows where no event applies. The
  summary carries the method, policy, full configuration, applied interval evidence by event,
  and negative and zero interval counts before and after.
- Outputs remain synthetic deterministic scenarios, not forecasts, probabilities, calibrated
  occurrence claims or investment evidence. No dispatch, forecast, finance or availability
  behaviour changed.

## Declared availability and outage paths

- `build_availability_profile` and `dispatch-bootstrap-paths --availability-schedule` apply a
  declared availability schedule to every path of a run: a baseline available fraction with no
  default, plus zero or more declared outage windows each carrying its own fraction in [0, 1].
- Outages are **declared, never sampled**. A forced-outage rate would be an uncalibrated
  probability — there is no operating history for a Greek merchant battery, no fleet maintenance
  record and no warranty series in scope — so a configuration carrying one is refused by name.
- The baseline has no default, following the source-era and reference-basis precedent, because
  `AGENTS.md` requires availability to be an explicit assumption. An empty window list is the
  declared full-availability scenario and is preferable to an implied one.
- A window applies whole to every interval it covers. A boundary strictly inside an interval is
  refused, naming the interval, rather than prorated: prorating would apply a finer schedule than
  the one declared, and rounding would apply a different one.
- Overlapping windows, a window covering no dispatched interval, reversed or empty windows, naive
  timestamps, duplicate outage identifiers and out-of-range fractions are refused. Paths that do
  not share one canonical interval identity are refused, so what differs between paths is the
  sampled price and not the physical condition.
- The dispatch summary records the schedule by identity and the run writes per-interval
  availability provenance, so a margin traces back to the outage assumption behind it.
- Availability scales grid-side charge and discharge power only. Auxiliary load, state-of-charge
  drift while unavailable, restart behaviour and any cost of the outage itself are not modelled,
  and a perfect-foresight dispatch positions the battery for a declared outage, so the margin
  stays an upper bound.
- Timing is the whole content of the scenario and the model gives no help choosing it: the same
  outage costs almost nothing in a low-spread week and a great deal in a high-spread one.

## Scenario-ensemble range reporting

- `report-scenario-ensemble` and `greek_bess.stress.report_scenario_ensemble` compose
  bootstrap-path dispatch results already produced under two or more named scenarios and report
  the minimum, maximum and spread of their margin outcomes. Nothing new is computed: no price
  transformation, dispatch mode, forecast method or finance treatment is introduced.
- The range is taken per bootstrap path, naming the scenario at each end. Nothing is aggregated
  across paths: a total or an average over sampled paths would read as an expectation the uniform
  block resampling of a non-stationary history cannot support.
- Every scenario is named by the caller in an explicit manifest. There is no default scenario set
  and no implicit baseline — `transformation_summary_json` is required, so an untransformed replay
  declares itself as `null` — and an ensemble of fewer than two scenarios is refused.
- A range across named scenarios is a range across judgments, not a distribution. No probability,
  percentile, likelihood, expected value, loss metric, ranking or central case is produced, and
  the exclusion is executable: every emitted column name and summary key is checked against
  `FORBIDDEN_REPORT_TERMS`, and a match raises instead of being written.
- Scenarios are combined only on an equivalent basis, and the basis is the asset and the sample:
  battery parameters, the terminal-energy constraint, the selected source era and the path
  identities must match, and a difference is refused with the mismatching basis and both values
  named. The terminal-energy constraint is checked separately, with the derived terminal energy
  recorded.
- The price transformation and the availability schedule are the judgments under examination
  rather than part of the basis, and are carried as provenance on every reported figure. Without
  that line an ensemble could never place a declared outage against a baseline (decision entry
  2026-08-31). An unrecorded availability assumption is still refused.
- Every reported figure carries its scenario name, transformation method and parameters, the
  source-era selection and the input run identity, so a range traces back to the runs behind it.
- The range is bounded by the scenarios the caller chose. Adding or removing one changes it with
  no new evidence, and a wide range describes disagreement between judgments rather than
  measurable uncertainty.

## Spread compression about a daily reference level

- `compress-spread` and `greek_bess.stress.apply_spread_compression` transform within-day spread
  rather than level: `compressed = reference + factor * (price - reference)` over each path's
  CET/CEST market day, so every within-day range is scaled by exactly the declared factor.
- This is the economically first-order storage stress and the way cannibalisation pressure is
  represented. A constant level shift leaves spreads untouched and moves margin only through
  round-trip losses and fees; compression changes the quantity being arbitraged.
- The factor is bounded to [0, 1]: 1.0 is the identity, 0.0 flattens each day onto its reference.
  Spread widening is deliberately out of scope, which is a scope limit and not a judgment that
  widening is unlikely.
- `reference_basis` is declared with no default, following the source-era precedent. `daily_mean`
  preserves each daily mean exactly, so the result is a pure spread change; `daily_median` does
  not, and the summary reports the maximum absolute daily-mean shift it causes.
- Zero and negative results are preserved and never clipped. Compression pulls prices toward the
  reference, so intervals can cross zero and change sign; the count is reported rather than
  suppressed, because a scenario that materially changes the negative-interval count is changing
  the market's character and not only its spread.
- Missing prices are refused explicitly: one would propagate through its market day's reference
  level and corrupt every interval of that day.
- The summary reports mean and maximum daily range and negative and zero interval counts, before
  and after. Interval provenance records the market day, reference level, factor, basis, original
  and compressed prices and input source metadata.
- The factor is a declared judgmental scenario, not an estimate. The replayed history predates
  operating battery competition almost entirely, so no competitive spread response is estimable
  from it. No probability, percentile, loss metric or ranking attaches to a factor.
- The per-delivery-year decomposition is the direct evidence for prioritising this over level:
  2026 shows the highest ceiling per market day of any non-crisis year on the lowest mean price
  since 2020, because mean daily range rose every year since 2023 while mean price fell.

## Bootstrap source-era and resolution policy

- A source era is a maximal contiguous run of market days at one delivery resolution. The
  bootstrap samples from exactly one; a resolution change or a market-day gap ends an era.
- A single-era history needs no declaration. A multi-era history must declare one with
  `source_resolution_minutes`, narrowed by `source_start_day`/`source_end_day` when ambiguous.
  There is no default and no "most recent" rule.
- The accepted history holds two eras: 60 minutes over 2020-11-01 to 2025-09-30 (1,795 market
  days, five or six occurrences of every season) and 15 minutes over 2025-10-01 to 2026-08-25
  (329 market days, exactly one occurrence of each season). Passing it undeclared now fails
  with a message naming both, instead of a bare resolution complaint.
- The selected era is recorded in the run summary and on every provenance row, and days outside
  it are absent from the candidate search, so no block can straddle a regime boundary.
- Minimum and median block-candidate counts are reported, so a position where every path
  repeats one source block is visible rather than smoothed.
- Resampling one resolution into another, blending eras and attaching any likelihood to an era
  remain out of scope. The policy is recorded in `docs/bootstrap_source_era_policy.md`.

## Per-delivery-year decomposition of the accepted replay

- `decompose-annual-replay` regroups an already-accepted replay into delivery years, adding no
  model, market or transformation.
- A delivery year is the calendar year of the interval's CET/CEST market-day start, the same
  convention the committed custody records use; the summary states why a UTC grouping of the
  same intervals differs by one interval at a year boundary.
- Each year carries market-day coverage, an explicit partial-year flag, interval counts by
  resolution, preserved negative, zero and missing price counts, price context including the
  mean daily price range, and its perfect-foresight ceiling.
- Forecast capture is reported per method on that method's own backtested days, and separately
  on the days every method backtested, where the recorded ceiling spread is the like-for-like
  evidence.
- `optimize-perfect-foresight --daily-solves` publishes the daily-composed dispatch mode the
  2026-08-27 acceptance ran through a temporary runner, so the annual ceiling and the annual
  capture ratio share one basis and no trade spans a year boundary.
- A schedule whose settled prices differ from the supplied history at any interval is refused,
  so a decomposition cannot be paired with a history it was not solved on.
- Per-market-day figures are within-period averages; nothing is annualized, and no probability,
  percentile, loss metric or year ranking is produced.
- The `Decompose the accepted replay by delivery year` workflow verifies the accepted artifact
  against its committed custody record before consuming it, then runs the daily ceiling, the
  four causal naïve backtests and the decomposition inside Actions.
- **Accepted on 2026-08-28** by workflow run `33147448666` against artifact run `32971677163`.
  Custody verification passed, so no official publication has been revised since acceptance.
  Every per-year figure reconciles with previously accepted aggregates: the annual ceilings sum
  to EUR 24,974,729.59 over 2,124 market days, the four methods' realized margins, own-days
  ceilings, day counts and loss-day counts all match, and the 2,098-day common-day ceiling of
  EUR 24,665,532.17 is identical across methods with a spread of EUR 0.00 in every year.
- The decomposition shows regime dependence the aggregate conceals: 2022 contributes 23.5 % of
  the six-year ceiling from 17.2 % of the days; mean daily price range has risen every year
  since 2023 while the mean price fell, so 2026 has the second-widest range on the lowest mean
  price since 2020; ensemble capture spans 0.6937 to 0.8724 against an aggregate of 0.7814; and
  the method ranking reverses in 2026, where `rolling_mean` overtakes the ensemble.
- Evidence is recorded in `docs/official_annual_decomposition_2026-08-28.md`.

## Durable custody of accepted official artifacts

- Accepted official artifacts are to be stored as encrypted assets on a release in this private
  repository, and are already fingerprinted by price-free custody records committed under
  `docs/custody/`. A committed record is a fingerprint, not a durable copy: the operator upload is
  not verified complete in the repository record, so custody is not recorded as complete.
- A custody record holds per-file digests and content-level invariants of the normalized
  series, including a digest of the interval and price series that is independent of CSV
  formatting, column order and float repr.
- `record-custody` builds a record; `verify-custody` re-derives it from a stored copy and
  returns exit code 2 on any difference, so a copy can be proven to be the accepted artifact
  and a re-retrieval that differs is detected rather than silently adopted.
- The `Record official artifact custody` workflow performs the same check inside Actions,
  recording when no committed record exists and verifying against it once one does.
- Artifact retention on all official-data workflows is raised from 7 to 90 days, so a passed
  acceptance no longer has a one-week shelf life.
- Encryption keys and the release upload remain with the operator; no automation in this
  repository holds a key that could decrypt an accepted artifact.
- The procedure, the operator steps and the failure taxonomy are recorded in
  `docs/official_artifact_custody.md`.
- Custody covers retrieved official artifacts only. Derived evidence computed from a custodied
  history, such as the `annual-replay-decomposition` artifact, is guaranteed by reproduction
  from the recorded history, commit and configuration instead.
- **The encrypted copies now exist.** Run `33497084006` verified both artifacts against their
  committed records, encrypted them to the operator's recipient and published release
  `custody-2026-09-01` on 1 September 2026: `greek-dam-official-history.tar.gz.age`
  (1,312,353 B, ciphertext SHA-256 `3fa76c75…0329bf`) and
  `henex-entsoe-reconciliation.tar.gz.age` (1,672,921 B, `43c5b07b…0ae431`). The reconciliation
  copy is the only surviving form of that evidence once its source artifact expires
  3 September 2026.
- **The key was exercised the same day**, while the source artifacts still existed and a failure
  would have been recoverable. The operator decrypted the reconciliation copy and recovered an
  archive of the expected size, so the private key opens the published copies. With the
  pre-encryption verification and age's authenticated encryption, that composes into the full
  claim: the stored copies are recoverable and are the accepted artifacts.
- **One gap remains, and it is not bookkeeping:** the second copy under separate control does not
  exist. One release is one failure domain. Until it does, custody is not recorded as complete.
- The `Publish encrypted custody copies` workflow now performs the download, verification,
  encryption and release upload inside Actions, so the operator's remaining part is generating
  one age key pair and supplying the public recipient. An age recipient can encrypt and cannot
  decrypt, so no automation here can read an accepted artifact. An artifact that does not verify
  against its committed record is refused before encryption. The second copy under separate
  control, and the private key itself, remain the operator's.

## Replacement official-history retrieval, 1 September 2026

- The accepted artifact from run `32971677163` was created under the original seven-day
  retention and expires 2 September 2026 at 13:07:24 UTC. Run `33483975614` re-ran
  `Fetch official Greek market history` with the same inputs on 1 September 2026, producing a
  replacement that expires **30 November 2026 at 07:49:14 UTC** under the 90-day retention.
- Verification run `33484823956` checked the replacement against the committed custody record
  and reported `difference_count: 4`, `verified: false`. **All four differences are per-file
  byte digests and no content fingerprint differs at all.** Both `price_series_sha256` values
  match, so the price series is identical interval for interval, as are the interval counts,
  first and last interval, market-day counts, negative/zero/missing counts and quality-flag
  counts. No file changed size and both quality reports are byte-identical.
- The difference is a **faithful re-retrieval**, a case the custody procedure did not name.
  `retrieved_at_utc` is a canonical column, so any re-retrieval rewrites one field in every row
  of both price CSVs; the manifests carry retrieval timestamps for the same reason. For a
  re-retrieval only the content fingerprints are diagnostic. Recorded as case 4 in
  `docs/official_artifact_custody.md`.
- Normalization did not change either: the only data-layer edit since the accepted run is a
  behaviour-preserving `pd.Timedelta` call in `data/henex.py`.
- The finding was reported before the record was touched. The record was then **re-recorded
  against run `33483975614`** as a separate decision, because after 2 September 2026 no obtainable
  copy could match the superseded per-file digests and a record that verifies against nothing
  preserves no evidence. Run `33489920268` generated it in `record` mode and the committed file is
  what that run emitted; against the superseded record only `source_run_id`, the published digest,
  `recorded_at_utc` and the four per-file digests changed, with every content fingerprint
  unchanged. The superseded record stays in Git history.
- `record_mode` makes a deliberate re-record an explicit request. Previously it required deleting
  the committed record so the "no record exists" branch would fire, which is indistinguishable
  from tampering. Neither mode writes to `docs/custody/`.
- The same run re-verified `henex-entsoe-reconciliation` from run `33073631530` with
  `difference_count: 0`, and its regenerated record matched, so that record is unchanged.

## Blocked: the reconciliation artifact has no replacement

- `henex-entsoe-reconciliation` from run `33073631530` expires **3 September 2026 at 12:50 UTC**
  and is the only copy of the ENTSO-E interval series and retrieval metadata behind the passed
  reconciliation.
- A refresh dispatched on 1 September (run `33489364087`) was refused ten seconds in by the
  workflow's own guard: **`ENTSOE_SECURITY_TOKEN` is no longer configured as a repository
  secret.** No ENTSO-E request was made and no artifact was produced. The guard behaved
  correctly; it failed loudly rather than retrieving nothing and calling it a reconciliation.
- Restoring the secret is an operator action. Until then the encrypted upload of the existing
  artifact, which needs no secret, is the only thing that preserves the evidence past
  3 September.

## Run manifest and report contract

- `greek_bess.reporting`, `record-run-manifest` and `verify-run-manifest` record any result
  summary under a versioned manifest. The producing module's summary is carried **verbatim**; the
  contract adds a projection over it and reinterprets nothing.
- The projection is what a consumer reads instead of incidental keys: declared `result_kind` from
  a closed registry, the `basis` that kind reports on, the required non-empty `result_label`,
  `produced_by`, `project_version`, declared inputs and the standing exclusions.
- `basis` distinguishes a historical replay upper bound, a historical forecast backtest, a
  synthetic scenario, screening arithmetic and data-acceptance evidence. The same euro figure
  means something different under each.
- **Label retention is now executable.** `PROMPT.md` requires outputs to retain their source and
  limitation labels through downstream analysis; fifteen of sixteen modules kept that convention
  and nothing enforced it. A summary without a non-empty `result_label` is refused.
- A manifest is refused on read when its schema version, result kind or declared basis is not one
  this build understands, so a newer contract is never reinterpreted as the current one.
- The distributional-term check is scoped to the kinds that declare it (today
  `scenario_ensemble_range` alone). The term list bans claims about the distribution of outcomes,
  not the words: the optimizer's own `average_charge_price_eur_per_mwh`, a benchmark's mean
  absolute error and the audit's median lead time are none of them distributional claims, and a
  check that refuses honest arithmetic teaches readers to route around it.
- This adds no interface, exporter, rendering surface or dependency and **does not open v0.8**.
  Policy in `docs/run_manifest_contract.md`.

## ADMIE pre-auction publication timing (retained, unused)

> **ADMIE load and RES forecasts are out of scope** (decision entry 2026-09-01). Everything below
> is retained and runnable but is not in service: it is the executable form of the refusal, kept
> so that a future declaration can be tested without rebuilding it. No timing audit was ever run
> over the confirmed filetypes against a verified gate closure, and no ADMIE field ever entered
> forecasting. This section describes what the tooling does, not a capability the project uses.

- `audit-admie-publication-timing` and `greek_bess.data.admie_timing` turn the
  `requires_pre_auction_timing_validation` quarantine label into a pass or a fail. The audit reads
  ADMIE retrieval manifests and reports, per filetype and delivery day, whether a file was
  published strictly before that day's day-ahead gate closure. No forecast file is parsed.
- The closure is **declared, with no default and no built-in constant**: one or more dated
  regimes, each naming the clock its time is stated on and carrying a required reference to the
  market rule behind it, so a rule change during the audited history is representable and every
  accepted day carries the rule that accepted it.
- A delivery day earlier than the first declared regime is refused rather than audited against a
  rule that was not in force. A closure falling in a daylight-saving gap or repetition is refused
  rather than resolved by convention. A publication exactly at the closure counts as late.
- Evidence is graded and the grades never merge. `witnessed_pre_gate` means a retrieval performed
  before the closure observed the file in the catalog; `asserted_pre_gate` means only the
  provider's timestamp, read afterwards, says so. Running the audit before a delivery day is
  therefore how witnessed evidence accumulates.
- Each accepted day names its decision-time revision — the latest published strictly before
  closure, the only revision a backtest may read — and counts the revisions that superseded it.
  Retrieval for the audit must use `fetch-admie-files --all-revisions`.
- A day no supplied record covers is `no_record`, never assumed compliant. One ADMIE URL carrying
  two different digests across manifests is refused as an in-place replacement, and one carrying
  two different publication timestamps as a restated publication time.
- The `Audit ADMIE publication timing` workflow retrieves a declared window and uploads the
  manifest, per-day verdicts, per-observation evidence and summary for 90 days.
- **This establishes publication timing only.** It accepts no file format, proves no forecasting
  skill, and does not lift the forecast-feature quarantine; the summary states that in its own
  output. Policy in `docs/admie_publication_timing_policy.md`.
- **Filetype acceptance (2026-08-31):** the 74-entry live catalog identifies ISP1 and ISP2
  day-ahead load/RES forecast pairs. A 26-28 August retrieval discovered 12 ISP1 files (six load,
  six RES) and six ISP2 files (three load, three RES). The catalog-valid
  `DayAheadLoadForecast`/`DayAheadRESForecast` pair returned none over that window, so it is no
  longer declared leakage-relevant. Evidence in `docs/admie_filetype_acceptance_2026-08-31.md`.
- Retrieval no longer writes an empty manifest on an empty discovery: it refuses and names the
  live catalog's actual filetypes, so a wrong name cannot impersonate `no_record`, which reads as
  a publisher that published nothing.
- **Outstanding:** the operator's verified gate-closure schedule
  (`config/admie_gate_closure.example.json` ships the format with a placeholder reference), a
  publication-timing audit over the confirmed ISP1/ISP2 names, and file-format acceptance.

## Official cross-source reconciliation

- The accepted HEnEx history was compared interval by interval against ENTSO-E A44 Greek
  day-ahead prices over the identical window, market days 1 November 2020 through 25 August 2026.
- 74,662 of 74,663 intervals match within EUR 0.000001/MWh; neither source omits an interval the
  other publishes.
- One interval on the 29 October 2023 autumn DST market day differs by exactly EUR 0.01/MWh,
  consistent with the already-accepted HEnEx one-cent rounding-consensus bound.
- Both sources independently pass their own deterministic quality assessment over the window.
- The reconciliation corrected a real defect in the project's ENTSO-E reader: A44 `A03` curve-type
  repeats were being dropped, which had understated ENTSO-E coverage by 4,874 intervals.
- An immediate second run reproduced every count and statistic.
- This is cross-source ingestion evidence, not revenue, forecast or investment evidence.
- Aggregate evidence is recorded in `docs/official_source_reconciliation_2026-08-27.md`.

## Official multi-year operational acceptance

- The accepted `greek-dam-official-history` artifact was hash-verified before use and covers
  74,663 official intervals across 2,124 market days from 1 November 2020 through 25 August 2026.
- Input acceptance passed with zero missing prices, duplicates, gaps, overlaps, incomplete market
  days and mixed-resolution days, preserving 1,767 negative and 1,914 zero prices and 980
  rounding-consensus flags.
- The existing optimizer solved the complete 74,663-interval horizon in one optimal MILP solve and
  again as 2,124 independent daily solves, with zero constraint violations in either mode.
- All four causal naïve baselines and both ML benchmarks were backtested over the accepted history
  with proven leakage-free time ordering, exact realized-price settlement and identical
  like-for-like perfect-foresight ceilings.
- Every excluded forecast day is attributable to warm-up, causal-lag, spring DST or the
  2025-10-01 resolution change; none is unexplained.
- Both analytical paths reproduced identical results on an immediate second run.
- Results are historical perfect-foresight upper bounds and historical benchmark evidence, not
  expected revenue, forecasts, probabilities or investment conclusions.
- Aggregate evidence is recorded in
  `docs/official_multiyear_operational_acceptance_2026-08-27.md`.

## v0.7.2 bootstrap-path dispatch integration

- Validated synthetic multi-path input is solved independently under one battery configuration
  and one common availability assumption.
- Every path independently enforces the existing power, energy, efficiency, exclusivity, SOC,
  grid, optional cycle and terminal-energy constraints.
- Interval output preserves path ID, canonical identity and provenance; path-level output retains
  the optimizer's operational and revenue decomposition.
- Duplicate, incomplete, provenance-invalid or structurally inconsistent paths fail explicitly.
- Outputs remain synthetic perfect-foresight upper bounds, not forecasts, probabilities,
  expected revenue or investment evidence.

## v0.7.1 price-level shock

- One explicit additive constant EUR/MWh transformation operates only on validated bootstrap
  paths and preserves canonical timezone-aware interval keys and path IDs.
- Every output interval records its original price, shocked price, shift, transformation ID and
  input source provenance in a separate audit table.
- Missing prices, duplicate path intervals, incomplete market days and non-contiguous paths fail.
- Public API and CLI outputs remain labelled synthetic, non-forecast and non-investment evidence.

## v0.7 seasonal block-bootstrap foundation

- Deterministic sampling with an explicit non-negative random seed.
- Contiguous meteorological-season blocks sampled with replacement.
- Exact target/source daily interval-count matching preserves DST market-day structure.
- Prices are copied exactly; zero and negative prices remain valid.
- Missing prices, gaps, overlaps and incomplete source days fail rather than being filled.
- Every sampled block records target/source dates, candidate set size and selected index.
- Public Python API and CLI produce explicitly synthetic, non-forecast-labelled artifacts.
- Dispatch, finance, probability summaries and shock layers remain excluded.

## Repository foundation merged

- Completed v0.1-v0.6 implementation preserved as the first honest GitHub snapshot.
- Approved brief, decisions, methodology and limitations externalized.
- Repository exclusions enforce no official data, secrets, models or generated artifacts.
- PR checks run Ruff, mypy, pytest and a clean wheel build without private credentials.
- GitHub Actions passed all four gates, including all 60 tests, on 26 August 2026.
- PR #1 was merged into `main` on 26 August 2026.

## v0.6.1 data-ingestion milestone

- Verified HEnEx annual results archive URLs registered for 2020-2025.
- Safe annual ZIP extraction limited to English DAM result workbooks.
- Multi-workbook latest-revision selection with conflict rejection.
- Incremental HEnEx daily catalog discovery for the unarchived current year.
- ADMIE public filetype and date-range API client.
- Delivery coverage, provider publication time, retrieval time and SHA-256 provenance manifests.
- Strict HTTPS provider allowlists and atomic writes below ignored data directories.
- Manual private GitHub workflow for short-lived normalized-history artifacts.
- Eight new retrieval/security tests; complete suite currently 68 tests.
- Clean GitHub Actions validation passed Ruff, mypy, all 68 tests and wheel build on
  26 August 2026.
- PR #2 was merged on 26 August 2026.

## v0.6.2 live-history acceptance fix

- The first official-history workflow correctly failed on superseded 16 December 2020 workbook
  conflicts, revealing that revision selection occurred too late.
- Latest workbook revisions are now selected before parsing; the corrected v03 file is retained.
- The official nested 2021 DAM archive is extracted with bounded depth, size and provenance.
- One-cent differences in at most two cross-border rows may use a unique strict majority and are
  explicitly flagged; material or ambiguous conflicts still fail.
- The complete live 2020-2025 archives produce 51,915 contiguous intervals, no missing or
  duplicate UTC keys, and 196 preserved negative-price intervals.
- All 72 tests pass locally and in clean GitHub CI; Ruff, mypy and the wheel build also pass.
- Archive hashes and acceptance statistics are recorded in
  `docs/official_history_acceptance_2026-08-26.md`.

## v0.6.3 live daily-catalog fix

- PR #3 was merged and clean CI passed on 26 August 2026.
- Manual workflow run 32968302085 accepted the complete 2020-2025 archive history and uploaded
  the private `greek-dam-official-history` artifact.
- Incremental run 32969157951 failed only at daily discovery because the live HEnEx catalogue
  omits `.xlsx` from visible result names.
- Daily discovery now accepts the live suffix-less labels, uses the live `/web/guest/` Liferay
  pagination route and rejects repeated pages.
- Requested daily ranges must contain every delivery day; partial catalogue retrieval is an
  explicit error rather than a silently shortened dataset.
- Clean GitHub CI passed Ruff, mypy, all 77 tests and the wheel build.
- Manual workflow run 32971677163 passed both the 2020-2025 annual-archive stage and the
  1 January-25 August 2026 daily-retrieval stage.
- The private `greek-dam-official-history` artifact contains 74,663 contiguous official
  intervals from 1 November 2020 through 25 August 2026, including 22,748 daily-retrieved 2026
  rows, with zero missing intervals.
- The artifact SHA-256 is
  `127915bc6e143a6bf2a4cb0a559b798e231062097bdaf9bf467a051260c4b198`.

## Completed

- Canonical Greek DAM interval schema and DST normalization.
- ENTSO-E A44 client and HEnEx workbook parser.
- Data quality and cross-source comparison.
- Perfect-foresight mixed-integer dispatch with auditable margin outputs.
- Leakage-safe daily, weekly, rolling-mean and ensemble forecast baselines.
- Forecast metrics compatible with negative and zero prices.
- Walk-forward daily dispatch planned on forecasts and settled on realized prices.
- Like-for-like daily perfect-foresight ceiling, value capture and regret.
- Full-period and backtested-only forecast metrics reported separately.
- Incomplete forecast days, missing intervals and backtested fractions disclosed.
- Causal calendar, lag and rolling-price features with explicit provenance.
- Ridge and histogram-gradient-boosting walk-forward benchmarks.
- Time-based train/validation/test periods and validation-only model selection.
- Deterministic refit logs proving training dates precede forecast dates.
- Held-out forecast rankings against all v0.3 naïve baselines.
- Like-for-like held-out dispatch value, capture and regret comparisons.
- `forecast-ml` and `backtest-ml-dispatch` CLI workflows.
- Documentation and 60 passing tests.
- Production HEnEx parser acceptance against the official 24 and 25 August 2026
  `EL-DAM_Results_EN_v01` workbooks, covering 192 contiguous quarter-hour intervals.
- Cohort-based calendar and cycle fade with explicit retained-capacity arithmetic.
- Separate aging and throughput state for initial and augmented battery cohorts.
- Usable energy and charge/discharge power evolution.
- Proportional cell-discharge allocation across cohorts.
- Retained-capacity warranty, EFC throughput and retirement-threshold indicators.
- Optional hard EFC warranty headroom enforced in daily dispatch.
- Dated augmentation/replacement capacity, explicit cohort retirement and separately
  recorded event cost.
- Daily perfect-foresight dispatch using only beginning-of-day degradation state.
- Interval, daily, cohort and summary degradation CLI artifacts.
- Continuous daily operating-path validation with no missing-day extrapolation.
- Mandatory perfect-foresight, historical-backtest or user-scenario margin labels.
- Itemized initial CAPEX, fixed and variable OPEX, augmentation, decommissioning and
  residual-value cash flows.
- Nominal OPEX escalation and exact-date discounting.
- Unlevered NPV and IRR with explicit multiple-sign-change ambiguity handling.
- Simple and discounted payback dates and years.
- Maximum initial CAPEX, market-margin realization and average annual margin break-even
  outputs.
- `evaluate-project-finance` CLI with daily, annual and JSON summary artifacts.
- End-to-end degradation-dispatch-to-finance integration coverage.
- Explicit-unit pandas timedelta construction in synthetic, HEnEx and ENTSO-E ingestion, with a
  pytest warning policy scoped to warnings attributed to `greek_bess` or to the project's tests.
- One declared project version, with `pyproject.toml`, `greek_bess.__version__` and the README
  release line locked together by test.

## Validation still required

Nothing in the approved `PROMPT.md` scope is awaiting validation. ADMIE load/RES format and
pre-auction timing acceptance were the last open items here and are no longer asked: those
forecasts are out of scope (decision entry 2026-09-01).

The HEnEx acceptance evidence, raw-file hashes and exact results are recorded in
`docs/official_data_acceptance_2026-08-25.md`. Official raw workbooks are deliberately
excluded from the repository.

## Current limitations

- ML models use price-history and calendar features only; no validated exogenous data.
- ML results are benchmarks, not production forecasts or profitability evidence.
- Price-taking quantities are assumed fully accepted.
- No imbalance, intraday, balancing or reserve participation.
- Daily backtests restore initial SOC at every day-end.
- Daily persistence is naturally incomplete after spring DST because the preceding
  23-hour day lacks one wall-clock hour; the affected day is excluded and disclosed.
- Fade rates and warranty thresholds are illustrative until replaced with OEM evidence.
- Linear additive fade does not model temperature, C-rate, depth-of-discharge bins,
  state-of-charge dwell, nonlinear knees or cell-to-cell dispersion.
- Daily cohort throughput is allocated proportionally to usable energy rather than using
  a controller-specific rack dispatch policy.
- Finance inputs remain illustrative until replaced with project-specific EPC, grid,
  O&M, insurance, market-access and decommissioning evidence.
- A supplied perfect-foresight margin remains an upper bound even after finance treatment.
- Finance does not extrapolate an incomplete operating path or create future revenues.
- No tax, subsidy, debt, working-capital or Monte Carlo layer.
- No user interface.

## Immediate next milestone

Official multi-year operational acceptance has passed for both the perfect-foresight and
forecast-backtest paths. On 2026-08-27 the project was repositioned as a Greek DAM battery
replay and research benchmark, and the v0.7 scope was corrected to deterministic named
scenarios: percentile and loss-probability outputs were removed pending a defensible
calibration story. The bootstrap source-era/resolution policy landed on 2026-08-27 and spread compression on
2026-08-28, prioritised over availability/outage integration because the per-delivery-year
decomposition showed spread, not level, driving the ceiling. Scenario-ensemble range reporting,
declared availability/outage paths and declared negative-price events are now complete, closing
the approved v0.7 modeling scope. The formal completed-v0.7 review found no correctness or
data-integrity defect and reconciled one roadmap wording contradiction about availability
provenance. The v0.8 interface and exportable reports were gated until the user explicitly
approved their design; that approval arrived on 1 September 2026, `PROMPT.md` was amended, and
`docs/v0.8_design.md` was adopted as the design of record. v0.8.0, the report rendering
foundation, and v0.8.1, multi-run composition, both landed on 1 September 2026; v0.8.2 then
declined the interactive viewer and completed v0.8 with the static renderer. The
versioned run manifest and report contract the review named as the prerequisite landed on
2026-08-31. ENTSO-E reconciliation passed on 2026-08-27. Custody tooling and the storage
procedure landed on 2026-08-27; the encrypted copies were published on 2026-09-01 and the key was
exercised the same day. The ADMIE publication-timing audit, workflow and policy landed on
2026-08-31 and are retained as unused: ADMIE load and RES forecasts were removed from scope on
2026-09-01, so that acceptance is not pending but withdrawn. The per-year decomposition surface and workflow landed on 2026-08-27 and its official run
was accepted on 2026-08-28, so that track is complete.
