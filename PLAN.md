# Implementation plan

## GitHub milestone workflow

Every new milestone uses a feature branch, validation, diff review and one pull request. The
v0.1-v0.6 implementation predates the connected repository and will enter through the truthful
`repository-foundation-v0.6-import` snapshot; earlier Git history will not be fabricated.

Suggested future branch sequence:

1. `repository-foundation-v0.6-import`
2. `data-ingestion` (v0.6.1 official multi-year acquisition hardening)
3. `stress-testing` (v0.7)
4. `market-cannibalisation` (if separated from v0.7 after design review)
5. `research-reports` (v0.8; supersedes the earlier `streamlit-dashboard` label — the
   2026-09-01 design puts a static manifest renderer first and makes any interactive viewer a
   separate decision)
6. `point-in-time-fundamentals` (v0.9; the design of record is `docs/v0.9_design.md`, and each
   phase in it is one branch and one pull request)
7. `ai-explanations` (only after outputs and guardrails are validated)
8. `final-audit`

## Standing position (1 September 2026)

Every modeling milestone from v0.1 through v0.7, plus the v0.7.11 run manifest and report
contract, is landed on `main` and validated: the complete v0.7 scope was re-verified on
1 September 2026 on the unchanged v0.7.11 implementation (Ruff, mypy, all 301 tests, clean
wheel build). The dated deadline was met on 1 September 2026 and the custody chain behind it
closed the same day. The ADMIE forecast quarantine, open since 26 August, was closed by removing
ADMIE load and RES forecasts from scope rather than by working it to acceptance.

**v0.8 is complete.** The user approved it on 1 September 2026, `PROMPT.md` was amended the same
day, and `docs/v0.8_design.md` is the design of record. v0.8.0, the report rendering foundation,
and v0.8.1, multi-run composition, both landed on 1 September 2026.
v0.8.2 is complete: the dated decision declines an interactive viewer and closes v0.8 with the
static renderer. A viewer would duplicate a validated rendering surface and add a runtime
dependency and server lifecycle without adding evidence. Any future interactive proposal must
state a need the static report cannot meet and proceed as a separately approved milestone.
The completed v0.8 scope was then formally reviewed on 2 September 2026. The review found four
defects, all in the reporting layer and none affecting an analytical result, and v0.8.3 corrected
them: a verified manifest missing a guaranteed summary key crashed the renderer, two content
checks ran only when a manifest was recorded and not when one was read, a non-object
`declared_inputs` raised an unhandled error, and one in-document anchor could serve two
manifests.

**Two operator items remain open** (the custody second copy and `ENTSOE_SECURITY_TOKEN`,
below). The lesson the closed quarantine records is worth keeping in front of the plan: between
28 and 31 August the repository added roughly 3,100 lines of source, 3,000 of tests and 2,600 of
documentation around items that were already blocked, and retired none of them. Further audits,
policies and refusals around a blocked item do not retire it; they enlarge the machinery waiting
on the same missing declaration.

The plan below is therefore organised by what each item waits on, not by milestone number.

### The one hard deadline, met

- [x] **The accepted official-history artifact expires 2 September 2026 at 13:07 UTC, and its
  replacement is in place.** Run `32971677163` predated the retention increase and kept the
  original seven-day window. Run
  `33483975614` re-ran `Fetch official history` with the same inputs on 1 September 2026 and
  produced a replacement expiring **30 November 2026 at 07:49 UTC** under the 90-day retention.
- Verification run `33484823956` reported four differences against
  `docs/custody/greek-dam-official-history.json`, **all of them per-file byte digests, with no
  content fingerprint differing**. Both price-series digests match, so the accepted history is
  unchanged interval for interval. This is a faithful re-retrieval, now recorded as case 4 of
  the custody failure taxonomy; evidence in
  `docs/official_history_replacement_2026-09-01.md`.
- [x] **The custody record was re-recorded against `33483975614`.** The finding was reported
  before the record was touched, and the replacement was then taken as a separate decision: after
  2 September 2026 no obtainable copy could match the superseded per-file digests, and a record
  that verifies against nothing preserves no evidence. Run `33489920268` generated it in
  `record` mode; the committed file is what that run emitted, and every content fingerprint is
  unchanged. The workflow's `history_run_id` and `history_digest` defaults now point at the same
  run, and the superseded record remains in Git history.

