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
- [ ] v0.7 — Probabilistic stress testing.
  - [x] Foundation: seasonal block bootstrap, reproducible seeds and sampled-block provenance.
  - [x] Deterministic additive price-level shock with interval provenance.
  - [x] Independent deterministic dispatch across validated bootstrap paths.
  - Spread, outage and cannibalisation shocks. Negative-price-event transformations are deferred.
  - P5/P50/P95, loss probability and worst-case paths.
- [ ] v0.8 — Research interface and exportable reports.

## Parallel acceptance track

- [x] Validate real HEnEx workbooks.
  - Official `20260824` and `20260825` English v01 result workbooks.
  - 96 quarter-hour intervals per day and 192 contiguous intervals combined.
  - No missing prices, duplicate intervals, gaps, overlaps or quality errors.
- [ ] Validate the ENTSO-E client with a private token.
- [ ] Reconcile overlapping official sources.
- [x] Record the accepted HEnEx source versions, retrieval date and raw hashes.
- [ ] Record the ENTSO-E retrieval metadata and raw-response hashes.
- [x] Run and accept the 2020-2025 HEnEx annual archives live.
- [ ] Run and accept the incremental 2026 HEnEx daily retrieval live.
- [ ] Accept ADMIE load/RES file formats and prove pre-auction publication timing.
