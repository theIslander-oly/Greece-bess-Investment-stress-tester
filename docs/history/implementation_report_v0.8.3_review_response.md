# Implementation report — response to the v0.8.3 external review

**Date:** 2 September 2026
**Branch:** `claude/energy-optimizer-review-tv218w`
**Scope:** engineering items from an external review of v0.8.3. No analytical result changes.

## What the review said

An external review rated the engineering 8.5/10 and the decision-usefulness 4/10, and made
seven recommendations. The gap between those two numbers is the review's own summary: the tool
models Day-Ahead arbitrage only, which is one input to an investment decision rather than the
decision, and `LIMITATIONS.md` already says so.

## What was implemented

### 1. Relaxation-first dispatch (review item 3)

The review measured the mixed-integer solve at 19-23 s on a year of quarter-hourly intervals
against 2.5 s for the relaxation, and proposed solving the relaxation first. Implemented with an
exactness argument rather than a tolerance, recorded as a decision entry and in `METHODOLOGY.md`:
the relaxation bounds the integer optimum from above, and a relaxed solution that never charges
and discharges in the same interval is integer-feasible, so it is optimal and is returned
unchanged. Measured on the CI image, one year of quarter-hourly prices, 50 MWh / 25 MW:

| Prices | Solve | `mixed_integer` | `relaxation_first` | Change |
| --- | --- | --- | --- | --- |
| No negative | Full horizon | 39.0 s | 4.3 s | 9.1× faster |
| No negative | Daily composed | 21.2 s | 12.3 s | 1.7× faster |
| 5% negative | Full horizon | 60.6 s | 63.7 s | 5% slower |
| 5% negative | Daily composed | 21.7 s | 13.8 s | 1.6× faster |

Margins agreed to one floating-point unit in the last place in all four cases. The review's
observation that the binary is "load-bearing, but only because of negative prices, and only
barely" is confirmed: 34 simultaneous intervals out of 35,136 forced the integer program over the
full horizon, and under the daily convention only 26 of 366 days needed it.

### 2. Property-based tests, closed-form dispatch checks, coverage, 3.13 (review item 7)

Hypothesis generates delivery days across 2015-2035 at both resolutions. The review expected this
to find something and it did: `ensure_canonical` normalized everything about a timestamp except
its resolution, so a generated history and the same history round-tripped through canonical CSV
compared unequal. Fixed and recorded as a decision entry.

Four closed-form dispatch cases now check the optimizer against arithmetic. Writing them found no
defect in the optimizer and two errors in the arithmetic: at a zero price, topping up against
self-discharge is free, so the optimum tops up rather than holds; and 1 MW over a quarter-hour
clears only 0.25 MWh, so a terminal constraint forces worthless early discharge. Both cases were
reformulated to isolate what they claim to measure.

Coverage is measured at 88% and reported without a threshold. CI runs 3.12 and 3.13.

### 3. Subcommand registry (review item 6, first half)

Thirty subcommands moved from one 460-line `build_parser` and one 30-branch chain into nine
modules and a `Command` registry. All thirty help outputs and argument sets are byte-identical;
only the top-level listing order changed, now grouped by workflow stage.

### 4. README front door and `docs/history/` (review item 5)

A quickstart with a real worked command and its actual printed output, after the limitations,
which stay first. Thirty-five implementation reports and release notes moved to `docs/history/`.

## What was not implemented, and why

- **A second revenue stream or a rename (item 1).** Deferred by the user pending a decision on
  which exit to take. Nothing implemented here depends on it.
- **Endogenous spread compression (item 2).** The review is right that a user-declared
  compression factor makes the tool arithmetic on a guess. A structural link to installed storage
  GW needs its own design and its own decision entry; it is not a refactor.
- **Deleting the ADMIE timing audit (item 4).** Declined. The review treats 1,284 lines as
  rhetoric, but they back a working, documented `audit-admie-publication-timing` subcommand and a
  dispatchable workflow. "Maintenance liability" is an argument against any tested feature that
  is not currently in use, and the 2026-08-26 decision retains the client and the audit
  deliberately.
- **Templating `render.py` (item 6, second half).** Deferred. Rewriting 1,170 lines of correctly
  escaped HTML concatenation is the one refactor here that can introduce a security-relevant
  regression, and it should be done behind golden rendering tests rather than alongside four
  other changes.

## Validation

Ruff, mypy, and 387 tests pass on 3.12 and 3.13. Wheel builds clean. No analytical result
changes: the dispatch optimum, every recorded figure and every result label are unchanged.
