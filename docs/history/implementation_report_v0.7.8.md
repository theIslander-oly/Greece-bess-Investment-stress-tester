# Implementation report v0.7.8 — Declared availability and outage paths

**Date:** 31 August 2026

## Scope

Adds `greek_bess.stress.build_availability_profile`, the `--availability-schedule` option on
`dispatch-bootstrap-paths`, and the integration of a declared availability schedule into
bootstrap-path dispatch and scenario-ensemble reporting. This completes the last approved
modeling item of v0.7. Negative-price-event transformations remain deferred and unapproved.

No official data, price transformation, forecast method or finance treatment is involved.

## An outage is declared, never sampled

The transformation the project does **not** implement is the conventional one. A forced-outage
rate with sampled failure times would produce a probability statement, and the 2026-08-27
decision that removed percentiles and loss probabilities applies with full force: nothing
calibrates a forced-outage rate for a Greek merchant battery that has not operated. There is no
fleet history, no maintenance record and no warranty claim series in scope.

A schedule is therefore a declared baseline available fraction plus zero or more declared
windows, each carrying its own available fraction. It is a judgmental scenario in exactly the
sense a compression factor is: a statement of what to examine, not a claim about what will
happen. `AvailabilityScheduleConfig.from_dict` refuses unknown fields, so a configuration
carrying a `forced_outage_rate` is rejected by name rather than silently ignored.

The baseline fraction has **no default**, following the source-era and reference-basis
precedent. `AGENTS.md` requires availability to be an explicit assumption, and a silent 1.0
would make full availability an accident of the input rather than a decision. A schedule with an
empty window list is legitimate and useful: it is the declared full-availability scenario, and
it is a better baseline than an implied one.

## Boundaries are refused, not rounded

A window is applied whole to every interval it covers. There is no within-interval proration,
because prorating would apply a schedule finer than the one declared. To keep that from
silently changing what was asked for, a window boundary falling strictly inside a delivery
interval is refused, naming the interval:

```
Outage half_hour: start_utc 2025-12-31T23:30:00+00:00 falls inside delivery interval
2025-12-31T23:00:00+00:00..2026-01-01T00:00:00+00:00. Declare a boundary on an interval edge;
a partly covered interval is not prorated, because that would apply a schedule that was never
declared
```

The other refusals follow the same rule of never approximating over a defect: overlapping
windows (an interval covered twice has no declared fraction), a window covering no dispatched
interval (a declared input that applies to nothing is an error, not a no-op), reversed or empty
windows, naive timestamps, duplicate outage identifiers, and fractions outside [0, 1].

Because the profile is built from the paths' own canonical UTC keys, 23- and 25-hour market days
and the quarter-hour regime are handled by construction. Paths that do not share one interval
identity are refused: one schedule must map onto every path of a run, so that what differs
between paths is the sampled price and not the physical condition.

## Integration with dispatch

`dispatch_bootstrap_paths` accepts an `AvailabilityProfile` alongside the existing constant and
raw profile forms. A declared schedule records its own identity in the dispatch summary:

```json
{
  "type": "declared_schedule",
  "schedule_id": "planned_maintenance",
  "baseline_available_fraction": 1.0,
  "declared_window_count": 1,
  "derated_interval_count": 6,
  "derated_hours": 6.0,
  "minimum_available_fraction": 0.0,
  "windows": [{"outage_id": "morning_outage", "...": "...", "applied_interval_count": 6}]
}
```

An anonymous array of fractions would have left a margin traceable only to a number of
intervals. The declaration means a margin can be traced to the outage assumption behind it.

## Integration with the scenario ensemble

v0.7.7 put `availability_assumption` in the ensemble's equivalent-basis check, which refused any
two scenarios whose availability differed. That was too strong, and this milestone corrects it:
an ensemble that refuses a differing availability schedule can never place a declared outage
against a baseline, which is the comparison an outage scenario exists to make.

The line the basis now draws is between **the asset** and **what is done to it**:

