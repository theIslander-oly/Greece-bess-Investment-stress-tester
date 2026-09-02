# Decision log

## 2026-09-02 — Make point-in-time feature joins revision-aware and whole-day atomic

- **Decision:** Select one value per delivery interval from the latest revision published strictly before the declared effective cutoff; count and exclude later revisions; map only by half-open UTC containment; and exclude a whole delivery day when any declared variable-area pair is incomplete. Every emitted value has an audit row naming its source document, revision and raw-byte digest.
- **Reason:** Selecting a current revision or retaining a partial day can leak future information or silently change the model's feature set. Whole-day atomicity and complete provenance make the causal claim executable.
- **Consequence:** Publications at the cutoff are late, nothing is filled or imputed, hourly-to-quarter-hour use is labelled as a coarser broadcast, and finer features are refused without a declared aggregation rule. v0.9.2 is validated only on synthetic fixtures; real-data acceptance remains blocked on the three absent operator declarations.

## 2026-09-02 — Treat manifest-local plotting as rendering, with a closed chart doorway

- **Decision:** Permit deterministic inline SVG only for values already recorded inside the one verified manifest whose labelled block contains it. The initial closed mapping is `scenario_ensemble_range.path_ranges`.
- **Reason:** Visual encoding can improve legibility without creating evidence, while an arbitrary plotting doorway could bypass the manifest-only contract.
- **Consequence:** Renderer version 3 uses no script, network or external asset, opens no manifest-declared path, combines no manifests or bases, preserves labels and exclusions, and states unusable chart fields instead of inventing values.

## 2026-09-02 — Keep performance claims attributable and reproducible

- **Decision:** Every engineering timing names its workload and execution environment; provide an opt-in benchmark over deterministic synthetic prices that emits configuration, environment, solve paths and throughput.
- **Reason:** An unattributed timing becomes folklore, while synthetic data makes engineering behavior reproducible without distributing official prices.
- **Consequence:** The accepted-history 69-second decomposition remains attributed to run `33147448666`; synthetic benchmark output is engineering evidence only and changes no model assumption or investment conclusion.

## 2026-09-02 — Build v0.9.1 ingestion so that availability is per interval, and correct the step range

- **Decision:** v0.9.1 lands the point-in-time ingestion path and the availability audit, and
  fixes four things the design and the source assessment left open or stated at the wrong
  granularity.
  1. **Availability is established per delivery interval, never per delivery day.** A day is
     accepted only when every one of its intervals is covered by an admitted-grade value
     published strictly before the cutoff. One late forecast step makes the day
     `incomplete_before_cutoff`, not a day with fewer intervals.
  2. **The required forecast steps are 22-47, and are derived rather than declared.** The source
     assessment computed 21-46 from the *Athens* delivery day. This project's delivery day is the
     **CET/CEST market day** — the same day `market_day_starts` and the canonical price schema use
     — which begins an hour later. Rather than replace one constant with another,
     `required_forecast_steps` derives the set from each market day, so a 23-hour or 25-hour day
     produces its own; a test asserts the widest range over the whole usable record is exactly
     (22, 47) and lies inside the hourly product.
  3. **A derived value's provenance is the union of its inputs.** Wind speed combines the two
     10 m components and a de-averaged radiation hour combines two adjacent step objects, so for
     such a value `published_at_utc` is the **latest** contributing object's instant,
     `source_document_id` names every contributing object and message, and `raw_sha256` is taken
     over the contributing message digests in a stated order.
  4. **The stored evidence grade records what the retrieval established; the effective grade is
     derived per delivery day.** `witnessed` is defined by a row's own two instants against a
     cutoff, and a retrieval does not know the cutoff, so the audit computes it. The derivation
     may lower a grade and may raise `provider_declared` to `witnessed` when the row's own
     retrieval instant earns it, but a row stored as `assumed` stays `assumed` whatever its
     timestamps say.
- **Reason:** Each is forced by something already on the record rather than chosen for
  convenience. (1) is the spike's observation that upload order is not monotone in forecast step
  — on 1 August 2026 step 48 was written before step 24 — so a day-level verdict built from any
  one object would be wrong in both directions. (2) follows from this repository's own definition
  of a delivery day, which is `MARKET_TZ`; adopting the assessment's Athens-based range would have
  left the last hour of every winter market day without its radiation bucket. (3) is the only
  reading that does not over-claim: a value is available when its *last* input is, and a digest of
  one input would not identify the value. (4) keeps the anti-promotion rule where it belongs — what
  is weak about an assumed row is that the instant was inferred, not that the arithmetic came out
  badly — while letting the two mechanically defined grades be computed rather than trusted.
- **What this does not decide:** nothing is accepted. No value, unit or source enters
  forecasting; the data-acceptance document of design Section 7 still precedes any benchmark
  document, and the audit summary says so in its own output
  (`establishes_only_availability: true`, `quarantine_lifted: false`). The `assumed` grade stays
  quarantined: admitting it makes a run exploratory and gives its days a status that can never be
  counted as accepted. ADMIE-originated forecasts are not reopened by any route.
- **Also settled, smaller:** `AdmiePublicationTimingError` becomes an **alias** of
  `DecisionCutoffError` rather than a subclass, so that a refusal raised by the moved schedule
  code is still caught by every existing `except AdmiePublicationTimingError`;
  `tests/test_admie_timing.py` passes untouched, which is the evidence the move changed nothing.
  A declared sampling point must land on a grid node, because a point between nodes would have to
  be interpolated and no interpolation rule is declared. `source_revision` is normalized to a
  nullable string, because a revision is an identity rather than a quantity and an absent one must
  read back from CSV as absent rather than as `NaN`. `eccodes` alone is declared as the new
  dependency; `cfgrib` and `xarray` are not, because the low-level single-message read needs
  neither.
- **Consequence:** v0.9.1's code is complete and tested, and no v0.9 surface can run until the
  operator declares the decision cutoff, the decision lead and the sampling geography (G3). The
  witness workflow is scheduled from today and refuses at its guard step without them, stating
  each time that the day it did not witness is not recoverable.
- **Records:** `docs/point_in_time_feature_contract.md`,
  `docs/history/implementation_report_v0.9.1.md`.

## 2026-09-02 — Choose NOAA GFS forecast vintages as the v0.9 fundamentals source

- **Decision:** The v0.9.0 source-selection spike is run and recorded in
  `docs/fundamentals_source_assessment_2026-09-02.md`. It passed all three checks the design made
  the source choice conditional on, so **NOAA GFS 0.25° forecast vintages from the AWS Open Data
  archive** are the single v0.9 fundamentals source, taken from the **00 UTC cycle of D-1**,
  restricted to delivery days from **27 February 2021** onward, with the object's `Last-Modified`
  instant as the `provider_declared` availability evidence and the witness workflow adding
  `witnessed` days from v0.9.1. G0 is not triggered, so the EEX EU ETS fallback is **not** selected
  and stays unassessed; it may not be adopted later without its own spike.
- **Reason:** The design named a recommendation and labelled every external fact behind it an
  inference. The spike verified them: the archive serves anonymous byte-range reads through `.idx`
  sidecars at a 157× reduction (3.27 MiB rather than 514 MiB per step, 85 MiB per delivery day,
  167 GiB across the usable history); all four proposed variables are present in every step
  inspected; a pip-installable ecCodes binding installs with no system package and the
  repository's four gates pass unchanged with it on 3.12 and 3.13; and the provider's licence text
  permits the intended use under attribution, no implied endorsement and no presentation of
  derived values as unaltered NOAA data. No credential is involved, so nothing here touches the
  blocked-secret items.
- **What the spike corrected, and what that costs:**
  - **The usable record starts later than the archive does.** Before 26 February 2021 the 0.25°
    product is 3-hourly, so the first delivery day that can carry hourly features is 27 February
    2021. **118 of the accepted history's 2,131 delivery days carry no feature**; they are
    disclosed and excluded by named cause, and a 3-hourly broadcast over that window is refused
    rather than used to fill it.
  - **The cycle is 00 UTC of D-1.** The 06 UTC cycle's step-48 object was observed appearing at
    10:00:22 UTC on 15 July 2025, after a 12:00 CEST cutoff. The 00 UTC cycle cleared the same
    illustrative cutoff on all 365 days of 2025, with a normal publication lag of 3 h 41 m to
    4 h 10 m.
  - **Two ingestion facts became requirements.** Both key layouts must be tried for days before
    April 2021 — the `atmos/` segment appears only from 23 March 2021 — and availability must be
    checked per forecast step, because upload order is not monotone in step (1 August 2026: step
    48 was written before step 24).
  - **A restated-timestamp finding is recorded, not resolved.** Every object from 1 January to
    25 February 2021 carries a `Last-Modified` from March or April 2024, 1,107 to 1,215 days after
    its cycle. This is G7. It changes no admissibility, because `Last-Modified` is written when
    the object is written and a re-upload can only move the recorded instant later: the
    `provider_declared` grade can under-claim availability but cannot over-claim it, which is the
    direction a leakage control must fail in.
  - **A genuinely late run and a missing cycle exist in the sample.** The 00 UTC run of 14 June
    2021 published 1 h 39 m after the illustrative cutoff, and the whole 00 UTC 0.25° cycle of
    2 February 2021 is absent from the archive. Both days are excluded by named cause. The late
    run is the concrete case that justifies quarantining the `assumed` grade: a nominal-latency
    assumption of "about four hours" would have admitted it and been wrong.
- **A correction to the plan:** `PLAN.md` recorded that live endpoints are reachable only from
  Actions runners and that this spike therefore had to be a workflow dispatch. That holds for
  `www.admie.gr` and not for this archive, which is reachable from a working checkout, so the
  spike ran locally. The egress policy did refuse `www.eex.com`, `eur-lex.europa.eu`,
  `data.ecmwf.int`, `archive-api.open-meteo.com` and `registry.opendata.aws`, which is why the
  assessment carries those candidates as recorded unknowns rather than verified facts.
- **What is landed today:** the assessment document, an amendment note on Section 3 of the design,
  and the project-record entries. Still no source code, no dependency, no workflow and no data
  source: the decoder was installed into a throwaway virtual environment to test the four gates
  and `pyproject.toml` is unchanged. No accepted figure or analytical behaviour changed, and
  nothing retrieved during the spike is committed.
- **What is still refused:** the decision cutoff, the decision lead and the sampling geography
  remain operator declarations with no defaults, and no v0.9 surface runs without them (G3). The
  12:00 `Europe/Brussels` instant used in the assessment to size publication margins is
  illustrative arithmetic, not a declaration, and nothing is accepted against it. Successful
  retrieval is still not accepted use: the data-acceptance document of Section 7 precedes any
  benchmark document.
