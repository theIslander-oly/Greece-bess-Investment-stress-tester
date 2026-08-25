# Decision log

This file records decisions that materially affect interpretation or reproducibility. Add a
dated entry when a milestone changes scope, assumptions, data handling or validation.

## 2026-08-26 — Make four clean-environment checks mandatory

- **Decision:** Every pull request must pass Ruff, mypy, pytest and a clean wheel build on
  Python 3.12 without private API keys or official datasets.
- **Reason:** Style, type consistency, behavior and packaging fail in different ways; one check
  cannot substitute for the others.
- **Consequence:** The initial foundation PR was corrected until all four checks passed. The
  typed-package marker is included in built distributions, and tests use package-qualified
  imports that work under both unittest and pytest discovery.

## 2026-08-26 — Import the completed v0.6 project honestly

- **Decision:** Treat the first GitHub contribution as a repository-foundation/import
  milestone containing the already completed v0.1-v0.6 implementation.
- **Reason:** The analytical code predates the connected repository. Fabricating historical
  commits or pretending the optimizer and forecast code do not exist would make the project
  history misleading.
- **Consequence:** Future milestones use feature branches and one reviewable pull request per
  milestone. Earlier implementation reports remain the audit record for pre-GitHub work.

## 2026-08-26 — Keep market data outside Git

- **Decision:** Commit download/import code, official URLs, hashes, schemas and aggregate
  quality evidence, but not full HEnEx or ENTSO-E datasets.
- **Reason:** Data can be large and its redistribution terms must be checked separately.
- **Consequence:** `data/raw`, `data/interim` and `data/processed` contain only `.gitkeep`
  placeholders. Small clearly synthetic fixtures may be committed under `tests/fixtures`.

## 2026-08-25 — Use UTC as the canonical interval key

- **Decision:** Store timezone-aware UTC interval boundaries and retain market-clock and
  Europe/Athens views.
- **Reason:** Greece/market clock changes create 23/25-hour and 92/100-quarter-hour days.
- **Consequence:** Local clock labels alone are never treated as unique interval identifiers.

## 2026-08-25 — Preserve prices exactly

- **Decision:** Preserve zero and negative official prices and reject or disclose missing
  prices rather than silently interpolating them.
- **Reason:** These observations materially affect dispatch value and risk.

## 2026-08-25 — Separate ceilings, backtests and scenarios

- **Decision:** Every operating path carries a label identifying perfect foresight,
  historical forecast backtest or user scenario.
- **Reason:** A physically feasible optimum with future price knowledge is not an achievable
  forecast.

## 2026-08-25 — Restrict the initial commercial scope

- **Decision:** Model Greek DAM arbitrage only.
- **Reason:** Other markets and revenue streams require separate access, acceptance,
  settlement, regulatory and operational evidence.

## 2026-08-25 — Use daily terminal-energy equality in comparative backtests

- **Decision:** Restore initial state of charge at each day end for like-for-like daily
  forecast comparisons.
- **Reason:** This prevents one strategy from receiving free value by emptying the battery at
  the evaluation boundary.
- **Consequence:** This is a benchmark convention, not a full multi-day trading policy.

## 2026-08-25 — Keep finance unlevered in v0.6

- **Decision:** Include explicit CAPEX, OPEX, augmentation, decommissioning and residual value,
  but exclude tax, debt, subsidies and working capital.
- **Reason:** Those layers require project-specific evidence and jurisdiction-specific advice.
