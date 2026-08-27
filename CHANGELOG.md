# Changelog

All notable project changes are documented here.

## [Unreleased]

### Added

- `decompose-annual-replay` command and a `greek_bess.analysis` package, which regroup an
  already-accepted replay into delivery years without adding a model, market or
  transformation. A delivery year is the calendar year of the interval's CET/CEST market-day
  start, matching the committed custody records. The per-year overview carries market-day
  coverage, an explicit partial-year flag, interval counts by resolution, preserved negative,
  zero and missing price counts, price context including the mean daily price range, and the
  perfect-foresight ceiling; a second table reports forecast capture per method on that
  method's own backtested days; a third restricts every method to the days all methods
  backtested and records the ceiling spread that proves the comparison is like-for-like.
  Per-market-day figures are within-period averages and nothing is annualized. No probability,
  percentile, loss metric or ranking of years is produced.
- `optimize-perfect-foresight --daily-solves` and `optimize_daily_perfect_foresight`, which
  solve every market day independently and compose the schedules. This publishes the
  daily-composed mode the 2026-08-27 acceptance ran through a temporary runner, requires the
  terminal SOC to equal the initial SOC, and is the basis on which no trade can span a
  delivery-year boundary. The composed schedule carries a `market_day` column and its summary
  records per-day solver statuses and the largest terminal-energy error.
- `Decompose the accepted replay by delivery year` GitHub Actions workflow, which verifies an
  accepted `greek-dam-official-history` artifact against its committed custody record before
  consuming it, then runs the daily-composed ceiling, the requested causal naïve backtests and
  the decomposition inside Actions, publishing only per-year aggregates to the job summary.

- `record-custody` and `verify-custody` commands and a `greek_bess.data.custody` module, which
  fingerprint an accepted official artifact without recording any price. A custody record holds
  per-file digests plus content-level invariants of the normalized series — interval count,
  window, market-day count, negative/zero/missing price counts, counts by delivery year,
  resolution and source, quality-flag counts by name — and a digest of the interval and price
  series computed over sorted `(delivery_start_utc, delivery_end_utc, price)` triples at six
  fixed decimals, so it is independent of CSV column order, file formatting and float repr.
  `verify-custody` returns exit code 2 on any difference.
- `Record official artifact custody` GitHub Actions workflow, which downloads an accepted
  artifact inside Actions and either records a custody record when none is committed or
  verifies the artifact against the committed one and fails on any difference.
- `docs/official_artifact_custody.md`, recording the durable storage procedure for accepted
  official artifacts: encrypted assets on a private repository release, fingerprinted by
  committed custody records, with operator steps, a verification drill and a taxonomy
  separating a corrupted copy, a revised official publication and a change in this project's
  own normalization.
- `read_canonical_csv` in `greek_bess.data.schema`, which restores a written canonical history
  with its timezone-aware views and decoded quality flags. The CLI's private reader now
  delegates to it.
- `merge-canonical` command and `concat_canonical` helper, which join normalized CSV files
  from one official source into a single quality-assessed history and refuse to mix sources or
  to drop a repeated interval.
- `Reconcile HEnEx and ENTSO-E prices` GitHub Actions workflow, which reads the accepted
  `greek-dam-official-history` artifact from an earlier run, derives the reconciliation window
  from that history, retrieves ENTSO-E A44 prices for the same window with the encrypted
  repository secret, classifies every interval with `compare-sources` and uploads the interval
  detail as an artifact while keeping official prices out of the job log.
- `docs/official_source_reconciliation_2026-08-27.md`, recording the passed live reconciliation
  of the accepted HEnEx history against ENTSO-E A44 prices over market days 1 November 2020
  through 25 August 2026: 74,662 of 74,663 intervals match within EUR 0.000001/MWh, neither
  source omits an interval the other publishes, and one 29 October 2023 interval differs by
  EUR 0.01/MWh.
- Bounded retry with backoff for ENTSO-E timeouts, connection failures and 429/5xx responses,
  with the socket timeout, attempt budget and backoff exposed on `fetch-entsoe`.
- The request period and the acknowledgement reason in a rejected ENTSO-E request's error.
- Reader-facing "What this tool cannot tell you" README section covering the April 2026 entry
  of batteries into the Greek DAM/IDM, expected spread compression from the arriving storage
  fleet, and the exclusion of balancing-market and availability-support revenues.