- **Consequence:** v0.9.1 may start. It declares `eccodes` alone — not `cfgrib` or `xarray`, which
  the low-level single-message read does not need — and its first CI run closes the one residual
  the spike could not: the decoder was proven on CPython 3.12.3 and 3.13.12 in this environment,
  not on the `actions/setup-python` images. If it fails there, the source choice returns to the G0
  branch and the fallback needs the spike it has not had. The 2026-09-01 removal of ADMIE load and
  RES forecasts from scope is untouched: the chosen source carries no ADMIE content by any route,
  and the ENTSO-E candidates stay isolated as Track B with their unknowns intact.

## 2026-09-02 — Open v0.9 as a point-in-time fundamentals forecast benchmark

- **Decision:** Open v0.9 and record `docs/v0.9_design.md` as its design of record. v0.9 asks
  one question: does an independently validated exogenous input improve the *realized settled
  dispatch value* of a day-ahead battery over price-history models alone? It answers it as an
  ablation — the two existing model families on the existing causal features, against the same
  two families with the same fixed hyperparameters, refit cadence and splits plus accepted
  point-in-time features — settled against realized official prices on common delivery days under
  an identical battery and a common perfect-foresight ceiling. `PROMPT.md` is amended the same day
  to name exogenous point-in-time inputs as in scope for forecasting.
- **Reason:** `LIMITATIONS.md` names exactly one open analytic question in the forecasting layer:
  validated weather, demand, fuel, renewable and interconnector forecasts are not included, so
  every accepted forecast figure comes from price history alone. The accepted held-out comparison
  already shows the two model families and a naive rolling mean within half a percentage point of
  capture of each other, which says the binding constraint is the *information* available to the
  models and not the function class. A third price-history model would answer nothing; a
  dashboard, a second demo or a finance layer would add no evidence and two of the three are
  already declined or excluded by dated decision.
- **What is landed today:** the design, `config/decision_cutoff.example.json`,
  `config/fundamentals_geography.example.json`, the test keeping both parseable and both refused
  as declarations, and the project-record entries. No source code, dependency, workflow or data
  source, and no accepted figure or analytical behaviour changed.
- **Controls:**
  - **The cutoff is declared, never defaulted.** A declared closure schedule in the existing
    dated-regime format and a declared decision lead in minutes are required arguments of every
    v0.9 surface where availability matters. A feature is available for delivery day D only if its
    publication instant is strictly before the cutoff; a publication at the cutoff is late. Both
    committed examples carry placeholder references and are refused as declarations, as the
    gate-closure example already is.
  - **Availability evidence is graded and the grades never merge.** `witnessed` (retrieved by this
    project before the cutoff) and `provider_declared` (a provider instant attached to that datum)
    are admissible and reported separately. `assumed` — inferred from a regulatory deadline or a
    nominal latency rather than from the datum — is quarantined and usable only in an explicitly
    labelled exploratory run that is never recorded as accepted.
  - **Leakage is ruled out by construction, not by assertion.** Every revision is stored, the
    decision-time revision is the latest published strictly before the cutoff, later revisions are
    counted and excluded, every feature value is traceable to a source document, revision and byte
    digest, and a day is complete or excluded by named cause with nothing forward-filled,
    interpolated or imputed. Realized target-day quantities are refused by name as well as by
    timestamp, so a label cannot be smuggled in through a timestamp error.
  - **Data acceptance precedes any model.** Successful retrieval is not accepted use. A dated
    acceptance document must exist before any benchmark document, and no benchmark manifest may
    declare a feature-set digest that no acceptance document names.
  - **The result is recorded whichever way it falls.** If fundamentals do not improve settled
    value, the negative result is recorded under the same labels. The cutoff, split, geography and
    feature set are never revised after seeing test results; any such revision is a new benchmark
    under a new decision entry. If accepted coverage yields fewer than one full meteorological
    season of quarter-hour common test days, the run is labelled exploratory and no general
    conclusion reaches the README.
- **Consequence:** The 2026-09-01 removal of ADMIE load and RES forecasts from scope is not
  reopened. ENTSO-E's Greek load and renewable forecasts originate from ADMIE, so taking them
  through another publisher would be that reversal by another route; they are isolated as Track B
  and require their own dated decision, the restored token and forward-witnessed acceptance, and
  no part of v0.9 depends on them. Perfect foresight remains an upper bound, forecast backtests
  remain historical research results, and the standing exclusions — intraday, balancing, reserves,
  capacity, subsidies, taxes, debt, grid feasibility and revenue stacking — are unchanged. The
  choice of data source is *not* made by this entry: the recommended primary source and its
  fallback are recommendations until the v0.9.0 spike verifies them and a further dated entry
  names the source.

## 2026-09-02 — Commit one reproducible synthetic-only demonstration report

- **Decision:** Add `greek-bess demo` and commit `docs/sample_report.html` as the sole exception
  to the rule that generated research outputs stay outside Git.
- **Reason:** The installed CLI is the portable project interface on every supported platform;
  using its existing `Command` registry avoids making a Make installation a second prerequisite
  and reduces the path from clone to a complete result to one command. The sample lets a reader
  inspect the output without an ENTSO-E token, official data or a local run.
- **Controls:** The report is built only from deterministic synthetic prices and illustrative
  assumptions, and every block retains its result label, synthetic basis and standing
  exclusions. `greek-bess demo --output docs/sample_report.html` regenerates it, and an automated
  byte-for-byte test prevents the committed artifact from drifting from current behaviour.
- **Consequence:** No official or user data, secret, investment output or unsupported evidence is
  committed. Other generated reports remain excluded from Git.

This file records decisions that materially affect interpretation or reproducibility. Add a
dated entry when a milestone changes scope, assumptions, data handling or validation.

## 2026-09-02 — Lead the repository landing page with accepted findings

- **Decision:** Present the accepted annual official-history decomposition before the README's
  limitations, then retain those limitations immediately after it; keep detailed per-command
  workflows in `docs/command_reference.md`.
- **Reason:** The landing page should state the tool's recorded research result before bounding
  its interpretation, rather than making readers traverse operating instructions to discover
  that accepted official-history evidence exists. The command catalogue obscured that result and
  made the README difficult to navigate.
- **Consequence:** Every landing-page figure carries its historical result basis, partial years
  and the resolution-change caveat. The move changes documentation structure only: perfect
  foresight remains an upper bound, forecast capture remains a historical backtest, and no figure
  becomes expected revenue, a forecast or investment evidence.

## 2026-09-02 — Solve the dispatch relaxation first where that is provably the same answer

- **Decision:** `optimize_perfect_foresight` solves the continuous relaxation of the dispatch
  program before the mixed-integer program, and returns the relaxed solution unchanged when it
  charges or discharges but never both in one interval. Otherwise it solves the mixed-integer
  program as before. The battery configuration accepts `solve_strategy`, defaulting to
  `"relaxation_first"`; `"mixed_integer"` forces the integer program.
- **Reason:** The binary operating mode is the only integer variable and it is load-bearing in
  one situation: a negative price with no headroom to charge into, where being paid to import is
  reachable only by exporting at the same time to make room, and the round trip's own losses turn
  the pair into a profit. Dropping the binary enlarges the feasible set, so the relaxed optimum
  bounds the mixed-integer optimum from above; and because both bounds already cap charge and
  discharge at their limits, a relaxed solution that never does both admits a mode value in every
  interval and is therefore mixed-integer feasible. A feasible point attaining an upper bound on
  the optimum is an optimum. This is why the shortcut is exact rather than close: it is taken
  only where it is provably the same answer, and the mixed-integer program is solved wherever it
  is not.
- **Consequence:** No result changes. On a year of quarter-hourly prices the full-horizon solve
  is 9.1x faster with no negative prices and the daily composed convention 1.6-1.7x faster, with
  margins agreeing to one floating-point unit in the last place, nine orders of magnitude inside
  the solver's own `mip_relative_gap`. A full-horizon solve over a year containing negative
  prices pays a 5% penalty for a relaxation it then rejects; the daily convention the forecast
  backtests use does not, needing the integer program on 26 of 366 days. The summary gains
  `solve_path`, `relaxation_simultaneous_interval_count` and, for daily solves,
  `mixed_integer_solve_count`, so which path produced a figure is recorded with it.

## 2026-09-02 — Normalize canonical timestamp resolution

- **Decision:** `ensure_canonical` converts all five timestamp columns to nanosecond resolution.
- **Reason:** A property-based test of the canonical CSV round trip found that a history from
  `generate_synthetic_prices` carried microseconds, because that is what `Timestamp.now` returns,
  while the same history written and read back carried nanoseconds, because that is what
  `to_datetime` parses into. The two described identical instants and compared unequal, so a
  function documented to normalize was normalizing everything about a timestamp except its
  resolution. Nanoseconds are the target because widening to them from any coarser unit is exact,
  where narrowing would silently truncate.
- **Consequence:** No recorded figure changes and no interval moves; only the dtype of the
  timestamp columns is affected. A history and its round-tripped copy now compare equal, which is
  what lets a reconciliation or a regression test compare two frames directly instead of
  comparing them column by column with dtype checks disabled.

## 2026-09-02 — Check recorded content on read, and guaranteed keys only on record

- **Decision:** `read_run_manifest` applies every check that is a property of a manifest's
  recorded content — the schema version, the closed kind registry, the basis cross-check, the
  standing-claim cross-check and the scoped distributional-term refusal. It deliberately does
  **not** apply the guaranteed-key check, which stays a record-time check; a report states an
  absent guaranteed key as not recorded instead of assuming it or refusing the manifest.
- **Reason:** The completed-v0.8 review found the two content checks running only when a
  manifest was built. A manifest travels, and a reader has only the file, so a summary declaring
  `is_probabilistic` was refused at record time yet rendered — printed directly above the
  standing exclusion "not a probability-calibrated estimate". Neither check can refuse a
  manifest this project recorded, because building one already applied both, so moving them to
  the doorway costs nothing and closes the gap. The guaranteed-key check is different in kind: it
  is a promise about what a producing module recorded at the time it recorded it, and the
  2026-09-01 amendment relies on it staying a record-time check so an ensemble manifest written
  before `path_ranges` existed still verifies and still renders.
- **Consequence:** v0.8.3 corrections. The manifest envelope, `schema_version`, renderer version,
  report format and index fields are unchanged, and no recorded figure changes value. A manifest
  that was hand-edited, truncated or produced elsewhere is now refused at the doorway with the
  contract's own error rather than rendered or crashing the renderer.

