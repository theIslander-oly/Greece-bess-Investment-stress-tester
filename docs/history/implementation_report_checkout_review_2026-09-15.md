# Checkout review and README consolidation — 15 September 2026

## Observed state

The working tree was clean on `release-integrated-research-study` at `45fdc7a`.
After fetching origin, the branch was two commits ahead of `main`, with no commits behind.
PR #78 was open and mergeable, with no submitted reviews and successful Python 3.12/3.13 CI.

Inspection covered the integrated daily runner, command registry, demonstration, official-study
workflow and its guard/seal helper, configuration policy and relevant tests. The integrated
runner invokes existing forecast, settlement, degradation and finance modules; ML/weather
benchmarks remain separate. This was a checkout assessment, not a certification of every model
or a completed review of every release change. No official data was retrieved or study dispatched.

## Maintenance

Reduce the README from 713 lines / 45,488 bytes to 151 lines / 8,377 bytes. Preserve its accepted
findings section verbatim. Remove duplicated feature inventories, old next-phase narratives,
release histories and the stale price-history-only claim; link to maintained references.
Retain the explicitly approved synthetic sample and its byte-for-byte regression test.

Ignore root `private/`, which the release workflow uses for official CSVs, JSON receipts and
logs. No local data, evidence, environments or caches were deleted. Add a regression check that
README local references resolve. Analytical code, configurations and declaration digests are
unchanged. Historical decision and validation records are retained.

## Validation

- Ruff passed; mypy passed across all 75 source files.
- The full suite collected before the link test was added passed: 804 tests in 430.92 seconds.
  The updated metadata module, including that new test, separately passed all 7 tests.
- An isolated wheel build from a fresh copy of tracked package sources passed.
- The installed `greek-bess --help` entry point passed. An initial probe using
  `python -m greek_bess.cli` was inapplicable: the package exposes a console script, not a
  module entry point.
- Git ignore checks cover private prices, evidence JSON and command logs. README local links
  resolve, and the accepted findings match the previous revision verbatim.
- The maintenance diff passed whitespace and added-content secret/attribution checks and
  contains no generated output, official data, model changes or declaration changes.

The new maintenance commit has local validation; the existing PR CI result belongs to its
previous head and must rerun after any push.

## Next step

Complete release PR review before merge. The official integrated study then requires its declared
run gate; publication follows evidence review. Do not add a new model solely to expand coverage.
Further simplification should start with measured maintenance or runtime costs, preserving
source-specific validation and evidence custody.