| Part of the equivalent basis (must match) | Declared scenario input (expected to differ) |
| --- | --- |
| Battery parameters | Price transformation and its parameters |
| Terminal-energy constraint | Availability schedule |
| Source-era selection | |
| Path count and path identity | |

Availability moves into provenance rather than out of the record. Every margin row carries
`availability_type`, `availability_schedule_id` and the full `availability_declaration`; each
range row names the availability at both ends; and the summary records each scenario's
declaration. A scenario whose dispatch summary records no availability assumption is still
refused, because a margin whose availability is unknown cannot be placed in a range against one
whose availability is known.

The forbidden-term guard extends to the new keys automatically, since it walks nested summary
keys. The declaration vocabulary is deliberately plain for that reason.

## Invariants preserved

- Prices are never read by this module, so zero and negative prices pass through untouched.
- Missing or malformed schedule inputs are refused, never repaired.
- The profile has no random component: identical paths and configuration give an identical
  profile, provenance and summary, which a determinism test asserts.
- Availability enters dispatch through the existing power caps, so simultaneous charge and
  discharge remains impossible and the terminal-energy constraint is unchanged.
- Every output keeps its labels: the summary denies being a forecast, a probability or an
  outage rate.

## Tests

`tests/test_availability.py` (23 tests):

- a declared outage derates exactly the intervals it covers, at its declared depth, with
  hand-checked interval counts and derated hours over a two-day hourly horizon;
- several windows apply independently and each reports what it covered;
- an empty window list is the declared full-availability scenario, and a baseline below 1
  derates the whole horizon;
- determinism across two runs of the same paths and schedule;
- provenance names the outage on every covered interval, and the declaration records each
  window with its applied interval count;
- refusals: overlapping windows, a window covering no dispatched interval, a boundary inside an
  interval (asserting the message says it is not prorated), reversed and empty windows, naive
  timestamps, out-of-range and non-numeric fractions, a missing baseline, duplicate outage
  identifiers, an unknown `forced_outage_rate` field, and paths that do not share one identity;
- dispatch integration: the summary records the schedule by name, a declared outage cannot
  raise the margin it constrains, and a full outage holds the battery still for its intervals.

`tests/test_scenario_ensemble.py` adds `DeclaredAvailabilityTests`: a declared outage ranges
against a baseline, the declaration reaches every margin row and both ends of every range row,
the summary records each scenario's availability, `equivalent_basis` no longer carries it, and
an unrecorded availability assumption is still refused.

`tests/test_cli.py` adds an end-to-end `--availability-schedule` run asserting the recorded
schedule, the availability provenance sidecar and that the battery does not trade while
declared unavailable, plus a refusal when both `--availability` and `--availability-schedule`
are given.

## Validation

| Command | Result |
| --- | --- |
| `scripts/bootstrap-dev-env.sh` | exit 0 |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/mypy` | `Success: no issues found in 38 source files` |
| `.venv/bin/pytest -v` | `235 passed` (207 before, 28 added) |
| `rm -rf build dist && .venv/bin/python -m build --wheel` | `greek_bess_investment_stress_tester-0.7.8-py3-none-any.whl` |

## Limitations specific to this milestone

- A schedule is a judgment about what to examine. It is not an outage rate, an availability
  guarantee, a maintenance plan or a reliability model, and no likelihood attaches to it.
- Timing is the whole content of the scenario and the model gives no help choosing it. An
  outage placed in a low-spread week costs almost nothing and the same outage in a high-spread
  week costs a great deal, so a single schedule describes one placement and nothing more.
- Availability scales grid-side charge and discharge power only. Auxiliary load, state-of-charge
  drift while unavailable, partial-string derating, restart behaviour and any cost of the outage
  itself are not modelled.
- A perfect-foresight dispatch knows the outage in advance and positions the battery for it. A
  real unplanned outage arrives without notice, so the margin reported under a declared outage
  remains an upper bound, and it is a less conservative bound for unplanned outages than for
  planned maintenance.
- Degradation-aware and forecast-dispatch backtests do not yet accept a declared schedule; the
  integration covers bootstrap-path dispatch only.
