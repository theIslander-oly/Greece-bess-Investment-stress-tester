# Project status

**Version:** 0.7.6
**Updated:** 28 August 2026
**Status:** Official multi-year operational acceptance and HEnEx-to-ENTSO-E cross-source
reconciliation passed; artifact custody tooling in place awaiting the operator upload;
per-delivery-year replay decomposition accepted against the official history;
bootstrap source-era policy and spread compression landed; scenario-ensemble range reporting and
availability/outage integration awaiting approval

## Spread compression about a daily reference level

- `compress-spread` and `greek_bess.stress.apply_spread_compression` transform within-day spread
  rather than level: `compressed = reference + factor * (price - reference)` over each path's
  CET/CEST market day, so every within-day range is scaled by exactly the declared factor.
- This is the economically first-order storage stress and the way cannibalisation pressure is
  represented. A constant level shift leaves spreads untouched and moves margin only through
  round-trip losses and fees; compression changes the quantity being arbitraged.
- The factor is bounded to [0, 1]: 1.0 is the identity, 0.0 flattens each day onto its reference.
  Spread widening is deliberately out of scope, which is a scope limit and not a judgment that
  widening is unlikely.
- `reference_basis` is declared with no default, following the source-era precedent. `daily_mean`
  preserves each daily mean exactly, so the result is a pure spread change; `daily_median` does
  not, and the summary reports the maximum absolute daily-mean shift it causes.
- Zero and negative results are preserved and never clipped. Compression pulls prices toward the
  reference, so intervals can cross zero and change sign; the count is reported rather than
  suppressed, because a scenario that materially changes the negative-interval count is changing
  the market's character and not only its spread.
- Missing prices are refused explicitly: one would propagate through its market day's reference
  level and corrupt every interval of that day.
- The summary reports mean and maximum daily range and negative and zero interval counts, before
  and after. Interval provenance records the market day, reference level, factor, basis, original
  and compressed prices and input source metadata.
- The factor is a declared judgmental scenario, not an estimate. The replayed history predates
  operating battery competition almost entirely, so no competitive spread response is estimable
  from it. No probability, percentile, loss metric or ranking attaches to a factor.
- The per-delivery-year decomposition is the direct evidence for prioritising this over level:
  2026 shows the highest ceiling per market day of any non-crisis year on the lowest mean price
  since 2020, because mean daily range rose every year since 2023 while mean price fell.

## Bootstrap source-era and resolution policy

- A source era is a maximal contiguous run of market days at one delivery resolution. The
  bootstrap samples from exactly one; a resolution change or a market-day gap ends an era.
- A single-era history needs no declaration. A multi-era history must declare one with
  `source_resolution_minutes`, narrowed by `source_start_day`/`source_end_day` when ambiguous.
  There is no default and no "most recent" rule.
- The accepted history holds two eras: 60 minutes over 2020-11-01 to 2025-09-30 (1,795 market
  days, five or six occurrences of every season) and 15 minutes over 2025-10-01 to 2026-08-25
  (329 market days, exactly one occurrence of each season). Passing it undeclared now fails
  with a message naming both, instead of a bare resolution complaint.
- The selected era is recorded in the run summary and on every provenance row, and days outside
  it are absent from the candidate search, so no block can straddle a regime boundary.
- Minimum and median block-candidate counts are reported, so a position where every path
  repeats one source block is visible rather than smoothed.
- Resampling one resolution into another, blending eras and attaching any likelihood to an era
  remain out of scope. The policy is recorded in `docs/bootstrap_source_era_policy.md`.

## Per-delivery-year decomposition of the accepted replay

- `decompose-annual-replay` regroups an already-accepted replay into delivery years, adding no
  model, market or transformation.
- A delivery year is the calendar year of the interval's CET/CEST market-day start, the same
  convention the committed custody records use; the summary states why a UTC grouping of the
  same intervals differs by one interval at a year boundary.
- Each year carries market-day coverage, an explicit partial-year flag, interval counts by
  resolution, preserved negative, zero and missing price counts, price context including the
  mean daily price range, and its perfect-foresight ceiling.
- Forecast capture is reported per method on that method's own backtested days, and separately
  on the days every method backtested, where the recorded ceiling spread is the like-for-like
  evidence.
- `optimize-perfect-foresight --daily-solves` publishes the daily-composed dispatch mode the
  2026-08-27 acceptance ran through a temporary runner, so the annual ceiling and the annual
  capture ratio share one basis and no trade spans a year boundary.
- A schedule whose settled prices differ from the supplied history at any interval is refused,
  so a decomposition cannot be paired with a history it was not solved on.
- Per-market-day figures are within-period averages; nothing is annualized, and no probability,
  percentile, loss metric or year ranking is produced.
