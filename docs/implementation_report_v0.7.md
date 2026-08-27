# Greek Battery Investment Stress Tester — Implementation Report v0.7 Foundation

**Date:** 26 August 2026
**Scope:** Deterministic seasonal block-bootstrap price-path generator

## Delivered method

The generator validates a complete, continuous canonical history before sampling. It divides
each requested path into fixed-size market-day blocks (with a shorter final block), constructs
the target interval-count pattern, and samples with replacement from calendar-contiguous source
blocks in the same meteorological season that have exactly that pattern. A configured NumPy seed
makes candidate selection reproducible.

Prices are copied in physical interval order without interpolation, smoothing or adjustment.
Target UTC, CET/CEST market and Europe/Athens timestamps are rebuilt from target market days.
This prevents duplicate local-clock labels from becoming keys and preserves spring/autumn DST
day lengths. Each block records source and target boundaries, season, day/interval counts,
candidate count and sampled candidate index.

## Public surfaces

- `BootstrapConfig`, `BootstrapResult` and `generate_seasonal_bootstrap_paths` form the focused
  Python API.
- `greek-bess generate-bootstrap-paths` reads canonical history plus JSON configuration and
  writes paths, sampled-block provenance and a method/configuration summary.
- Output labels state that paths are synthetic and are not forecasts or investment evidence.

## Validation coverage

Small generated synthetic inputs prove deterministic equality for identical seeds, timezone-aware
output, exact preservation of sampled zero and negative prices, 92/100-quarter-hour DST target
days, strict configuration parsing, block provenance, and explicit rejection of missing prices
or intervals. CLI integration verifies all three output artifacts. No official data or generated
path artifact is committed.

## Deliberate exclusions and limitations

This foundation does not dispatch a battery, calculate degradation or finance, assign calibrated
probabilities, report P5/P50/P95 or loss probability, rank worst paths, or add outage, spread,
negative-price or cannibalisation shocks. Meteorological seasons are a coarse stationarity
assumption, and exact DST compatibility can make a candidate set empty. Generated paths cannot
support an investment conclusion.
