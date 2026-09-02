# Implementation report v0.9.2 — revision-aware point-in-time join

**Date:** 2 September 2026

## Scope and result

v0.9.2 adds the reusable point-in-time join and `build-point-in-time-features` command. It is built and tested exclusively against synthetic fixtures because `config/decision_cutoff.json`, `config/decision_lead_minutes.txt` and `config/fundamentals_geography.json` do not exist. The optional v0.9.1 acceptance work was therefore not run. No declaration was invented, defaulted or inferred; no real join result, model, manifest or acceptance document exists.

## Join contract

For each canonical price delivery day and each variable-area pair present in the declared feature table, the join resolves the effective cutoff from the supplied schedule and lead. It chooses per native feature interval the latest row ordered by publication instant, revision and source-document identity, with the publication instant required to be strictly before the cutoff. A tie is late. Rows published at or after the cutoff remain evidence: they are counted and excluded.

Each price interval receives a value only when its UTC start lies within exactly one selected feature interval. Equal resolution and a coarser-feature broadcast are distinguished in the audit; a finer feature is refused without a declared aggregation rule. Any unavailable or incomplete pair excludes the entire delivery day, leaving every feature column absent for that day. There is no forward fill, interpolation or imputation.

The audit table records the selected value's source document, revision, raw-byte SHA-256, publication, retrieval and forecast-issue instants, cutoff margin, effective evidence grade, resolution relation and later-revision count. The summary records complete/excluded days with named causes, grade and lead-time aggregates, schedule and lead declarations, and deterministic input/audit digests. The command exits 2 after writing evidence when a day is excluded.

## Synthetic verification

Focused tests cover the design cases assigned to v0.9.2: a publication at the cutoff is excluded, the latest earlier revision is selected, later revisions are counted, a missing interval excludes a complete day without partial values, hourly features broadcast explicitly across quarter-hours, input-row permutation leaves outputs identical, assumed evidence requires an explicitly exploratory run, and finer-resolution features are refused. Existing schema tests continue to cover timezone awareness, duplicate conflicts, DST market-day cardinality and provenance syntax.

## Documentation and deferred operations

The methodology, limitations, command reference, README, changelog, status, decisions and plan now describe the join. The deferred v0.8.x chart and engineering narratives were merged and their staging files removed. The accepted-replay publication staging file remains because the required new Pages deployment did not run: the working environment had no GitHub authentication and `gh workflow run` refused before dispatch. This is not treated as deployment success, and the placeholder and README deployment link were not filled.

The scheduled witness workflow has no declarations with which to pass its guard. Every refused target day permanently costs one witnessed day. Exact scheduled run IDs and target dates were not accessible from the unauthenticated private-repository checkout and are not inferred.

## Interpretation

Passing the join establishes causal revision selection and traceability only. It does not accept the feature values, prove their forecasting skill or support an investment conclusion. Perfect foresight remains a historical gross-margin upper bound, and ADMIE-originated forecasts remain excluded by every route.

## Verification record

Ruff passed, mypy passed over 62 source files, all 526 tests passed, and a clean wheel build succeeded on Python 3.12.13. The sample synthetic report was regenerated for project version 0.9.2. The complete diff, ignored-artifact inventory and secret-pattern scan were reviewed; build products were removed before commit.