## 2026-09-01 — Decline an interactive viewer and complete v0.8 with the static renderer

- **Decision:** Do not add Streamlit or another local interactive viewer in v0.8. The indexed,
  self-contained static report is the completed research interface. Any future interactive
  proposal must identify a need the static report cannot meet, define whether approved scope
  changes, and proceed as its own dated decision and milestone.
- **Reason:** A viewer creates no new evidence. Controls that compute, filter into derived
  results, open manifest-declared files or combine manifests would violate the approved design;
  controls that do none of those things only duplicate navigation already supplied by the report
  index and stable links. That duplication would still add a runtime dependency, server
  lifecycle and second rendering surface on which manifest verification, adjacent labels, basis
  separation and all export refusals would have to remain aligned.
- **Consequence:** v0.8.2 is a decision-only release with no runtime or rendering-behaviour
  change, and v0.8 is complete. The project keeps one deterministic presentation surface that
  works offline and in CI. Interactivity is neither prohibited forever nor carried as hidden
  unfinished scope; it requires independently approved evidence of need.

## 2026-09-01 — Record the ensemble's per-path ranges in its summary, rather than reading its CSV

- **Decision:** Extend the scenario-ensemble run summary with `path_ranges`, a per-path
  projection of the range table the module already reduces, and promote `scenarios`,
  `equivalent_basis`, `path_count` and `path_ranges` to guaranteed summary keys of the
  `scenario_ensemble_range` result kind. The report renderer reads them from the manifest like
  every other figure. The renderer is **not** given permission to open `report-scenario-ensemble`'s
  ranges CSV, or any other file a run wrote.
- **Reason:** v0.8.1 requires a scenario ensemble to be presented side by side with its per-path
  ranges. Those ranges lived only in the CSV; the summary carried the scenario list, the
  equivalent basis, the path count and four extreme aggregates. That left exactly two honest
  routes, because "a report renders verified manifests, and only verified manifests" is the
  sentence the whole layer rests on and reading the CSV would break it. The first route is to
  render only the aggregates and say so. The second is to record the ranges where a report can
  legitimately see them. The first was rejected: a report showing the widest and narrowest path
  spread but not the ranges themselves sends a reader back to a spreadsheet to see the evidence,
  which is the exact failure mode the reporting layer exists to remove — and a figure read out of
  a CSV by hand arrives stripped of the label the manifest carries. The second costs a recorded
  decision and nothing else. Recording is not computing: the rows are a projection of the same
  frame the CSV is written from, taken in the same order, with no value rounded, converted or
  re-reduced, and a test asserts each recorded cell equals the frame's cell. The producing module
  stays the one source of truth for its own numbers, which is what the contract has always
  required.
- **Consequence:** An ensemble manifest is larger, growing with the path count. That is bounded
  by the `path_count` the ensemble already declares and is the accepted price of the ranges being
  renderable at all. Per-scenario provenance — transformation, availability, source era, input
  run — is recorded once under `scenarios` and joined by scenario name rather than repeated on
  every path row, so the manifest grows with the paths and not with the paths times the fields;
  the CSV keeps the fully repeated per-row form and is unchanged. Because the guarantee is
  checked when a manifest is built and not when one is read, an ensemble manifest recorded before
  this decision still verifies and still renders; the report states plainly that it records no
  per-path ranges rather than filling them in, and a test pins that. The contract's
  distributional-term check now reaches nested key names for the kinds that declare it, because a
  report renders a nested key as a visible column heading and a top-level scan would clear a
  table whose headings claim a percentile.

## 2026-09-01 — The index across manifests carries no figure

- **Decision:** The multi-manifest index names each manifest by ID, result kind, recorded label,
  producing command, recorded time and digest, groups the rows by basis, links to the block that
  holds the figures, and names the bases the report does not cover. It carries no numeric figure
  of any kind. Composition across manifests is layout only: no value is computed, totalled,
  ranked or carried from one manifest into a row with another.
- **Reason:** A multi-manifest report creates exactly one temptation the single-manifest report
  did not — a summary table spanning the whole document. That table is the first place a
  perfect-foresight ceiling would sit in a column beside a settled backtest and a synthetic
  scenario range, and the second step, adding or differencing them, is a short one that produces
  a number whose basis is none of the five the contract defines. Keeping every figure inside its
  own manifest's block, beside its label, is what makes that step impossible rather than
  discouraged. Naming the absent bases follows from the same reasoning in reverse: a reader
  cannot otherwise tell a basis this report does not cover from a question the project cannot
  answer.
- **Consequence:** A reader who wants to compare a ceiling with a scenario range must read two
  labelled blocks and do it themselves, knowing what each one is. That is the intended cost. The
  rule is executable: a test asserts every cell of the index is one of the manifest's identity,
  label or provenance fields, so a figure cannot appear there even by accident.

## 2026-09-01 — Scope the renderer's distributional-term check to what the renderer says

- **Decision:** In `greek_bess.reporting.render`, apply `FORBIDDEN_REPORT_TERMS` to the headings
  and captions the renderer itself emits for a block whose kind declares
  `forbids_distributional_terms`, and exempt text carried verbatim from the manifest — the
  `result_label`, the standing exclusions and the recorded values.
- **Reason:** The design requires the three standing exclusions beside every figure, and two of
  them read "not a probability-calibrated estimate" and "not expected or forecast investment
  revenue". Both contain terms on the list. A blanket scan of rendered text would therefore
  refuse to render a scenario-ensemble figure precisely because it carries the disclaimer that
  makes the figure safe to read, which is the opposite of what the check is for. The manifest's
  own summary keys need no second check: the contract cleared them for that kind when the
  manifest was built. So the renderer checks what the renderer adds, and inherits the rest.
- **Consequence:** The exemption is pinned by two tests rather than left as a comment — one
  asserts a renderer caption reading "Expected value" refuses the render, and one asserts the
  standing exclusions survive intact beside an ensemble block after first asserting that those
  exclusions do contain exactly `expected` and `probability`. A future reader who meets the
  exemption meets its reason with it.

## 2026-09-01 — Identify a rendered manifest by digest, never by its path

- **Decision:** The report index names each rendered manifest by its `manifest_id` and the
  SHA-256 digest of the exact bytes read, and records no filesystem path. Two inputs declaring
  one `manifest_id` are refused rather than rendered as two entries.
- **Reason:** An export is the artifact most likely to travel beyond a reader who knows this
  project's limits, and a local path names the operator's machine rather than the evidence. The
  digest is what makes a report auditable back to the exact manifests behind it; the path is
  what leaks. Refusing a repeated ID follows the same reasoning from the other side: an ID names
  one recorded run, so a report listing it twice would present one run as two.
- **Consequence:** A report is reproducible from the digests it records, and the index is
  comparable across machines. Rendering the same run twice is an error to fix at the call site,
  not a duplicate to deduplicate silently.

## 2026-09-01 — Render recorded values exactly as recorded

- **Decision:** The renderer formats a recorded value as the JSON it was recorded as. No display
  rounding, unit conversion, thousands grouping or currency formatting is applied, and manifests
  are ordered by basis, then kind, then manifest ID rather than by input order.
- **Reason:** Each of those conveniences is a transformation, and the one thing this layer
  promises is that it transforms nothing. A rounded figure in an export is a different figure
  from the one the validated module recorded, and a reader has no way to tell which they are
  holding. Declared ordering, likewise, is what makes identical inputs produce byte-identical
  documents regardless of the order a caller happened to pass them.
- **Consequence:** Reports are less typographically polished than a formatting layer would make
  them, and deliberately so. Determinism is testable: a test renders every kind in the registry
  in both directions and compares the documents. The only timestamp the renderer adds is
  `rendered_at_utc`, and it lives in the index so the document itself stays comparable.

## 2026-09-01 — Open v0.8 by user approval: render verified manifests, and only verified manifests

- **Decision:** Open v0.8, the research interface and exportable reports, on the user's explicit
  instruction of 1 September 2026, which is the approval the 2026-08-31 gate required. Amend the
  approved scope in `PROMPT.md` accordingly, adopt `docs/v0.8_design.md` as the design of record,
  and answer the three questions the gate posed: the landing state with no judgmental input
  declared is the declaration checklist itself, never a result or a demo with implied defaults;
  every rendered figure carries its manifest's `result_label`, its basis in reader-facing words
  and the standing exclusions adjacent to the figure, read from the manifest and never
  re-declared; and an export refuses to contain any figure not reachable from a verified
  manifest, any interval-level official price series, distributional vocabulary where the kind
  forbids it, any unlabeled figure, and any value computed across manifests or across bases.
- **Reason:** The completed-v0.7 review found the domain APIs interface-ready once a versioned
  run manifest and report contract existed, and that contract landed as v0.7.11. The manifest is
  therefore the sole doorway into a report: everything the contract enforces — the closed kind
  registry, the basis discriminator, executable label retention, the scoped distributional-term
  refusal — is inherited by the presentation layer rather than restated by it, which is what
  keeps a rendering surface from becoming a second place where interpretation rules must be
  maintained. The core renderer is a deterministic CLI producing self-contained static files
  with no new runtime dependency, because exportable evidence is what the 2026-08-27
  repositioning as a replay and research benchmark actually needs; the `streamlit-dashboard`
  label in the suggested branch sequence predates that repositioning.
- **Consequence:** v0.8 proceeds as three milestones — v0.8.0 report rendering foundation,
  v0.8.1 multi-run composition, v0.8.2 a separate dated decision on any interactive viewer —
  each one reviewable PR through the unchanged four gates. The package version stays at 0.7.11
  until v0.8.0 merges. A report computes nothing: composition across manifests is layout only,
  and figures of different bases are never merged into one row, total or derived value. Exports
  remain generated research outputs and stay outside Git. AI-generated explanations remain
  outside v0.8 entirely. Changing the design of record requires a further dated decision entry.

## 2026-09-01 — Automate custody encryption and upload to an operator-held recipient

- **Decision:** Add a `Publish encrypted custody copies` workflow that encrypts accepted official
  artifacts to an operator-supplied age recipient and attaches the ciphertext to a private
  release. This reverses the recorded exclusion that "the procedure does not automate the
  upload". Generating the key pair, holding the private half and keeping a second copy under
  separate control remain the operator's.