- `CLAUDE.md` and a `.claude/` SessionStart hook that prepares a Python 3.12 virtual
  environment so Claude Code on the web sessions can run Ruff, mypy and the test suite.
- Explicit documentation that the dispatch summary's equivalent full cycles are grid-side while
  the degradation model uses cell-side cycles.
- `docs/official_multiyear_operational_acceptance_2026-08-27.md`, recording live acceptance of the
  existing perfect-foresight dispatch and forecast-dispatch backtests over all 74,663 official
  HEnEx intervals from 1 November 2020 through 25 August 2026.
- Aggregate input, constraint, leakage, settlement, coverage, exclusion and determinism evidence,
  including the accepted artifact SHA-256, solver identity and software versions.

### Changed

- Artifact retention on `Fetch official Greek market history`, `Fetch ENTSO-E prices` and
  `Reconcile HEnEx and ENTSO-E prices` is raised from 7 to 90 days, so a passed acceptance no
  longer has a one-week shelf life.

- ENTSO-E A44 parsing now honors the document's declared curve type. Under `A03` a point's price
  holds until the next declared position, so those intervals are materialized and labelled
  `entsoe_variable_block_repeat` instead of being reported as missing; `A01` documents are
  unchanged and an unknown curve type is rejected. The previous behavior understated ENTSO-E
  coverage of the accepted window by 4,874 intervals (decision entry 2026-08-27).
- `PLAN.md` records private-token validation and overlapping-source reconciliation as accepted;
  `STATUS.md` and `LIMITATIONS.md` record the reconciliation result and drop the pending items it
  resolves.
- Repositioned the project documentation as a Greek DAM battery replay and research benchmark;
  repository, package and CLI names are unchanged (decision entry 2026-08-27).
- Corrected the v0.7 scope from "probabilistic stress testing" to deterministic named
  scenarios: source-era/resolution policy, availability/outage paths, spread-compression
  transformations and non-probabilistic scenario ranges. P5/P50/P95 and loss-probability
  outputs were removed pending a defensible calibration methodology (decision entry
  2026-08-27).
- Documented that a constant price-level shift leaves within-path spreads unchanged and is
  therefore a weak stress for arbitrage value (`METHODOLOGY.md` §8, `LIMITATIONS.md`).
- Added parallel-track items for durable private storage of the accepted history before
  artifact expiry (2 September 2026) and a per-calendar-year replay decomposition.
- `PLAN.md` records the incremental 2026 daily retrieval as accepted; workflow run `32971677163`
  and the hash-verified artifact prove the previous pending state was stale.
- `STATUS.md` records the operational acceptance and removes the completed multi-year optimizer and
  forecast-backtest validation item.

### Interpretation limits

- No model, market, stress transformation, degradation, finance or interface behaviour changed;
  no production code was modified.
- Perfect-foresight results are historical gross-margin upper bounds and forecast results are
  historical benchmark evidence, not expected revenue, forecasts, probabilities, rankings of future
  performance or investment conclusions.

## [0.7.2] — 2026-08-27

### Added

- Strict multi-path bootstrap validation and independent deterministic dispatch using identical
  battery and availability assumptions.
- Interval schedules retaining path/canonical identity and path-level operational/revenue
  summaries.
- `dispatch-bootstrap-paths` CLI plus deterministic synthetic API, failure and CLI regressions.

### Interpretation limits

- Results remain synthetic perfect-foresight gross-margin upper bounds, not forecasts,
  probabilities, expected revenues, finance outputs or investment evidence.
- Degradation, percentiles, probability metrics, rankings and negative-price-event
  transformations are not included.

## [0.7.1] — 2026-08-27

### Added

- Strict additive price-level shock configuration with a finite EUR/MWh shift and required
  transformation identifier.
- Deterministic public Python API and `apply-price-level-shock` CLI workflow.
- Interval provenance containing path identity, UTC key, original and shocked prices, method,
  configured shift and input source metadata.
- Synthetic tests for exact arithmetic, reproducibility, signed prices, CLI artifacts and
  rejection of missing, duplicate or incomplete paths.

### Interpretation limits

- Shocked paths are synthetic sensitivities, not forecasts, probabilities, revenues or
  investment evidence.
- No spread, negative-price-event, outage or cannibalisation shocks are included.

## [0.7.0] — 2026-08-26

### Added

- Deterministic meteorological-season block bootstrap with explicit target dates, path count,
  block length and random seed.
