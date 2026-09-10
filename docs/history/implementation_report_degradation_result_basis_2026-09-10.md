# Implementation report — degradation result basis

**Date:** 10 September 2026
**Execution-plan stage:** 5
**Review finding:** 1

## Scope

This stage corrects what the degraded dispatch result *is*. It changes no dispatch decision, no
degradation arithmetic, no cost assumption and no computed euro figure, and it launches no
official-data workflow. It changes the basis, label and interpretation those unchanged figures
are recorded under.

## The defect

`simulate_degradation_dispatch` solves each market day optimally under the usable energy and
power that day begins with. Every *day* is therefore a perfect-foresight ceiling for that day,
and the result was labelled accordingly: a "Daily perfect-foresight Greek DAM gross-margin upper
bound", recorded on the `historical_replay_upper_bound` basis.

The aggregate over many days is not a bound. The limits a day begins with depend on what earlier
days discharged, so the total is the outcome of one policy rather than a ceiling over all of
them — and that policy is myopic with respect to any lifetime budget.

## The counterexample

Reproduced against the real code before anything was changed. A 1 MW / 1 MWh battery, one
warranted equivalent full cycle, `enforce_warranty_throughput_limit` set, and two delivery days
whose spreads are EUR 1 and EUR 100 per MWh:

| Policy | Margin |
| --- | --- |
| Daily solve (what this module does) | **EUR 1.00** |
| Wait one day, then dispatch | **EUR 100.00** |

The daily solve spends the single warranted cycle on the first day, because that day is optimised
in isolation, and reaches the second day with zero throughput headroom. A feasible policy beat
the "upper bound" by a factor of one hundred, which is the shortest possible proof that it was
not one.

## The correction

A new result basis, `historical_replay_simulation`, records a day-by-day simulation over real
history. `degradation_dispatch` reports on it. The basis is the discriminator a consumer reads
before rendering a figure, so moving the kind onto it is what actually stops the total being read
as a ceiling; the label change alone would not.

The label now states that the total is what the daily policy achieved and not a lifetime optimum
or an upper bound. A `result_basis_note` accompanies it in the summary, explaining the myopia in
one sentence, because a reader who sees only the total needs the reason attached to the number
rather than left in a docstring.

The renderer gains wording and a heading for the new basis, so a simulation is grouped separately
from a ceiling in any report rather than appearing under the same section.

Finance gains a `daily_policy_degraded_simulation` operating-margin case. Without it, a degraded
path fed into the finance model would have been declared `perfect_foresight_upper_bound` and
inherited wording asserting the margins "remain a gross-margin upper bound", reintroducing
downstream exactly the claim this stage removes.

**A lifetime optimum is at least as large as this total.** The aggregate is therefore a lower
bound on that optimum, not an upper bound on achievable margin, and the documentation says so
rather than leaving the direction unstated.

## What is preserved

The daily optimization policy is unchanged. No lifetime optimizer is introduced; this stage
declares what the existing result is.

Genuine fixed-capacity upper bounds keep their basis. `perfect_foresight_dispatch` and
`daily_perfect_foresight_dispatch` solve a fixed, non-degrading battery, where no state evolves
between days and the aggregate really is a ceiling. Both still report on
`historical_replay_upper_bound`, asserted by test.

Every computed figure is unchanged: the same dispatch decisions, the same margins, the same
degradation states.

## Stored manifests

A manifest recording `degradation_dispatch` under `historical_replay_upper_bound` is refused, with
a message naming what changed and instructing the operator to re-run the command that produced
it. It is not relabelled in place. The same number means something different under the two bases,
and rewriting the label without re-deriving the result would assert evidence this project never
produced.

The refusal is safe to make absolute because the kind appears in no accepted record: not in the
custody documents, not in any acceptance document, and not in the committed sample report. It
appears only in command-reference usage examples. Manifests carrying it exist, if at all, on an
operator's own disk, outside Git. This is recorded as a material assumption; the alternative the
execution plan permits — reading old manifests under an explicit compatible interpretation —
would have been the right choice had an accepted record carried the kind.

## Validation

- Ruff
- mypy (65 source files)
- pytest: 677 passed, up from 671
- isolated wheel build

`docs/sample_report.html` is regenerated. Its only change is the line listing bases the report
does not represent, which now includes historical replay simulations. No figure in it moves.

New regression tests cover: the EUR 1 against EUR 100 counterexample, including that a feasible
policy exceeds the aggregate; the label no longer claiming a bound and carrying the basis note;
the kind reporting on the simulation basis; the superseded basis being registered with a
migration message; both fixed-capacity kinds keeping the upper-bound basis; and the finance
interpretation for the new case not inheriting upper-bound wording while the genuine bound case
keeps it.
