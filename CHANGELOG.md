# Changelog

All notable project changes are documented here.

## [Unreleased]

### Added

- `apply-negative-price-events` and `greek_bess.stress.apply_negative_price_events`, completing
  the approved v0.7 modeling scope. Each event declares an identifier, inclusive UTC start,
  exclusive UTC end and strictly negative absolute replacement price in EUR/MWh; every
  consequential field has no default and `events: []` is the exact identity.
- Event occurrence is declared, never sampled, inferred, fitted, ranked or searched. Frequency,
  rate, likelihood, probability, percentile and expected-count fields are refused as unknown.
  Windows must align to whole delivery intervals, cover at least one interval and not overlap.
- One-to-one provenance covers every path interval, including untouched rows. The summary records
  the policy, method, full configuration, applied interval counts and negative/zero counts before
  and after. Existing signed prices outside named windows are unchanged and no price is clipped.
- `docs/implementation_report_v0.7.9.md`, and a dated decision defining the event unit and the
  refusal to sample occurrence.

- `greek_bess.stress.build_availability_profile` and `dispatch-bootstrap-paths
  --availability-schedule`, completing the last approved v0.7 modeling item. An availability
  schedule is a declared baseline available fraction with **no default** plus zero or more
  declared outage windows, each with its own available fraction in [0, 1]. Timing, duration and
  depth are judgmental scenario inputs and are never sampled: a forced-outage rate would be an
  uncalibrated probability, and a configuration carrying one is refused by name.
- A window is applied whole to every interval it covers. A boundary falling strictly inside a
  delivery interval is refused, naming the interval, rather than prorated or rounded — prorating
  would apply a schedule finer than the one declared. Overlapping windows, a window covering no
  dispatched interval, reversed or empty windows, naive timestamps, duplicate outage identifiers
  and out-of-range fractions are all refused. A schedule with an empty window list is the
  declared full-availability scenario.
- The profile is built from the paths' own canonical UTC keys, so 23/25-hour market days and the
  quarter-hour regime are handled by construction, and paths that do not share one interval
  identity are refused. Per-interval provenance records the schedule, the baseline, the outage
  covering each interval and the applied fraction, and `dispatch-bootstrap-paths` writes it as an
  `.availability.csv` sidecar.
- The dispatch summary records a declared schedule by identity — `schedule_id`, baseline,
  window count, derated intervals and hours, minimum fraction and each window with its applied
  interval count — so a margin traces back to the outage assumption rather than to an anonymous
  array of fractions.

### Changed

- Completed the formal v0.7 consistency review across public APIs, CLI surfaces, provenance,
  summaries, tests, methodology, limitations, decisions and implementation reports. The review
  found no correctness or data-integrity defect and confirmed the missing-price, signed-price,
  time-ordering, realized-settlement, equivalent-basis and non-probabilistic invariants.
- Reconciled one roadmap wording contradiction: differing declared availability schedules are
  scenario judgments carried as provenance, not part of the equivalent asset-and-sample basis.
  Battery parameters, terminal-energy constraints, source-era selection and path identity must
  still match, and an unrecorded availability assumption is still refused.

- The scenario-ensemble equivalent-basis check no longer covers the availability assumption.
  The basis is now the asset and the sample — battery parameters, terminal-energy constraint,
  source-era selection and path identity — while the price transformation and the availability
  schedule are the judgments under examination and are expected to differ. Without this an
  ensemble could never place a declared outage against a baseline, which is the comparison an
  outage scenario exists to make. Availability is carried as provenance instead: every margin
  row gains `availability_type`, `availability_schedule_id` and `availability_declaration`, each
  range row names the availability at both ends, and the summary records each scenario's
  declaration. An unrecorded availability assumption is still refused. See the dated
  `DECISIONS.md` entries of 2026-08-31.

- `report-scenario-ensemble` command and `greek_bess.stress.report_scenario_ensemble`, which
  compose bootstrap-path dispatch results already produced under two or more named scenarios and
  report the minimum, maximum and spread of their margin outcomes. Ranges are taken per bootstrap
  path — nothing is aggregated across paths, because a total or an average over sampled paths
  would read as an expectation the uniform block resampling cannot support. The milestone
  composes accepted outputs and adds no price transformation, dispatch mode, forecast method or
  finance treatment.
- Every scenario is named by the caller through an explicit manifest. There is no default
  scenario set and no implicit baseline: `transformation_summary_json` is a required key, so a
  scenario with no transformation declares that as `null`, and an ensemble of fewer than two
  scenarios is refused.
- The non-probabilistic framing is enforced rather than described.
  `greek_bess.stress.FORBIDDEN_REPORT_TERMS` lists the excluded vocabulary — probability,
  percentile, likelihood, expected value, mean, median, quantile, loss, rank, central and others —
  and every emitted column name and summary key, including nested provenance keys, is checked
  against it before the result is returned. A field such as `p95_margin_eur` raises rather than
  being written.
- Scenarios are combined only on an equivalent basis. Differing battery parameters,
  terminal-energy constraint, selected source era or path identity are refused with the
  mismatching basis named and both values shown; the terminal-energy constraint is checked
  separately from the rest of the battery configuration so a day-end energy difference is
  refused by that name. Differing declared availability schedules remain scenario provenance.
- Provenance on every reported figure: `scenario_margins` carries the scenario name,
  transformation method, transformation ID, recorded transformation parameters, source-era
  resolution and day span, input run identity and bootstrap seed for each scenario and path, and
  `scenario_ranges` repeats scenario name, transformation and run identity for the scenarios at
  both ends of each path's range.
