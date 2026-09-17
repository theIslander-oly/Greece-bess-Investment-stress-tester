# Stages 1–9 executable-readiness audit — 15 September 2026

## Scope and conclusion

Audit started from `f760c7d` on the Stage 10 checkout, with a clean working tree, then moved to
`codex/audit-stages1-9`. This is a maintenance branch stacked on the release preparation.
The earlier 804-test result established a tested baseline, not complete operational readiness.

Inspection found one reproducible Stage 9 library-input defect, repaired here. The recorded
Stage 7 and Stage 9 evidence passes the identity and consistency checks below. Stage 8 has
implemented and tested its synthetic runner, but its original official-history acceptance check
remains outstanding under the Stage 10 run. Stages are not renumbered.

## Stage-by-stage disposition

| Stage | Evidence inspected or exercised | Disposition / next action |
| --- | --- | --- |
| 1 — retrieval failures | `data/http.py`, the GFS retrieval path and HTTP/GFS regressions distinguish 404/410 from server/transport failures, bound retries and preserve named exclusions. The accepted corrected feature artifact is available and verifies. | No new failure reproduced. Keep transport faults fatal after retry exhaustion; do not rebuild the full history merely for this audit. |
| 2 — GFS values | Decoder identity/units/step guards, local wind aggregation and radiation de-averaging tests include a generated GRIB decoded through ecCodes. The current live witness uses this pipeline. | No new value defect reproduced. The accepted table retains corrected semantics; raw historical GRIB messages were not retained, so this audit does not independently re-decode all historical source messages. |
| 3 — receipt timing and shards | Successful receipt timing, strict cutoff and shard reconciliation code/tests inspected. Current feature custody verifies all 7 files. Latest witness audit records 3 of 3 variable-days witnessed. Earlier run-start witnesses were reviewed against workflow completion times in the Stage 3 report. | Current evidence supports the correction. Preserve historical witness evidence before expiry; do not invent more precise historic receipts. |
| 4 — dated finance | Dated-cash-flow IRR implementation and independent-root, partial-year, leap-year and multiple-root regressions; later cash/shadow-cost accounting regressions. | No new timing defect reproduced. Passing arithmetic tests is not validation of illustrative project costs. |
| 5 — degradation interpretation | Daily-policy versus lifetime-optimum counterexample and result-basis propagation tests through finance/manifests/reporting. | No new interpretation defect reproduced. Retain simulation labels; no lifetime-optimal claim is warranted. |
| 6 — matched training | Retained Stage 7 forecast summary contains 100 refits per arm for each model family. Every matched/control-weather pair has identical records, including row and target digests, and training ends before prediction starts. | 200 paired refits reconcile; no reduced-training coverage is being reported as weather information in the matched comparison. |
| 7 — official weather experiment | Price and feature custody, three verified result manifests, accepted feature identity, 320 common held-out days and non-exploratory classification. Point-in-time feature reconstruction checked separately below. | Existing experiment has verifiable evidence. A fresh numeric replay must recreate recorded dependency versions and use accepted inputs; no new fit or dispatch benchmark was run here. |
| 8 — integrated study | Runner ordering, separate state/energy ledgers and complete-window/future-information tests. Original acceptance calls for synthetic **and official** execution; its implementation report explicitly records synthetic execution only. | Implementation complete; official-data acceptance remains open. Run and reconcile the prepared declared study before claiming full end-to-end acceptance. |
| 9 — value selection | All 8 indexed evidence file digests, frozen record digest, validation-scoreboard selections and actual-price identity verified. Synthetic fault injection changed the RMSE pick by altering only the copied actual-price column. | Repair the input inconsistency refusal before accepting external candidate tables. The shipped CLI generates its own table; the retained official table has zero discrepancy and its recorded result is unaffected. |

## Evidence examined privately

- Accepted history run `33483975614`: custody verifies 6 files with zero differences.
- Accepted combined feature run `34503398871`: custody verifies 7 files with zero differences.
- Stage 7 result run `34524611285`: all three retained manifests verify. Feature-set identity is
  `a718f46265678cf1e37c31fca439b9f2f03479901fe8f0ac126766431b99aefc`.
- Stage 9 run `34623616511`: all eight evidence-index hashes match; frozen selection hashes
  correctly; both picks match their validation scoreboards. The copied actual prices agree
  exactly with the settlement prices after timestamp alignment.
