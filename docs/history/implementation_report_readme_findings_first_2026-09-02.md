# README findings-first restructuring — 2 September 2026

## Scope

This documentation milestone makes the accepted official-history evidence visible on the
repository landing page and moves detailed command material into a dedicated reference. It does
not change code, analytical behavior, accepted data, assumptions, result manifests or runtime
dependencies.

## Evidence presented

The README table transcribes the market-day counts, daily-composed perfect-foresight ceilings,
negative-price interval counts and mean within-day ranges recorded in
`docs/official_annual_decomposition_2026-08-28.md`. Its annual capture ranges use the minimum and
maximum of the four ratios already recorded for each delivery year on each method's own
backtested days. No ratio is recomputed from underlying prices or schedules.

The landing-page interpretation is deliberately adjacent to the table: these are historical
replay and backtest results, perfect foresight is a gross-margin upper bound, 2020 and 2026 are
partial, method coverage differs, and the hourly-to-quarter-hour transition prevents direct
comparison of interval counts. The existing limitations follow immediately and remain verbatim.

## Documentation structure

The detailed scenario/transformation sections and numbered end-to-end command workflows moved
without substantive edits from `README.md` to `docs/command_reference.md`. The README retains the
synthetic quickstart, current capability summary, installation, repository guide, data policy,
package layout, project status and links to the command reference and primary records.

The README changed from 1,391 lines to 452 lines. The extracted command reference is 981 lines.

## Validation

The Python 3.12 development environment was prepared through `scripts/bootstrap-dev-env.sh`.
Ruff, mypy, pytest and a clean wheel build were run. The complete diff and tracked-file list were
reviewed for generated artifacts, official data and secrets before commit.
