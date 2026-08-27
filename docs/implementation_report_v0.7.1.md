# Greek Battery Investment Stress Tester — Implementation Report v0.7.1

**Date:** 27 August 2026
**Scope:** Deterministic additive price-level transformation for bootstrap paths

## Methodology

`PriceLevelShockConfig` strictly requires a finite `shift_eur_per_mwh` and non-empty
`transformation_id`; unknown or missing fields fail. The transformation adds that constant to
every interval price. It performs no sampling, clipping, flooring, interpolation or timestamp
remapping, so input path identity, UTC order, market/Greece views, DST structure, and zero or
negative results are preserved.

Each path must independently satisfy the canonical schema, continuous interval and complete
market-day checks. Missing prices, duplicate path/UTC keys, gaps, overlaps, invalid IDs and
structurally incomplete days fail before transformation.

## Public surfaces and provenance

`apply_price_level_shock`, `PriceLevelShockConfig` and `PriceLevelShockResult` are the focused
Python API. `greek-bess apply-price-level-shock` reads bootstrap paths and strict JSON config and
writes shocked paths, interval provenance and a method summary. Every provenance row includes
path ID, UTC interval key, transformation ID, method, shift, original price, shocked price and
input source/version. Labels explicitly identify outputs as synthetic non-forecasts that cannot
support investment conclusions.

## Validation and exclusions

Small synthetic tests cover deterministic equality, exact additive arithmetic, zero and negative
results, path/timestamp preservation, provenance completeness, strict config validation, CLI
artifacts and rejection of missing, duplicate and incomplete paths. No official or generated
data is committed. Spread, negative-price-event, outage and cannibalisation shocks, dispatch,
degradation, finance, probabilities, percentiles, loss metrics and rankings remain excluded.
