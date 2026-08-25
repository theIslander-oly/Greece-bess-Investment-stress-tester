# Greek Battery Investment Stress Tester

Transparent research and pre-feasibility tooling for a standalone grid-scale battery in Greece.

This is not financial advice, an investment-grade forecast, a bankable revenue study or a substitute for legal, tax, grid-connection and market-access diligence.

**Current release:** `v0.6.0` — explicit unlevered project finance and break-even analysis.

## Current implementation

Version 0.6 provides:

- a canonical Greek Day-Ahead Market interval schema;
- an ENTSO-E A44 day-ahead price client for the Greek bidding zone;
- a HEnEx `EL-DAM_Results_EN` workbook parser;
- UTC, CET/CEST market-clock and Europe/Athens timestamp views;
- correct 23/25-hour and 92/100-quarter-hour daylight-saving days;
- publication revision and raw-file SHA-256 provenance;
- missing-price, duplicate, resolution and daily-completeness checks;
- HEnEx-versus-ENTSO-E interval comparison;
- deterministic synthetic data for public demonstrations and tests;
- automated tests covering parsing, negative prices, DST and source mismatches;
- a mixed-integer perfect-foresight Greek DAM dispatch optimizer;
- explicit grid-meter charge/discharge conventions and one-way efficiencies;
- power, energy, SOC, availability, grid and terminal-energy constraints;
- optional daily equivalent-cycle limits, market fees and degradation cost;
- interval-level dispatch and revenue decomposition;
- a mandatory result label identifying perfect foresight as an upper bound;
- strictly causal daily, weekly and rolling-seasonal naïve price forecasts;
- a leakage-safe blended forecast baseline;
- signed-price-safe forecast metrics, including negative-price detection;
- daily forecast-planned dispatch settled against realized prices;
- a like-for-like perfect-foresight ceiling, value capture and regret comparison;
- explicit disclosure of incomplete forecast days and backtested coverage;
- causal calendar, lag and rolling-price feature engineering;
- ridge and histogram-gradient-boosting ML benchmarks;
- explicit training, validation and held-out test periods;
- deterministic walk-forward model refitting with training-date audit logs;
- validation-only model selection and separate held-out test rankings;
- like-for-like held-out dispatch comparison against every naïve baseline;
- additive calendar and equivalent-cycle capacity fade with explicit assumptions;
- separately aged initial and augmentation cohorts;
- usable energy and charge/discharge power evolution;
- proportional cell-throughput allocation across cohorts;
- retained-capacity, throughput-warranty and retirement-threshold screening;
- optional hard per-cohort EFC warranty constraints;
- dated augmentation or replacement capacity and separately recorded event cost;
- day-by-day perfect-foresight dispatch using beginning-of-day degraded limits;
- an explicit continuous daily operating-path contract for project finance;
- separately itemized initial CAPEX, fixed OPEX, variable OPEX and augmentation costs;
- OPEX escalation, residual value and decommissioning assumptions;
- exact-date discounted unlevered cash flows, NPV and IRR;
- simple and discounted payback;
- maximum initial CAPEX and market-margin break-even outputs;
- mandatory operating-margin labels that preserve upper-bound and backtest limitations.

Probabilistic scenario analysis and the user interface remain subsequent phases.

## Repository guide

- [`PROMPT.md`](PROMPT.md) — approved mission, scope and interpretation rules.
- [`PLAN.md`](PLAN.md) and [`STATUS.md`](STATUS.md) — milestones and current progress.
- [`DECISIONS.md`](DECISIONS.md) — dated analytical and repository decisions.
- [`METHODOLOGY.md`](METHODOLOGY.md) — end-to-end analytical method.
- [`LIMITATIONS.md`](LIMITATIONS.md) — consolidated cautions and exclusions.
- [`docs/data_sources.md`](docs/data_sources.md) and
  [`docs/data_dictionary.md`](docs/data_dictionary.md) — official-source provenance and schema.

The first GitHub snapshot imports the already completed v0.1-v0.6 implementation. Its earlier
history is preserved in the versioned implementation reports; no historical commits are
fabricated.

## Data policy

Real research runs use official data fetched privately by the user. Official raw prices are not bundled with this project.

