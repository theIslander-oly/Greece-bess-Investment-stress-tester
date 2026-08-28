# Implementation report v0.7.6 — Bootstrap spread compression

**Date:** 28 August 2026

## Scope

Adds a deterministic spread-compression transformation for validated synthetic bootstrap paths,
the v0.7 milestone PLAN.md describes as how cannibalisation pressure is represented. No official
data, dispatch, finance or probability layer is involved.

## Why spread before availability

PLAN.md listed deterministic availability/outage-path integration before spread compression. The
per-delivery-year decomposition accepted on 28 August 2026 reordered them, and the reason is
recorded rather than assumed:

| Year | Mean price EUR/MWh | Mean daily range EUR/MWh | Ceiling EUR/market day |
| ---: | ---: | ---: | ---: |
| 2023 | 119.11 | 121.75 | 9,801 |
| 2024 | 100.88 | 162.59 | 13,047 |
| 2025 | 106.19 | 171.90 | 14,115 |
| 2026 | 98.47 | 181.30 | 14,431 |

Mean daily range rose every year since 2023 while mean price fell, and 2026 produced the highest
ceiling per market day of any non-crisis year on the lowest mean price since 2020. The ceiling
tracks spread, not level. The existing price-level shock leaves every within-day spread unchanged
and therefore moves margin only through round-trip efficiency losses and per-MWh fees, which
makes it a near-inert stress for storage; compressing spread changes the quantity being
arbitraged.

## Transformation

For compression factor `f` in [0, 1] and declared daily reference level `r` for path `k` on
CET/CEST market day `d`:

```
compressed(i) = r(k, d(i)) + f * (price(i) - r(k, d(i)))
```

Properties, each asserted by a test:

- `f = 1.0` is exactly the identity.
- `f = 0.0` flattens each market day onto its reference level (maximum daily range 0).
- Every within-day range is scaled by exactly `f`.
- A `daily_mean` basis preserves each daily mean exactly, so the transformation is a pure spread
  change and level sensitivity stays separable from spread sensitivity.

## Declared, not defaulted

`reference_basis` has **no default**, following the source-era precedent of 2026-08-27. The basis
decides whether the transformation is a pure spread change or also moves the level: `daily_mean`
preserves each daily mean, `daily_median` does not. The summary reports
`max_absolute_daily_mean_shift_eur_per_mwh` so a median basis discloses its own level effect
rather than hiding it. Defaulting would settle the most consequential assumption in the
transformation silently, which is the accident the source-era policy exists to remove.

The factor is bounded to [0, 1]. Spread widening is out of scope — a deliberate scope limit, not
a judgment that widening is unlikely, since the decomposition found ranges widening every year
since 2023.

## Preserved signs and the sign-change count

Zero and negative results are preserved and never clipped or floored. Because compression pulls
prices toward the daily reference, an interval on the far side of that level can cross zero and
change sign. This is a real consequence of compressing spread, not a defect, so it is counted as
`sign_change_interval_count` rather than suppressed: a scenario that materially changes the number
of negative intervals is changing the market's character and not only its spread, and a reader
should be able to see that.

Missing prices are refused explicitly, over and above the shared quality gate. A single missing
price would propagate through its market day's reference level and silently corrupt every
interval of that day, so it fails with a message that says so.

## Outputs

- **Paths** — canonical columns with compressed prices, `spread_compression:<id>` appended to
  `source_version`, and `spread_compression` and `synthetic_not_forecast` quality flags.
- **Provenance** — one row per interval: path ID, UTC key, market day, transformation ID, method,
  factor, basis, reference level applied, original and compressed price, input source and version.
- **Summary** — configuration, path/interval/market-day counts, mean and maximum daily range
  before and after, maximum absolute daily-mean shift, negative and zero interval counts before
  and after, sign-change count, reference-level range, and the result label and policy text.

## Shared validation contract

The price-level and spread-compression transformations now share
`greek_bess.stress._paths.validate_bootstrap_paths`, so two transformations cannot drift apart on
what counts as an acceptable path. The helper takes the caller's error type, so a failure names
the transformation the operator actually invoked. `price_level.py` behaviour is unchanged and its
existing tests pass without modification.

## Validation

- `ruff check .`, `ruff format --check`, `mypy`, `pytest -v`, `python -m build --wheel` all pass.
- 12 new tests: 11 in `tests/test_spread_compression.py` and one CLI test in `tests/test_cli.py`.
- Coverage includes determinism, identity and flattening endpoints, exact per-day range scaling,
  daily-mean preservation, preserved negative results with sign-change counting, median basis
  selection, provenance and labelling, rejection of missing/duplicate/incomplete/malformed input,
  configuration bounds and strict `from_dict` parsing, and the summary's spread evidence.

## Interpretation limits

The compression factor is a declared judgmental scenario, not an estimate, a calibration or a
probability-weighted view. The replayed 2020-2026 history predates operating battery competition
in the Greek DAM almost entirely, so it contains no episode from which a competitive spread
response could be inferred — which is precisely why the factor is declared rather than fitted.
Compression is uniform across days, seasons and hours, which real cannibalisation would not be.
No likelihood, percentile, loss metric or ranking attaches to a factor, and no dispatch, finance
or investment conclusion follows from one. Full text in `LIMITATIONS.md`.
