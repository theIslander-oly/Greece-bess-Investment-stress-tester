# Implementation plan

## GitHub milestone workflow

Every new milestone uses a feature branch, validation, diff review and one pull request. The
v0.1-v0.6 implementation predates the connected repository and will enter through the truthful
`repository-foundation-v0.6-import` snapshot; earlier Git history will not be fabricated.

### Fixed execution-plan tracker

The staged plan in `Greek_BESS_Execution_Plan.md` is active. Only one stage moves at a time.

| Stage | Status | Evidence or next gate |
| --- | --- | --- |
| Entry | Complete | Cross-platform baseline validated and merged in PR #56 (`84ec878`) |
| 1 | Complete | Retrieval repair merged as `f149f61`; tree matches reviewed PR #55 head |
| 2 | Complete | GFS value semantics and identity guards merged as `316e9f5` (PR #57) |
| 3 | Complete | Unit 1 merged as `8dc72e3`, unit 2 as `61afae0` |
| 4 | Complete | Dated cash-flow NPV and IRR merged as `d5f0ca1` |
| 5 | In progress | Degradation result basis ready for review |
| 6–10 | Pending | Follow the fixed plan in order |

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
### Resolved on 3 September 2026: the three v0.9 declarations

The decision cutoff, the decision lead and the sampling geography were the only reason v0.9.1
through v0.9.4 accepted nothing, and all three were declared on 3 September 2026
(`docs/fundamentals_declarations_2026-09-03.md`): a two-regime cutoff schedule in
`config/decision_cutoff.json`, a zero-minute lead in `config/decision_lead_minutes.txt` and a
pre-test-vintage wind-capacity geography in `config/fundamentals_geography.json`. The refusal was
load-bearing rather than prospective — `read_decision_cutoff_schedule` and
`read_sampling_geography` reject the committed examples by name and both workflows stop at their
guard steps — so this is what makes every v0.9 surface runnable for the first time. The tooling
still cannot check a declared closure against the market rules, so the primary rulebook and
capacity statistics must accompany the acceptance evidence.

**One witnessed day was lost on the way, and cannot be recovered.** The scheduled
`witness-fundamentals` run of 3 September 2026 (`33722543960`, the workflow's first) started at
06:17 UTC against commit `a64bb21`, about two hours before the declarations merged, and stopped
at its guard. Delivery day 4 September 2026 closed at 12:00 CEST that day, so it can now only
ever be provider-declared evidence. The cron needs no change: 06:00 UTC is after the observed
publication window of the 00 UTC cycle and before the declared closure, and the next scheduled
run is the first that will find all three declarations present.

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
  - [x] v0.9.4 — The settled dispatch comparison on common days under an identical battery,
    identical realized prices and a common perfect-foresight ceiling, recording the incremental
    realized margin of each challenger over its own control and the paired daily differences.
    Landed 2026-09-03 (`docs/history/implementation_report_v0.9.4.md`):
    `backtest/fundamentals_dispatch.py`, `benchmark-fundamentals-dispatch`, the
    `fundamentals_dispatch_benchmark` manifest kind, and the paired-difference CSV. Each arm is
    planned and settled through `_backtest_precomputed_forecast`, the accepted path the ML
    dispatch benchmark already uses, and a test asserts the control arm and the naive baselines
    reproduce `backtest_ml_dispatch_benchmark` figure for figure on the synthetic suite.
    - The settled days are **the ablation's own** — the held-out subset of the days it recorded
      as common to every baseline and both arms. A gap on one of those days is refused rather
      than excluded: excluding it here would give two arms different calendars, which is the
      defect the common-day rule exists to prevent (decision entry 2026-09-03).
    - Equivalence is **asserted and recorded**, not assumed: one battery whose terminal SOC must
      equal its initial SOC, one realized price series, and one perfect-foresight ceiling checked
      identical across arms to 1e-6 EUR, with the shared basis written into the summary as
      `equivalent_basis`.
    - The **incremental margin is recorded by the producing module**, never derived by a
      consumer, and the paired daily differences are published with their sign counts and total.
      No dispersion or significance statistic is computed from them; adding one would be a
      separate decision about vocabulary.
    - **Validated on synthetic fixtures only, for the same one reason as v0.9.1 through
      v0.9.3:** the three operator declarations are absent, so no accepted feature table exists
      and no settled figure, manifest or acceptance document was produced.
  - [~] v0.9.5 — Manifest and report integration and the official acceptance run: a data
    acceptance document before any benchmark document, and no benchmark manifest declaring a
    feature-set digest that no acceptance document names. **The machinery landed on 3 September
    2026; the official run has not started** (`docs/history/implementation_report_v0.9.5.md`).
    - [x] Research declarations pre-registered on 3 September 2026, before any test run: the
      two-regime cutoff, zero lead, wind-capacity geography, structural price bands, fixed
      quarter-hour test boundary and separate 25 MW / 100 MWh example
      (`docs/fundamentals_declarations_2026-09-03.md`). Primary sources still have to accompany
      acceptance evidence; no official feature table or benchmark result exists.
    - [x] The custody-gated `Benchmark point-in-time fundamentals` workflow, which runs the fixed
      order and refuses anything out of it, guarding every pre-registered declaration by value.
    - [x] The manifest refusal itself: both fundamentals benchmark kinds are refused, on record
      and on read, unless the declared inputs name the same accepted feature-set digest as the
      producer summary, so no benchmark can be presented whose feature table acceptance did not
      identify.
    - [x] Feature-table custody through the established record, verify and encrypted-copy paths
      rather than a second mechanism, plus generic renderer coverage of all three v0.9 kinds and
      the dated-document templates under `docs/templates/`.
    - [ ] **The official run itself, which is the whole point and has not begun.**
      `Fetch point-in-time fundamentals` has never been dispatched, so no feature table, no
      availability audit against retrieved data, no custody record, no acceptance document and no
      benchmark figure exists. The v0.9 chain is complete in code and empty of evidence.
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

## v0.9.5 — acceptance and report integration

- [x] Parameterize the established custody paths for the accepted feature-table artifact.
- [x] Add the manual acceptance-before-benchmark workflow and fixed-declaration guards.
- [x] Require benchmark manifests to match an accepted feature-set digest.
- [x] Exercise the generic renderer for all three v0.9 kinds and add dated-document templates.
- [ ] **The official run, in this fixed order and no other.** The engineering above merged on
  3 September 2026, so nothing here waits on a branch any more:
  1. Dispatch `Fetch point-in-time fundamentals` over the declared window and read its
     availability audit. *Measured but not yet run against the declared window — see v0.9.6.*
  2. Check the complete-season preflight, which decides whether the run is labelled exploratory
     before any result is seen rather than after.
  3. Record and verify custody of the accepted feature table through
     `Record official artifact custody` and `Publish encrypted custody copies`.
  4. Commit the dated acceptance document, which must name the accepted feature-set digest and
     carry the primary rulebook and capacity sources the tooling cannot verify
     (`docs/templates/fundamentals_acceptance.md`).
  5. Dispatch `Benchmark point-in-time fundamentals` from that digest, and commit its result
     regardless of sign (`docs/templates/fundamentals_benchmark.md`).

## v0.9.6 — the declared window becomes retrievable

The first dispatch of the retrieval surface was a measurement, and it found the official run
impossible as designed: **72.1 s per delivery day** (run `33760441164`, 30 days in 36 minutes)
is **40.2 hours** across the pre-registered 2,006-day window against a six-hour per-job ceiling,
and **83 MB per delivery day** retained is **163 GB** against roughly 14 GB of runner disk.
Nothing but a dispatched run could have shown this; every earlier v0.9 milestone was validated
on synthetic fixtures.

- [x] Stop retaining raw GRIB2 messages in the retrieval workflow. The retrieval manifest
  already records each message's digest, byte count and source URL, so the messages are not what
  the evidence rests on. This removes the disk ceiling outright.
- [x] Tile the window into slices retrieved in parallel — 23 slices of about 1 h 50 m at 90
  delivery days each — leaving the retrieval client untouched, because making it concurrent
  would change how an evidence path talks to the provider.
- [x] `combine-feature-tables`, which refuses anything that is not a tiling: an overlap rather
  than deduplicating it, a gap by name, and slices disagreeing on source, variable set or
  declared geography by naming the fields that differ.
- [x] Read feature tables with round-trip float precision wherever a digest is taken over them.
  The default parser is accurate to one unit in the last place, which no result here can see,
  but a digest has no tolerance and the acceptance gate is a digest.
- [ ] **The declared window is still not retrieved.** The 30-day dispatch is a measurement, not
  an accepted feature table.

## v0.9.7 — the retrieval survives its source

The declared window was dispatched for the first time on 4 September 2026 (run `33843070945`,
23 slices of 90 delivery days) and failed: six slices died on attempt 1 and four on attempt 2, so
`combine` never ran. Four distinct events did it — a connection reset, a truncated body, a `.idx`
sidecar indexing another publication, and an object reported missing — and each cost 90 delivery
days.

- [x] Classify every official-data HTTP failure by kind and preserve the status, so that only
  `404`/`410` mean absence. The key-layout loop reads absence alone as "not at this key"; a 5xx,
  a reset or a truncated body stops the retrieval rather than being reported as a provider
  non-publication that nothing downstream could detect as false.
- [x] Retry transport faults and 5xx answers, bounded at five attempts with 1, 2, 4 and 8 second
  backoff. Never retry absence, the sidecar mismatch or any other deterministic refusal, and do
  not add concurrency: that would change how an accepted evidence path talks to the provider.
- [x] Exclude a delivery day by name — `missing_object`, `sidecar_object_mismatch` — and continue,
  instead of aborting the slice, with both causes carried as a typed attribute rather than matched
  from message text. **Every other refusal still stops the retrieval**, and this item is void
  without the classification above.
- [x] Record `excluded_day_count_by_cause` in the retrieval and combined summaries, summing each
  slice's own total rather than recounting its capped list.
- [ ] **The declared window is still not retrieved.** This milestone makes the first step capable
  of finishing; it does not perform the run.

**The window is never shortened to fit a runner or to route around a source condition.** A
delivery day the provider did not publish is excluded by name and stays in the record as an
exclusion; it is not removed from the declared window.

**The window is never shortened to fit a runner.** The split, the boundary and the source are
pre-registered; trimming the window to make a job fit would be revising a declaration to suit an
operational constraint, which is exactly the move the pre-registration exists to prevent.

**A `workflow_dispatch` workflow must be on the default branch to be triggerable.** The sharded
retrieval and the acceptance preflight are therefore not dispatchable until they merge, and that
merge is the gate in front of every remaining step of the official run.
