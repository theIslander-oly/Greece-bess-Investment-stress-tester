# Greek Battery Investment Stress Tester — Implementation Report v0.7.2

**Date:** 27 August 2026
**Scope:** Deterministic explicit negative-price-event transformation

## Methodology

The configuration strictly requires a transformation ID, a finite negative additive EUR/MWh
shift and one or more uniquely identified, non-overlapping half-open UTC windows. Event boundaries
must align with complete canonical intervals and select identical UTC keys in every path. The
shift applies only inside events, non-event prices remain exact, and every selected result must be
strictly negative. There is no random placement, interpolation, clipping or replacement.

## Public surfaces and provenance

`NegativePriceEventConfig`, `NegativePriceEventWindow`, `NegativePriceEventResult` and
`apply_negative_price_events` form the Python API. `greek-bess apply-negative-price-events`
writes shocked paths, interval provenance and a summary. Each input interval has one provenance
row containing path/UTC identity, event-applied status, event/transformation IDs, shift,
original/shocked prices and input source/version.

## Validation and limitations

Small synthetic tests cover reproducibility, exact unchanged non-event prices, negative event
outcomes, path/timestamp identity, provenance, strict config parsing, UTC and boundary alignment,
overlap rejection, insufficient shifts and CLI artifacts. Event timing, duration and magnitude
are explicit user sensitivities rather than calibrated Greek market estimates. Outputs are not
forecasts, probabilities or investment evidence. Spread, outage, cannibalisation, dispatch,
degradation, finance, percentiles, loss metrics and rankings remain excluded.
