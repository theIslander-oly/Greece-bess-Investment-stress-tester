# Greek Battery Investment Stress Tester — Implementation Report v0.3.1

**Date:** 25 August 2026  
**Status:** Forecast-coverage reporting hardened  
**Scope:** Corrective release; Greek Day-Ahead Market standalone BESS only

## Reason for the release

A release-style audit confirmed the optimizer, settlement accounting, DST interval
construction, package and default ensemble workflow, but found an incomplete-day
disclosure problem in the daily-persistence dispatch backtest.

Daily persistence forecasts a target interval from the previous market day's matching
wall-clock slot. The first normal day after spring DST contains an hour that did not exist
on the preceding 23-hour day. The forecast table correctly contained missing values, but
v0.3.0 removed the whole incomplete day before recalculating the backtest's forecast
coverage. As a result, the backtest summary could show 100% coverage without listing the
excluded date.

## Implementation

`backtest_forecast_dispatch` now classifies every requested evaluation day before solving
dispatch. Complete days continue through the existing planned/perfect daily solves.
Incomplete days are retained in structured summary metadata.

The summary now includes:

- `evaluation_day_count` and `evaluation_interval_count`;
- `backtested_day_count` and `backtested_interval_count`;
- `backtested_day_fraction` and `backtested_interval_fraction`;
- `excluded_incomplete_forecast_day_count`;
- `excluded_incomplete_forecast_days`, including date, total intervals and missing count;
- `missing_forecast_interval_count`;
- `forecast_metrics` over the complete requested evaluation table;
- `backtested_forecast_metrics` over dispatched complete days only;
- a concise `forecast_coverage_policy` explanation.

This preserves the no-interpolation policy and prevents optimization with missing prices
while making exclusions explicit.

## Regression coverage

New tests use 28 March through 31 March 2026 as the evaluation period:

- hourly daily persistence reports 95 evaluation intervals, one missing forecast,
  exclusion of 30 March, and 71 dispatched intervals;
- quarter-hourly daily persistence reports 380 evaluation intervals, four missing
  forecasts, exclusion of 30 March, and 284 dispatched intervals;
- the ensemble reports full coverage and dispatches all 95 hourly or 380 quarter-hourly
  evaluation intervals.

The full suite contains 35 tests.

## Packaging

The package version is 0.3.1. NumPy is declared as a direct dependency, and the ENTSO-E
client user-agent derives its version from the package rather than retaining a stale
hard-coded value.

## Interpretation and remaining acceptance work

The release does not change financial results for days already backtested. It changes the
denominator and disclosure needed to interpret coverage honestly. Perfect foresight
remains a labelled upper bound, and synthetic data remains test/demo data only.

Production acceptance still requires a legitimate HEnEx workbook, a private ENTSO-E API
run, cross-source reconciliation and a complete official multi-year backtest.
