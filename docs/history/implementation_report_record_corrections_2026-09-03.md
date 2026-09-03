# Implementation report — v0.9.5 record corrections

**Date:** 3 September 2026

## Scope

No source, test, workflow or configuration behaviour changed. This is a record-keeping pass over
the repository's standing documents after the v0.9.5 merge, correcting four placement defects, one
false present-tense claim, one stale declared version and one incomplete index, and recording two
facts about the official track that no document carried.

The project's own convention is that the repository records what was decided, what was validated
and what the evidence is. A standing document that contradicts the state of the repository fails
that convention as surely as a wrong number would, which is why these are corrected rather than
left to the next milestone.

## Placement defects

The v0.9.5 merge appended its documentation to the end of four files rather than into the
structures those files already had.

- `STATUS.md` carried its v0.9.5 section below `Current limitations` and `Immediate next
  milestone`, while every other milestone section is in reverse-chronological order at the top.
  The section is moved ahead of v0.9.4 and the lead summary now carries v0.9.5.
- `CHANGELOG.md` carried a `## [0.9.5] — 2026-09-03` release section below `## [0.1.0] —
  2026-08-24`, breaking the newest-first order and adopting a released-section convention that
  v0.8.0 through v0.9.4 do not use — no version above 0.7.2 has been released or tagged. The entry
  is rewritten in the established `[Unreleased]` bullet style.
- `README.md` carried a `## v0.9 official-run preparation` section below the closing licence note.
  Its content is folded into the v0.9 narrative where the rest of the milestone is described.
- `PLAN.md` tracked v0.9.5 twice, as an unchecked roadmap entry and as an appended checklist that
  marked four of its five items done. The roadmap entry now records what landed and what did not,
  and the checklist states the official-run order as five numbered steps.

## Corrections of fact

- **The declared version was two places, not three.** `STATUS.md` still read `0.9.4` while
  `pyproject.toml`, `greek_bess.__version__` and the README release line read `0.9.5`. The
  version test locks the latter three; `STATUS.md` is outside it and had drifted.
- **The README claimed the v0.9 declarations do not exist.** Its v0.9 section read "No surface
  runs yet: … until all three exist nothing is retrieved". All three were committed on 3 September
  2026, which is what makes every v0.9 surface runnable. The paragraph now says that the
  declarations exist, that nothing has been run through them, and that every figure the README
  reports still comes from the accepted price history alone.
- **`PLAN.md` still listed the three declarations under "Waiting on an operator declaration".**
  They are moved to a dated resolved section, leaving the two operator items the standing position
  already names — the second custody copy and `ENTSOE_SECURITY_TOKEN`.
- **The README's "full list" of project records stopped at v0.8.2.** Eighteen committed records —
  among them the completed-v0.7 review, the v0.8.3 review response, both design documents, the
  point-in-time feature contract, the source assessment, the operator declarations and every v0.9
  implementation report — were not linked from a list that claims to be complete. They are added.

## Facts recorded that no document carried

- **`Fetch point-in-time fundamentals` has never been dispatched.** The v0.9 chain is complete in
  code and empty of evidence: no feature table, no availability audit against retrieved data, no
  custody record, no acceptance document and no benchmark figure exists. Documents written before
  the declarations landed attributed this to the missing declarations, which is no longer the
  reason. `STATUS.md` and `PLAN.md` now say so plainly, and the immediate next milestone is
  restated as the execution order rather than the v0.8 history it still described.
- **One witnessed day is lost and cannot be recovered.** The scheduled `witness-fundamentals` run
  of 3 September 2026 — run `33722543960`, the workflow's first — started at 06:17 UTC against
  commit `a64bb21`, about two hours before the declarations merged, and stopped at its guard.
  Delivery day 4 September 2026 closed at 12:00 CEST that day, so no retrieval can witness it now
  and it can only ever be provider-declared evidence. The cron needs no change: 06:00 UTC falls
  after the observed publication window of the 00 UTC cycle and before the declared closure, so
  the next scheduled run is the first that will find all three declarations in place.

## Validation

Ruff, mypy over 64 source files, all 592 tests and a clean wheel build pass on the unchanged
implementation. No analytical result, accepted figure, manifest digest or declared assumption
changed, and no official data was retrieved.