- HEnEx data is imported from a workbook obtained by the user.
- ENTSO-E data is fetched with the user's personal API token.
- Public demonstrations and automated tests use clearly labelled synthetic prices.
- A real token must never be committed or printed in logs.

The HEnEx parser has been production-checked against the official English v01 result
workbooks for 24 and 25 August 2026. Both files passed the complete-day and continuity
checks without code changes. See
[`docs/official_data_acceptance_2026-08-25.md`](docs/official_data_acceptance_2026-08-25.md)
for hashes, boundaries and acceptance results. The workbooks themselves are not
redistributed by this repository.

Review the source terms before any deployment or redistribution:

- [HEnEx Terms of Use](https://www.enexgroup.gr/web/guest/terms-of-use)
- [ENTSO-E Legal Terms](https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions)

## Installation

Python 3.12 is required.

```bash
python -m venv .venv
```

Activate the virtual environment, then install the package:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development and the same checks used by GitHub Actions:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest -v
python -m build --wheel
```

CI runs these checks on every pull request without private API keys or official datasets. Tests
use deterministic synthetic or purpose-built small inputs.

## 1. Generate public-demo data

```bash
greek-bess generate-synthetic \
  --start-day 2025-01-01 \
  --end-day 2026-01-01 \
  --resolution-minutes 60 \
  --seed 42 \
  --output data/curated/synthetic_prices.csv
```

This produces:

- `data/curated/synthetic_prices.csv`
- `data/curated/synthetic_prices.quality.json`

Synthetic data is always marked with `source=synthetic` and the quality flag `synthetic_demo_data`.

## 2. Import HEnEx results

```bash
greek-bess parse-henex \
  path/to/YYYYMMDD_EL-DAM_Results_EN_v01.xlsx \
  --output data/curated/henex_prices.csv
```

The parser:

1. locates a worksheet containing the documented result columns;
2. selects the latest publication version per delivery day;
3. verifies one unique MCP per MTU despite repeated asset-level rows;
4. reconstructs DST-safe timestamps from `DDAY`, `SORT` and `DELIVERY_DURATION`;
5. writes normalized data and a quality report.

Use `--allow-partial-days` only when a deliberately incomplete workbook is being inspected. Incomplete days are rejected by default.

## 3. Fetch ENTSO-E prices

Register on the ENTSO-E Transparency Platform and obtain REST API access. Store the personal token in the environment:

```bash
export ENTSOE_SECURITY_TOKEN="your-personal-token"
```

Then fetch a full market-clock-aligned period:

```bash
greek-bess fetch-entsoe \
  --start 2025-12-31T23:00Z \
  --end 2026-01-31T23:00Z \
  --output data/curated/entsoe_prices.csv
```

The ENTSO-E endpoint uses UTC request periods. For complete local market days, calculate the correct UTC boundary for CET/CEST rather than assuming every day begins at `00:00Z`.

Raw XML responses are cached under `data/raw/entsoe/` by default. The token is never included in filenames, output rows or error messages.

If local command-line execution is unavailable, the manual
[`Fetch official ENTSO-E prices`](.github/workflows/fetch-entsoe.yml) GitHub Actions
workflow performs the same retrieval using an encrypted repository secret and publishes
only the normalized CSV and quality JSON as a short-lived artifact. See the
[`secure GitHub retrieval guide`](docs/entsoe_github_retrieval.md).

## 4. Compare HEnEx and ENTSO-E

After normalizing an overlapping period from each source:

```bash
greek-bess compare-sources \
  data/curated/henex_prices.csv \
  data/curated/entsoe_prices.csv \
  --tolerance 0.000001 \
  --output data/curated/source_comparison.csv
```

Each interval is classified as `match`, `price_mismatch`, `missing_henex` or `missing_entsoe`. A comparison containing anything other than matches exits with code `2` so it can fail an automated validation job.

## 5. Optimize perfect-foresight dispatch

The included example battery configuration is deliberately illustrative. Replace every
technical and commercial assumption with project-specific evidence before interpreting a
result.

```bash
greek-bess optimize-perfect-foresight \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --output outputs/perfect_foresight_dispatch.csv
```

This produces:

- `outputs/perfect_foresight_dispatch.csv`, with interval-level power, SOC, energy,
  settled energy value, fees, degradation cost and net margin;
- `outputs/perfect_foresight_dispatch.summary.json`, with aggregate energy,
  equivalent cycles, captured prices and margin components.

The optimizer uses these conventions:

- charge MW and MWh are grid imports settled at the DAM price;
- discharge MW and MWh are grid exports settled at the DAM price;
- stored energy increases by grid charge multiplied by charge efficiency;
- stored energy falls by grid discharge divided by discharge efficiency;
- a binary operating mode prevents simultaneous charging and discharging;
- the terminal SOC defaults to the initial SOC, preventing free end-of-horizon depletion;
- an optional daily cycle cap limits grid-delivered discharge MWh divided by nameplate MWh;
- availability scales battery power capability, while grid limits remain absolute;
- negative charging costs are preserved when the battery is paid to consume energy.

Perfect foresight assumes every future price is known. Its result is therefore a
deterministic gross-margin upper bound under the supplied constraints—not a forecast and
not expected investment revenue. It excludes forecast error, imbalance exposure, bid
acceptance, market access, taxes, financing, subsidies, grid feasibility, and revenues
outside the Day-Ahead Market.

## 6. Generate walk-forward naïve forecasts

```bash
greek-bess forecast-naive \
  data/curated/henex_prices.csv \
  --methods daily_persistence weekly_persistence rolling_mean ensemble \
  --rolling-window-days 28 \
  --start-day 2025-02-01 \
  --output outputs/naive_forecasts.csv
```

This writes the interval forecasts and `outputs/naive_forecasts.metrics.json`.

All intervals for a target market day are forecast before any realized price from that
day is added to history. The methods are:

- `daily_persistence`: same wall-clock market slot on the previous day;
- `weekly_persistence`: same slot seven days earlier;
- `rolling_mean`: prior values for the same slot within the selected window;
- `ensemble`: mean of the causal forecasts available for that interval.

Wall-clock slots and occurrence ranks handle 23/25-hour and 92/100-quarter-hour DST days.
The metrics exclude MAPE because zero and negative electricity prices make it unstable or
misleading. MAE, RMSE, mean error, median absolute error, WAPE, correlation and
negative-price precision/recall are reported instead.

## 7. Backtest forecast-planned dispatch

```bash
greek-bess backtest-forecast-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --method ensemble \
  --rolling-window-days 28 \
  --start-day 2025-02-01 \
  --output outputs/forecast_dispatch_intervals.csv
```

This produces:

- `outputs/forecast_dispatch_intervals.csv`;
- `outputs/forecast_dispatch_intervals.daily.csv`;
- `outputs/forecast_dispatch_intervals.summary.json`.

For each market day, the backtest optimizes dispatch using forecast prices, settles the
planned quantities against realized prices, and runs a perfect-foresight solve under the
same battery constraints. Initial SOC is restored at day-end for fair daily comparison.

Dispatch is run only for market days whose selected forecast is complete. The summary
retains metrics for the full requested evaluation period and separately reports metrics
for dispatched days, the fractions of days and intervals backtested, missing forecast
intervals, and every excluded date. For example, daily persistence cannot forecast the
spring clock slots that did not exist on the preceding 23-hour market day; those gaps are
reported rather than silently hidden. The ensemble normally remains complete because it
can use available weekly and rolling-history components.

The backtest assumes price-taking planned quantities are fully accepted. Bid acceptance,
imbalance exposure and route-to-market constraints remain excluded and must be modeled
before any commercial use.

## 8. Run the ML forecast benchmark

```bash
greek-bess forecast-ml \
  data/curated/henex_prices.csv \
  --validation-start-day 2024-01-01 \
  --test-start-day 2025-01-01 \
  --models ridge hist_gradient_boosting \
  --feature-window-days 28 \
  --refit-frequency-days 7 \
  --min-training-days 365 \
  --output outputs/ml_forecasts.csv
```

The training period contains only dates before `validation-start-day`. Model selection
uses validation RMSE only. The test period begins at `test-start-day` and is never used to
select the winning model. At each refit, only earlier realized market days are fitted;
the JSON summary records the exact training start, training end and forecast start for
every model refit.

Features include market-clock/calendar cycles, causal daily/two-day/weekly price lags,
and prior matching-slot rolling statistics. Missing historical features are imputed by a
transformer fitted only on the current training sample. No target-day realized price is a
feature. External weather, fuel, renewable and interconnector inputs remain excluded
until their publication timestamps and day-ahead availability can be validated.

The output CSV includes validation/test labels, all four naïve forecasts and both ML
forecasts. The summary contains forecast metrics, validation and test rankings, selected
model, feature provenance and refit logs.

## 9. Compare held-out ML and naïve dispatch value

```bash
greek-bess backtest-ml-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --validation-start-day 2024-01-01 \
  --test-start-day 2025-01-01 \
  --min-training-days 365 \
  --output outputs/ml_dispatch.csv
```

This runs every ML model and naïve baseline over the identical held-out test days for
which all comparison forecasts are complete. It reports excluded dates, forecast error,
realized dispatch margin, the common perfect-foresight ceiling, value capture and regret.
The selected model's interval schedule is written to `ml_dispatch.csv`; forecasts, all
method/day results and both forecast and dispatch summaries are written beside it.

Forecast RMSE and dispatch value are both reported because the lowest price error does
not necessarily produce the most valuable battery schedule. Synthetic demonstrations
must not be interpreted as evidence of real project profitability.

## 10. Simulate degradation and augmentation-aware dispatch

```bash
greek-bess simulate-degradation-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --degradation-config examples/illustrative_degradation_with_augmentation.json \
  --output outputs/degradation_dispatch.csv
```

This writes:

- `outputs/degradation_dispatch.csv`, the interval dispatch schedule annotated with the
  beginning-of-day degraded energy and power limits;
- `outputs/degradation_dispatch.daily.csv`, daily throughput, margin, capacity, warranty
  and augmentation state;
- `outputs/degradation_dispatch.cohorts.csv`, the final state of the initial battery and
  every separately aged augmentation cohort;
- `outputs/degradation_dispatch.summary.json`, aggregate market margin, physical state,
  warranty indicators, assumptions and policy labels.

Calendar fade and cycle fade are linear and additive within each cohort. Equivalent full
cycles use cell-side discharged energy: grid discharge divided by discharge efficiency,
then divided by that cohort's nominal energy. Daily cell throughput is allocated across
cohorts in proportion to beginning-of-day usable energy. Retained capacity cannot fall
below zero, and power scales with retained capacity raised to the configured exponent.

A capacity event is applied at the beginning of its dated market day. With an empty
`retired_cohort_ids` list it is an augmentation and does not reset old cells. When named
cohorts are retired, the event becomes an explicit replacement: those cohorts leave the
fleet and the new capacity begins with zero age and throughput. Added nominal energy,
charge power, discharge power and event cost are recorded independently. The cost is not
subtracted from DAM market margin. The separate v0.6 finance workflow places it into the
dated project cash flow.

The warranty fields are screening assumptions, not an interpretation of an OEM contract.
When `enforce_warranty_throughput_limit` is `true`, the day-level optimizer limits grid
discharge so proportional cohort allocation cannot exceed the configured per-cohort EFC
ceiling. Retained-capacity warranty and retirement thresholds are reported as indicators;
they do not automatically repair, retire or replace the asset.

The included degradation JSON is intentionally illustrative. In particular, its fade
rates, warranty values, augmentation size, date and zero placeholder cost are not Greek
market facts or OEM evidence. Replace every value with documented project-specific
assumptions before interpreting a run.

The dispatch path still uses perfect foresight within each market day and restores the
initial SOC fraction at day-end. It is therefore a degraded-capacity gross-margin upper
bound—not expected revenue or an investment conclusion.

## 11. Evaluate unlevered project finance

The finance workflow consumes a complete daily operating-results file. The degradation
dispatch daily output already contains the required columns:

- `market_day`;
- `net_market_margin_eur`;
- `grid_discharge_mwh`;
- optional `augmentation_cost_eur`.

```bash
greek-bess evaluate-project-finance \
  outputs/degradation_dispatch.daily.csv \
  --finance-config examples/illustrative_finance_not_project_specific.json \
  --output outputs/project_cash_flows.csv
```

This writes:

- `outputs/project_cash_flows.csv`, with time-zero CAPEX and annual cash-flow totals;
- `outputs/project_cash_flows.daily.csv`, with daily market margin, OPEX, augmentation,
  terminal costs, discount factors and discounted cash flow;
- `outputs/project_cash_flows.summary.json`, with NPV, IRR status, simple and discounted
  payback, break-even margin realization and maximum initial CAPEX.

The operating path must contain every calendar day from `project_start_day` through
`project_end_day`. Missing days, duplicates and unsorted dates are rejected. The finance
engine never repeats a historical year, fills missing revenue with zero or invents a
future price path.

`operating_margin_case` must explicitly be one of:

- `perfect_foresight_upper_bound`;
- `historical_forecast_backtest`;
- `user_supplied_scenario`.

The configured `market_margin_realization_fraction` can reduce the supplied margin for a
transparent sensitivity, but it does not convert a perfect-foresight upper bound into an
expected forecast. The included finance JSON contains deliberately illustrative round
numbers and is not a Greek construction-cost estimate, financing offer or recommendation.

The calculation is unlevered, nominal, pre-tax and pre-subsidy. It excludes debt,
financing fees, working capital, grid feasibility, bid acceptance and revenues from the
Intraday, Balancing or reserve markets. A positive NPV flag is a mathematical result under
the inputs—not a build recommendation.

## Quality-result exit codes

- `0`: ingestion and quality checks passed;
- `1`: retrieval, parsing or configuration failed;
- `2`: data was parsed but failed required quality checks.

Missing prices are never silently interpolated. Negative and zero prices are preserved as valid values.

## Run the tests

The test suite uses only synthetic fixtures and temporary workbooks:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

No official prices or personal API credentials are required.

## Package layout

```text
src/greek_bess/
  cli.py
  data/
    entsoe.py
    henex.py
    quality.py
    schema.py
    synthetic.py
    timezones.py
  dispatch/
    perfect_foresight.py
  forecast/
    naive.py
    ml.py
  degradation/
    model.py
  finance/
    model.py
  backtest/
    degradation_dispatch.py
    forecast_dispatch.py
    ml_dispatch.py
examples/
  battery_50mw_100mwh.json
  illustrative_degradation_with_augmentation.json
  illustrative_finance_not_project_specific.json
tests/
```

## Next phase

The next modeling phase is probabilistic stress testing: reproducible seasonal price-path
resampling, spread and negative-price shocks, availability/outage blocks, degradation and
CAPEX sensitivities, battery-market cannibalisation, P5/P50/P95 outcomes, loss
probability and worst paths. Tax, subsidy and leveraged financing remain excluded until
their jurisdiction-specific assumptions are independently validated. HEnEx workbook
acceptance has passed; private-token ENTSO-E reconciliation and a complete official
multi-year benchmark remain parallel acceptance tasks.

## Project records

- [Changelog](CHANGELOG.md)
- [Release notes v0.2.0](docs/release_notes_v0.2.md)
- [Implementation report v0.2](docs/implementation_report_v0.2.md)
- [Release notes v0.3.0](docs/release_notes_v0.3.md)
- [Implementation report v0.3](docs/implementation_report_v0.3.md)
- [Release notes v0.3.1](docs/release_notes_v0.3.1.md)
- [Implementation report v0.3.1](docs/implementation_report_v0.3.1.md)
- [Release notes v0.4.0](docs/release_notes_v0.4.md)
- [Implementation report v0.4](docs/implementation_report_v0.4.md)
- [Release notes v0.5.0](docs/release_notes_v0.5.md)
- [Implementation report v0.5](docs/implementation_report_v0.5.md)
- [Release notes v0.6.0](docs/release_notes_v0.6.md)
- [Implementation report v0.6](docs/implementation_report_v0.6.md)
- [Current status](STATUS.md)
- [Implementation plan](PLAN.md)
- [Contributing guidance](CONTRIBUTING.md)
- [Security and private-data guidance](SECURITY.md)

## License

Copyright is reserved. See [LICENSE](LICENSE). The repository is available for viewing,
educational evaluation and portfolio demonstration; reuse requires prior permission.