- **Reason:** The exclusion was written to keep decryption capability out of this repository, and
  that concern is fully preserved: an age recipient is a public key, so the automation can
  encrypt and cannot decrypt. What the exclusion also did, unintentionally, was put six manual
  steps between an expiring artifact and a durable copy, and the reconciliation artifact reached
  within two days of expiry with none of them performed. A procedure that is correct but unused
  preserves nothing. Reducing the operator's part to one `age-keygen` and one public key removes
  the reason it kept not happening.
- **Consequence:** The recipient is a dispatch input rather than a secret, both because it is not
  secret and so the run record shows which key a copy was encrypted to. Two refusals are
  deliberate: a value beginning `AGE-SECRET-KEY-` is rejected with instructions to rotate, and an
  artifact that does not verify against its committed custody record is never encrypted, because
  durably preserving the wrong bytes under a name that claims otherwise is worse than preserving
  nothing. The manual procedure remains documented and is the fallback. Custody is still not
  complete on the repository record: nothing here reads live release state, and the second copy
  is outside this repository's knowledge.

## 2026-09-01 — Remove ADMIE load and RES forecasts from scope

- **Decision:** ADMIE load and RES forecasts are **out of scope**. The 2026-08-26 quarantine is
  closed as **never accepted**: no ADMIE field entered forecasting, none ever will under the
  current brief, and the quarantine label is retired rather than discharged. The retrieval client,
  the publication-timing audit, the gate-closure format, their tests and their workflow are all
  **kept and documented as unused**, pending a future declaration that would reopen the question.
  Nothing carrying evidence is deleted.
- **Reason:** The quarantine had two recorded exits and had been open since 26 August. One exit
  required an operator declaration of the day-ahead gate closure, with rulebook section and
  effective dates, that the repository is deliberately built to refuse to supply; then a
  contemporaneous audited window, since witnessed evidence accumulates one delivery day at a time;
  then file-format acceptance; then a further recorded decision. The other exit was this entry.
  Between 28 and 31 August the repository added roughly 3,100 lines of source, 3,000 of tests and
  2,600 of documentation around the quarantine and retired none of it, because every one of those
  additions sat behind the same missing declaration. That is the pattern `PLAN.md` already names:
  work that cannot retire the item it surrounds is not progress toward acceptance.
  `PROMPT.md` mentions ADMIE nowhere — the approved data scope is HEnEx and ENTSO-E prices — so
  ADMIE forecasts were an extension the project took on itself, and removing them narrows the
  project back to its brief rather than amending it. The price-history ML benchmark already stands
  without them.
- **Consequence:** No exogenous ADMIE variable may enter any forecast, feature set, dispatch plan
  or reported result. This removes a *candidate input* and changes no accepted figure: no ADMIE
  data was ever parsed, so every recorded ceiling, backtest, capture ratio and scenario is
  unaffected. Forecasting continues to use causal price-history features only.
  The retained code is not dead weight to be pruned on sight — it is the executable form of a
  refusal, and `list-admie-filetypes`, `fetch-admie-files` and `audit-admie-publication-timing`
  remain runnable so a future declaration can be tested without rebuilding them. Reversing this
  entry requires the same operator declaration the quarantine always needed, plus a new dated
  decision. The 2026-08-31 filetype acceptance and the timing-audit policy keep their evidentiary
  value as records of what was established, which was names and non-empty discovery only.

## 2026-09-01 — Re-record the history custody record against the replacement artifact

- **Decision:** Replace `docs/custody/greek-dam-official-history.json` so that it fingerprints run
  `33483975614` instead of the expiring run `32971677163`, and point the
  `Record official artifact custody` workflow's `history_run_id` and `history_digest` defaults at
  the same run. Add a `record_mode` input so that a deliberate re-record is an explicit request
  rather than something provoked by deleting the committed record.
- **Reason:** A custody record exists so that a future copy can be proven to be the accepted
  artifact. Once run `32971677163` expires on 2 September 2026, no obtainable copy can match its
  per-file digests, so every verification would return exit code 2 on the four lines the earlier
  2026-09-01 entry already explained. A record that cannot verify against any obtainable artifact
  does not preserve evidence; it trains readers to wave through the exit code that exists to stop
  them, which is precisely the habit the custody procedure was written to prevent. The
  replacement is safe to adopt because the finding established positively that the data is
  unchanged: both `price_series_sha256` values, every content fingerprint, both `*.quality.json`
  digests and every recorded file size are identical.
- **Consequence:** The new record was **generated by the tooling in `record` mode** (run
  `33489920268`) and committed as emitted, never edited by hand. Against the superseded record it
  differs only in `source_run_id`, `published_artifact_digest_sha256`, `recorded_at_utc` and the
  four per-file digests; every content fingerprint is unchanged. The superseded record remains in
  Git history as the fingerprint of the originally accepted artifact, so the earlier acceptance is
  still provable. `record_mode` never writes to `docs/custody/`, so replacing a record stays a
  reviewed commit plus a decision entry. This decides nothing about the third option the finding
  listed — separating provenance columns from data in what a record compares — which remains
  available if re-recording after every retrieval proves burdensome. The reconciliation record was
  regenerated in the same run and matched in all five per-file digests, so it is unchanged.

## 2026-09-01 — Record the replacement retrieval as a finding, and keep the custody record

- **Decision:** Replace the expiring official-history artifact by re-running
  `Fetch official Greek market history` with the inputs that produced the accepted baseline
  (run `33483975614`, expiring 30 November 2026), record the verification result as a finding,
  and **do not replace `docs/custody/greek-dam-official-history.json`**. Add the faithful
  re-retrieval to the custody failure taxonomy as case 4, and state that per-file digests are
  not diagnostic for a re-retrieval.
- **Reason:** Verification run `33484823956` reported four differences, all of them per-file
  byte digests, with no content fingerprint differing: both `price_series_sha256` values match,
  as do interval counts, first and last interval, market-day counts, negative, zero and missing
  price counts and quality-flag counts, and no file changed size. The price series is unchanged
  interval for interval. The differences are fully explained by `retrieved_at_utc` being a
  canonical column and by retrieval timestamps in the manifests, so they would recur on any
  re-retrieval of identical data. Normalization did not change either: the only data-layer edit
  since the accepted run is a behaviour-preserving `pd.Timedelta` call. The taxonomy as written
  described only a corrupted copy, a revised publication and a normalization change, all three
  tested by per-file digests, so it would have led a reader to classify this as a possible
  provider revision.
- **Consequence:** The accepted history is unchanged and no accepted figure is revised. The
  committed record still fingerprinted run `32971677163` when this entry was written, and whether
  to re-record was deliberately left open; that question is settled by the entry above. Evidence
  in `docs/official_history_replacement_2026-09-01.md`.

## 2026-09-01 — Plan by what an open item waits on, not by milestone number

- **Decision:** Reorganise `PLAN.md` around the input each open item is missing. The approved
  `PROMPT.md` scope is recorded as implemented; the five remaining items are recorded as waiting
  on a replacement retrieval, on an operator declaration, or on a scope decision by the user. No
  further audit, policy or refusal is added around an item that is already blocked on a missing
  declaration.
- **Reason:** Between 28 and 31 August the repository added roughly 3,100 lines of source, 3,000
  lines of tests and 2,600 lines of documentation and retired none of the five open items: four
  were already blocked before that work began, and the fifth, an artifact expiry, was not being
  tracked at all. The milestone numbering concealed this,
  because every blocked item still had adjacent buildable machinery. Work that cannot retire the
  item it surrounds is not progress toward acceptance, and the plan should say so.
- **Consequence:** This entry records the shape of the remaining work. It decides nothing about
  the ADMIE forecast quarantine, which still has two recorded exits — an operator-declared gate
  closure worked through to timing and format acceptance, or removal from scope by a further
  recorded decision — and it does not open v0.8 or amend the approved scope. It also records the
  operating constraint that live market endpoints are reachable only from GitHub Actions
  runners, so every live acceptance step is a workflow dispatch.

## 2026-08-31 — Use the live-retrievable ISP1 and ISP2 day-ahead forecast filetypes

- **Decision:** Declare `ISP1DayAheadLoadForecast`, `ISP1DayAheadRESForecast`,
  `ISP2DayAheadLoadForecast` and `ISP2DayAheadRESForecast` as the leakage-relevant ADMIE
  filetypes. Remove `DayAheadLoadForecast` and `DayAheadRESForecast` from that declaration while
  retaining the recorded finding that the live catalog recognizes them.
- **Reason:** The 74-entry live English catalog labels the DAM pair and both ISP pairs as daily
  day-ahead forecasts. Over delivery days 26-28 August 2026, however, the DAM pair returned no
  files, ISP1 returned six load and six RES files, and ISP2 returned three load and three RES
  files. Leakage controls and audit defaults must follow retrievable publications rather than
  catalog membership alone.
- **Consequence:** Retrieval and the timing workflow target the confirmed ISP1/ISP2 pairs. This
  decision accepts names and non-empty discovery only. It neither declares the auction gate
  closure nor accepts publication timing or file formats, and it does not lift the 2026-08-26
  forecast-feature quarantine.

## 2026-08-31 — Define a versioned run manifest before any presentation layer

- **Decision:** Introduce `greek_bess.reporting`, a versioned run manifest and report contract,
  as a standalone milestone rather than as part of a v0.8 interface. A manifest carries the
  producing module's summary verbatim and adds a stable projection: a `result_kind` from a closed
  registry, the `basis` that kind reports on, the required non-empty `result_label`, the caller's
  declared identifiers and inputs, and the project's standing exclusions. `schema_version` is
  checked on read and a newer contract is refused rather than reinterpreted.
- **Reason:** The completed-v0.7 review named this as the prerequisite for any future interface,
  and it is worth doing whether or not one is ever built. Sixteen modules emit summaries across
  twenty-seven commands, and before this exactly one artifact carried a schema version. More
  importantly, `PROMPT.md` requires outputs to retain their source and limitation labels through
  downstream analysis; fifteen of sixteen modules kept that convention and nothing enforced it.
  A consumer could drop the label and no check would notice.
- **Consequence:** The contract adds no interface, exporter, rendering surface or dependency, and
  does not open v0.8. The label is carried from the summary rather than re-declared in the
  registry, so the two cannot drift. `audit-admie-publication-timing` gained the `result_label` it
  was missing; no other module changed.

## 2026-08-31 — Scope the distributional-term check to the kinds that declare it

- **Decision:** Apply `FORBIDDEN_REPORT_TERMS` in the report contract only to result kinds
  declaring `forbids_distributional_terms` — today `scenario_ensemble_range` alone, matching the
  ensemble's existing behaviour exactly — rather than to every manifest. Where a summary declares
  `is_probabilistic`, `is_forecast` or `is_investment_evidence`, cross-check it and refuse any
  value but false.