- Block-level provenance recording target/source dates, season, interval count, candidate count
  and sampled candidate index.
- Public Python API and `generate-bootstrap-paths` CLI with path, provenance and summary outputs.
- Synthetic tests for reproducibility, timezone-aware timestamps, zero/negative prices, spring
  and autumn DST market days, strict configuration and missing-observation rejection.

### Interpretation limits

- Bootstrap paths are labelled synthetic scenarios, not forecasts, probability-calibrated
  outcomes, expected revenues or investment evidence.
- Dispatch, degradation, finance, percentile/loss outputs and additional shocks are excluded
  from this foundation.

## [0.6.3] — 2026-08-26

### Fixed

- Parse live HEnEx daily result labels that omit the `.xlsx` suffix.
- Use the current `/web/guest/` Liferay pagination route and redirect parameter.
- Continue through catalogue pages newer than the requested range.
- Reject repeated catalogue pages and missing requested delivery days.

### Validation

- The preceding 2020-2025 workflow run passed and its private artifact was integrity-checked.
- Failed incremental workflow run 32969157951 is retained as evidence of the live-layout defect.
- Six focused catalogue regression tests cover the corrected behavior.

## [0.6.2] — 2026-08-26

### Fixed

- Select the latest HEnEx daily workbook revision before parsing superseded files.
- Safely extract the official nested 2021 DAM archive and retain its parent/child hashes.
- Accept only a tightly bounded one-cent MCP rounding consensus when one or two cross-border
  asset rows differ from the dominant Greek-zone value; flag every affected interval.
- Continue to reject ties, larger differences and non-majority MCP disagreements.

### Validation

- Live HEnEx archives for 1 November 2020 through 31 December 2025 produced 51,915 contiguous
  intervals with no missing or duplicate UTC keys.
- All six annual archive hashes, row counts, DST validation and provider-row rounding flags are
  recorded in `docs/official_history_acceptance_2026-08-26.md`.
- The failed first workflow run is retained as evidence of the acceptance defects that prompted
  this patch.

## [0.6.1] — 2026-08-26

### Added

- Verified HEnEx annual DAM-results archive register for 2020-2025.
- Safe ZIP extraction restricted to English `EL-DAM_Results` workbooks.
- Multi-workbook latest-revision normalization and conflict rejection.
- Incremental HEnEx daily results discovery for unarchived dates.
- ADMIE filetype and range API client with latest-revision selection.
- File-level retrieval manifests with coverage, publication/retrieval timestamps, hashes and
  leakage classifications.
- Exact HTTPS source-host allowlists and atomic raw-file writes.
- Manual private GitHub Actions retrieval workflow.
- Eight archive, ADMIE, daily-catalog and HTTP-security tests.

### Changed

- Package version increased from 0.6.0 to 0.6.1.
- Official multi-year evidence acquisition now precedes v0.7 stress testing.
- ADMIE forecast candidates are explicitly quarantined pending publication-time acceptance.

### Validation

- All 68 source tests pass.
- Clean GitHub CI passed Ruff, mypy, all 68 tests and a wheel build.
- Live 2020-2026 provider retrieval remains required before evidence acceptance.

## [0.6.0] — 2026-08-25

### Added

- Explicit unlevered, nominal, pre-tax and pre-subsidy project-finance model.
- Continuous daily operating-path validation from configured project start through end.
- Mandatory operating-margin provenance labels for perfect foresight, historical
  forecast backtests and user-supplied scenarios.
- Separately itemized battery, power-conversion, grid, development/construction and other
  initial CAPEX.
- Fixed OPEX, insurance, asset management, discharge-linked variable OPEX and nominal
  OPEX escalation.
- Dated augmentation cost integration from v0.5 daily degradation-dispatch outputs.
- Project-end decommissioning cost and residual value.
- Daily and annual cash-flow artifacts with exact-date discount factors.
- Unlevered NPV and IRR, with explicit suppression when multiple cash-flow sign changes
  make IRR ambiguous.
- Simple and discounted payback dates and years.
- Maximum initial CAPEX, break-even market-margin realization and break-even average
  annual market-margin outputs.
- `evaluate-project-finance` CLI command and illustrative non-project-specific finance
  configuration.
- Seven new finance and CLI tests, including end-to-end degradation-to-finance coverage.

### Changed

- Package version increased from 0.5.0 to 0.6.0.
- v0.5 augmentation costs are now explicitly consumable by the separate finance layer.
- The immediate next milestone is probabilistic stress testing.

