# Implementation report — GFS feature semantics

**Date:** 9 September 2026
**Execution-plan stage:** 2
**Review findings:** 3 and 4

## Scope

This stage corrects how already-selected NOAA GFS messages are validated and how their values are
combined. It does not change the declared source, 00 UTC D-1 cycle, geography, decision cutoff,
feature set or held-out period. It launches no retrieval, acceptance or benchmark workflow.

## Decoded-message contract

The `.idx` sidecar remains the byte-range selector, but is no longer treated as proof of the
message's meaning. Each selected record must declare the requested source cycle and the exact
instant or six-hour reset-bucket averaging window. ecCodes metadata is retained for parameter
short and long name, units, level type and value, step type, start and end step, step-unit code,
source date/time and validity date/time.

Before a sample is admitted, all of that decoded metadata is compared with the registered message
contract, the selected sidecar record and the requested cycle. A wrong parameter, unit, level,
cycle, valid time, forecast step or average/accumulation interpretation raises a named integrity
refusal. It is not recorded as a provider non-publication and is not silently converted.

## Feature construction

The earlier implementation first took a geographic weighted mean of signed U and V wind
components and then calculated one magnitude. Components from different places can cancel under
that order. The correction calculates `hypot(U, V)` independently at each declared point and
then applies the unchanged weights. With weights 0.25/0.75, eastward winds +12/−4 m/s and zero
northward wind, the corrected weighted local speed is 6 m/s rather than zero.

Radiation de-averaging is now performed for every point before geographic weighting. The existing
arithmetic remains unchanged: ordinary steps subtract adjacent bucket means with their spans,
while the first step after a six-hour reset needs no predecessor. Performing the transformation
locally makes the value construction order explicit and shares the same physical aggregation
boundary as wind.

## Provenance and invalidation

Retrieval summaries now record `feature_semantics_version = 2`, the complete declared geography
and the complete decoded-message contract. Feature rows continue to carry the 00 UTC D-1 issue
time and name every contributing source document and digest.

Every GFS feature table produced before this correction used semantics version 1 implicitly. All
such tables, including any private artifacts from the incomplete 4 September retrieval attempts,
must be rebuilt. No old feature-set digest or acceptance identity may be silently reused.

## Executable evidence

The tests generate a small real GRIB2 message with ecCodes and decode it through the production
decoder. Separate refusal cases mutate parameter identity, units, level, source cycle, valid time,
forecast step and average semantics. Sidecar cases reject another cycle and accumulation where a
bucket average is required. Feature tests cover the opposite-wind example and radiation ordinary
steps and reset boundaries.

The final local gate ran on Windows with Python 3.13.7, ecCodes 2.48.0, pytest 8.4.2 and
Hypothesis 6.168.0. Ruff passed, mypy reported no issues in 65 source files, all 637 tests passed
in 119.61 seconds, and the isolated wheel build completed successfully. GitHub CI remains the
clean Python 3.12/3.13 review gate.

## Interpretation

This is a data-integrity correction, not evidence that weather improves a forecast or battery
dispatch. NOAA GFS features remain unaccepted until the later declared workflow stages complete.
Nothing here is financial advice, a forecast, expected revenue, investment evidence or a bankable
study.