### Waiting on a workflow dispatch

- **Public deployment of the accepted-replay report.** Render run `33609809770` successfully
  exercised the v0.8 renderer against accepted decomposition run `33147448666`, passed custody
  and manifest gates, and produced the private report artifact. The Pages job landed afterward,
  so a new dispatch against the same decomposition run is still required before publication.
  This is the last mile of a delivered feature rather than new scope: no source behaviour,
  dependency, contract or report format changes, and the workflow computes nothing.

### Waiting on an operator declaration

- **The second custody copy.** Both encrypted copies were published as release
  `custody-2026-09-01` on 1 September 2026 and the private key was exercised the same day, so the
  accepted artifacts are recoverable. What remains is a copy under separate control: one release
  is one failure domain, and nothing in this repository can perform or verify that placement.
- **`ENTSOE_SECURITY_TOKEN`.** The secret is no longer configured, so
  `Reconcile HEnEx and ENTSO-E prices` refuses at its guard step and the reconciliation cannot be
  re-run. The accepted evidence is safe in the custody copy; only regeneration is blocked.
- **The v0.9 decision cutoff and decision lead.** The point-in-time benchmark opened on
  2 September 2026 needs a declared day-ahead closure schedule with a real rulebook citation and a
  declared decision lead in minutes, and supplies neither on the operator's behalf. This is the
  same refusal the gate-closure schedule already records: the tooling reports whatever closure is
  declared and cannot check the declaration against the market rules.
  `config/decision_cutoff.example.json` shows the format and is refused as a declaration while its
  placeholder reference remains. Nothing in v0.9 runs without it.
- **The v0.9 sampling geography.** A gridded fundamentals variable must be sampled at declared
  points with declared weights and a stated basis for the choice; there is no default geography.
  `config/fundamentals_geography.example.json` shows the format under the same refusal.
- **All three v0.9 declarations are now load-bearing rather than prospective.** Since v0.9.1
  landed on 2 September 2026 the code exists and refuses: `read_decision_cutoff_schedule` and
  `read_sampling_geography` reject the committed examples by name, `validate_decision_lead_minutes`
  refuses an absent lead, and both workflows stop at their guard steps. The declarations are
  `config/decision_cutoff.json`, `config/decision_lead_minutes.txt` (one non-negative integer;
  `config/decision_lead_minutes.example.txt` deliberately holds no number) and
  `config/fundamentals_geography.json`. **Each day without them costs a witnessed day that cannot
  be recovered:** witnessed evidence exists only if a retrieval happened before that delivery
  day's cutoff, and the scheduled `witness-fundamentals` workflow says so every time it refuses.

### Resolved on 2 September 2026: the v0.9 source-selection spike

- **The spike is run and the source is chosen.**
  `docs/fundamentals_source_assessment_2026-09-02.md` resolves every inference behind the
  recommendation and the dated decision names **NOAA GFS 0.25° forecast vintages**, 00 UTC cycle
  of D-1, delivery days from 27 February 2021 onward. All three checks passed — archive coverage,
  `.idx` byte-range retrieval at a 157x reduction, and an ecCodes binding installing with no
  system package and leaving the four gates green on 3.12 and 3.13 — so G0 is not triggered and
  the EEX fallback is not selected and stays unassessed. The archive turned out to be reachable
  from a working checkout, so the spike was a local run rather than a workflow dispatch; the
  plan's assumption to the contrary is corrected below.
- **The ecCodes CI-image residual is closed.** Green CI on merged main commit `38ca0bc` installed
  the declared `eccodes` dependency on the `actions/setup-python` images, and
  `tests/test_gfs.py` exercised the binding and library version. G0 was not triggered.

### Resolved on 1 September 2026: the v0.8 scope decision

- **v0.8 is approved and open.** The user approved it on 1 September 2026; `PROMPT.md` now
  carries the amended scope bullet and `docs/v0.8_design.md` records the design (decision entry
  2026-09-01). Any revenue stream beyond DAM arbitrage still waits on its own scope decision
  and independent validation — opening v0.8 changes nothing there.

### Operating constraint on live retrieval