- The `Decompose the accepted replay by delivery year` workflow verifies the accepted artifact
  against its committed custody record before consuming it, then runs the daily ceiling, the
  four causal naïve backtests and the decomposition inside Actions.
- **Accepted on 2026-08-28** by workflow run `33147448666` against artifact run `32971677163`.
  Custody verification passed, so no official publication has been revised since acceptance.
  Every per-year figure reconciles with previously accepted aggregates: the annual ceilings sum
  to EUR 24,974,729.59 over 2,124 market days, the four methods' realized margins, own-days
  ceilings, day counts and loss-day counts all match, and the 2,098-day common-day ceiling of
  EUR 24,665,532.17 is identical across methods with a spread of EUR 0.00 in every year.
- The decomposition shows regime dependence the aggregate conceals: 2022 contributes 23.5 % of
  the six-year ceiling from 17.2 % of the days; mean daily price range has risen every year
  since 2023 while the mean price fell, so 2026 has the second-widest range on the lowest mean
  price since 2020; ensemble capture spans 0.6937 to 0.8724 against an aggregate of 0.7814; and
  the method ranking reverses in 2026, where `rolling_mean` overtakes the ensemble.
- Evidence is recorded in `docs/official_annual_decomposition_2026-08-28.md`.

## Durable custody of accepted official artifacts

- Accepted official artifacts are to be stored as encrypted assets on a release in this private
  repository, and are already fingerprinted by price-free custody records committed under
  `docs/custody/`. A committed record is a fingerprint, not a durable copy: the operator upload is
  not verified complete in the repository record, so custody is not recorded as complete.
- A custody record holds per-file digests and content-level invariants of the normalized
  series, including a digest of the interval and price series that is independent of CSV
  formatting, column order and float repr.
- `record-custody` builds a record; `verify-custody` re-derives it from a stored copy and
  returns exit code 2 on any difference, so a copy can be proven to be the accepted artifact
  and a re-retrieval that differs is detected rather than silently adopted.
- The `Record official artifact custody` workflow performs the same check inside Actions,
  recording when no committed record exists and verifying against it once one does.
- Artifact retention on all official-data workflows is raised from 7 to 90 days, so a passed
  acceptance no longer has a one-week shelf life.
- Encryption keys and the release upload remain with the operator; no automation in this
  repository holds a key that could decrypt an accepted artifact.
- The procedure, the operator steps and the failure taxonomy are recorded in
  `docs/official_artifact_custody.md`.
- Custody covers retrieved official artifacts only. Derived evidence computed from a custodied
  history, such as the `annual-replay-decomposition` artifact, is guaranteed by reproduction
  from the recorded history, commit and configuration instead.
- **Outstanding operator action:** the encrypted copies must be uploaded before the source
  artifacts expire on 2 and 3 September 2026. Custody is not complete until they are.

## Official cross-source reconciliation

- The accepted HEnEx history was compared interval by interval against ENTSO-E A44 Greek
  day-ahead prices over the identical window, market days 1 November 2020 through 25 August 2026.
- 74,662 of 74,663 intervals match within EUR 0.000001/MWh; neither source omits an interval the
  other publishes.
- One interval on the 29 October 2023 autumn DST market day differs by exactly EUR 0.01/MWh,
  consistent with the already-accepted HEnEx one-cent rounding-consensus bound.
- Both sources independently pass their own deterministic quality assessment over the window.
- The reconciliation corrected a real defect in the project's ENTSO-E reader: A44 `A03` curve-type
  repeats were being dropped, which had understated ENTSO-E coverage by 4,874 intervals.
- An immediate second run reproduced every count and statistic.
- This is cross-source ingestion evidence, not revenue, forecast or investment evidence.
- Aggregate evidence is recorded in `docs/official_source_reconciliation_2026-08-27.md`.

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
- Explicit-unit pandas timedelta construction in synthetic, HEnEx and ENTSO-E ingestion, with a
  pytest warning policy scoped to warnings attributed to `greek_bess` or to the project's tests.
- One declared project version, with `pyproject.toml`, `greek_bess.__version__` and the README
  release line locked together by test.

## Validation still required

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
calibration story. The bootstrap source-era/resolution policy landed on 2026-08-27 and spread compression on
2026-08-28, prioritised over availability/outage integration because the per-delivery-year
decomposition showed spread, not level, driving the ceiling. The remaining v0.7 modeling
milestones are scenario-ensemble range reporting across named scenarios, labelled
non-probabilistic, and deterministic availability/outage-path integration; both still require
explicit approval before implementation. Negative-price-event
transformations remain deferred. ENTSO-E reconciliation passed on 2026-08-27. Custody tooling and the storage
procedure landed on 2026-08-27 and await the operator upload. ADMIE timing acceptance remains a parallel
task. The per-year decomposition surface and workflow landed on 2026-08-27 and its official run
was accepted on 2026-08-28, so that track is complete.
