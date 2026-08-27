# Official multi-year operational acceptance — 27 August 2026

## Scope and interpretation

This report records the first live operational acceptance of the existing dispatch and forecast
code over the complete accepted official HEnEx Greek Day-Ahead Market history. It exercises two
already-implemented analytical paths without adding a model, a stress transformation or a market:

- **A.** the perfect-foresight dispatch upper bound; and
- **B.** the walk-forward forecast-planned dispatch backtests settled at realized official prices.

Every result below is **historical benchmark evidence about a selected historical period**. Nothing
here is expected revenue, a forecast, a probability, a ranking of future performance, bankable or
investment-grade evidence, or an investment conclusion. Only Greek DAM energy arbitrage is modelled.

Official prices, schedules and generated artifacts remain outside Git. Only aggregate statistics,
hashes and diagnostics are recorded here.

## Accepted input

| Item | Value |
| --- | --- |
| Artifact | `greek-dam-official-history` from workflow run `32971677163` |
| Artifact SHA-256 | `127915bc6e143a6bf2a4cb0a559b798e231062097bdaf9bf467a051260c4b198` |
| Provider / source label | HEnEx (`source=henex`), bidding zone `GR` |
| Distinct publication versions | 3 |
| First delivery interval (UTC) | `2020-10-31 23:00:00+00:00` |
| Last delivery interval (UTC) | `2026-08-25 21:45:00+00:00` |
| Market-day coverage | 2020-11-01 through 2026-08-25 |
| Market days | 2,124 |
| Total intervals | 74,663 |
| Archived 2020-2025 intervals | 51,915 |
| Incremental 2026 intervals | 22,748 |

The artifact hash was verified before extraction and matches both the value published by the GitHub
Actions artifact digest and `docs/official_history_acceptance_2026-08-26.md`.

## Aggregate input quality findings

| Check | Result |
| --- | --- |
| Canonical schema and timezone-aware UTC key | Valid; market-clock and Europe/Athens views retained |
| Missing prices | 0 |
| Duplicate canonical UTC keys | 0 |
| Gaps or overlaps between consecutive intervals | 0 |
| Timestamp-vs-`duration_hours` mismatches | 0 |
| Incomplete or unexpected market-day intervals | 0 |
| Mixed resolution inside one market day | 0 |
| Resolution regimes present | 1.0 h (43,079 intervals), 0.25 h (31,584 intervals) |
| Hourly market-day lengths | 23 × 5 days, 24 × 1,786 days, 25 × 4 days |
| Quarter-hour market-day lengths | 92 × 1 day, 96 × 327 days, 100 × 1 day |
| Negative prices preserved | 1,767 |
| Zero prices preserved | 1,914 |
| `henex_mcp_rounding_consensus` flags | 980 |
| Deterministic quality status | Valid, information notices only |

The six spring and five autumn transitions inside the coverage are all present with their expected
short and long market-day structure across both resolution regimes. The negative, zero and
rounding-consensus counts reconcile exactly with the archived and incremental stage reports in
`docs/official_history_acceptance_2026-08-26.md`. No price was interpolated, clipped or filled.

## A. Perfect-foresight acceptance

Configuration: `examples/battery_50mw_100mwh.json`, unmodified — 50 MW charge/discharge,
100 MWh, SOC 5-95 %, initial and terminal SOC 0.50, one-way charge and discharge efficiency 0.94
each, no self-discharge, grid import/export limits 50 MW, maximum 1.5 daily equivalent cycles,
zero buy fee, zero sell fee, zero degradation-throughput cost, MIP relative gap 1e-7, no solver
time limit. Availability is the scalar 1.0 for every interval; no outage or derating path exists
yet. These values are deliberately illustrative and are not project evidence.

Solver: HiGHS branch-and-cut MILP via `scipy.optimize.milp`, bundled with SciPy 1.18.1.
Environment: Python 3.12.3, NumPy 2.5.2, pandas 2.3.3, scikit-learn 1.9.0.

The existing API accepted the **entire 74,663-interval horizon in one solve**, so both the true
full-horizon bound and the repository's daily terminal-energy convention were recorded.

