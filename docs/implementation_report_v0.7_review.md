# Completed-v0.7 formal review — 31 August 2026

## Scope and outcome

The completed deterministic v0.7 scope was reviewed across its public APIs, CLI commands,
configuration contracts, interval and run provenance, summaries, regression tests, methodology,
limitations, decisions and implementation reports. The review found no blocking correctness or
data-integrity defect. Ruff, mypy, all 245 tests and a clean wheel build passed on the unchanged
v0.7.9 implementation.

One documentation contradiction was found and corrected. `PLAN.md` retained superseded wording
that placed availability in the scenario-ensemble equivalent basis. The implemented and approved
contract instead treats battery parameters, terminal-energy constraint, selected source era and
path identity as the asset-and-sample basis. Differing declared availability schedules are
scenario judgments carried on every reported figure as provenance; an unrecorded availability
assumption is still refused. The correction changes no model behavior.

## Confirmed integrity boundaries

- Missing official or synthetic path prices are refused and never interpolated.
- Zero and negative prices remain signed and are never clipped or floored.
- Canonical timezone-aware UTC identity is retained with market and Greece views; complete
  23/25-hour and 92/100-quarter-hour market days remain supported.
- Source-era selection is explicit when more than one eligible era exists, and its resolution and
  bounds remain in run and interval provenance.
- Power, energy, efficiency, SOC, grid, terminal-energy and availability assumptions remain
  explicit, and dispatch prevents simultaneous charge and discharge.
- Forecast-planned schedules are settled against realized prices, with time-ordered forecast
  construction and future-mutation regression tests preventing leakage.
- Scenario comparisons enforce equal battery, terminal-energy, source-era and path bases while
  retaining each declared transformation and availability schedule as scenario provenance.
- Scenario ranges remain ranges across named judgments, with no probability, percentile,
  expected value, loss metric, ranking or central case.
- Perfect foresight remains a labelled gross-margin upper bound, never expected revenue.
- Each transformation performs only its declared arithmetic, and interval transformations retain
  one-to-one provenance with their relevant path rows.

## Interface-readiness boundary

The existing validated domain APIs are suitable for a future thin presentation layer. Their
result summaries are dictionaries rather than a versioned presentation schema, so a future
interface should first define a versioned run manifest and report contract instead of coupling UI
callbacks directly to incidental summary keys. That is a v0.8 design item, not a v0.7 defect.

This review does not open v0.8. The research-interface and exportable-report design still requires
explicit user approval, and no Streamlit or reporting dependency, branch, scaffold or stub is
introduced here.