- **Reason:** The term list bans claims about the distribution of **outcomes**, not the words
  themselves. The perfect-foresight optimizer's own summary reports
  `average_charge_price_eur_per_mwh`, a settled input price; a forecast benchmark reports a mean
  absolute error, an accuracy statistic about a model; the publication-timing audit reports a
  median lead time, a statistic about a publisher. A blanket ban would refuse all three. A check
  that refuses honest arithmetic teaches its readers to route around it, which is worse than no
  check.
- **Consequence:** A regression test asserts that a genuine optimizer summary carries such a
  term, so the reason for the scoping stays visible rather than being tidied away later. A kind
  that should forbid the terms declares it explicitly when it is added.

## 2026-08-31 — Make ADMIE pre-auction timing an executable audit with a declared closure

- **Decision:** Discharge the 2026-08-26 ADMIE quarantine through an audit rather than a
  judgment. `audit-admie-publication-timing` reads ADMIE retrieval manifests and reports, per
  filetype and delivery day, whether a file was published strictly before that day's day-ahead
  gate closure. The closure is declared as one or more dated regimes, each naming its clock and
  carrying a required reference to the market rule it comes from; there is no default and no
  built-in constant. A publication exactly at the closure counts as late. A delivery day earlier
  than the first declared regime, and a closure falling in a daylight-saving gap or repetition,
  are refused rather than resolved by a convention. No forecast file is parsed.
- **Reason:** The quarantine label `requires_pre_auction_timing_validation` was an assertion no
  code could turn into a pass or a fail, so the exclusion depended on nobody forgetting it. A
  built-in closure constant would have replaced that with a worse failure: a hard-coded rule is
  invisible in the evidence, cannot express a rule change across a history starting in November
  2020, and would make an unverified assumption look like a validated one. The repository can
  compare a file's timestamp against a declared rule; it cannot verify the rule, and it says so
  instead of pretending otherwise.
- **Consequence:** `config/admie_gate_closure.example.json` ships the format with a placeholder
  reference that must be replaced before use. The `Audit ADMIE publication timing` workflow
  produces the evidence, and retrieval for it must pass `--all-revisions`, because the default
  latest-revision selection discards exactly the post-closure revisions the audit reports.

## 2026-08-31 — Grade publication evidence and never promote asserted to witnessed

- **Decision:** Record two distinct grades of pre-closure evidence. A retrieval performed before
  the closure of the delivery day in question witnesses availability contemporaneously
  (`witnessed_pre_gate`); a publication timestamp read after the closure only asserts it
  (`asserted_pre_gate`). Both count as accepted for timing, both are reported separately on every
  observation and in the run summary, and the weaker is never presented as the stronger. A day no
  supplied record covers is reported as `no_record` rather than assumed compliant. One ADMIE URL
  carrying two different digests across manifests is refused as an in-place replacement, and one
  carrying two different publication timestamps as a restated publication time.
- **Reason:** `file_published` is provider metadata read at retrieval time — what ADMIE says today
  about the past, not an observation of when the file became reachable. A restated timestamp, a
  site migration or a silent replacement would be believed. Collapsing both grades into one
  "passed" would state an independence the evidence does not have.
- **Consequence:** The audit is worth running before a delivery day as well as over history:
  historical runs establish asserted compliance in one pass, and each pre-closure run adds one
  witnessed day that no retrospective query can produce.

## 2026-08-31 — Name the decision-time revision and keep the quarantine closed

- **Decision:** For every accepted delivery day, name the latest revision published strictly
  before closure as the decision-time revision, with its URL, publication time and lead, and
  count the revisions that superseded it after closure. Timing acceptance does not lift the
  forecast-feature quarantine: lifting it additionally requires file-format acceptance against
  real files and a separate recorded decision. The audit summary carries this exclusion in its
  own output (`establishes_only_publication_timing`, `does_not_establish`, `quarantine_lifted`).
- **Reason:** A day can pass on timing and still leak. Reading "the published file" for a past
  delivery day ordinarily returns the provider's latest revision, which is post-decision
  information. And a proof about timing is not a proof about content: the file's format, units
  and meaning are untested by this audit, so treating a timing pass as clearance would smuggle an
  unvalidated variable into a forecast on the strength of an unrelated check.
- **Consequence:** A future feature built from these files must read the decision-time revision by
  URL. `PLAN.md` keeps the ADMIE acceptance item open, with the operator's declared schedule, a
  live audited window and format acceptance named as the outstanding parts.

## 2026-08-31 — Close the completed-v0.7 review without changing the model

- **Decision:** Accept the completed-v0.7 consistency review with no correctness or
  data-integrity defect. Reconcile the one contradictory roadmap sentence so it matches the
  existing implemented contract: battery parameters, terminal-energy constraint, selected
  source era and path identity form the equivalent basis; differing declared availability
  schedules are scenario judgments carried as provenance, while an unrecorded availability
  assumption is refused. Keep v0.8 closed until its design receives explicit user approval.
- **Reason:** The public API, CLI, provenance, summaries, methodology, limitations and tests
  consistently implement the amended same-day availability decision below. Only `PLAN.md`
  retained the superseded wording. Treating it as authoritative would make a future interface
  refuse the intended declared-outage-versus-baseline comparison even though the core correctly
  supports and audits it.
- **Consequence:** No dispatch, forecast, stress, degradation, finance or data behavior changes.
  A metadata regression keeps the roadmap aligned with the tested ensemble contract. The formal
  review is recorded in `docs/history/implementation_report_v0.7_review.md`; no v0.8 branch, dependency,
  stub or implementation is authorized by this decision.

## 2026-08-31 — Define negative-price events as declared interval replacements

- **Decision:** A negative-price event is a sequence of whole market intervals selected by a
  required inclusive UTC start and exclusive UTC end and assigned one required strictly negative
  replacement price in EUR/MWh on every bootstrap path. The event ID, both boundaries, depth and
  transformation ID have no defaults; the event list itself is required, and `[]` is the exact
  identity. Windows must align to interval edges, cover at least one interval and not overlap.
  Event occurrence is declared, never sampled, inferred, fitted, ranked, threshold-searched or
  expressed as a frequency, rate, likelihood, probability, percentile or expected count.
- **Reason:** The whole delivery interval is the smallest price unit the validated path actually
  contains, so an interval-aligned inclusive-start/exclusive-end window states exactly which
  settlement prices change without inventing sub-interval prices. An absolute negative EUR/MWh
  replacement makes depth inspectable and ensures the declared event is in fact negative. A
  sampled occurrence would be the same uncalibrated probability claim rejected for percentiles
  on 2026-08-27 and for outages on 2026-08-31. Replacing only named windows is also analytically
  distinct from adding one constant to the full horizon or scaling every deviation around a
  daily reference.
- **Consequence:** Partial, overlapping or empty-on-input windows and non-negative depths are
  refused rather than rounded, prorated or ignored. Existing zero and negative prices outside
  named windows remain unchanged and no result is clipped or floored. One-to-one provenance
  includes untouched intervals, while the summary reports negative counts before and after.
  This completes the approved v0.7 modeling scope; v0.8 remains gated on review of completed
  v0.7.

## 2026-08-31 — Declare outages, never sample them

- **Decision:** Represent availability as a declared schedule: a baseline available fraction
  with no default, plus zero or more declared windows, each with its own available fraction in
  [0, 1]. Timing, duration and depth are judgmental scenario inputs. No forced-outage rate, no
  sampled failure times, no availability distribution and no expected unavailability. A window
  is applied whole to every interval it covers; a boundary falling strictly inside an interval
  is refused, naming the interval, rather than prorated or rounded. Overlapping windows, a
  window covering no dispatched interval, and a configuration field such as
  `forced_outage_rate` are all refused by name.
- **Reason:** A sampled outage is a probability statement, and the 2026-08-27 entry already
  settled that this project does not make those without an independently validated calibration.
  Nothing calibrates a forced-outage rate here: there is no operating history for a Greek
  merchant battery, no fleet maintenance record and no warranty claim series in scope, so a rate
  would be a number borrowed from another asset class and dressed as evidence. A declared window
  is honest about being a judgment. The boundary refusal follows the same principle one level
  down: prorating a half-covered interval would apply a schedule finer than the one declared, and
  rounding it would apply a different one, so the only truthful options are to refuse or to make
  the caller state an aligned boundary.
- **Consequence:** An outage scenario is as informative as the placement the caller chose, and no
  more. The model gives no help choosing when the outage falls, which is recorded in
  `LIMITATIONS.md`: the same outage costs almost nothing in a low-spread week and a great deal in
  a high-spread one. A schedule with no windows is legitimate and is the declared
  full-availability scenario, which is preferable to an implied one. Because dispatch has perfect
  foresight, it positions the battery for a declared outage, so the reported margin stays an
  upper bound and is a weaker bound for unplanned outages than for planned maintenance.

## 2026-08-31 — The equivalent basis is the asset, not the scenario

- **Decision:** Narrow the scenario-ensemble equivalent-basis check introduced on 2026-08-31 so
  that it covers battery parameters, the terminal-energy constraint, the source-era selection and
  the path identities, and no longer covers the availability assumption. Availability joins the
  price transformation as a declared scenario input, carried as provenance on every margin row,
  on both ends of every range row and in the per-scenario summary. An unrecorded availability
  assumption is still refused.
- **Reason:** The earlier rule was too strong and would have made the availability milestone
  unusable: an ensemble that refuses a differing availability schedule can never place a declared
  outage against a baseline, which is the only comparison an outage scenario exists to make. The
  standing invariant in `AGENTS.md` is about comparing *strategies* under equal constraints, so
  the honest line is between the asset and what is done to it. Battery parameters, the
  terminal-energy constraint, the source era and the path identities describe the asset and the
  sample and must match; the price transformation and the availability schedule describe the
  judgment being examined and are expected to differ. Keeping availability in the basis and
  adding an opt-out flag was rejected: an escape hatch that callers learn to pass erodes the
  invariant faster than a clearly drawn line.
- **Consequence:** A range across a baseline and a declared outage is now reportable, and reads
  as what it is — the cost of that declared outage on those sampled paths, under one unchanged
  battery. The information is not lost from the record: availability is more visible as
  provenance than it was as a basis field, because it now appears on every reported row rather
  than once per ensemble. The forbidden-term guard extends over the new keys automatically, since
  it walks nested summary keys, so the declaration vocabulary is deliberately plain.

