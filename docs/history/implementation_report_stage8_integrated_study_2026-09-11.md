# Implementation report — Stage 8: the integrated study runner

**Date:** 11 September 2026
**Execution-plan stage:** 8, implementation unit (`build-integrated-study`), against the design
adopted in `docs/integrated_study_design.md`.

This unit runs no official-data workflow, accepts no dataset, produces no official figure and
changes no analytical result. Every figure it has produced is on deterministic synthetic prices,
in tests. The stage-7 fundamentals result and every accepted acceptance record are untouched.

## The gap this closes

The repository could already plan a day on a causal forecast and settle it at realized prices
(`backtest/forecast_dispatch.py`), evolve a degradation state day by day
(`backtest/degradation_dispatch.py`), and turn a continuous daily operating path into dated cash
flows (`finance/model.py`). It could not do them together. The first plans against a battery that
never ages; the second plans with perfect foresight; the third receives its path as a file
somebody produced elsewhere.

So the question the project exists to ask — *does a better forecast pay for itself once the
battery ages under the throughput that forecast causes?* — required a human to run three commands
and join their outputs by hand. That join was the one step no contract governed, which is exactly
where an error would have been invisible.

## What landed

`src/greek_bess/study/`, a new package, and `run-integrated-study`, one command:

| File | What it owns |
| --- | --- |
| `study/config.py` | The declared study: window, price source, strategies and their information sets, and the battery, degradation and finance configurations, read from one JSON file |
| `study/runner.py` | The per-day loop of design §4, and the per-strategy degradation states it advances |
| `study/results.py` | Per-strategy tables, the recorded summary, and the reconciliations that run on every run |
| `cli/study.py` | The command and the five artifacts it writes |

A new closed-registry result kind, `integrated_study`, on the `historical_replay_simulation`
basis. The existing renderer consumes its manifest unchanged; no renderer code was needed.

Artifacts, all named after the declared `study_id`: `.daily.csv` (one row per strategy per
delivery day), `.strategies.csv`, `.cash_flows.csv`, `.summary.json`, `.manifest.json`.

Nothing under `dispatch/`, `degradation/`, `finance/` or `reporting/` changed except that one
registry entry. The study is a composition of existing contracts and adds no arithmetic: it calls
`generate_naive_forecasts`, `prepare_degradation_day`, `optimize_perfect_foresight`,
`complete_degradation_day` and `evaluate_project_finance` in the one order that makes the join
safe.

## The contracts the join needed

**Each strategy owns its ageing state.** Every strategy holds a private `DegradationState` from
the same declared starting point, advanced only by the cell discharge its own settled schedule
produced. Sharing one state object across the strategy loop is the obvious way to write this loop
and produces entirely plausible numbers in which a cautious strategy pays for an aggressive one's
throughput. The symptom that defect cannot hide — different cell throughput, identical
end-of-window usable energy — is refused. That refusal is scoped to configurations whose cycle
fade is non-zero, because under the declared zero-fade reproduction identical capacities are the
correct answer and refusing them would refuse the one run that proves the composition did not
change the existing arithmetic.

**A gap is refused, never bridged.** A delivery day missing from the declared window fails the
run naming the day and the count; an incomplete forecast for any compared strategy fails it
naming the method and the first day. No price is filled, no forecast is imputed, no day becomes a
no-trade day. The window check runs *before* the canonical quality gate, deliberately: the gate
would also refuse a missing day, but as a non-contiguous horizon somewhere in the history, which
tells a reader nothing about which day to supply.

**Finance uses exactly the declared horizon.** The finance configuration's start and end days
must equal the window's, checked when the study is declared rather than when finance is reached.

**No shared ceiling.** Each strategy's own per-day perfect-foresight ceiling and regret are
recorded under that strategy's own beginning-of-day state. No ceiling is reported across
strategies and no aggregate of the per-day ceilings exists anywhere in the output; the summary
records `shared_ceiling_reported: false` and the sentence saying why. This is `METHODOLOGY.md`
§5.1 applied across strategies rather than across days.

**Future prices cannot reach an earlier decision.** Prices for delivery days after the window are
discarded before any forecast is generated, and the discarded day and interval counts are
recorded. Inside the window, causality is the forecast generator's existing guarantee; the test
below checks the composition holds it rather than assuming it.

**Reconciliation runs on every run, not only in tests.** Fees, the monetary degradation adder, the
augmentation cost passed to finance, and each day's initial and terminal stored energy against
the configured SOC are all checked against their configured inputs before a summary is assembled.
A failure there is a defect in the join rather than an unusual input, and nothing downstream
could detect a broken join from the numbers alone.

## The one implementation finding

The design states that if implementation finds an existing module must change, that is a finding
to record and review rather than a change to make quietly. One arose.

`FinanceConfig.operating_margin_case` describes the *operating path*, not the cost and discounting
basis. A study declares one finance configuration, but a study comparing a forecast planner
against perfect foresight necessarily spans two cases. Requiring one declared case for every
strategy would forbid the comparison the study exists to run; accepting the declared case for
every strategy would label at least one path with a case that is not its own.

The study therefore derives the case per strategy from its planner —
`daily_policy_degraded_simulation` for `perfect_foresight`, `historical_forecast_backtest` for a
forecast planner — refuses a declared case that is neither, and records the declared case beside
the derived ones. `finance/model.py` is unchanged; the study replaces a field on a frozen
configuration it owns for the call. Recorded as a dated decision on 11 September 2026.

## Validation

All eight of the design's §7 acceptance checks have a test under a name that says which check it
is (`tests/test_integrated_study.py`, 23 tests). The two worth naming again:

- **Zero-fade reproduction.** With calendar and cycle fade set to zero, every day's settled margin
  equals `backtest_forecast_dispatch`'s `realized_margin_eur` for the forecast strategy and its
  `perfect_foresight_margin_eur` for the perfect-foresight strategy, to six decimal places. This
  is the check that proves the new path did not change the old arithmetic; it passes exactly,
  because with zero fade the beginning-of-day battery the study derives is the configured battery
  to the last bit.
- **Causality.** Prices for every delivery day after a chosen boundary inside the window are
  multiplied by seven and shifted by EUR 250, the study is re-run, and every daily row up to and
  including that boundary must be identical for all three strategies. It is.

The others: one command and one configuration write the five artifacts and a manifest that
verifies through `read_run_manifest`; two strategies with different throughput reach different
end-of-window capacities and the heavier discharger is the one that aged more; reversing the
declaration order changes no strategy's result; fees, the adder and augmentation reconcile against
their configured inputs and every day starts and ends at the configured SOC; a gap names the day
and an incomplete forecast names the method; two runs of one configuration agree exactly; and no
key or column anywhere in the output names a ceiling except the two that say none is reported.

Full gates on Python 3.12: `ruff check` clean, `mypy` clean across 70 source files, `pytest` 730
passed, `python -m build --wheel` succeeds and the wheel carries the new package.

## What this does not do

- No official-history study has been run. The runner has seen deterministic synthetic prices only.
- Planners are the naïve forecast methods and `perfect_foresight`. The ML and fundamentals
  planners are not wired in; the design's `decision_information` field is where that would be
  declared, and it would be a separate unit.
- Multi-year extrapolation, a terminal-value model beyond the existing configured residual,
  strategy-specific batteries, intraday or ancillary revenue and any lifetime-optimal dispatch
  policy remain deferred, each a scope change requiring its own decision.