- `docs/implementation_report_v0.7.7.md`, and dated `DECISIONS.md` entries covering the
  non-probabilistic framing and the equivalent-basis refusal rule.

### Fixed

- Replaced generic-unit `pd.Timedelta` construction with explicit units in synthetic, HEnEx and
  ENTSO-E ingestion and in the two affected tests, removing the NumPy generic-unit deprecation
  the suite had been emitting.
- Scoped the pytest warning gate instead of promoting every warning to an error. `filterwarnings`
  now fails on warnings attributed to `greek_bess` or to the project's own test modules and
  reports the rest: dependencies are installed from ranges, so a blanket policy would let an
  upstream release rather than a reviewed change decide when validation breaks. The narrowed gate
  still catches the deprecation above, because pandas attributes it to the constructing line.
  `tests/test_warning_policy.py` covers the deprecation at each call site and the policy's scope.
- Repaired the declared project version, which had drifted between `pyproject.toml` (`0.7.6`) and
  `greek_bess.__version__` (`0.7.2`). The package version is sent as the `User-Agent` on official
  HEnEx and ENTSO-E retrievals, so the stale value mislabelled the client that fetched an accepted
  artifact. `tests/test_project_metadata.py` locks `pyproject.toml`, `greek_bess.__version__`, the
  README release line and that header together. The version stays at `0.7.6`, because this is a
  maintenance correction and not a milestone; the changelog's released sections still stop at
  `[0.7.2]`, with `0.7.3`-`0.7.6` content under `[Unreleased]`.
- Corrected custody wording that read as a claim about stored copies. The records committed under
  `docs/custody/` are fingerprints, not durable encrypted copies; the operator upload is not
  verified complete in the repository record, and nothing here reads live GitHub release state.
- Aligned the limitations with the decision to exclude scenario probability estimates unless an
  independently validated calibration methodology is approved.

### Added

- `compress-spread` command and `greek_bess.stress.apply_spread_compression`, a deterministic
  compression of within-day spread about a declared daily reference level:
  `compressed = reference + factor * (price - reference)` over each path's CET/CEST market day.
  Every within-day range is scaled by exactly the factor; a factor of 1.0 is the identity and 0.0
  flattens each day onto its reference. `reference_basis` is declared with no default
  (`daily_mean` preserves each daily mean exactly, `daily_median` does not and the summary
  reports the resulting shift), the factor is bounded to [0, 1], and spread widening is out of
  scope. Zero and negative results are preserved and never clipped, so intervals can cross zero;
  the count is reported as `sign_change_interval_count`. The summary also reports mean and
  maximum daily range and negative and zero interval counts, before and after. Interval
  provenance records the market day, reference level, factor, basis, original and compressed
  prices and input source metadata. Missing prices are refused explicitly, because one would
  propagate through its market day's reference level.

- `scripts/bootstrap-dev-env.sh`, a tracked, editor-neutral development environment bootstrap.
  It creates or updates `.venv` on Python 3.12, installs the project with its development
  extras, and optionally appends `VIRTUAL_ENV`/`PATH` exports to a file for callers that source
  an environment file. Local session tooling should call it rather than reimplement the steps.

- A decision entry scoping custody to retrieved official artifacts. Derived evidence such as
  the `annual-replay-decomposition` artifact gets no custody record: it carries no
  interval-level price and no provider that could revise it, and its inputs — the custodied
  history, the pinned commit and the recorded configuration — are already fingerprinted, so
  reproducibility is the guarantee that fits it.

- `docs/official_annual_decomposition_2026-08-28.md`, recording the accepted per-delivery-year
  decomposition of the official replay from workflow run `33147448666`. Custody verification of
  the source artifact passed, and every per-year figure reconciles with previously accepted
  aggregates to the euro, including the EUR 0.00 common-day ceiling spread within each year.

- An explicit bootstrap source-era and resolution policy. A source era is a maximal contiguous
  run of market days at one delivery resolution; a resolution change or a market-day gap ends
  one. `BootstrapConfig` gains `source_resolution_minutes`, `source_start_day` and
  `source_end_day`; `detect_source_eras` and `select_source_era` are public. A single-era
  history needs no declaration, a multi-era history must declare one, and there is no default,
  because the accepted 2020-2026 history holds an hourly and a quarter-hour era and a default
  would settle that trade-off silently. The refusal lists the available eras and their windows,
  the selection is recorded in the run summary and on every provenance row, sampling is confined
  to the selected era so no block straddles a regime boundary, and minimum and median
  block-candidate counts are reported so scarcity is visible.
- `docs/bootstrap_source_era_policy.md`, recording the policy, the two eras of the accepted
  history with their season coverage, what each choice costs, and the deliberate exclusions:
  no resampling between resolutions, no blending of eras and no likelihood attached to either.

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
  percentile, loss metric or ranking of years is produced. A duplicated accepted history, a
  schedule settled on prices the history does not publish and a daily-results table describing
  another history are each refused explicitly.
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

- The price-level and spread-compression transformations now share one bootstrap-path validation
  contract (`greek_bess.stress._paths.validate_bootstrap_paths`), so two transformations cannot
  drift apart on what counts as an acceptable path. Behaviour is unchanged.
- Repository content is contributor-neutral: no tool or assistant attribution in commit
  messages, pull requests, comments, documentation or tracked configuration (decision entry
  2026-08-28). Editor- and service-specific session configuration is untracked and ignored.
- `CONTRIBUTING.md` now states the real Python 3.12 requirement and the four validation gates;
  it previously described a `python -m unittest` invocation the project does not use.

- The bootstrap no longer refuses a mixed-resolution history with a bare "must use one
  interval resolution" message. It reports the eras the history contains and requires one
  to be chosen.
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