The development environment's egress policy refuses `www.admie.gr`, so ADMIE catalog queries,
file retrieval and timing audits are performed by dispatching the relevant workflow and reading
its uploaded evidence, never from a working checkout. That constraint is per host and not
universal: the v0.9 spike of 2 September 2026 reached `noaa-gfs-bdp-pds.s3.amazonaws.com`,
`pypi.org` and `raw.githubusercontent.com` from a checkout, while the same policy refused
`www.eex.com`, `eur-lex.europa.eu`, `data.ecmwf.int`, `archive-api.open-meteo.com` and
`registry.opendata.aws`. Check the host before assuming a live step must be a workflow run, and
plan it as one whenever the host is refused.

## Completed milestones

- [x] v0.1 — Official-data ingestion foundation.
- [x] v0.2 — Perfect-foresight dispatch upper bound.
- [x] v0.3 — Naïve price forecasts and forecast-dispatch backtesting.
- [x] v0.3.1 — Honest incomplete-forecast-day and backtested-coverage reporting.
- [x] v0.4 — ML forecasting benchmark.
  - Time-based training, validation and held-out test periods.
  - Calendar, lag and rolling-price features with explicit availability provenance.
  - Walk-forward refitting with training-date audit logs.
  - Ridge and histogram-gradient-boosting comparison against every naïve baseline.
  - Like-for-like held-out forecast-dispatch value and perfect-foresight regret.
- [x] v0.5 — Degradation and augmentation state model.
  - Linear additive calendar and equivalent-cycle fade by cohort.
  - Usable energy and power evolution with explicit beginning-of-day timing.
  - Per-cohort retained-capacity and EFC warranty screening.
  - Optional hard throughput headroom under proportional cohort allocation.
  - Dated augmentation/replacement cohorts with explicit retirement and recorded costs.
  - Degradation-aware daily perfect-foresight dispatch and auditable artifacts.
- [x] v0.6 — Project finance.
  - Explicit initial CAPEX components, fixed and variable OPEX and project life.
  - Dated augmentation, decommissioning and residual-value cash flows.
  - Unlevered NPV, IRR, simple and discounted payback.
  - Maximum initial CAPEX and market-margin break-even outputs.
  - Mandatory operating-margin provenance labels and explicit exclusions.

## Next milestones

- [x] Repository foundation/import — governance, provenance, CI and v0.6 snapshot PR.
- [x] v0.6.1/v0.6.2 — Official multi-year data acquisition and live acceptance hardening.
  - Verified HEnEx annual archive register and safe ZIP extraction.
  - Incremental daily HEnEx catalog discovery.
  - Multi-workbook latest-revision normalization.
  - ADMIE filetype/range client with publication-time provenance.
  - Private short-lived GitHub retrieval artifact.
