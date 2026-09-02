# Greek Battery Investment Stress Tester — Implementation Report v0.7.4

**Date:** 27 August 2026
**Scope:** Per-delivery-year decomposition of an accepted replay, and a published
daily-composed perfect-foresight mode

## Why this milestone exists

The accepted 2020-2026 replay reports one aggregate perfect-foresight margin and one aggregate
forecast capture ratio. That period contains a COVID price trough, the 2022 gas crisis, a
negative-price surge in 2025-2026 and a change of market resolution on 1 October 2025. Averaging
those regimes into one number conceals the property that most affects how the replay should be
read. This milestone regroups results the dispatch and backtest stages already produce; it adds
no model, market, transformation or data.

## Delivered decomposition

`decompose_annual_replay` takes the accepted canonical history, optionally a perfect-foresight
interval schedule, and optionally one daily-results table per forecast method. It produces three
tables and a summary.

A **delivery year** is the calendar year of the interval's CET/CEST market-day start. This is the
convention the committed custody records already use, and the summary states why grouping the
same intervals by UTC year moves the interval beginning 31 December 23:00Z into the earlier year.

The **per-year overview** carries the year's first and last market day, its market-day count, its
coverage against the calendar year, an explicit partial-year flag, interval counts by resolution
regime, delivered hours, preserved negative, zero and missing price counts, price context
including the mean daily price range, and the perfect-foresight ceiling with its margin
components, captured prices and, when a capacity is supplied, equivalent full cycles.

The **per-method table** reports, for each delivery year and method, backtested-day coverage
against the days available, interval-weighted MAE and RMSE recomposed from the daily table,
forecast-planned and realized margin, that method's own-days ceiling, regret, capture and
loss-making days. A year a method did not backtest reports no margin rather than a zero.

The **common-day table** restricts every method to the market days all supplied methods
backtested and records the ceiling spread for that year, which is the like-for-like evidence: on
a shared day set under one battery and one availability assumption the ceiling must be identical.

Three refusals protect the pairing. An accepted history repeating a canonical delivery
interval is rejected, because a decomposition of a duplicated history would double-count its own
totals. A schedule that settles any interval at a price the supplied
history does not publish is rejected, as is a schedule covering an interval the history does not
contain; this is the annual analogue of the acceptance settlement audit. A daily-results table
covering a market day absent from the history is rejected as describing a different history.

## Daily-composed perfect foresight

`optimize_daily_perfect_foresight` and `optimize-perfect-foresight --daily-solves` solve every
market day independently and compose the schedules. The 2026-08-27 acceptance ran this mode
through a temporary runner that no longer exists, so there was no published surface for it.

The mode requires `terminal_soc_fraction` to equal `initial_soc_fraction`, so independent days
can be composed without an energy discontinuity. Its composed margin is at or below the single
full-horizon margin, because restoring SOC each day removes inter-day arbitrage; both remain
labelled upper bounds. It is the required basis for annual attribution: a full-horizon solve may
charge on 31 December and discharge on 1 January, splitting one trade's cost and revenue across
two delivery years.

## Outputs and public surfaces

`greek_bess.analysis` exports `decompose_annual_replay`, `AnnualReplayDecomposition` and
`AnnualDecompositionError`. `greek_bess.dispatch` additionally exports
`optimize_daily_perfect_foresight`.

`greek-bess decompose-annual-replay` writes the per-year overview CSV, the per-method CSV, the
common-day CSV and a summary JSON carrying the delivery-year, normalization and like-for-like
policies, the partial years, the ceiling reconciliation residual and the common-day ceiling
spread. `--daily-results METHOD=PATH` accumulates across repeated flags.

The `Decompose the accepted replay by delivery year` workflow verifies a downloaded
`greek-dam-official-history` artifact against its committed custody record and refuses to proceed
on a difference, merges the archived and daily history, solves the daily-composed ceiling,
backtests every requested causal naïve method and decomposes the result. Only per-year aggregates
reach the job summary; the tables are uploaded as a private 90-day artifact.

## Validation and limitations

Ruff, mypy, 157 tests and a clean wheel build pass, up from 116. Twenty-seven new deterministic
synthetic tests cover market-clock year assignment against a UTC grouping, partial-year coverage,
preserved zero, negative and missing prices, annual ceiling reconciliation, interval-weighted
error recomposition, the identical common-day ceiling, a year with no backtested days, a year with
no common days, a duplicated accepted history, both schedule refusals, both daily-results
refusals, the daily-solve terminal-SOC
requirement, per-day availability, availability alignment under a shuffled input frame, the bound
ordering between the two solve modes, and the CLI artifacts. No official data or generated output
is committed.

Every annual figure inherits the label of the aggregate it decomposes: a per-year
perfect-foresight margin is a historical gross-margin upper bound and a per-year capture ratio is
a historical backtest outcome. Neither is expected revenue, a forecast for a comparable future
year, or investment evidence. Years of unequal coverage are not comparable on totals alone;
partial years are flagged with their day counts and per-market-day figures are within-period
averages that are deliberately not annualized. No probability, percentile, loss metric or ranking
of delivery years is produced, and ordering years by margin ranks nothing about the future.

The decomposition has not yet been run against the accepted official history. Until it is, the
repository holds the surface and the workflow but no accepted per-year evidence.
