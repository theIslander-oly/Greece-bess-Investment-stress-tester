# Implementation report — dated cash-flow IRR

**Date:** 10 September 2026
**Execution-plan stage:** 4
**Review finding:** 2

## Scope

This stage puts every monetary metric on one dated cash-flow series. It changes no declared
source, dispatch rule, degradation model, cost assumption or scenario, and it launches no
official-data workflow. It changes reported IRR figures, and says so below.

## The defect

`evaluate_project_finance` built a daily table in which each delivery day's operating cash flow
carries its own date, and a separate annual table summing each project year's flows and dating
the total at that year's **final day**.

NPV discounted the daily series. IRR solved on the annual one. The two metrics therefore
described different cash-flow timings, and the difference is not small: for EUR 1,000 paid
initially and EUR 1,200 received evenly across 365 daily periods, solving on the dated series
gives **45.586%**, while relocating the year's receipts to its final day gives **20.015%**. The
annual figure understates the return because it treats money received in January as if it
arrived in December.

The summary already declared the intended convention — "Initial CAPEX at project start (time
zero); operating cash flows at each market-day end" — so the recorded policy was correct and IRR
was the metric that did not honour it.

## The correction

`_dated_cash_flows` builds one series: the initial capex at `t = 0`, and each day's operating
cash flow at that day's own `years_from_project_start`. That column is reused rather than
recomputed, because an IRR solved against a separately derived set of instants could disagree
with the NPV it is supposed to zero. NPV and IRR now read the same series.

The annual table is unchanged and remains a summary. What changed is that no monetary metric is
derived from it.

## Ambiguity checks on the dated series

Moving the ambiguity checks onto the daily series required more than moving the existing test.
Counting sign changes over daily cash flows refuses far too much: a project that pays for a
mid-life augmentation changes sign twice and is the ordinary case here, not an ambiguous one.

Three tests are applied in order, and a rate is reported only when one settles uniqueness.

1. **The sign rule.** A series whose amounts change sign exactly once has exactly one rate above
   -100%. No sign change at all means no rate exists.
2. **Norstrom's criterion (1972).** A series may change sign many times and still have a unique
   rate provided its *cumulative* balance starts negative, turns positive once and never turns
   back — a project financed once and repaid once. This is what separates an augmentation dip
   from a project that genuinely reverses.
3. **A scan of the search range.** Neither condition above is necessary, so failing both does not
   make a rate ambiguous. A project that never recovers its outlay fails Norstrom and still has
   exactly one rate, deeply negative; refusing there would withhold a real figure. The fallback
   evaluates the objective on a log-spaced grid dense near -100%, where the discount factor moves
   fastest, and answers from the root structure actually present: one crossing is reported,
   several are not.

This was checked rather than assumed. The repository's existing ambiguity fixture — EUR 3,000
received across year one and EUR 2,500 paid across year two — has **two** roots in
(-100%, ∞), so it is correctly refused. The committed synthetic demonstration, whose project
never recovers its capex, has exactly **one**, so it is correctly reported.

Two roots closer together than adjacent grid points would be missed by the scan. That is why it
is the fallback and not the first test, and it is recorded here as a known limitation rather than
presented as a proof of uniqueness.

## Changed status vocabulary

`not_evaluable_multiple_sign_changes` is renamed `not_evaluable_multiple_rates`. Under the
corrected logic a series is refused when it has several *rates*, not when it has several sign
changes, and the old name would have described the check inaccurately. No module outside
`finance/model.py` reads `irr_status`.

## Changed figures

**Every previously reported IRR is superseded.** The corrected figure is the one consistent with
the declared timing convention and with the NPV reported beside it; the earlier figure was not.

The committed synthetic demonstration moves from `-0.9798843527086536` to
`-0.9800653165183428`, and `docs/sample_report.html` is regenerated. That project never recovers
its capex, so both figures are deeply negative and the correction is small; a project whose
receipts are spread through the year moves far more, as the 45.586% against 20.015% example
above shows.

No accepted official result carries an IRR: the v0.9 chain has never been run against official
data, so nothing in the acceptance record changes.

## What did not change

NPV, payback, discounted payback, break-even outputs, cash-flow totals, fees and augmentation
costs are all unchanged. The correction moves no euro and counts nothing twice, which is
asserted directly: the undiscounted project cash flow still reconciles from its own components,
augmentation still totals exactly what was supplied, and realized margin is still the supplied
margin times the declared realization fraction, once.

## Validation

- Ruff
- mypy (65 source files)
- pytest: 671 passed, up from 664
- isolated wheel build

New regression tests cover: the plan's EUR 1,000 / EUR 1,200 fixture, whose IRR agrees with an
independent root solved from the daily table's own dates and equals the 45.59% the plan names;
a dated NPV residual at the reported IRR within `1e-7 * max(1, initial_capex_eur)`, asserted for
both a full and a partial year; a partial year dated by its own days; leap-year dates including
29 February 2028, with 366 daily periods; a series that never recovers still reporting its single
rate; a series with several rates being disclosed rather than quoted; totals, fees and
augmentation unchanged; and the annual table remaining a summary whose own solved rate is
demonstrably not the reported one.
