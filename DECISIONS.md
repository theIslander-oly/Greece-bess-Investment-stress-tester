# Decision log

This file records decisions that materially affect interpretation or reproducibility. Add a
dated entry when a milestone changes scope, assumptions, data handling or validation.

## 2026-08-26 — Accept the complete official HEnEx acquisition baseline

- **Decision:** Accept workflow run 32971677163 and its private
  `greek-dam-official-history` artifact as the official acquisition baseline through 25 August
  2026. The artifact contains 74,663 intervals, including 22,748 rows retrieved from the 2026
  daily catalogue, and has SHA-256
  `127915bc6e143a6bf2a4cb0a559b798e231062097bdaf9bf467a051260c4b198`.
- **Reason:** Both annual archive retrieval and incremental daily retrieval passed, coverage is
  continuous from 1 November 2020 through 25 August 2026, and the combined history has zero
  missing intervals.
- **Consequence:** v0.7 may use this privately retrieved history for research validation while
  preserving all existing interpretation limits. The artifact and official data remain outside
  Git, and acceptance is ingestion evidence rather than an investment conclusion.

## 2026-08-26 — Require complete daily-catalog coverage

- **Decision:** Parse the live suffix-less HEnEx result labels, follow the current Liferay
  pagination route and require one latest-revision publication for every requested delivery day.
- **Reason:** Incremental workflow run 32969157951 found zero files because the synthetic fixture
  included `.xlsx` while the live catalogue labels do not. Pagination must also never repeat or
  stop merely because a page lies outside the requested range.
- **Consequence:** Layout drift and incomplete ranges fail explicitly; daily data cannot enter an
  official-history artifact unless catalogue coverage is complete.

## 2026-08-26 — Select publications before parsing and bound row-level MCP consensus

- **Decision:** Select the greatest workbook filename revision for each HEnEx delivery day before
  parsing. Within that selected workbook, accept a dominant MCP only when it is unique, more than
  half of the rows, differs from at most two rows, and the total spread is no more than
  EUR 0.011/MWh.
- **Reason:** Superseded 16 December 2020 workbooks contain material conflicts corrected by v03.
  Across the latest 2020-2025 publications, 980 intervals contain only a EUR 0.01/MWh difference
  in one or two Greek-border import/export rows; all other asset rows agree.
- **Consequence:** Corrected later publications are authoritative, bounded rounding consensus is
  labeled `henex_mcp_rounding_consensus`, and material or ambiguous disagreements still fail.

## 2026-08-26 — Support the documented 2021 nested annual DAM archive

- **Decision:** Allow one size-limited nested ZIP only when its name matches
  `YYYY_EL-DAM_Results.zip`; reject deeper nesting and ignore unrelated LIDA/CRIDA archives.
- **Reason:** The official 2021 annual download contains the DAM history as a nested archive,
  unlike the other registered years.
- **Consequence:** Both outer and nested archive hashes enter the manifest, and 2021 is no longer
  silently absent from the normalized history.

## 2026-08-26 — Quarantine ADMIE forecast candidates until timing acceptance

- **Decision:** Retrieve and timestamp ADMIE load, RES and system files, but do not parse them
  into forecast features until their publication sequence is proven to precede the target-day bid
  decision for every applicable historical regime.
- **Reason:** A useful-looking official variable can still create look-ahead leakage if it was
  published after the decision point.
- **Consequence:** Retrieval manifests label these files `requires_pre_auction_timing_validation`.

## 2026-08-26 — Use annual HEnEx archives before daily catalog discovery

- **Decision:** Treat reviewed 2020-2025 annual ZIPs as the primary history path and use the
  current website catalog only for unarchived daily increments.
- **Reason:** Annual archive URLs are stable and compact; the daily asset publisher is more likely
  to change layout.
- **Consequence:** Daily discovery fails visibly on layout changes and never bypasses the normal
  parser, revision selection or quality checks.

## 2026-08-26 — Preserve file-level retrieval provenance

- **Decision:** Record exact source URL, delivery coverage, publication time when available,
  retrieval time, revision, byte size and SHA-256 for every official file. Extracted HEnEx
  workbooks also retain their parent archive hash.
- **Reason:** Revisions and provider-side replacement can otherwise make a historical research
  run impossible to reproduce or audit.
- **Consequence:** Manifests are generated beside ignored data and may be retained as private
  workflow artifacts; official file contents remain outside Git.

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