| Diagnostic | Single full-horizon solve | Daily independent solves composed |
| --- | ---: | ---: |
| Input / output intervals | 74,663 / 74,663 | 74,663 / 74,663 |
| Market days solved | 2,124 (one horizon) | 2,124 of 2,124 |
| Failed or excluded days | 0 | 0 |
| Solver status | HiGHS 7 — Optimal | status 0 for all 2,124 solves |
| Solve time | 537.9 s | 51.5 s |
| Simultaneous charge and discharge intervals | 0 | 0 |
| Charge / discharge power violations | 0 / 0 | 0 / 0 |
| Grid import / export limit violations | 0 / 0 | 0 / 0 |
| SOC lower / upper violations | 0 / 0 | 0 / 0 |
| Storage-balance max residual | 7.2e-12 MWh | 2.4e-11 MWh |
| Terminal-energy compliance | exact (0.0 MWh error) | exact for every day (max 0.0 MWh) |
| Daily equivalent-cycle cap breaches | 0 | 0 |
| Aggregate grid charge | 332,354.99 MWh | 343,653.31 MWh |
| Aggregate grid discharge | 293,668.87 MWh | 303,652.06 MWh |
| Aggregate purchase cost | EUR 30,355,440.87 | EUR 33,312,114.94 |
| Aggregate sale revenue | EUR 57,284,528.81 | EUR 58,286,844.53 |
| Aggregate fees | EUR 0.00 | EUR 0.00 |
| Aggregate degradation-throughput cost | EUR 0.00 | EUR 0.00 |
| **Aggregate gross margin** | **EUR 26,929,087.93** | **EUR 24,974,729.59** |
| Equivalent full cycles | 2,936.69 | 3,036.52 |
| Realised discharge/charge ratio | 0.8836 | 0.8836 |

Both results are a **historical perfect-foresight gross-margin upper bound**.

Two internal consistency properties hold. The daily-composed margin is strictly below the
full-horizon margin, because restoring the initial SOC each day is a binding constraint that
removes inter-day arbitrage. The realised discharge/charge ratio equals 0.94 × 0.94 in both modes,
matching the configured one-way efficiencies exactly.

An identical second run of both modes reproduced the same decision-variable fingerprint and the
same aggregate margin to the last recorded digit.

## B. Forecast-dispatch acceptance

All four existing causal naïve baselines were backtested over the full accepted history with a
28-day rolling window, and the existing ML benchmark was run over the period its API supports. No
model was added, retuned or replaced.

### Leakage and time-order audit

Prices for every market day after 2025-06-30 (33,792 intervals) were replaced with a grossly
different signed series and all baselines were regenerated. Every forecast for the 40,871
pre-cutoff intervals was **bit-identical** to the unmutated run for all four methods, so no future
observation reaches an earlier target day. The forecast table is time-ordered.

For the ML benchmark, all 278 recorded refits (139 per model) satisfy
`training_end_day < forecast_start_day`. Training begins at 2020-11-01; the latest training window
ends 2026-08-18. Validation covers 2024-01-01 to 2024-12-31 (366 days) and the held-out test period
covers 2025-01-01 to 2026-08-25 (602 days), with no boundary crossing. The winning model
(`hist_gradient_boosting`) was selected on validation error only.

### Settlement audit

For every method, the realized settlement price of every dispatched interval equals the official
HEnEx price for that canonical UTC key exactly, and an independent restatement of
`realized price × planned quantities − fees` reproduces the reported realized margin with a maximum
absolute residual of **EUR 0.00**. Planned quantities come from the forecast solve and differ from
the realized price series, confirming the plan was not settled against its own forecast.

### Coverage and structured exclusions — full accepted period

Requested period: 2,124 market days / 74,663 intervals.

| Method | Days backtested | Day coverage | Interval coverage | Excluded days | Missing forecast intervals |
| --- | ---: | ---: | ---: | ---: | ---: |
| `daily_persistence` | 2,116 | 99.62 % | 99.55 % | 8 | 105 |
| `weekly_persistence` | 2,104 | 99.06 % | 98.59 % | 20 | 681 |
| `rolling_mean` | 2,122 | 99.91 % | 99.84 % | 2 | 96 |
| `ensemble` | 2,122 | 99.91 % | 99.84 % | 2 | 96 |

Every excluded day is attributable to a documented structural cause; **none is unexplained**:

| Exclusion reason | daily | weekly | rolling | ensemble |
| --- | ---: | ---: | ---: | ---: |
| First day, no prior history | 1 | 1 | 1 | 1 |
| Insufficient causal lag history (7-day warm-up) | 0 | 6 | 0 | 0 |
| Spring DST day removes the required wall-clock slot | 6 | 6 | 0 | 0 |
| 2025-10-01 hourly-to-quarter-hour resolution change | 1 | 1 | 1 | 1 |
| Resolution-change lag warm-up | 0 | 6 | 0 | 0 |

The spring exclusions are the previously documented behaviour: the 23-hour market day preceding the
target does not contain the wall-clock slot a persistence lag requires (one hourly interval, or
four quarter-hour intervals in 2026). The 2025-10-01 exclusion is the first quarter-hour market day,
whose 15-, 30- and 45-minute slots have no hourly predecessor. No autumn DST day is excluded,
because the repeated wall-clock hour is disambiguated by occurrence rank.

### Full-period versus backtested-only metrics and dispatch value

