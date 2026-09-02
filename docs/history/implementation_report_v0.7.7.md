# Implementation report v0.7.7 — Scenario-ensemble range reporting

**Date:** 31 August 2026

## Scope

Adds `report-scenario-ensemble` and `greek_bess.stress.report_scenario_ensemble`, which consume
bootstrap-path dispatch results that have already been produced under two or more named scenarios
and report the minimum, maximum and spread of their margin outcomes. This milestone composes
accepted outputs; it introduces no price transformation, dispatch mode, forecast method or
finance treatment, and it reads no official data.

Deterministic availability/outage-path integration and negative-price-event transformations
remain unapproved and are not implemented, stubbed or prepared for.

## What the report does

For every bootstrap path the named scenarios share, the report gives the lowest margin any
scenario produced for that path, the highest, the spread between them and the scenario at each
end. The margin is `net_market_margin_eur`, taken unchanged from the recorded dispatch summary of
each scenario.

The ranges are taken per path and never across paths. A total or an average over sampled paths
would read as an expectation, and the uniform block resampling of a non-stationary 2020-2026
history supports no such reading; the 2026-08-27 decision that removed percentiles and loss
probabilities from scope applies with equal force to a mean.

## Named scenarios, no implicit baseline

Every scenario is named by the caller. The CLI takes a manifest that lists them explicitly:

```json
{
  "scenarios": [
    {
      "name": "baseline_replay",
      "run_id": "bootstrap-2026-08-31-seed-42",
      "path_summaries_csv": "baseline.paths.csv",
      "dispatch_summary_json": "baseline.summary.json",
      "bootstrap_summary_json": "bootstrap_paths.summary.json",
      "transformation_summary_json": null
    }
  ]
}
```

`transformation_summary_json` is a required key. A scenario with no price transformation states
that as `null` rather than omitting the field, so an untransformed replay is a declared member of
the ensemble rather than something the tool supplied on the reader's behalf. There is no default
scenario set: an ensemble of fewer than two named scenarios is refused, because a range across one
scenario is that scenario.

## Non-probabilistic by construction

A range across named scenarios is a range across judgments. No probability, percentile,
likelihood, expected value, loss metric, ranking or central case is produced.

The rule is executable rather than documentary. `greek_bess.stress.FORBIDDEN_REPORT_TERMS` lists
the excluded vocabulary, and every emitted column name and summary key — including keys nested
inside the per-scenario provenance — is checked against it before the result is returned. A field
named `p95_margin_eur`, `expected_margin_eur` or `mean_margin_eur` raises rather than being
written. A test asserts the output schema is clean, and a second test asserts the guard refuses a
forbidden name rather than passing it through.

The consequence for the summary vocabulary is deliberate: the ensemble-wide figures are
`lowest_`/`highest_net_market_margin_eur` with the scenario and path that attained each, and
`widest_`/`narrowest_path_spread_eur` with their path. None of them is a central case.

## Equivalent basis, or refusal

`AGENTS.md` requires that strategies be compared only under equivalent physical and
terminal-energy constraints. A range taken across scenarios solved on different bases would
report a modelling difference as if it were a scenario difference, so the following are checked
across the ensemble and a difference is refused with the mismatching basis named:

| Basis | Source | Refusal names |
| --- | --- | --- |
| Battery parameters | `dispatch_summary.battery_configuration` | `battery parameters` |
| Terminal-energy constraint | capacity, SOC limits, initial and terminal SOC fractions | `terminal-energy constraint` |
| Availability assumption | `dispatch_summary.availability_assumption` | `availability assumption` |
| Source-era selection | `bootstrap_summary.selected_source_era` | `source-era selection` |
| Path count and identity | the dispatched `path_id` values | `path count and path identity` |

The terminal-energy constraint is checked separately from the rest of the battery configuration,
and the derived `terminal_energy_mwh` is recorded, so a scenario that differs only in day-end
energy is refused by that name rather than as a generic parameter mismatch. A declared
`path_count` that disagrees with the supplied paths is refused as well.

A scenario whose dispatch summary records no `battery_configuration` or whose bootstrap summary
records no `selected_source_era` is refused: only recorded bootstrap-path dispatch results can
enter an ensemble, and the source era is part of the comparison basis.

## Provenance

`scenario_margins` carries one row per scenario and path, each with the scenario name, the
transformation method, the transformation ID, the transformation parameters as recorded JSON, the
selected source era's resolution and day span, the input run identity, the bootstrap random seed
and the result label. `scenario_ranges` repeats the scenario name, transformation ID, method,
parameters and run identity for the scenarios at both ends of each path's range, so a range
traces back to the runs that produced it without joining tables.

The summary additionally records the full per-scenario declaration, the equivalent basis the
ensemble was accepted on, and the `reported_figure_count`.

## Invariants preserved

- Zero and negative prices are untouched: no price is read or transformed here.
- A missing or non-finite margin is refused explicitly, never filled.
- The composition has no random component. Identical inputs give identical frames and summary,
  which a determinism test asserts; scenario order is the caller's declaration order.
- Every output row keeps its source and limitation labels, including a `result_label` naming the
  figure as a perfect-foresight upper bound on synthetic paths and not a forecast, a probability
  or investment evidence.

## Tests

`tests/test_scenario_ensemble.py` (25 tests):

- range arithmetic against a hand-checked three-scenario, two-path fixture, including which
  scenario attains each end and the ensemble-wide lowest, highest, widest and narrowest figures;
- the non-probabilistic labelling of the summary;
- determinism across two runs of the same inputs;
- provenance completeness on every margin row and on both ends of every range row, including the
  recorded transformation parameters and the refusal of a transformation summary with no recorded
  configuration;
- refusal on mismatched battery parameters, terminal-energy constraint, availability assumption,
  source era, path count and path identity, each asserted to name its own mismatch, and one
  asserting the refusal cites the standing invariant;
- refusal of a single-scenario and an empty ensemble, an unnamed scenario, a scenario with no run
  identity, duplicate scenario names, a missing margin, and summaries missing the battery
  configuration or the selected source era;
- the output schema against the forbidden vocabulary, the coverage of that vocabulary, and the
  guard refusing a forbidden field rather than emitting it.

`tests/test_cli.py` adds an end-to-end run — synthetic prices, bootstrap paths, baseline dispatch,
spread compression, compressed dispatch, manifest, report — asserting that compression cannot
raise a perfect-foresight margin, that the spread column equals maximum minus minimum, that both
run identities and the source-era resolution reach the margin rows, and that a single-scenario
manifest exits 1 with the refusal on stderr and writes no output.

## Validation

| Command | Result |
| --- | --- |
| `scripts/bootstrap-dev-env.sh` | exit 0 |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/mypy` | `Success: no issues found in 37 source files` |
| `.venv/bin/pytest -v` | `207 passed` (180 before, 27 added) |
| `rm -rf build dist && .venv/bin/python -m build --wheel` | `greek_bess_investment_stress_tester-0.7.7-py3-none-any.whl` |

## Limitations specific to this milestone

- The range is bounded by the scenarios the caller chose. It says nothing about outcomes outside
  that set, and adding or removing a scenario changes the range without any new evidence.
- Each end of the range is a perfect-foresight upper bound on synthetic paths and inherits every
  limitation of the bootstrap, the transformation and the dispatch that produced it.
- A wide range is a statement about disagreement between named judgments, not about uncertainty
  in any measurable sense, and a narrow one is not confirmation.
- The report composes recorded summaries. It cannot detect that two scenarios were produced from
  different price histories if their recorded bases agree, so the recorded summaries must be the
  ones the runs actually emitted.
