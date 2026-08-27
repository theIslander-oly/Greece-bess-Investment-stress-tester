# Methodology

## 1. Analytical chain

The project is intentionally modular:

1. acquire official price publications privately;
2. normalize them to a canonical interval schema;
3. audit completeness, timestamps, revisions and cross-source consistency;
4. calculate a constrained perfect-foresight dispatch ceiling;
5. generate causal price forecasts using information available before delivery;
6. plan dispatch on forecasts and settle the plan on realized prices;
7. evolve usable energy and power through degradation and augmentation cohorts;
8. transform a continuous operating path into explicit unlevered cash flows;
9. generate reproducible synthetic price paths for later stress scenarios (v0.7 foundation).

Each stage emits auditable interval, daily and summary outputs rather than only a headline
return.

## 2. Data and time

The canonical price observation contains UTC interval start/end, market-clock and
Europe/Athens timestamps, resolution, price, currency/unit, source, publication version,
retrieval metadata and quality flags. UTC is the unique key. Daylight-saving days are
validated against their expected 23/25 hourly or 92/100 quarter-hour intervals.

HEnEx workbook ingestion selects a single published market-clearing price per interval and
records the raw file SHA-256. The greatest published workbook revision is selected per delivery
day before parsing. Repeated asset rows must agree, except for a unique strict majority with at
most two one-cent cross-border rounding outliers; accepted cases remain interval-level quality
flags. Annual retrieval records outer and approved nested DAM ZIP hashes, member revisions and
coverage. Incremental daily discovery is used only for years not yet in the annual archive and
must pass the same parser and quality gates. ENTSO-E ingestion uses the A44 day-ahead document
type for the Greek bidding zone. Overlapping normalized series can be compared interval by
interval.

ADMIE retrieval preserves publication time independently from delivery coverage. Candidate load,
RES, availability and interconnector variables are quarantined from forecast features until their
historical publication time is proven to precede the bid decision for the target market day.

Official raw files and normalized datasets are not committed. Reproduction depends on the
source register, commands, retrieval manifests, hashes and quality reports described in
`docs/data_sources.md` and `docs/official_data_retrieval.md`.

## 3. Dispatch

The perfect-foresight problem maximizes settled DAM energy value less configured fees and
degradation cost subject to:

- charge/discharge power and grid limits;
- usable energy and state-of-charge bounds;
- separate one-way charge and discharge efficiency;
- availability;
- a binary operating mode preventing simultaneous charge and discharge;
- optional daily equivalent-cycle limits; and
- explicit initial and terminal state of charge.

Grid import for charging and grid export for discharge are settled at the interval price.
Negative prices are preserved. Because all future prices are known, this result is labelled a
gross-margin upper bound.

## 4. Forecast evaluation

Naive daily, weekly and rolling-seasonal baselines and the ML benchmarks are causal. For a
target day, no realized target-day price enters its features or model fit. Model selection uses
the validation period only; the held-out test period is reported separately. Forecast-planned
quantities are settled against realized prices and compared with a perfect-foresight solve under
the same physical and terminal-energy constraints.

MAE, RMSE, bias, median absolute error, WAPE, correlation and negative-price detection are
reported. MAPE is excluded because zero and negative prices make it misleading.

## 5. Degradation

Each battery cohort ages separately through additive calendar and equivalent-cycle fade.
Beginning-of-day usable energy and power constrain that day's dispatch. Cell throughput is
allocated proportionally across active cohorts. Capacity additions, replacements, retirement,
retained-capacity thresholds and optional EFC warranty limits are explicit. The model is a
transparent approximation and not an electrochemical lifetime model.

## 6. Finance

The finance engine requires a continuous daily operating path and preserves its provenance
label. It itemizes initial CAPEX, fixed and variable OPEX, augmentation, decommissioning and
residual value. OPEX can escalate nominally. Cash flows use exact dates for discounting and
report unlevered NPV, IRR (with sign-change ambiguity handling), simple/discounted payback,
maximum initial CAPEX and market-margin break-even values.