### Validation

- All 60 automated tests pass.
- Exact cash-flow components, NPV reconstruction, break-even values, payback behavior and
  IRR status are covered.
- Missing, duplicate and unsorted daily operating paths are rejected.
- Invalid costs, margin labels and realization fractions are rejected.
- Existing ingestion, DST, optimizer, forecast, leakage, ML and degradation tests remain
  green.

### Interpretation limits

- Finance outputs inherit the evidence quality of the supplied operating margins.
- A perfect-foresight operating path remains an upper bound after NPV treatment.
- The included finance values are illustrative round numbers, not Greek project costs.
- Taxes, subsidies, debt, financing fees, working capital, grid feasibility, bid
  acceptance and non-DAM revenues remain excluded.

## [0.5.0] — 2026-08-25

### Added

- Cohort-based battery state with separately aged initial and augmentation capacity.
- Linear calendar fade and cell-discharge equivalent-cycle fade assumptions.
- Usable energy and charge/discharge power evolution with configurable power coupling.
- Proportional daily cell-throughput allocation across usable cohorts.
- Retained-capacity warranty, EFC throughput and retirement-threshold indicators.
- Optional enforceable per-cohort EFC warranty headroom in daily dispatch.
- Dated augmentation/replacement energy, power and cost records with explicit retirement
  of named cohorts.
- `simulate-degradation-dispatch` CLI command.
- Interval, daily, final-cohort and JSON summary degradation artifacts.
- Illustrative degradation and augmentation configuration.
- Eleven new degradation, warranty, augmentation/replacement, DST and CLI tests.

### Changed

- Package version increased from 0.4.0 to 0.5.0.
- The immediate next milestone is now unlevered project finance.
- Documentation distinguishes physical capacity fade from the optional per-MWh monetary
  degradation adder already available in dispatch configuration.

### Validation

- All 53 automated tests pass.
- Exact additive calendar/cycle fade arithmetic is tested.
- Augmentation cohorts retain independent age and throughput histories.
- Beginning-of-day degraded limits constrain the current market-day solve; current-day
  discharge changes only end-of-day and future capacity.
- Enforced EFC headroom prevents later dispatch from exceeding the modeled throughput
  ceiling.
- A 92-quarter-hour spring DST market day remains complete.
- Existing ingestion, optimizer, forecast, leakage and like-for-like tests remain green.

### Interpretation limits

- The generic fade and warranty parameters are illustrative, not OEM evidence.
- The degradation-aware dispatch remains a daily perfect-foresight DAM gross-margin upper
  bound, not expected revenue.
- Augmentation cost is recorded separately; cash-flow timing begins in v0.6.
- Temperature, C-rate, depth-of-discharge, nonlinear knee and controller-specific cohort
  dispatch models remain outside v0.5.

## [0.4.0] — 2026-08-25

### Added

- Causal calendar, prior-price lag and matching-slot rolling feature table.
- Feature-level availability provenance and explicit no-target-price policy.
- Deterministic ridge and histogram-gradient-boosting benchmark models.
- Time-based training, validation and held-out test periods.
- Walk-forward expanding/optional rolling-window refits with exact training-date logs.
- Validation-only model selection and separate validation/test metric rankings.
- Forecast-error comparison against daily, weekly, rolling-mean and ensemble baselines.
- Like-for-like held-out dispatch benchmarking over common complete forecast days.
- Cross-method realized margin, perfect-foresight capture and regret rankings.
- `forecast-ml` and `backtest-ml-dispatch` CLI commands.
- GitHub Actions wheel construction after the complete test suite.
- Leakage, split, refit, DST, common-horizon, settlement and CLI regression tests.

### Changed

- Package version increased from 0.3.1 to 0.4.0.
- Forecast metrics accept any explicitly supplied forecast column, enabling ML and naïve
  methods to use the same signed-price-safe calculations.
- Scikit-learn is now a direct runtime dependency.

### Validation

- All 42 automated tests pass.
- Future-price mutations cannot change earlier ML predictions.
- Hourly and quarter-hour DST behavior remains valid.
- Synthetic fixtures test engineering behavior only and provide no investment evidence.
- The production HEnEx parser accepted the official English v01 result workbooks for
  24 and 25 August 2026: 96 quarter-hour intervals per day, 192 contiguous intervals,
  no missing prices and no quality errors. Raw hashes are recorded in the official-data
  acceptance report; the workbooks are not bundled.