- Witness run `34936253216`, for delivery day 2026-09-16: all three variable-days are witnessed,
  rather than inferring timeliness from the successful job status alone.

Downloads, reconstructed tables and command logs are under ignored `private/stages1-9-audit/`.
No official interval data or generated report is committed. No new official model benchmark,
workflow dispatch, study acceptance or publication occurred.

## Repair and counterexample

`compare_selection_objectives` settled against canonical prices but calculated RMSE against the
candidate table's independent `actual_price_eur_per_mwh` copy. With unchanged synthetic prices
and candidate forecasts, replacing that copy with the second candidate changed the RMSE pick
from `low_rmse_wrong_order` to `high_rmse_right_order`. A missing copied actual also silently
reduced metric coverage. Both refusal regressions failed before the fix and pass afterwards.

Match the copied actuals to the canonical UTC interval keys before scoring. Refuse missing,
non-finite or inconsistent actuals, invalid/duplicate keys and unmatched intervals. Numerical
comparison uses an absolute 1e-9 EUR/MWh tolerance and zero relative tolerance. Valid inputs keep
the existing arithmetic and selections. The future-outcome invariance regression updates both
copies of evaluation actuals while leaving candidate forecasts and validation data unchanged.

The original 11 September run declaration remains byte-identical because the accepted result
links to its digest. A prospective 15 September declaration pins the changed implementation and
helper without changing any experiment setting. It prepares a future reviewed run, not a rerun
request or a replacement for the old evidence.

## Operational work still required, in priority order

1. Review and merge this refusal repair with final-head CI. If a future official Stage 9 run is
   needed, use the new declaration after review; reproduce the old run at its recorded commit.
2. Complete Stage 8's official-data acceptance using the prepared Stage 10 declaration: reconcile
   complete calendars, realized settlement, strategy-specific ageing/energy, costs and report
   values. Do not call the synthetic tests alone official validation.
3. Preserve the irrecoverable witness records and verify a restore from independently controlled
   storage. Current Actions downloads expire: history on 30 November, accepted features and
   Stage 7 evidence on 9 December, Stage 9 evidence on 10 December 2026. Encrypted accepted-input
   assets exist on repository releases, but this audit did not decrypt them or establish a copy
   under separate control. Workflows currently download accepted inputs by Actions run ID;
   exercise the documented restore procedure before those inputs expire.
4. Restore ENTSO-E access only for fresh cross-source reconciliation. Repository secrets are
   absent, and the last reconciliation run `33489364087` failed; this does not block computation
   from the accepted HEnEx history that verified here.
5. Recreate recorded numerical dependencies for any exact benchmark reproduction. The retained
   Stage 9 run records scikit-learn 1.9.1; this workstation has 1.9.0. Broad package ranges are
   suitable for compatibility testing but do not promise identical refits. Do not reinterpret
   dependency drift as evidence that a model improved or degraded.

Public report deployment remains a release task, not a missing prerequisite for Stages 1–9
calculations. New forecast families or connecting ML/weather to the integrated study are scope
extensions, not fixes required to meet its existing naive-planner design.

## Validation

- Both new refusal tests failed on the old implementation and pass after the repair.
- Final full suite: 807 tests passed in 549.38 seconds on Windows/Python 3.13.
- Ruff passed, mypy passed across 75 source files, and an isolated wheel build from a fresh
  copy of the package sources passed.
- The updated guard accepts the retained official Stage 9 table. Every prospective declaration
  pin matches, and the old declaration remains byte-identical. Documentation references resolve.
- Full current-code reconstruction from verified official price and feature inputs reproduces
  the accepted feature-set digest, price-input digest, feature-input digest and audit digest.
  All 2,124 daily records match: 2,002 complete and 122 excluded, with identical grade counts
  and exclusion reasons. Exit code 2 is the documented incomplete-coverage result, not a
  changed acceptance or a failed reconstruction; the accepted history has those exclusions.
- The original official workflow spent 7 minutes 1 second on this join. The local full-window
  reconstruction is also substantial; profile this existing join before proposing performance
  changes, and preserve the exact accepted identities as their regression basis.

These are local results. CI on a pushed repair head and review remain required before merge.