Metrics are signed-price safe; MAPE is excluded by methodology.

| Method | Full-period RMSE | Backtested RMSE | Backtested MAE | WAPE | Realized margin | Ceiling | Regret | Capture | Loss days |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `daily_persistence` | 43.893 | 43.845 | 26.287 | 0.2094 | 17,339,039 | 24,868,683 | 7,529,644 | 0.6972 | 110 |
| `weekly_persistence` | 52.505 | 52.509 | 32.567 | 0.2585 | 16,943,803 | 24,743,656 | 7,799,854 | 0.6848 | 110 |
| `rolling_mean` | 46.094 | 46.090 | 29.608 | 0.2359 | 19,134,060 | 24,946,807 | 5,812,747 | 0.7670 | 62 |
| `ensemble` | 39.204 | 39.202 | 25.008 | 0.1993 | 19,492,323 | 24,946,807 | 5,454,484 | 0.7814 | 52 |

RMSE and MAE are EUR/MWh; margins are EUR. Each method's ceiling covers only its own backtested
days, so the ceilings differ. On the 2,098 market days backtested by **all four** methods the
perfect-foresight ceiling is identical at EUR 24,665,532.17 with a spread of exactly EUR 0.00,
confirming a like-for-like physical, availability and terminal-energy comparison.

Negative-price detection differs sharply by method (`ensemble` precision 0.790 / recall 0.072;
`daily_persistence` precision and recall 0.483; `rolling_mean` recall 0.002), which is why the
signed-price metric set is reported rather than a single error figure.

### Held-out ML comparison

On the 591 held-out test days (37,223 intervals) where every comparison method has a complete
forecast — 98.17 % of the 602 test days, 11 excluded — all six methods share one identical
perfect-foresight ceiling of EUR 8,365,158.63.

| Method | Backtested RMSE | Realized margin | Capture |
| --- | ---: | ---: | ---: |
| `hist_gradient_boosting` | 30.958 | 6,885,079 | 0.8231 |
| `rolling_mean` | 37.848 | 6,875,718 | 0.8219 |
| `ridge` | 31.408 | 6,850,165 | 0.8189 |
| `ensemble` | 33.538 | 6,822,522 | 0.8156 |
| `daily_persistence` | 38.260 | 6,324,531 | 0.7561 |
| `weekly_persistence` | 45.742 | 6,040,064 | 0.7221 |

These are historical outcomes on one selected period, not a production forecast, an expected
winner or a future revenue estimate. They illustrate the documented caution that price accuracy and
dispatch value are different objectives: `rolling_mean` has materially worse RMSE than `ridge` yet
captures marginally more historical value.

An identical second run reproduced the daily result fingerprints for all four naïve backtests and
bit-identical ML forecasts.

## Reproducibility

The acceptance used a temporary, untracked runner that only composes existing public APIs; no
optimizer or forecasting logic was duplicated, and no repository code required changing. The
equivalent published surfaces are:

- `greek_bess.data.quality.assess_quality(..., require_complete_days=True)` for input acceptance;
- `greek_bess.dispatch.optimize_perfect_foresight(prices, config)` for path A, once over the full
  horizon and once per market day;
- `greek_bess.backtest.backtest_forecast_dispatch(prices, config, method=..., rolling_window_days=28)`
  for each of the four naïve methods;
- `greek_bess.forecast.generate_ml_forecasts` with `MLForecastConfig(validation_start_day=2024-01-01,
  test_start_day=2025-01-01, feature_window_days=28, refit_frequency_days=7, min_training_days=365,
  random_seed=42)`, then `greek_bess.backtest.backtest_ml_dispatch_benchmark`.

The equivalent CLI workflows are documented in `README.md` sections 5 to 9. The official history is
retrieved privately with `fetch-henex-archives` and `fetch-henex-daily` as described in
`docs/official_data_retrieval.md`; it is never committed.

## Limitations carried forward

- Perfect foresight remains a gross-margin ceiling under the stated assumptions, not achievable or
  expected revenue.
- Illustrative battery, fee and degradation-cost inputs are not project evidence.
- Availability is a constant 1.0; no outage, derating or auxiliary-load model exists.
- Price-taking quantities are assumed fully accepted; bid acceptance, imbalance exposure and
  route-to-market constraints are excluded.
- Daily backtests restore the initial SOC at each day end and do not optimise energy across days.
- ML features remain calendar and price history only; no validated exogenous variable is used.
- The 2025-10-01 resolution change means models trained on hourly history forecast quarter-hour
  delivery inside the held-out test period; this is disclosed, not corrected.
- Degradation, finance, NPV, probabilities, percentiles, loss probabilities, shocks,
  cannibalisation and any user interface are outside this milestone.
- ENTSO-E private-token reconciliation and ADMIE publication-timing acceptance remain open.
