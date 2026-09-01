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
5. `streamlit-dashboard` (v0.8)
6. `ai-explanations` (only after outputs and guardrails are validated)
7. `final-audit`

## Standing position (1 September 2026)

The approved scope in `PROMPT.md` is implemented. Every modeling milestone from v0.1 through
v0.7, plus the v0.7.11 run manifest and report contract, is landed on `main` and validated.
Nothing in the approved brief is waiting on an engineering decision.

What remains is not code. The one dated deadline was met on 1 September 2026. **The four items
still open each wait on an input only the operator can supply, or on a scope extension only the
user can approve.** Between 28 and 31 August the repository added roughly 3,100 lines of source,
3,000 lines of tests and 2,600 lines of documentation and retired none of them, because all four
were already blocked before that work began. Further audits, policies and refusals around a
blocked item do not retire it; they enlarge the machinery waiting on the same missing
declaration.

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

- **The ADMIE gate-closure schedule.** `config/admie_gate_closure.json` does not exist; only the
  format example does. The audit reports whatever closure it is given and refuses to supply the
  market rule, so it cannot run until the operator cites the day-ahead trading schedule with its
  rulebook section and effective dates, one regime per rule change across the audited history.
  Until then the live timing audit cannot run and the forecast quarantine cannot lift on timing.
- **The custody upload.** The encrypted copies of the accepted official history and of the
  ENTSO-E reconciliation artifact must be placed in operator-controlled storage. A committed
  fingerprint is not a durable copy, and no automation in this repository can perform or verify
  the upload.

### Waiting on a scope decision by the user

- **The ADMIE forecast quarantine.** Two exits exist and the repository cannot choose between
  them. Either the operator declares the gate closure and the quarantine is worked to a close
  through a live audited window and file-format acceptance, or ADMIE load and RES forecasts are
  removed from scope by a recorded decision. The price-history ML benchmark already stands
  without them. Leaving the quarantine open indefinitely is the one option that keeps producing
  work without producing acceptance.
- **v0.8, or any successor scope.** A research interface and exportable reports appear in the
  suggested branch sequence but not in `PROMPT.md`'s approved scope, so opening v0.8 is a scope
  change rather than the next milestone. The same holds for any revenue stream beyond DAM
  arbitrage. No design work should begin before `PROMPT.md` is amended.

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
- [ ] v0.8 — Research interface and exportable reports (the corrected v0.7 scope and its formal
  review are complete, but v0.8 remains gated until the user explicitly approves its design).
  - [x] Prerequisite: a versioned run manifest and report contract (v0.7.11), which the
    completed-v0.7 review named as the thing to define before any consumer couples to incidental
    summary keys. `greek_bess.reporting` carries any result summary verbatim under a stable
    projection and makes label retention executable. It adds no interface, exporter, rendering
    surface or dependency, and does not open v0.8. Policy in `docs/run_manifest_contract.md`.
  - [ ] A design answering, at minimum: what the landing state is when no judgmental input has
    been declared (every one of them has no default by recorded decision, and an interface must
    render something); how every rendered figure carries its label and the standing exclusions;
    and what an export refuses to contain. Reconsidered 2026-08-31: v0.8 appears in the suggested
    branch sequence but not in `PROMPT.md`'s approved scope, so opening it is a scope change
    rather than the next milestone.

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
- [~] Accept ADMIE load/RES file formats and prove pre-auction publication timing.
  - [x] Executable publication-timing audit. `audit-admie-publication-timing` compares each
    retrieved file's publication time against a declared dated gate-closure schedule with no
    default, per filetype and delivery day, without parsing any file. Evidence witnessed by a
    pre-closure retrieval is separated from publisher-asserted timestamps and never promoted to
    it; a publication exactly at the closure counts as late; each accepted day names the
    decision-time revision and counts the revisions that superseded it. Policy in
    `docs/admie_publication_timing_policy.md`.
  - [x] `Audit ADMIE publication timing` workflow, which retrieves every revision covering a
    declared window and uploads the manifest, per-day verdicts, per-observation evidence and
    summary.
  - [ ] Operator declaration of the gate-closure schedule. The repository ships the format in
    `config/admie_gate_closure.example.json` and refuses to supply the market rule: the audit
    reports whatever closure it is given and cannot check a declaration against the rulebook.
  - [x] Confirm the leakage-relevant names against the live catalog and a non-empty retrieval.
    On 2026-08-31 the catalog identified the ISP1 and ISP2 day-ahead load/RES pairs; retrieval
    over 26-28 August 2026 discovered 12 ISP1 files (six per type) and six ISP2 files (three per
    type). The catalog-valid DAM pair returned none and is no longer declared leakage-relevant.
    Evidence in `docs/admie_filetype_acceptance_2026-08-31.md`.
  - [ ] A live publication-timing audit over the confirmed ISP1/ISP2 filetypes. Non-empty
    discovery settles names and window only; no publication timestamp has yet been compared with
    a verified gate closure.
  - [ ] File-format acceptance against real load/RES files. Timing acceptance establishes
    publication timing alone; the quarantine is lifted only by format acceptance and a recorded
    decision as well.
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
  - [ ] Operator supplies the age recipient and dispatches it. Custody is not complete until the
    encrypted copies exist, and the second copy under separate control remains outside this
    repository's knowledge.
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
