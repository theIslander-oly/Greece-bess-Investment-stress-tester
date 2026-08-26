# Release v0.4.0 — Leakage-Safe ML Forecast Benchmark

**Release date:** 25 August 2026

Version 0.4.0 adds the first machine-learning benchmark while preserving the project's
research-only interpretation and strict time-ordering rules.

## Models and features

The release includes deterministic ridge and histogram-gradient-boosting regressors.
Both use the same auditable feature table:

- market-slot, weekday and annual calendar cycles;
- weekend and DST occurrence indicators;
- previous-day, two-day and seven-day matching-slot prices;
- causal naïve ensemble values;
- matching-slot rolling mean, standard deviation, minimum and maximum.

Every price-derived feature uses only earlier market days. Missing historical values are
imputed inside the model pipeline using the current training sample only.

## Honest evaluation

Users provide validation and test start dates. Training precedes validation. Model
selection uses validation RMSE only, while the held-out test ranking remains a separate
report. Models refit walk-forward at a configurable frequency using expanding history or
an optional bounded training window. A refit is forced at the held-out test boundary so
all completed validation history is available without using test outcomes. Every refit
records its training start, training end and forecast start.

ML forecasts are compared against daily persistence, weekly persistence, rolling mean
and the causal naïve ensemble using identical signed-price-safe metrics.

## Dispatch benchmark

The held-out dispatch benchmark evaluates every method on the same complete test days.
This common-horizon rule prevents missing forecasts from changing the comparison period.
Planned charge/discharge quantities are settled at realized prices and compared with the
same perfect-foresight daily ceiling.

Price error and dispatch value are ranked separately. A lower RMSE is not assumed to
guarantee a higher battery margin.

## Commands

- `forecast-ml` writes validation/test forecasts and the full forecast audit summary.
- `backtest-ml-dispatch` writes the selected model schedule, all forecasts, all
  method/day dispatch results, and forecast/dispatch JSON summaries.

## Validation

- 42 automated tests pass.
- Future price mutations leave earlier model forecasts unchanged.
- Refit logs prove training ends before forecast starts.
- Hourly and quarter-hour spring DST cases pass.
- Like-for-like perfect-foresight and realized-settlement identities pass.

No official price history is bundled. Synthetic outputs are for tests and demonstrations
only and must not support an investment conclusion.