### Still pending

- Private-token ENTSO-E production acceptance, official-source reconciliation and
  multi-year Greek market benchmarking.
- Publication-time validation before any exogenous feature is admitted.
- Degradation state evolution, project finance, Monte Carlo and user interface.

## [0.3.1] — 2026-08-25

### Fixed

- Forecast-dispatch summaries now disclose every market day excluded because the
  selected forecast is incomplete.
- Full requested-period forecast coverage is retained instead of being recalculated as
  100% after incomplete days are removed.
- Spring-DST daily-persistence gaps are reported correctly as one missing hourly
  interval or four missing quarter-hour intervals.

### Added

- Separate full-period and backtested-only forecast metrics.
- Evaluation/backtest day and interval counts, coverage fractions, missing interval
  count, and structured excluded-day details.
- Hourly and quarter-hour spring-DST regression tests plus an ensemble-completeness test.
- NumPy as an explicit direct runtime dependency.

### Changed

- Package version increased from 0.3.0 to 0.3.1.
- ENTSO-E requests now identify the current package version in their user-agent.

### Validation

- All 35 automated tests pass.
- Source and packaged-wheel test suites pass independently.
- Official-data acceptance remains pending.

## [0.3.0] — 2026-08-25

### Added

- Strictly causal daily-persistence, weekly-persistence and rolling-mean price baselines.
- Leakage-safe ensemble forecast using only prior market days.
- Walk-forward forecast metrics compatible with negative and zero prices.
- Negative-price precision and recall alongside MAE, RMSE, bias, WAPE and correlation.
- Day-by-day dispatch planned on forecast prices and settled on realized DAM prices.
- Like-for-like daily perfect-foresight ceiling, value-capture and regret outputs.
- Daily and interval-level forecast-dispatch backtest results.
- `forecast-naive` and `backtest-forecast-dispatch` CLI commands.
- Durable `AGENTS.md`, `PLAN.md` and `STATUS.md` project context.

### Changed

- Package version increased from 0.2.0 to 0.3.0.
- Perfect-foresight optimization now uses a negligible numerical throughput tie-breaker
  to avoid unnecessary zero-value cycling in economically degenerate solutions.
- README expanded with forecast and backtest workflows.

### Validation

- All 32 automated tests pass.
- Tests cover future-data mutation, spring DST, negative-price metrics, exact forecast
  value capture, deliberately wrong forecasts, and end-to-end CLI outputs.

### Still pending

- Official-data acceptance and multi-year official backtesting.
- ML price forecasts benchmarked against the v0.3 naïve baselines.
- Degradation state evolution, project finance, Monte Carlo and user interface.

## [0.2.0] — 2026-08-24

### Added

- Mixed-integer perfect-foresight Greek Day-Ahead Market dispatch optimizer.
- Grid-meter charge and discharge accounting with separate one-way efficiencies.
- Power, energy, SOC, availability, grid-limit and terminal-SOC constraints.
- Binary charge/discharge exclusivity, including correct behavior at negative prices.
- Optional self-discharge and daily equivalent-cycle limits.
- Buy fees, sell fees and degradation-throughput costs.
- Interval schedule and auditable aggregate margin decomposition.
- `optimize-perfect-foresight` command-line workflow.
- Illustrative 50 MW / 100 MWh battery configuration.
- GitHub Actions test workflow for Python 3.12.

### Changed

- Package version increased from 0.1.0 to 0.2.0.
- README expanded with dispatch conventions, usage and limitations.
- Data quality now rejects gaps or overlaps between consecutive UTC intervals.
- Availability arrays remain aligned when input price rows are unsorted.

### Validation

- All 24 automated tests pass.
- A 744-interval synthetic engineering benchmark solved to optimality in the
  development environment. It is not an official-data or investment result.

### Still pending

- Live validation with a user-supplied HEnEx workbook or private ENTSO-E token.
- Real HEnEx-versus-ENTSO-E overlap comparison.
- Forecast-based dispatch, degradation state evolution, financial modeling,
  Monte Carlo stress testing and user interface.

## [0.1.0] — 2026-08-24

### Added

- Canonical Greek Day-Ahead Market interval schema.
- ENTSO-E A44 client and HEnEx workbook parser.
- DST-safe UTC, market-clock and Greece-clock timestamps.
- Data quality and official-source comparison tools.
- Deterministic, clearly labelled synthetic fixtures for tests and demos.
