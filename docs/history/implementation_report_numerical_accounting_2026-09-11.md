# Numerical and accounting repair — 11 September 2026

Scope: correctness repairs, and their application to the Stage 8 runner that merged while the
repair was open.

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

## Stage 8 reconciliation

Stage 8's integrated study runner (PR #69) merged into `main` on 11 September 2026, after this
repair branched. It was written against the pre-repair contracts and reintroduced two of the
defects above inside the new package. Both were reproduced before being fixed.

- **The wear penalty was settled as cash.** The runner passed `net_market_margin_eur` to
  `evaluate_project_finance` and omitted the wear column, so the legacy reconstruction saw a
  zero adder and read the net margin as cash. On a fourteen-day synthetic window at EUR 5/MWh,
  finance took EUR 71,406.16 where the cash margin was EUR 83,780.53, understating NPV by the
  whole EUR 12,374.37 penalty. `_Settlement` now carries `market_cash_margin_eur`, the daily row
  and the finance input carry it and the wear column beside it, and `_reconcile` refuses a run
  whose settled cash margin is not the figure finance read.
- **Augmentation created stored energy.** The day battery reapplied the configured state of
  charge to beginning-of-day usable capacity, so capacity an augmentation added arrived half
  full. A 50 MWh addition to a 100 MWh battery at 50% opened the day holding 75 MWh having
  closed the previous one at 50 MWh: 25 MWh nobody charged, dischargeable and sellable. With a
  declared `commissioning_energy_mwh` of 40 the day opened at 100 MWh rather than 90, and the
  declared EUR 400 never reached finance. Each strategy now carries its own stored energy and
  its commissioning cost reaches finance once.

The ledger itself moved to `degradation/stored_energy.py`. The degradation backtest and the
study would otherwise hold two copies of the same subtle accounting, and the failure that
produces is silent: a battery beginning a day with energy nobody charged still dispatches,
still settles and still reports a plausible margin. `degradation_dispatch.py` loses 44 lines to
the move and its behaviour is unchanged, which the existing suite confirms.

The design document this repair amended (`docs/integrated_study_design.md`, sections 4.5, 5.3
and 5.4) already specified these conventions; the merged implementation predates the amendment.
No stage is renumbered and Stage 8 stays complete.

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

The initial counterexample tests failed before the repair. Validation of the repair alone, at
commit `cffdcb4` on base `a733372`:

- Full suite: 729 passed (99.34 seconds).
- Final regression and integrated-design checks: 31 passed, including the subsequently added
  reserved-cohort-id guard. The regression module contains 23 cases including parametrization.
- Ruff passed; mypy passed for all 65 source files.
- Clean-source wheel build passed. The tracked synthetic demo was regenerated and its
  reproducibility check passed in the full suite.
- Complete changed-file review and whitespace/secret-pattern checks passed. No raw data,
  research outputs, credentials or build artifacts are included.

Validation after merging `main` and reconciling Stage 8, on Python 3.12:

- Full suite: 756 passed (149 seconds). The suite was 753 immediately after the merge, which is
  the first evidence worth recording: every acceptance check Stage 8 shipped with passed while
  both defects above were present, so no existing test covered them.
- The three added regressions fail on the pre-fix sources and pass on the current ones. The
  commissioning case fails by opening the day at 100 MWh where 90 MWh was carried and declared.
- Ruff passed; mypy passed for all 71 source files; clean-source wheel build passed.
- The IRR uniqueness certificate was independently cross-checked against a dense root count over
  the code's own search range on 3,000 random dated cash-flow series of two to seven flows: no
  series had a reported rate that was not a root, and none had multiple in-range roots under a
  uniqueness claim. Series whose only further root lies below -99.99% are reported as multiple
  rates, which is the documented convention rather than a disagreement.
