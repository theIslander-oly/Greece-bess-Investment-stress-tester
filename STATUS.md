# Project status

**Version:** 0.6.3
**Updated:** 26 August 2026  
**Status:** 2020-2025 official history accepted; v0.6.3 fix ready for manual review

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

## Validation still required

- Run ENTSO-E client with a private user token.
- Compare overlapping HEnEx and ENTSO-E official intervals.
- Run the optimizer and forecast backtest over a complete official multi-year history.

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

Complete the v0.6.3 daily-catalog fix PR, rerun the incremental 2026 daily range and record its
acceptance evidence before probabilistic stress testing on `stress-testing`.