## 2026-08-31 — Report scenario ranges as judgments, and refuse an unequal basis

- **Decision:** Report the minimum, maximum and spread of margin outcomes across scenarios the
  caller names, and label the result non-probabilistic in the output rather than only in prose.
  No probability, percentile, likelihood, expected value, loss metric, ranking or central case is
  produced, including no mean or median across scenarios or across bootstrap paths. The exclusion
  is enforced in code: `greek_bess.stress.FORBIDDEN_REPORT_TERMS` is checked against every emitted
  column name and summary key, and a match raises instead of being written. Every scenario is
  named by the caller; there is no default scenario set and no implicit baseline, so an
  untransformed replay is declared as a member like any other and an ensemble of fewer than two
  scenarios is refused.
- **Reason:** A range across named scenarios is a range across judgments, not a draw from a
  distribution. The scenarios carry no weights and nothing calibrates them: the 2026-08-27 entry
  removed percentiles and loss probabilities because uniform block resampling of a non-stationary
  2020-2026 history supports no calibrated probability interpretation, and that reasoning applies
  unchanged to an expected value, a central case or a ranking built from the same paths. A prose
  disclaimer beside a field named `p50` loses; a report that cannot emit the field does not. An
  implicit baseline would be the same failure in a different place — a scenario the reader never
  chose, presented as the reference the others deviate from.
- **Consequence:** Ensembles are supplied explicitly and read as bounded sets of judgments. The
  summary's ensemble-wide figures are the lowest and highest margin with the scenario and path
  that attained each, and the widest and narrowest per-path spread; none of them is a central
  case. Adding or removing a scenario changes the range without new evidence, which is a property
  of the method and is recorded in `LIMITATIONS.md`. A future probability layer would need an
  independently validated calibration methodology and its own decision entry, and would have to
  amend the forbidden-term list deliberately rather than by accident.

## 2026-08-31 — Combine scenarios only on an equivalent basis, and name the mismatch

- **Decision:** Refuse to report a range across scenarios that were not solved on the same basis.
  Battery parameters, the terminal-energy constraint, the availability assumption, the selected
  source era and the path identities must match across the ensemble, and a difference raises with
  the mismatching basis named and both values shown. The terminal-energy constraint is checked
  separately from the rest of the battery configuration, with the derived terminal energy in MWh
  recorded, so a scenario differing only in day-end energy is refused by that name. A scenario
  whose recorded dispatch summary carries no battery configuration, or whose bootstrap summary
  carries no selected source era, is refused rather than admitted on partial evidence.
- **Reason:** `AGENTS.md` holds it as a standing invariant that strategies are compared only under
  equivalent physical and terminal-energy constraints. A range is a comparison. Taking one across
  two different batteries, two different day-end energy constraints or two different source eras
  reports a modelling difference as if it were a scenario difference, and the wider the resulting
  range the more convincing the artifact looks. Approximating over the difference — rescaling by
  capacity, aligning path counts, blending eras — would manufacture the comparability the inputs
  do not have.
- **Consequence:** An ensemble is only as wide as its equivalent members, and building one across
  bases is a deliberate act of re-running the scenarios on a common basis rather than a flag. The
  refusal names what differs, so the operator can see which run to redo. Path identity, not only
  path count, must match: two scenarios with two paths each but different `path_id` values are
  different sampled paths and are refused.
- **Amended the same day** by "The equivalent basis is the asset, not the scenario": the
  availability assumption was removed from the basis and became declared scenario provenance.
  The rest of this entry stands. The entry is kept rather than rewritten, because the reasoning
  that put availability in the basis is the reasoning the amendment had to answer.

## 2026-08-28 — Fail on warnings this project emits, report the rest

- **Decision:** Build pandas timedeltas from numeric values with an explicit unit, and configure
  pytest to promote to errors only those warnings attributed to `greek_bess` or to the project's
  own test modules. A warning attributed to a dependency is reported in the pytest summary and
  does not fail the run. A third-party warning that must fail is added to `filterwarnings` by
  category and module with a recorded reason; there are none today.
- **Reason:** The full suite passed while emitting copies of a NumPy generic-unit timedelta
  deprecation that pandas surfaces at the constructing line. That deprecation is the project's to
  fix, and the fix is a clearer call site. The scope of the gate is a separate question from the
  fix: `[project].dependencies` declares version ranges and CI resolves them at install time, so a
  blanket `error` policy would let an unrelated upstream release turn validation red with no
  change in this repository — which is how this deprecation arrived in the first place. Attributing
  a failure to the party that can act on it is the point of the gate.
- **Consequence:** A warning raised through project code fails locally and in CI, including the
  deprecation above: the narrowed filter still catches it, because pandas attributes it to the
  calling module. A dependency's own warnings remain visible without failing the run, so upgrading
  a dependency is a reviewed decision rather than an unscheduled CI break. This does not settle
  whether any particular future dependency warning should fail; that is decided case by case and
  recorded here.

## 2026-08-28 — Compress spread about a declared daily reference, with no default basis

- **Decision:** Represent cannibalisation pressure as a deterministic compression of within-day
  spread about a declared daily reference level: `compressed = reference + factor * (price -
  reference)`, where the reference is that path's CET/CEST market day. The compression factor is
  bounded to [0, 1] and the reference basis (`daily_mean` or `daily_median`) is declared with no
  default, matching the source-era precedent. Zero and negative results are preserved and never
  clipped, and the number of intervals whose sign changes is reported. Spread widening — a factor
  above 1 — is out of scope.
- **Reason:** Spread, not level, is what a battery earns from. The 2026-08-27 price-level shock
  changes arbitrage economics only through round-trip losses and per-MWh fees, which makes it a
  near-inert stress; compressing the spread changes the quantity being arbitraged. The
  per-delivery-year decomposition supplied the evidence directly: 2026 shows the highest ceiling
  per market day of any non-crisis year (EUR 14,431) on the lowest mean price since 2020, because
  mean daily range rose every year since 2023 while mean price fell. A causal cannibalisation
  model is not buildable from this history — it predates operating battery competition almost
  entirely, so no competitive response is estimable from it — which is exactly why the factor is
  a declared scenario rather than a fitted parameter. The reference basis gets no default because
  it decides whether the transformation is a pure spread change (daily mean preserves the daily
  mean) or also moves the level (daily median does not), and defaulting would settle that
  silently.
- **Consequence:** Every within-day range is scaled by exactly the factor, which is a testable
  property rather than an approximate intent. A daily-mean basis leaves each daily mean
  unchanged, so level and spread sensitivities stay separable and can be reasoned about
  independently. Compression can pull an interval across zero and change its sign; that is a
  real consequence of the transformation and is counted in the summary rather than suppressed,
  because a scenario that materially changes the count of negative intervals is changing the
  market's character and not only its spread. Missing prices are refused explicitly, since one
  would propagate through its market day's reference level and corrupt every interval of that
  day. No probability, percentile, loss metric or ranking attaches to a factor.

## 2026-08-28 — Keep the repository record contributor-neutral

- **Decision:** Repository content carries no tool or assistant attribution. No commit message,
  pull request title or body, issue, code comment, document or tracked configuration file
  records which editor, generator or assistant produced a draft: no `Co-Authored-By` trailer
  naming a tool, no session or transcript link, no "generated by" footer, no tool-specific
  branding in headings or prose. Editor- and service-specific session configuration is
  untracked and ignored; the development environment it used to prepare now lives in the
  tracked, neutral `scripts/bootstrap-dev-env.sh`. The convention applies from this date
  forward and existing history is deliberately not rewritten.
- **Reason:** This repository's record exists to say what was decided, what was validated and
  what the evidence is. How a draft was produced is not part of that and does not change
  whether a figure reconciles, a test passes or a limitation holds. Tracking session
  configuration also coupled the project's development setup to one contributor's tooling,
  which is a portability defect independent of attribution: a contributor without that tooling
  had no tracked path to a working Python 3.12 environment. Rewriting existing history to
  match would be a destructive, wide-reaching change for no gain in accuracy.
- **Consequence:** Responsibility is unchanged and explicitly not disclaimed: whoever submits a
  change is responsible for it however it was drafted, and every change passes the same four
  gates and the same review. The environment bootstrap is now reviewable, callable by hand and
  reusable by any local session tooling, which should call it rather than reimplement it.
  History before this date still carries earlier attribution and is left as it is.

## 2026-08-28 — Custody derived evidence by reproducibility, not by a custody record

- **Decision:** Do not create a custody record for the `annual-replay-decomposition` artifact
  (run `33147448666`, artifact ID `9676575888`, 90-day retention), and do not create one for
  any comparable derived-evidence artifact. Reproducibility from a custodied official history
  at a pinned commit is sufficient. `docs/custody/` holds records for retrieved official
  artifacts only.
- **Reason:** A custody record exists to detect a *provider* revision silently replacing an
  accepted baseline, which is why `docs/official_artifact_custody.md` treats a digest
  difference as a finding rather than a check to re-run. A decomposition artifact has no
  provider. It holds no interval-level price, so the redistribution question that forces
  encryption does not arise, and every input to it is already fingerprinted: the accepted
  history by `docs/custody/greek-dam-official-history.json`, the code by `main` at `65e61f9`,
  and the configuration by `examples/battery_50mw_100mwh.json` in that commit.
  `docs/official_annual_decomposition_2026-08-28.md` records all three plus the artifact's own
  zip SHA-256, which is the whole reproducibility chain. Recording it in `docs/custody/` would
  assert that it is a baseline capable of drifting independently of its inputs, which it is
  not, and would blur the one distinction that makes a custody difference diagnosable.
- **Consequence:** Derived evidence survives as a committed aggregate report plus a
  reproduction recipe, not as a stored artifact under custody. If the artifact lapses after its
  26 November 2026 expiry, it is regenerated by re-running the workflow against the custodied
  history at the recorded commit; a regenerated artifact that disagreed with the committed
  report would be a finding about the code or the history, not about the artifact. The
  distinction is deliberate: the official history must be *kept*, because it cannot be
  reproduced; this must only be *reproducible*.

## 2026-08-27 — Require an explicit bootstrap source era, with no default

- **Decision:** Define a source era as a maximal contiguous run of market days at one delivery
  resolution, and require the bootstrap to sample from exactly one. A history holding a single
  era needs no declaration; a history holding several must declare one with
  `source_resolution_minutes`, narrowed by `source_start_day` and `source_end_day` when that
  would otherwise be ambiguous. There is no default and no "most recent" rule. The refusal
  lists the available eras, the run summary and every provenance row record the selection, and
  the summary reports the minimum and median block-candidate counts.
