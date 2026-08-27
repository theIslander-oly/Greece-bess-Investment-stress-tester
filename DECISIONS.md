# Decision log

## 2026-08-27 — Keep repository development configuration contributor-neutral

**Decision:** Track only project-wide setup, validation and contribution instructions. Do not
track editor-, service- or contributor-specific session bootstrap configuration. Automation must
also avoid contributor-specific branch naming conventions.

**Reason:** Project requirements belong in the package metadata and shared contribution files.
Personal environment automation adds duplicate instructions, makes the repository appear tied to
one development environment and can prevent workflows from validating otherwise equivalent
feature branches.

**Consequence:** Contributors create a Python 3.12+ environment using their preferred tooling and
run the commands in `AGENTS.md` or `CONTRIBUTING.md`. The custody workflow's path-filtered push
trigger applies consistently to every branch.

This file records decisions that materially affect interpretation or reproducibility. Add a
dated entry when a milestone changes scope, assumptions, data handling or validation.

## 2026-08-27 — Hold accepted official artifacts as encrypted release assets, fingerprinted in Git

- **Decision:** Store each accepted official artifact as an encrypted asset attached to a
  release in this private repository, and commit a price-free custody record for it under
  `docs/custody/`. The record carries per-file digests and content-level invariants of the
  normalized series, including a digest of the interval and price series computed over sorted
  `(delivery_start_utc, delivery_end_utc, price)` triples at six fixed decimals. Encryption
  keys and the upload itself stay with the operator; no automation in this repository holds a
  key that could decrypt an accepted artifact.
- **Reason:** The accepted history existed only as a workflow artifact expiring on 2 September
  2026, and official data may not enter Git. A release asset is durable and re-fetchable, but
  an unencrypted one would place official HEnEx and ENTSO-E data into a repository asset under
  redistribution terms this project has not assessed; encrypting before upload removes that
  question entirely. Re-retrieval cannot substitute for custody, because HEnEx replaces
  publications — the superseded 16 December 2020 workbooks are the precedent — so without a
  committed fingerprint a provider revision would silently replace an accepted baseline.
- **Consequence:** A stored copy can be proven to be the accepted artifact rather than merely
  plausible, and a re-retrieval that differs is detected rather than adopted. The encryption
  key becomes part of the custody chain, so a lost key forces re-retrieval with those drift
  consequences. A verification difference is a recorded finding to investigate, never a check
  to re-run, and a committed record is not overwritten without a decision entry.

## 2026-08-27 — Digest the price series, not only the artifact bytes

- **Decision:** Fingerprint an accepted history with both per-file SHA-256 digests and a
  separate digest of the interval and price series, and treat the latter as authoritative for
  whether the data changed. Missing prices digest as an empty field rather than a substituted
  number, and `-0.0` is normalized to `0.0`.
- **Reason:** Byte digests answer "are these the same bytes", which is not the question that
  matters across a re-export or a pandas upgrade. They are also insufficient on their own in
  practice: a one-cent price revision changes a file's SHA-256 while leaving its byte size
  unchanged, so size is no guard, and a format-only difference would otherwise be
  indistinguishable from a revised price.
- **Consequence:** A re-export of the same history verifies; a revised cent does not. The two
  digests together distinguish a formatting change from a data change, which is what makes a
  verification difference diagnosable rather than merely alarming.

## 2026-08-27 — Read the ENTSO-E curve type instead of assuming one point per interval

- **Decision:** Honor the `curveType` an A44 document declares. Under `A03` a point's price holds
  until the next declared position, so the omitted positions are materialized and labelled
  `entsoe_variable_block_repeat`. `A01` documents keep one interval per point, and an unknown
  curve type is rejected rather than guessed.
- **Reason:** The first complete reconciliation reported 4,874 official intervals as missing from
  ENTSO-E across 1,042 market days while every interval present in both sources agreed. The
  pattern was an artifact of the parser: it emitted one interval per point regardless of curve
  type, so every `A03` repeat became a false gap. Correcting it reduced the missing count to zero
  and produced exactly 4,874 labelled repeats.
- **Consequence:** Materializing a declared repeat is not interpolation, and the distinction is
  preserved in the data: an interval that ENTSO-E stated once carries no flag, and one implied by
  the variable-block encoding is labelled. A genuine gap in an `A01` document still fails the
  completeness check.

## 2026-08-27 — Reconcile the two official sources inside GitHub Actions

- **Decision:** Perform the HEnEx-to-ENTSO-E reconciliation in a dedicated manual workflow that
  reads the accepted `greek-dam-official-history` artifact, retrieves ENTSO-E prices for the
  window that history defines and classifies every interval, rather than comparing two files
  downloaded to a workstation. The window is derived from the accepted history instead of being
  typed in, and only interval counts, classification counts and aggregate difference statistics
  are printed; interval-level detail stays inside the run artifact.
- **Reason:** The personal ENTSO-E token exists only as an encrypted repository secret and the
  accepted history exists only as a short-lived private artifact, so the single place where both
  are available is the workflow runner. Deriving the window from the history removes the
  market-clock boundary guesswork that a hand-typed UTC range invites, and keeps the two sources
  on identical market days by construction.
- **Consequence:** A reconciliation is reproducible from a run ID plus the repository secret, and
  no official price ever reaches a commit or an ordinary log. The comparison result is a recorded
  classification: mismatched or missing intervals are the finding, while a source that is not
  deterministically valid on its own still fails the job.

