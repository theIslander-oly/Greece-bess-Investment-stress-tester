# Project status

**Version:** 0.7.2
**Updated:** 27 August 2026
**Status:** Official multi-year operational acceptance passed; broader stress testing pending

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

## Validation still required

- Run ENTSO-E client with a private user token.
- Compare overlapping HEnEx and ENTSO-E official intervals.
- Accept ADMIE load/RES formats and prove pre-auction publication timing.

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
calibration story. The next isolated v0.7 modeling milestone is deterministic
availability/outage-path integration, which requires explicit approval before implementation,
preceded by a documented bootstrap source-era/resolution policy. Negative-price-event
transformations remain deferred. ENTSO-E reconciliation, ADMIE timing acceptance, durable
private storage of the accepted history, and per-year replay decomposition remain parallel
tasks.
