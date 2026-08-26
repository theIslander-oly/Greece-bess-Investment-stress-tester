# Greek Battery Investment Stress Tester — Implementation Report v0.4

**Date:** 25 August 2026  
**Status:** Leakage-safe ML forecast and dispatch benchmark implemented  
**Scope:** Greek Day-Ahead Market standalone BESS only

## Outcome

Version 0.4 adds a reproducible ML research benchmark above the v0.3 causal naïve
baselines. It answers two separate engineering questions:

1. Does an ML forecast reduce held-out price error relative to simple causal baselines?
2. Does that forecast produce more realized battery value under identical constraints?

It does not answer whether a real project should be built. Official data acceptance,
degradation, finance and probabilistic risk remain incomplete.

## Time-split design

`MLForecastConfig` requires explicit validation and test start dates. All earlier data is
training history. Model choice is the lowest validation RMSE; test results never select
the model.

Predictions are generated one market day at a time. At each configured refit point, the
training sample ends before the forecast day. Between refits, the fitted model remains
fixed while causal lag features can use newly realized prior days. Expanding history is
the default, with an optional bounded training window. A refit is forced on the first test
day so the held-out run uses all completed validation history but no test outcomes.

The result records every refit's forecast start, training start/end, training-day count
and training-interval count.

## Feature engineering

The shared feature table contains 17 features:

- six cyclical market-calendar variables;
- weekend and DST-slot occurrence indicators;
- daily, two-day and weekly matching-slot lags;
- the v0.3 rolling mean and causal ensemble;
- seven-day matching-slot mean, standard deviation, minimum and maximum.

Target-day realized price is retained only as the label. All historical values are added
to feature history after the complete target day's features are fixed. Feature provenance
is included in every summary.

External variables are deliberately not accepted yet. Weather, renewable, fuel and
interconnector features need independently verified publication timestamps and Greek DAM
day-ahead availability rules before they can enter a leakage-controlled benchmark.

## Models

- Ridge regression provides a regularized, scaled linear reference.
- Histogram gradient boosting provides a deterministic nonlinear tree benchmark.

Both pipelines impute missing lag values from training data only. Scikit-learn and every
model assumption are recorded in package/config metadata.

## Forecast metrics

Validation and test reports cover every ML model and all four naïve baselines. Metrics
include coverage, MAE, RMSE, signed bias, median absolute error, WAPE, correlation and
negative-price precision/recall. Rankings use RMSE, but complete raw metrics remain.

## Dispatch comparison

`backtest_ml_dispatch_benchmark` first identifies the held-out days on which every method
has a complete forecast. All methods are then optimized and settled over precisely that
common horizon. Excluded days and method-specific missing counts are reported.

For every method:

- the forecast determines planned dispatch;
- realized DAM prices settle the planned grid energy;
- fees and degradation-throughput costs remain identical;
- initial SOC is restored at each day-end;
- a separate perfect-foresight solve supplies the common daily ceiling.

The output ranks realized margin, regret and value capture without claiming that test
performance is expected future revenue.

## Verification

The suite contains 42 tests. New tests cover:

- train/validation/test separation and complete model outputs;
- future-price mutation with unchanged earlier forecasts;
- insufficient-history and invalid-split rejection;
- quarter-hour spring DST forecasts;
- common dispatch horizons and disclosed DST exclusions;
- realized settlement reconstruction and identical perfect ceilings;
- end-to-end ML forecast and dispatch CLI artifacts.

Engineering-only synthetic runs are not retained as project evidence. Production
acceptance still requires an official HEnEx workbook, private ENTSO-E retrieval,
cross-source reconciliation and a complete official multi-year benchmark.
