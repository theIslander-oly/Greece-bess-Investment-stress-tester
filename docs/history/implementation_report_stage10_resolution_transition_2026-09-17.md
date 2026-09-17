# Stage 10 official-run failure and resolution-transition repair — 17 September 2026

## Observed official attempt

After PR #80 merged as `fc82941` and merge CI `35190409929` passed on Python 3.12 and
3.13, the operator authorized one dispatch of the unchanged 14 September declaration. Workflow
run `35191734263` used accepted history run `33483975614` and declaration SHA-256
`72b3a5c12b726735641e0f2e18f6309c2781faecbf2434d448bc5e80843106df`.

The declaration guard, history download, custody verification and complete-calendar preparation
passed. Custody verified all six files with zero differences. The first 50 MW/100 MWh study then
failed before emitting a manifest:

> The rolling_mean forecast is incomplete on 1 declared window day(s), first 2025-10-01.

The retained artifact is `integrated-study-private`, artifact id `10484486066`, expiring
16 December 2026 at 06:51:41 UTC. Its archive SHA-256 is
`13192b535cfaee2c1f7113e3db3f9fa30c9702c299b47bc3b3f6b7fe0e3511fb`, matching GitHub's
artifact digest. It contains the verified prices, declaration, preparation records and private
command log. It contains no `evidence_index.json`, summary, manifest or research result. The
attempt is retained as a failed acceptance outcome; nothing from it may be published as a study.

## Reproduced cause

The accepted market changes from hourly to quarter-hour delivery on 1 October 2025. The naïve
forecaster indexed history only by exact market-clock start. On that first quarter-hour day,
historical `:00` observations existed, but no historical `:15`, `:30` or `:45` observations
existed. The declaration's statement that rolling mean and ensemble were complete was therefore
false. Synthetic regressions reproduce both consequences: coarser history fails to cover a finer
target, while finer history at the same start can be mistaken for a coarser target.

This is not missing official data. Shortening the window, filling values or removing a declared
strategy would change the experiment merely to make it pass and is rejected.

## Repair

Index each historical price at the supported finer interval starts contained in its native
half-open delivery interval and retain its native duration. A lookup accepts the value only when
the historical duration is at least the target duration. Consequently an hourly price may be
broadcast to the four quarter-hours it contains; a quarter-hour value cannot stand in for an
hourly target. Exact-resolution behavior is unchanged. Forecasts for a target day remain fixed
before any realized price from that day enters history.

This is an explicit coarser-to-finer resolution relation, not interpolation or missing-value
imputation. It follows the direction already used for admitted point-in-time features. The
rolling mean applies the rule separately to every prior day in its declared 28-day window;
daily and weekly persistence and the ensemble use the same causal lookup.

Regression tests require complete daily, weekly, rolling-mean and ensemble forecasts across a
synthetic hourly-to-quarter-hour transition, pin the contained hourly value used by a `:15`
target, and refuse the reverse finer-to-coarser case. Existing causality and DST tests remain.
Against the retained accepted history, both official configurations now produce all 96 forecasts
for 1 October 2025 with zero missing rolling-mean or ensemble values and retain all 329 declared
study days. This check creates no official study result.

## Declaration and next gate

The failed 14 September declaration remains unchanged and identifies run `35191734263`. A new
17 September declaration preserves the accepted history, 329-day horizon, three strategies, two
battery configurations, degradation and illustrative finance assumptions. It adds the explicit
resolution rule and pins the naïve forecaster, workflow and helper identities. Its SHA-256 is
`007c90444aedf17135601035c3b46a9731b7117a531692f92e4173f28cdcbe79`.

The repair requires a focused PR, final-head CI and operator review. Any retry requires separate
authorization of the new declaration SHA-256. A merge is not dispatch authorization, and a
successful retry would still require private result reconciliation and separate publication
approval.

## Validation

- Both new transition regressions failed on the merged implementation and pass after the repair.
- A controlled 264-row hourly forecast table is identical before and after the repair.
- The retained official history preserves all 329 study days and has complete rolling-mean and
  ensemble forecasts, including all 96 intervals on 1 October 2025.
- Ruff passes; mypy reports no issues in 75 source files; all 812 tests pass in 192.32 seconds;
  and an isolated clean wheel build succeeds.
- Every prospective declaration pin matches. Diff whitespace, generated-file and credential
  checks pass. Official prices, partial outputs and the failed-run artifact remain ignored.
