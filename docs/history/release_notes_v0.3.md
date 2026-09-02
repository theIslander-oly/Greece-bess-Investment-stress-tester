# Release v0.3.0 — Leakage-Safe Forecast Dispatch

**Release date:** 25 August 2026

Version 0.3.0 establishes the forecast baseline and realized-settlement layer required to
move beyond perfect foresight without overstating achievable revenue.

## Highlights

- Daily, weekly and 28-day rolling price baselines.
- Causal ensemble using only prior market days.
- DST-safe market-slot matching for hourly and quarter-hour data.
- Forecast metrics designed for signed electricity prices.
- Daily battery schedules optimized against forecasts and settled on realized prices.
- Perfect-foresight value ceiling, realized value capture and regret.
- Explicit price-taking acceptance and daily terminal-SOC assumptions.
- CLI commands for forecast generation and forecast-dispatch backtesting.

## Leakage protection

All intervals for one target market day are forecast before any realized value from that
day enters model history. An automated test changes future prices and confirms that all
earlier forecasts remain unchanged.

## Settlement protection

Forecast prices determine the planned schedule, but realized prices determine backtest
revenue. A deliberately adverse test profile produces +€100 forecast-planned margin,
−€100 realized margin and +€100 perfect-foresight margin, proving those values are separated.

## Interpretation

This remains a research backtest, not expected project revenue. Price-taking quantities
are assumed accepted, initial SOC is restored at each day-end, and imbalance/bid-acceptance
effects are excluded.

## Validation

- 32 automated tests pass.
- Python package 0.3.0 builds successfully.
- Hourly and quarter-hour DST behavior remains covered.

Official multi-year validation remains pending. Synthetic fixtures test correctness only
and do not support an investment conclusion.

## Next direction

Version 0.4 should add time-split ML forecasting and walk-forward retraining. ML models
must be judged against the v0.3 baselines on both forecast error and realized dispatch
value.
