# Numerical and accounting repair — 11 September 2026

Branch: `repair-numerical-accounting`. Scope: correctness repairs before Stage 8 implementation.

## Counterexamples and corrections

- Annual cash flows -100, +200, -50 have two IRRs, approximately -70.71% and +70.71%.
  Positive-rate cumulative-balance reasoning cannot establish global uniqueness. Forward and
  reversed cash-flow certificates now cover both rate domains; a scan never certifies uniqueness.
  Close and tangent roots exercise conservative unresolved/multiple-root handling.
- EUR 365 CAPEX over 546 operating days at zero discount requires EUR 244.168956 of annualized
  realized cash margin. Daily discounted exposure replaces a whole-year payment denominator.
  Tests also cover partial years, leap years and positive discount rates by zeroing NPV.
- A 50% realization fraction applied to gains of 100 and losses of -40 yields 10, not 30.
  Tests verify loss preservation and the corresponding break-even realization fraction.
- A dispatch wear penalty is not a cash payment. Cash margin now travels through dispatch,
  forecast settlement and finance explicitly. Legacy net-plus-wear reconciles to cash; contradictory
  declarations are rejected. Actual augmentation and additional commissioning costs apply once.
- Adding 100 MWh to a battery holding 50 MWh must not manufacture another 50 MWh.
  New capacity is empty unless commissioning energy is declared. Charging, conversion losses,
  retirement, calendar/cycle fade and self-discharge reconcile opening and closing stored energy.
  Tests cover quarter-hour losses, same-day additions/retirement and fixed-capacity equivalence.
- Energy-only additions and zero power-fade exponent are now valid independent assumptions.

## Compatibility and limits

Legacy net margin remains the dispatch objective after wear; explicit cash margin is the finance
basis. Net-only external inputs are assumed to mean cash and cannot reveal an unknown wear basis.
Commissioning-energy cost is additional to augmentation CAPEX. Commissioning before the observed
price horizon is refused without prior history. Energy outside initial SOC bounds is not filled
silently. Proportional energy loss under fade is a declared approximation, not a new battery model.
IRR may remain unresolved even when a root exists; NPV stays available.
Affected stored outputs require reruns. No official-history results were regenerated or committed.
No integrated runner, forecasting model, dependency or publication workflow is introduced.

## Validation

The initial counterexample tests failed before the repair. Validation after repair:

- Full suite: 729 passed (99.34 seconds).
- Final regression and integrated-design checks: 31 passed, including the subsequently added
  reserved-cohort-id guard. The regression module contains 23 cases including parametrization.
- Ruff passed; mypy passed for all 65 source files.
- Clean-source wheel build passed. The tracked synthetic demo was regenerated and its
  reproducibility check passed in the full suite.
- Complete changed-file review and whitespace/secret-pattern checks passed. No raw data,
  research outputs, credentials or build artifacts are included.