- [x] v0.7 — Deterministic scenario stress testing (completed 2026-08-31; review gates v0.8).
  - [x] Foundation: seasonal block bootstrap, reproducible seeds and sampled-block provenance.
  - [x] Deterministic additive price-level shock with interval provenance.
  - [x] Independent deterministic dispatch across validated bootstrap paths.
  - [x] Explicit bootstrap source-era/resolution policy (the accepted official history mixes
    hourly and quarter-hour regimes; the bootstrap requires one resolution, so the sampling
    era must be a documented decision rather than an accident). A source era is a maximal
    contiguous single-resolution run; a multi-era history must declare one, with no default;
    the selection is recorded in the summary and on every provenance row, and candidate
    scarcity is reported. Policy in `docs/bootstrap_source_era_policy.md`.
  - [x] Deterministic availability/outage-path integration (approved 2026-08-31). An
    availability schedule is a declared baseline fraction with no default plus declared outage
    windows; timing, duration and depth are judgmental inputs and are never sampled, because a
    forced-outage rate would be an uncalibrated probability. Window boundaries must fall on
    interval edges — a partly covered interval is refused rather than prorated — and overlapping
    windows or a window covering no dispatched interval are refused by name. The schedule is
    recorded by identity in the dispatch summary and carried as scenario provenance through the
    ensemble (decision entries 2026-08-31).
  - [x] Spread-compression transformations about a daily reference level, as explicit
    judgmental scenarios; this is how cannibalisation pressure is represented, since a causal
    cannibalisation model is not buildable from price history alone. `compress-spread` scales
    every within-day range by a declared factor in [0, 1] about a declared daily reference
    basis with no default, preserves zero and negative results without clipping, and reports
    the intervals whose sign changes. Widening is out of scope (decision entry 2026-08-28).
  - [x] Scenario-ensemble range reporting (minimum/maximum/spread across named scenarios),
    explicitly labelled non-probabilistic. `report-scenario-ensemble` composes bootstrap-path
    dispatch results already produced under two or more scenarios the caller names, and reports
    the range per bootstrap path. There is no default scenario set and no implicit baseline, and
    nothing is aggregated across paths. No probability, percentile, expected value, loss metric,
    ranking or central case is produced, and the exclusion is executable: an emitted column or
    summary key matching `FORBIDDEN_REPORT_TERMS` raises. Scenarios solved under different
    battery parameters, terminal-energy constraints, source eras or path identities are refused
    with the mismatch named. Differing declared availability schedules are permitted scenario
    judgments and are carried as provenance; an unrecorded availability assumption is refused
    (decision entries 2026-08-31).
  - Removed from scope on 2026-08-27: P5/P50/P95 percentiles and loss probabilities. Uniform
    block resampling of the non-stationary 2020-2026 history supports no calibrated
    probability interpretation, and additional constant price-level shocks, which leave
    within-path spreads unchanged, are near-inert for arbitrage economics.
  - [x] Deterministic declared negative-price-event transformations (approved 2026-08-31).
    Each event is an interval-aligned inclusive-start/exclusive-end UTC window with a declared
    strictly negative replacement price in EUR/MWh. Timing and depth have no defaults and are
    never sampled, inferred, fitted or searched. An empty event list is the identity; overlap,
    partial intervals and windows covering nothing are refused (decision entry 2026-08-31).
- [x] v0.8 — Research interface and exportable reports (**opened and completed 2026-09-01**;
  `PROMPT.md` amended the same day; design of record in `docs/v0.8_design.md`).
  - [x] Prerequisite: a versioned run manifest and report contract (v0.7.11), which the
    completed-v0.7 review named as the thing to define before any consumer couples to incidental
    summary keys. `greek_bess.reporting` carries any result summary verbatim under a stable
    projection and makes label retention executable. Policy in `docs/run_manifest_contract.md`.
  - [x] A design answering the three gated questions. The landing state with no judgmental
    input declared is the declaration checklist — each default-free input, the dated decision
    behind it, and the command that records a result once declared — never a demo with implied
    defaults. Every rendered figure carries its manifest's `result_label`, basis and the
    standing exclusions adjacent to the figure, read from the manifest and never re-declared.
    An export refuses any figure not reachable from a verified manifest, interval-level
    official price series, distributional vocabulary where the kind forbids it, unlabeled
    figures, and any value computed across manifests or bases (decision entry 2026-09-01).
  - [x] v0.8.0 — Report rendering foundation (completed 2026-09-01;
    `docs/history/implementation_report_v0.8.0.md`). `render-report` CLI and
    `greek_bess.reporting.render`: verified-manifest input through `read_run_manifest` only,
    the landing state, per-figure label blocks, basis grouping, the export refusals,
    deterministic self-contained HTML plus a machine-readable index naming every manifest's
    kind, basis, label and digest. No new runtime dependency, no server, no computation.
    Tests cover every registry kind, the landing state's absence of numeric figures, refusal
    of a failing manifest, and byte-determinism. The index identifies a manifest by digest and
    never by its path, recorded values are rendered exactly as recorded, and the
    distributional-term check is scoped to the renderer's own vocabulary because the standing
    exclusions the design requires beside every figure themselves contain two of the terms
    (decision entries 2026-09-01).
  - [x] v0.8.1 — Multi-run composition (completed 2026-09-01;
    `docs/history/implementation_report_v0.8.1.md`). An index across many manifests, grouped by basis,
    naming each manifest's ID, kind, label, producing command, recorded time and digest, linking
    to its block and naming the bases the report does not cover — and carrying no figure at all,
    which is the point of it. A scenario ensemble is laid out side by side: one column per named
    scenario with its provenance, the equivalent-basis evidence the ensemble recorded, and one
    row per bootstrap path with the lowest and highest margin, the scenarios that attained each
    end, and the spread. Composition is layout only; nothing is computed across manifests, and
    no total spans the paths. The design tension the milestone opened — the per-path ranges lived
    in the ranges CSV, not in the summary a manifest carries — was resolved by recording them in
    the ensemble's own summary and guaranteeing them in the contract, never by reading the CSV
    (decision entries 2026-09-01; amendment in `docs/v0.8_design.md`).
  - [x] v0.8.2 — Interactive viewer decision (completed 2026-09-01;
    `docs/history/implementation_report_v0.8.2.md`). Declined: the indexed, self-contained static report
    satisfies the approved scope, while a local viewer would duplicate the validated rendering
    rules, add a dependency and server lifecycle, and create no new evidence. A future proposal
    must identify a need the static report cannot meet and receive its own approval and milestone.
    AI-generated explanations remain outside v0.8.
  - [x] v0.8.3 — Completed-v0.8 review corrections (completed 2026-09-02;
    `docs/history/implementation_report_v0.8.2_review.md`). The review covered the manifest contract,
    the renderer, the reporting CLI surfaces, the design of record and the project records. It
    confirmed that the renderer computes nothing, opens no file a manifest names, reads no
    environment or network, merges no figure across bases and re-declares no label — and found
    four defects at the doorway between a recorded manifest and a rendered one. Reading a
    manifest now applies every check that is a property of its recorded content, while the
    guaranteed-key check stays a record-time promise and an absent guaranteed key is stated
    rather than assumed or refused (decision entry 2026-09-02).