## 2026-08-27 — Reposition as a Greek DAM battery replay and research benchmark

- **Decision:** Present the project as a Greek Day-Ahead Market battery replay and research
  benchmark rather than an investment stress tester. The repository, package and CLI names are
  unchanged for now; README framing, a reader-facing "what this tool cannot tell you" section
  and the roadmap language carry the repositioning.
- **Reason:** An independent review (27 August 2026) found the implemented capability is a
  verified historical replay with leakage-safe forecast benchmarks and screening arithmetic.
  "Investment stress testing" overstates that: batteries only entered the Greek DAM in April
  2026, so the replayed history contains no storage competition; balancing-market and
  availability-support revenues that dominate real Greek battery commerce are excluded; and
  the only implemented shock is near-inert for arbitrage.
- **Consequence:** Outputs keep their existing labels. The positioning change is documentation
  only; no analytical behavior changed. A future full rename (repository/package/CLI) remains
  open as a separate decision.

## 2026-08-27 — Replace probabilistic v0.7 outputs with named deterministic scenarios

- **Decision:** Remove P5/P50/P95 percentiles and loss-probability outputs from the v0.7
  scope. v0.7 instead targets, in order: a documented bootstrap source-era/resolution policy,
  deterministic availability/outage paths, spread-compression transformations about a daily
  reference level, and scenario-ensemble range reporting explicitly labelled
  non-probabilistic. Cannibalisation is represented only as explicit judgmental
  spread-compression scenarios.
- **Reason:** The seasonal block bootstrap samples uniformly with replacement from a
  non-stationary 2020-2026 history (COVID trough, 2022 gas crisis, 2025-2026 negative-price
  surge), so percentiles over its paths have no calibrated probability interpretation and
  "loss probability" would be pseudo-statistical. A constant additive price-level shift leaves
  within-path spreads unchanged, so further level shocks change arbitrage economics only
  through efficiency losses and fees; spread transformations are the first-order stress. The
  bootstrap also requires a single input resolution while the accepted official history mixes
  hourly and quarter-hour regimes, so the sampling era must be an explicit decision.
- **Consequence:** No probability, percentile or loss metric will be attached to scenario
  outputs unless a defensible calibration methodology is independently justified first.
  Scenario results are reported as labelled ranges across named assumptions.

## 2026-08-27 — Record both horizons in official operational acceptance

- **Decision:** Accept the official multi-year history with the existing optimizer run twice: once
  over the complete 74,663-interval horizon in a single solve, and once as 2,124 independent daily
  solves composed without altering their physical semantics.
- **Reason:** The API maximises margin across whatever horizon it is given, and the full history
  proved tractable, so the true upper bound is recordable. The daily mode is the repository's
  established comparative convention and is the ceiling the forecast backtests use, so both are
  needed to interpret the forecast results.
- **Consequence:** The daily-composed margin is necessarily lower than the full-horizon margin
  because restoring the initial SOC each day removes inter-day arbitrage. Both remain labelled
  historical perfect-foresight gross-margin upper bounds; neither is expected revenue.

## 2026-08-27 — Attribute every excluded forecast day to a structural cause

- **Decision:** Require each excluded backtest day to be attributed to first-day warm-up,
  insufficient causal lag history, a spring DST day that removes the required wall-clock slot, or
  the 2025-10-01 hourly-to-quarter-hour resolution change and its lag warm-up.
- **Reason:** An unexplained exclusion could hide a defect, whereas these four causes are
  deterministic consequences of documented market structure and causal lag rules.
- **Consequence:** Acceptance reports coverage and exclusion counts by reason. Zero unexplained
  exclusions occurred across the accepted history, so no code change was warranted.

## 2026-08-27 — Dispatch bootstrap paths independently under shared assumptions

- **Decision:** Require equivalent complete canonical interval identities and retained synthetic
  provenance across all paths, then run the existing deterministic optimizer separately for each
  path with one unchanged battery configuration and common availability profile.
- **Reason:** This preserves path boundaries and makes operational/revenue sensitivity auditable
  without mixing state, constraints or assumptions between scenarios.
- **Consequence:** Results are labelled perfect-foresight gross-margin upper bounds on synthetic
  paths. No probabilities, percentiles, ranking, degradation, finance or investment conclusion
  is added; negative-price-event transformations are deferred.

## 2026-08-27 — Use one additive constant for the first price-level shock

- **Decision:** Apply a required finite EUR/MWh shift equally to every interval of each validated
  bootstrap path, identified by a required transformation ID, without clipping the result.
- **Reason:** A constant additive transformation is deterministic, transparent and preserves
  absolute price differences while allowing zero and negative shocked prices.
- **Consequence:** Original and shocked prices plus interval/path/source provenance are retained.
  The result is a synthetic sensitivity, not a calibrated distribution, forecast or investment
  conclusion; all other shock types remain excluded.

## 2026-08-26 — Start v0.7 with an auditable seasonal block bootstrap

- **Decision:** Sample complete contiguous market-day blocks with replacement from the same
  meteorological season, require exact target/source daily interval-count patterns, and expose
  the seed plus block-level candidate and selection provenance.
- **Reason:** This provides a deterministic dependence-preserving foundation while keeping DST,
  zero/negative prices and missing-data behavior explicit and testable.
- **Consequence:** Paths are labelled synthetic scenarios rather than forecasts or investment
  evidence. Missing observations are rejected, and dispatch, finance, probability summaries and
  shock overlays remain outside this reviewable foundation.

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
