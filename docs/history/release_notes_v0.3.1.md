# Release v0.3.1 — Transparent Forecast Coverage

**Release date:** 25 August 2026

Version 0.3.1 is a corrective release for forecast-dispatch reporting. It does not alter
battery physics, dispatch optimization, forecast values, or realized-price settlement.

## Correction

Daily persistence uses the previous market day's matching wall-clock slot. On the day
after the spring daylight-saving transition, the preceding 23-hour day has no values for
one clock hour. This leaves one hourly forecast or four quarter-hour forecasts missing.

The backtest already dispatched only complete forecast days, but v0.3.0 recalculated
forecast coverage after excluding the incomplete day. That could make coverage appear to
be 100% without directly identifying the excluded date.

Version 0.3.1 now reports:

- full requested evaluation day and interval counts;
- backtested day and interval counts and fractions;
- full-period forecast metrics and coverage;
- separate metrics for complete days actually dispatched;
- total missing forecast intervals;
- every excluded market day with its interval and missing-value counts.

The default ensemble remains complete across the tested spring DST period because it can
use available weekly and rolling-history components when daily persistence is missing.

## Packaging corrections

- NumPy is now declared directly because project modules import it directly.
- ENTSO-E requests identify the active package version in the user-agent.

## Validation

- 35 automated tests pass.
- New tests cover hourly and quarter-hour daily-persistence exclusions after spring DST.
- A separate test confirms that the ensemble backtests all evaluation days at both
  resolutions across the same transition.

Synthetic fixtures validate engineering behavior only. Official HEnEx and ENTSO-E data
acceptance remains pending and no result in this release is investment advice.