- [~] v0.9 — Point-in-time fundamentals forecast benchmark (**opened 2026-09-02**; design of
  record in `docs/v0.9_design.md`). The one open analytic question in the forecasting layer is
  the one `LIMITATIONS.md` already names: validated weather, demand, fuel, renewable and
  interconnector forecasts are not included, so every accepted forecast figure comes from price
  history alone. v0.9 asks whether an independently validated exogenous input improves *realized
  settled dispatch value* — not price error — and is built so that the answer is defensible in
  either direction. Every feature value used for a delivery day must be provably available before
  a declared decision cutoff; nothing else may enter a fit.
  - The milestone is two unequal halves, and the records keep them apart. The engineering half —
    a typed point-in-time feature schema, a declared decision cutoff, a revision-aware as-of join
    with a per-value audit table, an availability audit with graded evidence, and manifest kinds
    that carry all of it — is buildable today from parts the repository already has; the
    `Audit ADMIE publication timing` surface retained as unused is the working prototype of the
    availability policy. The analytical half depends on one candidate source passing a
    point-in-time availability audit over enough delivery days to say anything, and that is
    established for no source today.
  - **Two new judgmental inputs, both required and neither defaulted**, following the
    gate-closure refusal of 2026-08-31: a `decision_cutoff` schedule in the existing dated-regime
    format, and `decision_lead_minutes`, which may be `0`. A feature is available for delivery
    day D only when its publication instant is *strictly* before the cutoff; a publication at the
    cutoff is late. `config/decision_cutoff.example.json` ships the format with a placeholder
    reference and is not a declaration.
  - **Availability evidence is graded and the grades never merge.** `witnessed` (this project
    retrieved the datum before the cutoff) and `provider_declared` (a provider instant attached
    to that datum places it before the cutoff) are admissible and reported separately;
    `assumed` — availability inferred from a regulatory deadline or a nominal latency rather than
    from the datum — is quarantined and usable only in an explicitly labelled exploratory run
    that is never recorded as accepted.
  - **The ADMIE removal of 2026-09-01 is not reopened.** ENTSO-E's Greek load and renewable
    forecasts originate from ADMIE, so obtaining them through another publisher would be the same
    reversal by another route. They are isolated as Track B, need their own dated decision, the
    restored token and forward-witnessed acceptance, and no part of v0.9 depends on them.
  - **Source chosen 2 September 2026: NOAA GFS 0.25° forecast vintages**, 00 UTC cycle of D-1,
    surface downward shortwave radiation, 10 m wind components and 2 m temperature, delivery days
    from 27 February 2021 onward — before that date the product is 3-hourly, so 118 of the
    accepted history's 2,131 delivery days carry no feature and are excluded by named cause. The
    spike passed all three checks, so the EEX EU ETS fallback is not selected and stays
    unassessed; it may not be adopted later without its own spike
    (`docs/fundamentals_source_assessment_2026-09-02.md`).
  - [x] v0.9.0 — Design and source selection (design, examples and records landed 2026-09-02;
    spike run and source chosen the same day; `docs/history/implementation_report_v0.9.0.md`).
    Documentation and configuration only: no source code, no dependency, no workflow, no data
    source and no analytical change.
    - [x] `docs/v0.9_design.md` as the design of record, with the source assessment, the
      cutoff contract, the feature schema, the join algorithm and its invariants, the
      acceptance milestone, the benchmark and evaluation design, the adversarial test plan, the
      phase sequence, the risk register and the go/no-go gates.
    - [x] `config/decision_cutoff.example.json` and `config/fundamentals_geography.example.json`,
      both carrying placeholder references, with a test that keeps them parseable by the reader
      that will read the real declaration and refused as declarations while the placeholder text
      remains.
    - [x] `docs/fundamentals_source_assessment_2026-09-02.md`, the source-selection spike:
      archive coverage across 2021-2026, `.idx` byte-range retrieval, a pip-installable ecCodes
      binding leaving all four gates green on 3.12 and 3.13, and the licence text captured
      verbatim, with every remaining inference recorded as an unknown and a named closing step.
      The dated decision of the same day names the source, and Section 3 of the design carries an
      amendment note pointing at it.
  - [x] v0.9.1 — One-source ingestion and availability audit against the chosen source (landed
    2026-09-02; `docs/history/implementation_report_v0.9.1.md`,
    `docs/point_in_time_feature_contract.md`). `eccodes` alone is declared as the new dependency —
    not `cfgrib` or `xarray`, which the low-level single-message read does not need — and its
    first CI run closes the spike's one residual by proving the decoder on the
    `actions/setup-python` images. Landed: `data/decision_cutoff.py` (the gate-closure schedule
    moved to a neutral module and re-exported, with `tests/test_admie_timing.py` passing untouched
    as the evidence the move changed nothing), `data/point_in_time.py`, `data/gfs.py`,
    `data/availability_audit.py`, `cli/fundamentals.py` with `fetch-fundamentals` and
    `audit-feature-availability`, `fetch-fundamentals.yml`, `witness-fundamentals.yml`, the
    `point_in_time_availability_audit` manifest kind, and two renderer checklist entries
    covering all three declarations. The witness workflow is scheduled from today so that
    witnessed days accumulate by v0.9.5; witnessed days arrive one per day and cannot be
    backfilled.
    - Availability is established **per delivery interval**, never per day: upload order is not
      monotone in forecast step, so one step's availability says nothing about another's, and one
      late step makes the day `incomplete_before_cutoff` rather than a shorter day.
    - The required forecast steps are **22-47**, not the assessment's 21-46, because this
      project's delivery day is the CET/CEST market day rather than the Athens day; the step set
      is derived from each market day rather than declared, and a test asserts the widest range
      across the usable record (decision entry 2026-09-02).
    - **Its acceptance criteria that need a dispatched run are outstanding for one reason only:**
      the decision cutoff, decision lead and sampling geography are undeclared, so no
      `fetch-fundamentals` window has been retrieved and no witnessed day exists yet. The code
      path was exercised end to end against the live archive once during development for one
      delivery day; that is evidence the pipeline works, not an accepted figure, and nothing from
      it is committed.
  - [x] v0.9.2 — The point-in-time join and its audit table: one feature value per delivery
    interval, selected as the latest revision published strictly before the cutoff, with later
    revisions counted and excluded, every value traceable to a source document, revision and byte
    digest, and a day either complete or excluded by named cause. Nothing is forward-filled,
    interpolated or imputed. Its completed review corrected the implementation to select the
    latest revision before judging its evidence grade and to scope each audit row's supersession
    count to its native interval (`docs/history/implementation_report_v0.9.2_review.md`).
  - [x] v0.9.3 — The forecast ablation: the two existing models on price-history features
    (control) against the same two models, the same fixed hyperparameters, the same refit
    cadence and the same splits with the accepted features appended (challenger). One feature
    set, no tuning, validation-only model selection. Landed 2026-09-02
    (`docs/history/implementation_report_v0.9.3.md`): `forecast/fundamentals.py`,
    `benchmark-fundamentals-forecast`, the `feature_columns`/`require_non_null` parameter in
    `ml.py` with a bit-for-bit control-arm regression, the `fundamentals_forecast_benchmark`
    manifest kind, the contract's third claim check, and the price-regime checklist entry.
    - The benchmark **identifies** its inputs: the join now records `feature_set_sha256` over
      the joined frame, and the run refuses unless the digest, the cutoff schedule, the decision
      lead and the admitted grades all equal what the join recorded.
    - The exploratory rule of gate G4 is executable rather than editorial: a meteorological
      season counts only when every one of its calendar days is a common held-out quarter-hour
      day, and the causes of an exploratory label are recorded (decision entry 2026-09-02).
    - **Validated on synthetic fixtures only, for the same one reason as v0.9.1 and v0.9.2:**
      the three operator declarations are absent, so no accepted feature table exists and no
      benchmark figure, manifest or acceptance document was produced.
  - [ ] v0.9.4 — The settled dispatch comparison on common days under an identical battery,
    identical realized prices and a common perfect-foresight ceiling, recording the incremental
    realized margin of each challenger over its own control and the paired daily differences.
  - [ ] v0.9.5 — Manifest and report integration and the official acceptance run: a data
    acceptance document before any benchmark document, and no benchmark manifest declaring a
    feature-set digest that no acceptance document names.
  - **A negative result is a result.** If fundamentals do not improve settled value, that is
    recorded under the same labels; the cutoff, the split and the feature set are never revised
    after seeing test results. Any such revision is a new benchmark under a new decision entry.
  - **Exploratory unless the coverage earns otherwise.** If the accepted feature coverage yields
    fewer than one full meteorological season of quarter-hour common test days, the run is
    labelled exploratory, the label carries a suffix saying so, and no general conclusion reaches
    the README.
  - Out of scope for v0.9 and unchanged: ADMIE-originated forecasts by any route, fuel prices
    without a licensed feed, probability or confidence outputs, hyperparameter search, deep
    learning, any change to an accepted price-history figure, and every exclusion `PROMPT.md`
    already carries.