No revenue is extrapolated across missing operating days. Tax, debt, subsidy and working
capital layers are not included.

## 7. Seasonal block-bootstrap foundation

The v0.7 foundation samples contiguous historical market-day blocks with replacement. An
explicit seed drives NumPy's deterministic generator. Candidate blocks must begin in the same
meteorological season as the target block, be calendar-contiguous, and match the target block's
exact vector of daily interval counts. The last block may be shorter. Each sampled block records
its target/source day boundaries, season, interval count, candidate count and selected candidate
index.

Target UTC and local timestamps are reconstructed from the target market days; sampled prices
are copied by physical interval order without scaling, smoothing or interpolation. Complete-day
and continuous-horizon validation occurs before sampling, and a target block fails when no
seasonal source block has a compatible 23/25-hour or 92/100-quarter-hour structure. Outputs are
labelled synthetic scenarios and are not forecasts or probability-calibrated market evidence.

## 8. Additive bootstrap price-level transformation

The first shock layer accepts only complete canonical bootstrap paths. For configured shift
\(s\) in EUR/MWh, each interval price is transformed as \(p'_{i,k}=p_{i,k}+s\), where \(i\) is
the interval and \(k\) is the unchanged path ID. There is no random draw, clipping, flooring,
interpolation or calendar remapping. Consequently identical ordered inputs and configuration
produce identical results, and zero or negative shocked prices remain valid.

Because the shift is constant, within-path spreads are unchanged; dispatch schedules and gross
margins therefore respond only through round-trip efficiency losses and per-MWh fees. The
transformation is a level sensitivity, not a stress on the arbitrage opportunity itself.

Validation is performed independently for every path: canonical timezone-aware columns, unique
path/UTC keys, complete DST-aware market days, continuous intervals, one supported resolution and
non-missing prices are required. An interval audit table records the UTC key, path ID,
transformation ID, additive shift, original and shocked values, and input source/version. Outputs
are synthetic sensitivities and not forecasts or investment evidence.

## 9. Independent bootstrap-path dispatch

Every input path is validated independently for complete DST-aware market days, continuous
canonical UTC intervals, unique path/UTC keys, and retained synthetic/non-forecast provenance.
All paths must have exactly the same ordered canonical interval keys. One battery configuration
and one scalar or interval-aligned availability profile are then reused unchanged for every
independent full-horizon mixed-integer solve.

Power, energy, efficiency, exclusivity, grid, SOC, optional daily cycle, and terminal-energy
constraints therefore apply separately to every path; state never crosses path boundaries.
Outputs retain `path_id`, canonical interval identity, source labels, interval operations and
revenue decomposition. A separate table reports the existing optimizer summary for each path.
These are perfect-foresight upper bounds on synthetic paths, not expected revenues or forecasts.

## 10. Official operational acceptance

Before a stage is treated as exercised on real data, it is run over the complete accepted official
history and evidenced in aggregate only. Acceptance verifies the input artifact hash and provenance,
canonical timezone-aware identity, DST-aware market-day completeness across both resolution regimes,
duplicate/gap/overlap absence and signed-price preservation; then, for dispatch, solver identity and
status, constraint compliance restated independently from the published schedule columns, and
aggregate energy and margin components; then, for forecasting, a mutation audit proving no future
observation reaches an earlier target day, refit cutoffs preceding their forecast targets, exact
settlement against realized official prices, like-for-like ceilings on shared days, and coverage
with every excluded day attributed to a structural cause. Both paths must reproduce identical
results on an immediate second run. Interval prices and schedules are never recorded in the report.

## 11. Validation

Code changes must pass Ruff, mypy, pytest and a clean wheel build. Tests use deterministic
synthetic inputs or small purpose-built fixtures. Official-data acceptance is recorded as
aggregate evidence and hashes without committing the source files. Detailed milestone methods
and test evidence are retained in `docs/implementation_report_v*.md`.