- **Reason:** The Greek DAM moved from hourly to quarter-hour delivery on 1 October 2025, so
  the accepted 2020-2026 history holds two regimes while the bootstrap requires one. The
  previous behaviour refused such a history outright, which pushed the operator into slicing
  the CSV by hand; that slice is the single most consequential assumption behind every
  generated path and it existed nowhere in the record. Neither era is the right answer: the
  quarter-hour era is the regime the market actually operates under but contains exactly one
  occurrence of each meteorological season, so it expresses no inter-annual variation at all,
  while the hourly era holds five or six occurrences of every season but is a superseded
  delivery regime. A default would settle that trade-off silently.
- **Consequence:** Passing the accepted history to the bootstrap now fails with a message
  naming both eras and their windows rather than a bare resolution complaint. A path can no
  longer be read without knowing which regime produced it. Candidate scarcity is disclosed
  rather than smoothed: a minimum candidate count of 1 means every path repeats one source
  block at that position, which is a property of the era and not of the seed. Resampling one
  resolution into another, blending the two eras, and attaching any likelihood to an era all
  remain out of scope. The policy is recorded in `docs/bootstrap_source_era_policy.md`.

## 2026-08-27 — Decompose the accepted replay by market-clock delivery year

- **Decision:** Add a `decompose-annual-replay` surface and workflow that regroup an
  already-accepted replay into delivery years, where a delivery year is the calendar year of
  the interval's CET/CEST market-day start. Every year carries its market-day count, its
  coverage against the calendar year and an explicit partial-year flag; per-market-day figures
  are within-period averages and no annual figure is annualized, extrapolated or scaled to a
  full year. No probability, percentile, loss metric or ranking of years is attached.
- **Reason:** The accepted 2020-2026 aggregate margin averages a COVID trough, a gas-crisis
  year and a negative-price surge into one number, which conceals the regime dependence that
  is the most decision-relevant property of the replay. The market clock is the sense in which
  the Greek DAM has delivery years and is already the convention of the committed custody
  records, so a second convention would put two committed documents in apparent conflict.
  Partial years are unavoidable at both ends of the accepted window: 2020 begins on 1 November
  and 2026 ends on 25 August. Annualizing either would manufacture revenue the replay does not
  contain, which is the same objection that removed percentiles from the v0.7 scope.
- **Consequence:** A UTC-grouped count and a market-clock count of the same intervals differ
  by one interval at each year boundary; the summary states the equivalence so the difference
  is read as a grouping, not a defect. Annual figures keep the labels their aggregates carry:
  a per-year perfect-foresight margin remains a gross-margin upper bound and a per-year
  capture ratio remains a historical backtest outcome. Ordering years by margin is not a
  ranking of anything about the future.

## 2026-08-27 — Attribute a delivery year only from independent daily solves

- **Decision:** Decompose the perfect-foresight ceiling from a schedule composed of
  independent daily solves rather than from a single full-horizon solve, and publish that mode
  as `optimize_daily_perfect_foresight` and `optimize-perfect-foresight --daily-solves`. The
  mode requires `terminal_soc_fraction` to equal `initial_soc_fraction`. The decomposition
  additionally refuses any schedule whose settled price differs from the supplied history at
  any interval.
- **Reason:** A full-horizon solve may charge on 31 December and discharge on 1 January, which
  splits one trade's cost and revenue across two delivery years and makes an annual figure an
  artifact of where the boundary falls. Independent daily solves cannot do this, and they are
  already the repository's comparative convention and the ceiling the forecast backtests are
  measured against, so the annual ceiling and the annual capture ratio share one basis. The
  2026-08-27 acceptance ran this mode through a temporary runner that no longer exists; there
  was no published surface for it, so the decomposition could not be reproduced.
- **Consequence:** The composed annual ceilings sum to the composed total, and their sum is at
  or below the full-horizon bound because restoring SOC each day removes inter-day arbitrage.
  Both remain labelled upper bounds. The price-equality check means a decomposition cannot
  silently pair a schedule with a history it was not solved on, which is the annual analogue
  of the settlement audit the acceptance performed.

## 2026-08-27 — Hold accepted official artifacts as encrypted release assets, fingerprinted in Git

- **Decision:** Store each accepted official artifact as an encrypted asset attached to a
  release in this private repository, and commit a price-free custody record for it under
  `docs/custody/`. The record carries per-file digests and content-level invariants of the
  normalized series, including a digest of the interval and price series computed over sorted
  `(delivery_start_utc, delivery_end_utc, price)` triples at six fixed decimals. Encryption
  keys and the upload itself stay with the operator; no automation in this repository holds a
  key that could decrypt an accepted artifact.
- **Reason:** The accepted history existed only as a workflow artifact expiring on 2 September
  2026, and official data may not enter Git. A release asset is durable and re-fetchable, but
  an unencrypted one would place official HEnEx and ENTSO-E data into a repository asset under
  redistribution terms this project has not assessed; encrypting before upload removes that
  question entirely. Re-retrieval cannot substitute for custody, because HEnEx replaces
  publications — the superseded 16 December 2020 workbooks are the precedent — so without a
  committed fingerprint a provider revision would silently replace an accepted baseline.
- **Consequence:** A stored copy can be proven to be the accepted artifact rather than merely
  plausible, and a re-retrieval that differs is detected rather than adopted. The encryption
  key becomes part of the custody chain, so a lost key forces re-retrieval with those drift
  consequences. A verification difference is a recorded finding to investigate, never a check
  to re-run, and a committed record is not overwritten without a decision entry.

## 2026-08-27 — Digest the price series, not only the artifact bytes

- **Decision:** Fingerprint an accepted history with both per-file SHA-256 digests and a
  separate digest of the interval and price series, and treat the latter as authoritative for
  whether the data changed. Missing prices digest as an empty field rather than a substituted
  number, and `-0.0` is normalized to `0.0`.
- **Reason:** Byte digests answer "are these the same bytes", which is not the question that
  matters across a re-export or a pandas upgrade. They are also insufficient on their own in
  practice: a one-cent price revision changes a file's SHA-256 while leaving its byte size
  unchanged, so size is no guard, and a format-only difference would otherwise be
  indistinguishable from a revised price.
- **Consequence:** A re-export of the same history verifies; a revised cent does not. The two
  digests together distinguish a formatting change from a data change, which is what makes a
  verification difference diagnosable rather than merely alarming.

## 2026-08-27 — Read the ENTSO-E curve type instead of assuming one point per interval

- **Decision:** Honor the `curveType` an A44 document declares. Under `A03` a point's price holds
  until the next declared position, so the omitted positions are materialized and labelled
  `entsoe_variable_block_repeat`. `A01` documents keep one interval per point, and an unknown
  curve type is rejected rather than guessed.
- **Reason:** The first complete reconciliation reported 4,874 official intervals as missing from
  ENTSO-E across 1,042 market days while every interval present in both sources agreed. The
  pattern was an artifact of the parser: it emitted one interval per point regardless of curve
  type, so every `A03` repeat became a false gap. Correcting it reduced the missing count to zero
  and produced exactly 4,874 labelled repeats.
- **Consequence:** Materializing a declared repeat is not interpolation, and the distinction is
  preserved in the data: an interval that ENTSO-E stated once carries no flag, and one implied by
  the variable-block encoding is labelled. A genuine gap in an `A01` document still fails the
  completeness check.

## 2026-08-27 — Reconcile the two official sources inside GitHub Actions

- **Decision:** Perform the HEnEx-to-ENTSO-E reconciliation in a dedicated manual workflow that
  reads the accepted `greek-dam-official-history` artifact, retrieves ENTSO-E prices for the
  window that history defines and classifies every interval, rather than comparing two files
  downloaded to a workstation. The window is derived from the accepted history instead of being
  typed in, and only interval counts, classification counts and aggregate difference statistics
  are printed; interval-level detail stays inside the run artifact.
- **Reason:** The personal ENTSO-E token exists only as an encrypted repository secret and the
  accepted history exists only as a short-lived private artifact, so the single place where both
  are available is the workflow runner. Deriving the window from the history removes the
  market-clock boundary guesswork that a hand-typed UTC range invites, and keeps the two sources
  on identical market days by construction.
- **Consequence:** A reconciliation is reproducible from a run ID plus the repository secret, and
  no official price ever reaches a commit or an ordinary log. The comparison result is a recorded
  classification: mismatched or missing intervals are the finding, while a source that is not
  deterministically valid on its own still fails the job.

## 2026-08-27 — Reposition as a Greek DAM battery replay and research benchmark

- **Decision:** Present the project as a Greek Day-Ahead Market battery replay and research
  benchmark rather than an investment stress tester. The repository, package and CLI names are
  unchanged for now; README framing, a reader-facing "what this tool cannot tell you" section
  and the roadmap language carry the repositioning.
- **Reason:** An independent review (27 August 2026) found the implemented capability is a
  verified historical replay with leakage-safe forecast benchmarks and screening arithmetic.
  "Investment stress testing" overstates that: batteries only entered the Greek DAM in April
  2026, so the replayed history contains no storage competition; balancing-market and
  availability-support revenues that dominate real Greek battery commerce are excluded; and
  the only implemented shock is near-inert for arbitrage.
- **Consequence:** Outputs keep their existing labels. The positioning change is documentation
  only; no analytical behavior changed. A future full rename (repository/package/CLI) remains
  open as a separate decision.

## 2026-08-27 — Replace probabilistic v0.7 outputs with named deterministic scenarios

- **Decision:** Remove P5/P50/P95 percentiles and loss-probability outputs from the v0.7
  scope. v0.7 instead targets, in order: a documented bootstrap source-era/resolution policy,
  deterministic availability/outage paths, spread-compression transformations about a daily
  reference level, and scenario-ensemble range reporting explicitly labelled
  non-probabilistic. Cannibalisation is represented only as explicit judgmental
  spread-compression scenarios.
- **Reason:** The seasonal block bootstrap samples uniformly with replacement from a
  non-stationary 2020-2026 history (COVID trough, 2022 gas crisis, 2025-2026 negative-price
  surge), so percentiles over its paths have no calibrated probability interpretation and
  "loss probability" would be pseudo-statistical. A constant additive price-level shift leaves
  within-path spreads unchanged, so further level shocks change arbitrage economics only
  through efficiency losses and fees; spread transformations are the first-order stress. The
  bootstrap also requires a single input resolution while the accepted official history mixes
  hourly and quarter-hour regimes, so the sampling era must be an explicit decision.