## Parallel acceptance track

- [x] Make validation warning-free: build pandas timedeltas with explicit units, and scope the
  pytest warning gate to warnings attributed to `greek_bess` or to the project's own tests so an
  upstream release cannot fail CI on this project's behalf. Correct custody wording so committed
  fingerprints are not mistaken for a durable encrypted copy whose upload the repository record
  does not verify as complete, align limitations with the approved exclusion of uncalibrated
  probability estimates, and lock the declared project version to a single value.
- [x] Keep the repository record contributor-neutral: no tool or assistant attribution in
  commits, pull requests, comments, documentation or tracked configuration, from 2026-08-28
  forward, with existing history deliberately not rewritten (decision entry 2026-08-28).
  Editor- and service-specific session configuration is untracked; the development environment
  bootstrap it performed now lives in the tracked `scripts/bootstrap-dev-env.sh`.

- [x] Validate real HEnEx workbooks.
  - Official `20260824` and `20260825` English v01 result workbooks.
  - 96 quarter-hour intervals per day and 192 contiguous intervals combined.
  - No missing prices, duplicate intervals, gaps, overlaps or quality errors.
- [x] Validate the ENTSO-E client with a private token.
  - Workflow run `33073631530` retrieved the complete 1 November 2020 to 25 August 2026 window.
