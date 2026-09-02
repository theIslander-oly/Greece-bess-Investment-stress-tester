# Greek Battery Investment Stress Tester — Implementation Report v0.3

**Date:** 25 August 2026  
**Status:** Naïve forecast baselines and forecast-dispatch backtesting implemented  
**Scope:** Greek Day-Ahead Market standalone BESS energy arbitrage only

## Outcome

Version 0.3 adds a strictly causal price-forecast baseline and a realized-price dispatch
backtest. This is the first project version that separates:

1. prices used to plan battery actions;
2. prices used to settle those actions; and
3. the perfect-foresight value available under the same daily constraints.

That separation is necessary before evaluating ML forecasts or using dispatch results in
a financial model.

## Forecast methods

Four interval-level methods are available:

- `daily_persistence`: previous market day's same wall-clock slot;
- `weekly_persistence`: same slot seven market days earlier;
- `rolling_mean`: historical mean for the same slot over an editable calendar window;
- `ensemble`: mean of the causal baseline values available for the target interval.

The implementation uses market-clock hour/minute and occurrence rank. Occurrence rank
distinguishes the repeated fall-back DST slot. If a prior normal day has only one matching
slot, rank zero is used as the causal fallback for the repeated target slot.

## No-leakage control

Forecasts are generated one market day at a time. Every interval forecast for a target day
is fixed before any realized price from that day is appended to history. `start_day` limits
reported evaluation rows but does not discard the earlier history needed to produce them.

An automated test changes the last day's realized prices to €10,000/MWh and confirms that
every earlier forecast remains byte-for-byte identical.

## Forecast metrics

For each method the project reports:

- observation count and coverage;
- mean absolute error;
- root mean squared error;
- mean signed error;
- median absolute error;
- weighted absolute percentage error using absolute realized-price value;
- Pearson correlation when both series vary;
- negative-price precision and recall.

Ordinary MAPE is deliberately excluded because zero and negative prices make its ratios
undefined or misleading.

## Forecast-dispatch backtest

For every market day with complete forecasts:

1. copy the canonical realized-price frame;
2. replace only its objective price with the selected forecast;
3. solve the v0.2 mixed-integer battery dispatch model;
4. retain the planned power and energy schedule;
5. settle planned charge/discharge MWh against realized prices;
6. solve a separate perfect-foresight schedule using realized prices;
7. report forecast-planned margin, realized margin, perfect margin and regret.

## Fair-comparison rules

- Initial SOC must equal terminal SOC.
- Initial SOC is restored at the end of every market day.
- Forecast and perfect-foresight schedules use identical battery assumptions.
- Fees and degradation-throughput costs are identical in planning and settlement.
- Perfect-foresight capture is realized forecast-dispatch margin divided by the daily
  perfect-foresight ceiling when that ceiling is positive.

The daily terminal rule makes the backtest auditable but prevents cross-day arbitrage. A
later rolling-horizon implementation may carry SOC forward while preserving equivalent
forecast/perfect constraints.

## Optimizer hardening

A zero-price-cost and zero-degradation test exposed economically degenerate solutions with
unnecessary cycling. A numerical throughput tie-breaker of €0.0000001/MWh now favors the
lowest-throughput schedule among otherwise economically equivalent solutions. It is
reported separately and is not deducted from economic margin.

## Outputs

`forecast-naive` writes:

- interval forecasts;
- method-level metrics JSON.

`backtest-forecast-dispatch` writes:

- interval schedule with forecast and realized prices, planned dispatch, realized margin
  and perfect-foresight comparators;
- daily results with error, margin, regret, value capture, energy and cycles;
- aggregate summary JSON.

## Verification

The full suite contains 32 passing tests. New coverage includes:

- exact daily-persistence forecasts;
- future-mutation leakage protection;
- weekly persistence across spring DST;
- zero/negative-price metrics;
- exact forecast value capture;
- incorrect forecast settlement at realized prices;
- daily terminal-SOC validation;
- end-to-end forecast and backtest CLI outputs.

An engineering-only run backtested 59 days and 1,415 hourly intervals, including the
23-hour spring DST day. The 118 planned/perfect daily MILP solves completed in
approximately 2.8 seconds in the development environment. Synthetic financial outputs
from that run are not retained as project evidence and the observed runtime is not a
guarantee for official annual quarter-hour datasets.

## Limitations

- Forecasts are naïve baselines, not ML models.
- No exogenous load, renewable, fuel, weather or interconnector features are used.
- Price-taking planned quantities are assumed fully accepted.
- Bid curves, imbalance settlement and gate closure are excluded.
- Daily SOC restoration limits interday decisions.
- No official production dataset has yet been run end to end.
- No degradation state evolution, finance, scenario simulation or UI is included.

## User action

No action is required to continue development. The most valuable optional input is either:

1. one legitimately obtained HEnEx `EL-DAM_Results_EN` workbook; or
2. a privately configured `ENTSOE_SECURITY_TOKEN` environment variable.

Never paste the token into chat or commit it. Before project finance, project-specific MW,
MWh, grid limits, efficiencies, warranty/degradation, CAPEX, OPEX, lifetime and discount
rate assumptions will be required.
