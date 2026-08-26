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
9. stress assumptions and price paths in reproducible scenarios (planned for v0.7).

Each stage emits auditable interval, daily and summary outputs rather than only a headline
return.

## 2. Data and time

The canonical price observation contains UTC interval start/end, market-clock and
Europe/Athens timestamps, resolution, price, currency/unit, source, publication version,
retrieval metadata and quality flags. UTC is the unique key. Daylight-saving days are
validated against their expected 23/25 hourly or 92/100 quarter-hour intervals.

HEnEx workbook ingestion selects a single published market-clearing price per interval and
records the raw file SHA-256. Annual archive retrieval additionally records parent ZIP hashes,
member revisions and coverage. Incremental daily discovery is used only for years not yet in the
annual archive and must pass the same parser and quality gates. ENTSO-E ingestion uses the A44
day-ahead document type for the Greek bidding zone. Overlapping normalized series can be compared
interval by interval.

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

## 7. Validation

Code changes must pass Ruff, mypy, pytest and a clean wheel build. Tests use deterministic
synthetic inputs or small purpose-built fixtures. Official-data acceptance is recorded as
aggregate evidence and hashes without committing the source files. Detailed milestone methods
and test evidence are retained in `docs/implementation_report_v*.md`.