- [x] Reconcile overlapping official sources.
  - 74,662 of 74,663 intervals match exactly; one 29 October 2023 interval differs by
    EUR 0.01/MWh; neither source omits an interval the other publishes.
- [x] Record the accepted HEnEx source versions, retrieval date and raw hashes.
- [~] Record the ENTSO-E retrieval metadata and raw-response hashes. The reconciliation
  artifact from run `33073631530` carries them and is covered by the same custody procedure;
  the operator upload remains outstanding. **That artifact expires 3 September 2026 at 12:50 UTC
  and has no replacement:** a refresh dispatched on 1 September (run `33489364087`) was refused by
  the workflow guard because `ENTSOE_SECURITY_TOKEN` is no longer configured as a repository
  secret. Restoring the secret is an operator action; the encrypted upload of the existing
  artifact needs no secret and is what preserves the evidence in the meantime.
- [x] Run and accept the 2020-2025 HEnEx annual archives live.
- [x] Run and accept the incremental 2026 HEnEx daily retrieval live.
  - Workflow run `32971677163` completed both retrieval stages successfully.
  - The accepted artifact contains 22,748 incremental 2026 intervals through 25 August 2026.
- [x] Run the optimizer and forecast backtests over the complete official multi-year history.
  - Perfect-foresight dispatch accepted over all 74,663 official intervals.
  - All four causal naïve baselines and both ML benchmarks accepted with leakage,
    settlement, coverage and determinism evidence.
