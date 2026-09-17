# Release continuation review — 17 September 2026

## Verified checkout and integration

Started from clean `f3e8606` on `codex/audit-stages1-9`. Fetching origin disproved the
handoff's open-release-PR assumption: preparation PR #78 had merged as `57c0ba3` on
15 September, with passing CI `34940218055`. Pushed the existing README cleanup `f760c7d`
on its intended release branch and opened PR #79. Both PR CI `34984746645` and explicit
head CI `34984746017` passed on Python 3.12 and 3.13. PR #79 subsequently merged as
`d60b85c` on 17 September. No merge was performed during this review.

The audit repair now targets `main` directly; ancestry already includes the cleanup and
release implementation. No cherry-pick, duplicate implementation or overlapping PR is needed.

## Independent Stage 9 repair review

Executed the parent implementation against the synthetic counterexample: changing only
copied actual prices changes the RMSE pick. Valid synthetic inputs produce identical old/new
summaries. The new guard checks canonical UTC matching before metrics, with zero relative
and 1e-9 EUR/MWh absolute tolerance. Added regressions cover zero and negative prices,
both sides of the tolerance, high prices that would expose a relative allowance, non-finite
values in either source, invalid/duplicate forecast keys, duplicate canonical keys and
unmatched intervals. Existing tests exercise evaluation-outcome invariance of frozen selection.

The retained official forecast table passes the guard; all eight indexed evidence hashes
verify. No accepted result was rerun or replaced. The original declaration matches retained
run evidence byte for byte. Every prospective Stage 9 and Stage 10 implementation pin matches.

- Original Stage 9 declaration: `78822530a6f9c1d2f0f45e50ea08d0864dffd4ebf23c989cc4cb5428751fc611`.
- Prospective Stage 9 declaration: `9fb57de6c2152abe80ce81c76aaa5bb6b4720b57626deb14f7e774068456b944`.
- Existing Stage 10 declaration: `72b3a5c12b726735641e0f2e18f6309c2781faecbf2434d448bc5e80843106df`.

## Retention and reproducibility

Existing custody verifies all six history files and seven feature files without differences.
GitHub reports the accepted history available until 30 November 2026 07:49:14 UTC,
features until 9 December 16:39:07 UTC, Stage 7 evidence until 9 December 20:08:53 UTC,
and Stage 9 evidence until 10 December 16:43:18 UTC. The encrypted history and feature
assets on `custody-2026-09-10` remain available with the recorded ciphertext digests.
This checks availability, not decryption or independent storage.

The 14 currently listed witness artifacts cover delivery dates 5–18 September. Their
expiry dates span 3–16 December. Original ZIP archives and metadata are retained privately
under `private/stages1-9-audit/witness-archives/`, with GitHub SHA-256 and ZIP integrity
checks. These preserve contemporaneous observations; they do not recreate or strengthen
earlier timing evidence. A same-workstation copy is not independent custody.

No operator-provided identity-file path, configured `AGE_KEYFILE`, or independently
controlled destination is available. The published-assets restore drill therefore remains
open. Resolution: supply a secure local identity-file path and independent destination,
then decrypt using age's output-file option and verify plaintext against existing custody.
Never put a key or token in chat, logs or Git.

Local scikit-learn is still 1.9.0; official Stage 9 records 1.9.1 and Python 3.12.14.
NumPy 2.5.3, pandas 2.3.3 and SciPy 1.18.1 match. No scientific refit was attempted.
Any exact replay needs an isolated environment with recorded dependencies; tolerances do
not establish byte-identical refits. No development dependency was changed.

Repository secrets are still absent. The latest ENTSO-E reconciliation remains failed run
`33489364087`. Restoring `ENTSOE_SECURITY_TOKEN` through secure repository settings is
required for fresh reconciliation, but not for using verified accepted HEnEx history.

## Exact proposed official dispatch and remaining acceptance

The unchanged declaration names accepted history `33483975614`, 1 October 2025 through
25 August 2026, and the two fixed configurations (50 MW/100 MWh at 1.5 daily cycles and
25 MW/100 MWh at 1.0 daily cycles). Both pass complete-history and 329-day window checks
against retained verified prices. No official dispatch, forecast benchmark or study result
was produced during those checks.

Reviewed the workflow guard, custody-before-read ordering, private command logs, separate
strategy states, causal forecast construction, realized settlement, stored-energy ledgers,
finance horizon, verified-manifest rendering and sign-independent artifact retention.
Synthetic regression evidence supports these paths; only executing and reconciling the
authorized official study can close Stage 8's original official acceptance.

Proposed action submitted for separate operator approval: run `run-integrated-study.yml`
once at reviewed merged commit `57c0ba35f44f6016d111f6a7a16b0ec1d09dba24`, with
`history_run_id=33483975614` and the Stage 10 declaration digest above. If dispatched via
a branch, verify its resolved commit first and do not substitute a later head silently.
No approval has been recorded in this continuation. Result review and public deployment
remain separate gates. The release is not complete and nothing new is published.

## Validation

Ruff and mypy pass (75 source files); a wheel built successfully from a fresh temporary
source copy. The first full local test attempt stopped progressing across a workstation
session pause; it is not counted as a pass. A clean test-process retry uses the existing
development environment with numerical thread counts set to one. Final suite and PR CI
outcomes are recorded in the delivery status. Complete diff review checks declaration
identities, generated files, credentials and contributor-neutral attribution.
