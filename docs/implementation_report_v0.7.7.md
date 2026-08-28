# v0.7.7 implementation report — warning-free validation and record corrections

## Scope

This maintenance milestone removes a known dependency-upgrade failure mode without changing any
price, forecast, dispatch, finance or scenario calculation. It also corrects repository wording
that described the planned encrypted custody store as complete before the operator upload.

## Implementation

- Numeric `pd.Timedelta` calls now declare `min`, `h` or `D` explicitly in synthetic generation,
  HEnEx parsing, ENTSO-E chunking and the two affected tests.
- Pytest promotes all warnings to errors. This turns future deprecations into an immediate review
  gate instead of allowing them to accumulate behind a passing test result.
- `STATUS.md`, `LIMITATIONS.md` and the custody procedure distinguish committed fingerprints from
  the still-outstanding encrypted release upload.
- `LIMITATIONS.md` now reflects the 2026-08-27 decision: probability estimates are excluded unless
  independently validated calibration is approved; v0.7 ranges remain non-probabilistic.

## Interpretation

No modeling output changes. The custody correction does not claim that release assets are absent
at GitHub independently of the repository record; it states the project's recorded status and
keeps custody incomplete until the operator upload is verified. No official data is introduced.

## Validation

The milestone is accepted only after Ruff, mypy, all 169 pytest tests with warnings treated as
errors, and a clean wheel build pass, followed by generated-file and secret checks.