- [x] **ADMIE load/RES forecasts removed from scope** (decision entry 2026-09-01). The
  2026-08-26 quarantine is closed as never accepted rather than discharged: no ADMIE field ever
  entered forecasting and none may. File-format acceptance and pre-auction timing acceptance are
  therefore not pending items; they are questions the project no longer asks.
  - [x] What was established and retains its evidentiary value: the live catalog and a
    26-28 August 2026 retrieval confirmed the ISP1 and ISP2 day-ahead load/RES pairs as
    retrievable, which is names and non-empty discovery only
    (`docs/admie_filetype_acceptance_2026-08-31.md`).
  - [x] What was never established: publication before auction closure, any file format, and any
    timing audit over the confirmed filetypes against a verified closure.
  - [x] Retained and documented as unused: `list-admie-filetypes`, `fetch-admie-files`,
    `audit-admie-publication-timing`, the gate-closure format, their tests and the
    `Audit ADMIE publication timing` workflow. They are the executable form of the refusal, kept
    so a future declaration can be tested without rebuilding them, and are not to be pruned as
    dead code. Policy in `docs/admie_publication_timing_policy.md`.
  - Reopening requires the operator declaration the quarantine always needed, a contemporaneous
    audited window, format acceptance and a new dated decision.
- [~] Store the accepted normalized official history durably and privately outside Git. The
  source is now replacement run `33483975614`, which does not expire until 30 November 2026.
  - [x] Storage procedure, custody-record format and verification tooling
    (`docs/official_artifact_custody.md`, `record-custody`, `verify-custody`).
  - [x] Artifact retention raised from 7 to 90 days on every official-data workflow.
  - [x] Replacement retrieval before the original artifact lapsed (run `33483975614`,
    1 September 2026), verified against the committed record with no price-series difference.
  - [x] `Publish encrypted custody copies` workflow, which verifies each artifact against its
    committed record, refuses to encrypt one that differs, encrypts to an operator-supplied age
    recipient and attaches the ciphertext to a private release. The recipient is a public key, so
    no automation here can decrypt an accepted artifact.
  - [x] Encrypted copies published. Run `33497084006` verified both artifacts, encrypted them to
    the operator's recipient and published release `custody-2026-09-01` on 1 September 2026.
  - [x] **Decryption drill, run 1 September 2026.** The operator decrypted the reconciliation
    copy and recovered an archive of the expected size, while the source artifacts still existed
    and a failure would have been recoverable. The private key opens the published copies.
  - [ ] Second copy under separate control. One release is one failure domain, and this is
    outside the repository's knowledge either way.
- [x] Add a per-calendar-year decomposition of the accepted replay (annual perfect-foresight
  ceiling and forecast capture), since aggregate 2020-2026 margins conceal regime dependence
  such as the 2022 gas-crisis year.
  - [x] `decompose-annual-replay` surface, delivery years on the CET/CEST market clock,
    partial-year labelling, per-method and common-day capture tables.
  - [x] `optimize-perfect-foresight --daily-solves`, so the annual ceiling and the annual
    capture ratio share the daily terminal-energy basis and no trade spans a year boundary.
  - [x] `Decompose the accepted replay by delivery year` workflow, which verifies the accepted
    artifact against its committed custody record before consuming it.
  - [x] Ran the workflow against run `32971677163` on 2026-08-28 (run `33147448666`). Custody
    verification passed, every per-year figure reconciles with the previously accepted
    aggregates, and the evidence is recorded in
    `docs/official_annual_decomposition_2026-08-28.md`.
