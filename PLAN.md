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
6. `ai-explanations` (only after outputs and guardrails are validated)
7. `final-audit`

## Standing position (1 September 2026)

Every modeling milestone from v0.1 through v0.7, plus the v0.7.11 run manifest and report
contract, is landed on `main` and validated: the complete v0.7 scope was re-verified on
1 September 2026 on the unchanged v0.7.11 implementation (Ruff, mypy, all 301 tests, clean
wheel build). The dated deadline was met on 1 September 2026 and the custody chain behind it
closed the same day. The ADMIE forecast quarantine, open since 26 August, was closed by removing
ADMIE load and RES forecasts from scope rather than by working it to acceptance.

**v0.8 is open.** The user approved it on 1 September 2026, `PROMPT.md` was amended the same
day, and `docs/v0.8_design.md` is the design of record. v0.8.0, the report rendering foundation,
and v0.8.1, multi-run composition, both landed on 1 September 2026 and the package is at 0.8.1.
The only engineering milestone left in v0.8 is v0.8.2, which is a decision rather than an
implementation: whether an interactive viewer is added on top of the static renderer. It is not
assumed, and if it is declined v0.8 completes with the static renderer.

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

### Waiting on an operator declaration

- **The second custody copy.** Both encrypted copies were published as release
  `custody-2026-09-01` on 1 September 2026 and the private key was exercised the same day, so the
  accepted artifacts are recoverable. What remains is a copy under separate control: one release
  is one failure domain, and nothing in this repository can perform or verify that placement.
- **`ENTSOE_SECURITY_TOKEN`.** The secret is no longer configured, so
  `Reconcile HEnEx and ENTSO-E prices` refuses at its guard step and the reconciliation cannot be
  re-run. The accepted evidence is safe in the custody copy; only regeneration is blocked.

### Resolved on 1 September 2026: the v0.8 scope decision

- **v0.8 is approved and open.** The user approved it on 1 September 2026; `PROMPT.md` now
  carries the amended scope bullet and `docs/v0.8_design.md` records the design (decision entry
  2026-09-01). Any revenue stream beyond DAM arbitrage still waits on its own scope decision
  and independent validation — opening v0.8 changes nothing there.

### Operating constraint on live retrieval

Live market endpoints are reachable only from GitHub Actions runners. The development
environment's egress policy refuses `www.admie.gr`, so catalog queries, file retrieval and
timing audits are performed by dispatching the relevant workflow and reading its uploaded
evidence, never from a working checkout. Plan any live acceptance step as a workflow run.

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
- [ ] v0.8 — Research interface and exportable reports (**opened 2026-09-01 by user approval**;
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
    `docs/implementation_report_v0.8.0.md`). `render-report` CLI and
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
    `docs/implementation_report_v0.8.1.md`). An index across many manifests, grouped by basis,
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
  - [ ] v0.8.2 — Interactive viewer decision. A separate dated decision on whether a local
    interactive viewer (e.g. Streamlit) is added on top of the static renderer; it is a new
    dependency and rendering surface and is not assumed. If declined, v0.8 completes with the
    static renderer. AI-generated explanations remain outside v0.8 either way.

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