- **Consequence:** No probability, percentile or loss metric will be attached to scenario
  outputs unless a defensible calibration methodology is independently justified first.
  Scenario results are reported as labelled ranges across named assumptions.

## 2026-08-27 — Record both horizons in official operational acceptance

- **Decision:** Accept the official multi-year history with the existing optimizer run twice: once
  over the complete 74,663-interval horizon in a single solve, and once as 2,124 independent daily
  solves composed without altering their physical semantics.
- **Reason:** The API maximises margin across whatever horizon it is given, and the full history
  proved tractable, so the true upper bound is recordable. The daily mode is the repository's
  established comparative convention and is the ceiling the forecast backtests use, so both are
  needed to interpret the forecast results.
- **Consequence:** The daily-composed margin is necessarily lower than the full-horizon margin
  because restoring the initial SOC each day removes inter-day arbitrage. Both remain labelled
  historical perfect-foresight gross-margin upper bounds; neither is expected revenue.

## 2026-08-27 — Attribute every excluded forecast day to a structural cause

- **Decision:** Require each excluded backtest day to be attributed to first-day warm-up,
  insufficient causal lag history, a spring DST day that removes the required wall-clock slot, or
  the 2025-10-01 hourly-to-quarter-hour resolution change and its lag warm-up.
- **Reason:** An unexplained exclusion could hide a defect, whereas these four causes are
  deterministic consequences of documented market structure and causal lag rules.
- **Consequence:** Acceptance reports coverage and exclusion counts by reason. Zero unexplained
  exclusions occurred across the accepted history, so no code change was warranted.

## 2026-08-27 — Dispatch bootstrap paths independently under shared assumptions

- **Decision:** Require equivalent complete canonical interval identities and retained synthetic
  provenance across all paths, then run the existing deterministic optimizer separately for each
  path with one unchanged battery configuration and common availability profile.
- **Reason:** This preserves path boundaries and makes operational/revenue sensitivity auditable
  without mixing state, constraints or assumptions between scenarios.
- **Consequence:** Results are labelled perfect-foresight gross-margin upper bounds on synthetic
  paths. No probabilities, percentiles, ranking, degradation, finance or investment conclusion
  is added; negative-price-event transformations are deferred.

## 2026-08-27 — Use one additive constant for the first price-level shock

- **Decision:** Apply a required finite EUR/MWh shift equally to every interval of each validated
  bootstrap path, identified by a required transformation ID, without clipping the result.
- **Reason:** A constant additive transformation is deterministic, transparent and preserves
  absolute price differences while allowing zero and negative shocked prices.
- **Consequence:** Original and shocked prices plus interval/path/source provenance are retained.
  The result is a synthetic sensitivity, not a calibrated distribution, forecast or investment
  conclusion; all other shock types remain excluded.

## 2026-08-26 — Start v0.7 with an auditable seasonal block bootstrap

- **Decision:** Sample complete contiguous market-day blocks with replacement from the same
  meteorological season, require exact target/source daily interval-count patterns, and expose
  the seed plus block-level candidate and selection provenance.
- **Reason:** This provides a deterministic dependence-preserving foundation while keeping DST,
  zero/negative prices and missing-data behavior explicit and testable.
- **Consequence:** Paths are labelled synthetic scenarios rather than forecasts or investment
  evidence. Missing observations are rejected, and dispatch, finance, probability summaries and
  shock overlays remain outside this reviewable foundation.

## 2026-08-26 — Accept the complete official HEnEx acquisition baseline

- **Decision:** Accept workflow run 32971677163 and its private
  `greek-dam-official-history` artifact as the official acquisition baseline through 25 August
  2026. The artifact contains 74,663 intervals, including 22,748 rows retrieved from the 2026
  daily catalogue, and has SHA-256
  `127915bc6e143a6bf2a4cb0a559b798e231062097bdaf9bf467a051260c4b198`.
- **Reason:** Both annual archive retrieval and incremental daily retrieval passed, coverage is
  continuous from 1 November 2020 through 25 August 2026, and the combined history has zero
  missing intervals.
- **Consequence:** v0.7 may use this privately retrieved history for research validation while
  preserving all existing interpretation limits. The artifact and official data remain outside
  Git, and acceptance is ingestion evidence rather than an investment conclusion.

## 2026-08-26 — Require complete daily-catalog coverage

- **Decision:** Parse the live suffix-less HEnEx result labels, follow the current Liferay
  pagination route and require one latest-revision publication for every requested delivery day.
- **Reason:** Incremental workflow run 32969157951 found zero files because the synthetic fixture
  included `.xlsx` while the live catalogue labels do not. Pagination must also never repeat or
  stop merely because a page lies outside the requested range.
- **Consequence:** Layout drift and incomplete ranges fail explicitly; daily data cannot enter an
  official-history artifact unless catalogue coverage is complete.

## 2026-08-26 — Select publications before parsing and bound row-level MCP consensus

- **Decision:** Select the greatest workbook filename revision for each HEnEx delivery day before
  parsing. Within that selected workbook, accept a dominant MCP only when it is unique, more than
  half of the rows, differs from at most two rows, and the total spread is no more than
  EUR 0.011/MWh.
- **Reason:** Superseded 16 December 2020 workbooks contain material conflicts corrected by v03.
  Across the latest 2020-2025 publications, 980 intervals contain only a EUR 0.01/MWh difference
  in one or two Greek-border import/export rows; all other asset rows agree.
- **Consequence:** Corrected later publications are authoritative, bounded rounding consensus is
  labeled `henex_mcp_rounding_consensus`, and material or ambiguous disagreements still fail.

## 2026-08-26 — Support the documented 2021 nested annual DAM archive

- **Decision:** Allow one size-limited nested ZIP only when its name matches
  `YYYY_EL-DAM_Results.zip`; reject deeper nesting and ignore unrelated LIDA/CRIDA archives.
- **Reason:** The official 2021 annual download contains the DAM history as a nested archive,
  unlike the other registered years.
- **Consequence:** Both outer and nested archive hashes enter the manifest, and 2021 is no longer
  silently absent from the normalized history.

## 2026-08-26 — Quarantine ADMIE forecast candidates until timing acceptance

- **Decision:** Retrieve and timestamp ADMIE load, RES and system files, but do not parse them
  into forecast features until their publication sequence is proven to precede the target-day bid
  decision for every applicable historical regime.
- **Reason:** A useful-looking official variable can still create look-ahead leakage if it was
  published after the decision point.
- **Consequence:** Retrieval manifests label these files `requires_pre_auction_timing_validation`.

## 2026-08-26 — Use annual HEnEx archives before daily catalog discovery

- **Decision:** Treat reviewed 2020-2025 annual ZIPs as the primary history path and use the
  current website catalog only for unarchived daily increments.
- **Reason:** Annual archive URLs are stable and compact; the daily asset publisher is more likely
  to change layout.
- **Consequence:** Daily discovery fails visibly on layout changes and never bypasses the normal
  parser, revision selection or quality checks.

## 2026-08-26 — Preserve file-level retrieval provenance

- **Decision:** Record exact source URL, delivery coverage, publication time when available,
  retrieval time, revision, byte size and SHA-256 for every official file. Extracted HEnEx
  workbooks also retain their parent archive hash.
- **Reason:** Revisions and provider-side replacement can otherwise make a historical research
  run impossible to reproduce or audit.
- **Consequence:** Manifests are generated beside ignored data and may be retained as private
  workflow artifacts; official file contents remain outside Git.

## 2026-08-26 — Make four clean-environment checks mandatory

- **Decision:** Every pull request must pass Ruff, mypy, pytest and a clean wheel build on
  Python 3.12 without private API keys or official datasets.
- **Reason:** Style, type consistency, behavior and packaging fail in different ways; one check
  cannot substitute for the others.
- **Consequence:** The initial foundation PR was corrected until all four checks passed. The
  typed-package marker is included in built distributions, and tests use package-qualified
  imports that work under both unittest and pytest discovery.

## 2026-08-26 — Import the completed v0.6 project honestly

- **Decision:** Treat the first GitHub contribution as a repository-foundation/import
  milestone containing the already completed v0.1-v0.6 implementation.
- **Reason:** The analytical code predates the connected repository. Fabricating historical
  commits or pretending the optimizer and forecast code do not exist would make the project
  history misleading.
- **Consequence:** Future milestones use feature branches and one reviewable pull request per
  milestone. Earlier implementation reports remain the audit record for pre-GitHub work.

## 2026-08-26 — Keep market data outside Git

- **Decision:** Commit download/import code, official URLs, hashes, schemas and aggregate
  quality evidence, but not full HEnEx or ENTSO-E datasets.
- **Reason:** Data can be large and its redistribution terms must be checked separately.
- **Consequence:** `data/raw`, `data/interim` and `data/processed` contain only `.gitkeep`
  placeholders. Small clearly synthetic fixtures may be committed under `tests/fixtures`.

## 2026-08-25 — Use UTC as the canonical interval key

- **Decision:** Store timezone-aware UTC interval boundaries and retain market-clock and
  Europe/Athens views.
- **Reason:** Greece/market clock changes create 23/25-hour and 92/100-quarter-hour days.
- **Consequence:** Local clock labels alone are never treated as unique interval identifiers.

## 2026-08-25 — Preserve prices exactly

- **Decision:** Preserve zero and negative official prices and reject or disclose missing
  prices rather than silently interpolating them.
- **Reason:** These observations materially affect dispatch value and risk.

## 2026-08-25 — Separate ceilings, backtests and scenarios

- **Decision:** Every operating path carries a label identifying perfect foresight,
  historical forecast backtest or user scenario.
- **Reason:** A physically feasible optimum with future price knowledge is not an achievable
  forecast.

## 2026-08-25 — Restrict the initial commercial scope

- **Decision:** Model Greek DAM arbitrage only.
- **Reason:** Other markets and revenue streams require separate access, acceptance,
  settlement, regulatory and operational evidence.

## 2026-08-25 — Use daily terminal-energy equality in comparative backtests

- **Decision:** Restore initial state of charge at each day end for like-for-like daily
  forecast comparisons.
- **Reason:** This prevents one strategy from receiving free value by emptying the battery at
  the evaluation boundary.
- **Consequence:** This is a benchmark convention, not a full multi-day trading policy.

## 2026-08-25 — Keep finance unlevered in v0.6

- **Decision:** Include explicit CAPEX, OPEX, augmentation, decommissioning and residual value,
  but exclude tax, debt, subsidies and working capital.
- **Reason:** Those layers require project-specific evidence and jurisdiction-specific advice.
