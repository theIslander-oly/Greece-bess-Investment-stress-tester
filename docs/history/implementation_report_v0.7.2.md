# Greek Battery Investment Stress Tester — Implementation Report v0.7.2

**Date:** 27 August 2026
**Scope:** Independent deterministic dispatch across seasonal bootstrap paths

## Delivered integration

The integration accepts labelled multi-path output from the seasonal block bootstrap. It rejects
missing or invalid path IDs, duplicate path/UTC keys, incomplete market days, gaps, overlaps,
non-synthetic provenance and any difference in ordered canonical interval identity between
paths. Prices, zero/negative values, timezone-aware keys and source metadata are not transformed.

After validation, every path is passed independently to the existing mixed-integer
perfect-foresight optimizer. The same immutable battery configuration and the same scalar or
interval-aligned availability profile apply to every solve. Power, energy, one-way efficiency,
SOC, grid, charge/discharge exclusivity, optional daily-cycle and terminal-energy constraints
are therefore enforced within each path, with no cross-path state.

## Outputs and public surfaces

`dispatch_bootstrap_paths`, `BootstrapDispatchResult` and `BootstrapDispatchInputError` provide
the Python API. `greek-bess dispatch-bootstrap-paths` writes an interval schedule retaining
`path_id` and canonical identity, one operational/revenue summary row per path, and a JSON record
of common assumptions and interpretation labels.

## Validation and limitations

Deterministic synthetic regression tests cover shared availability, terminal energy, provenance,
interval/path output shapes, duplicate/incomplete/inconsistent-path failures and CLI artifacts.
No generated paths or official data are committed. Every solve uses perfect foresight and is a
synthetic gross-margin upper bound—not a forecast, expected revenue, calibrated probability or
investment conclusion. Degradation, finance, NPV, percentiles, probabilities, rankings, shocks
and UI are excluded. Negative-price-event transformations remain deferred.
