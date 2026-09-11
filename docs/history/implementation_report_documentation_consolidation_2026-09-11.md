# Documentation and code consolidation — 11 September 2026

The first unfinished milestone after the accounting repair: measure the repository, decide what
to keep, consolidate or remove on evidence, and act only where the replacement is proven.

**Result in one line: the documentation carried 2,165 lines of measured duplication and the code
carried none, so the documentation was consolidated and no module or command was removed.**

## 1. What was measured, before anything changed

| Surface | Before | After |
| --- | ---: | ---: |
| Root standing documents (12 files) | 8,063 lines | 5,948 lines |
| `STATUS.md` | 1,492 lines | 81 lines |
| `PLAN.md` | 827 lines | 73 lines |
| `docs/` active | 27 files, 6,048 lines | 27 files, 6,064 lines |
| `docs/history/` | 64 files, 5,737 lines | 67 files, 8,083 lines |
| All markdown | 20,336 lines | 20,591 lines |
| `src/greek_bess` | 71 files, 21,725 lines | unchanged |
| `tests/` | 54 files, 15,774 lines | 54 files, 15,807 lines |
| Workflows / CLI subcommands | 14 / 38 | 14 / 38 |

Total markdown rose by 255 lines. That is the honest shape of this change: **nothing was deleted.**
History was moved to the archive that already existed for it, and the active surface — the pages a
reader is expected to hold in their head — fell by 2,115 lines, or 26%.

## 2. Evidence gathered before any judgement

**Code reachability.** Every module under `src/greek_bess` was parsed and its imports resolved
into a graph, then walked from the CLI entry point. **70 of 71 modules are reachable.** The single
exception is `data/__init__.py`, a six-line package initializer that still executes at import time;
it is unreachable only as a graph node, not as code.

A first pass using textual reference counting reported four CLI modules with zero references. That
was a measurement artifact: `cli/_main.py` imports them in a multi-line parenthesized relative
import that the pattern did not match. The finding was withdrawn rather than acted on. It is
recorded here because it is exactly the failure the milestone warns about — treating an artifact of
measurement as evidence of disuse.

**Command reachability.** All 38 subcommands are registered, parse, and pair a `configure` with a
`run`. Each was cross-referenced against tests, workflows and `docs/command_reference.md`.

**The one real orphan.** `normalize-henex-directory` was named in exactly one place in the whole
repository — its own registration in `cli/ingest.py`. No test, no workflow, no reference entry, no
mention in any document.

## 3. Keep / consolidate / remove

| Surface | Verdict | Evidence |
| --- | --- | --- |
| All 71 source modules | **Keep** | 70 reachable from the CLI entry point by import-graph walk; the 71st is a package initializer |
| All 38 subcommands | **Keep** | Every one registered, parsed and paired; none duplicates another's function |
| ADMIE client and timing audit | **Keep** | Out of analytical scope by the decision of 1 September 2026, but deliberately retained and documented as unused; `fetch-admie-files`, `list-admie-filetypes` and `audit-admie-publication-timing` remain registered, and the audit runs in a workflow. Removing it would reverse a standing decision, not tidy the repository |
| Manual ingestion commands (`parse-henex`, `fetch-henex-*`, `fetch-entsoe`, `compare-sources`) | **Keep** | Low automated-test counts reflect that official data must never enter CI, not disuse; four are exercised by workflows |
| `normalize-henex-directory` | **Keep, document, test** | A genuine user-facing path that composes four helpers used elsewhere. The defect was that nobody documented it |
| `STATUS.md` dated log (1,411 lines removed) | **Consolidate** | A reverse-chronological record of every version, duplicating `CHANGELOG.md` and `docs/history/`. `docs/history/README.md` already declares that history belongs there and that `STATUS.md` is "where the work currently stands" |
| `STATUS.md` opening block | **Rewrite** | One 6,631-character paragraph chaining 21 semicolons with no sentence break |
| `PLAN.md` handoffs and completed milestones (754 lines removed) | **Consolidate** | 75 of 84 checkboxes already complete; five session handoffs each superseded by the next |
| `PLAN.md` availability-basis sentence | **Consolidate** | Restates a rule `METHODOLOGY.md` section 13 already owns in full |
| `CHANGELOG.md`, `DECISIONS.md` | **Keep; do not archive** | A changelog and a dated decision log are the canonical homes for their content, not duplication of it. Both receive this change's ordinary entry; neither has its accumulated history moved |
| `docs/` dated acceptance and result documents | **Keep unchanged** | Each is provenance for a recorded result and is cited by digest or run id |

## 4. What changed

- `STATUS.md` is now a current-state page: where the work stands, what the repair moved, a table
  of where each recorded result lives, the three open gates, and the standing exclusions.
- `PLAN.md` is now the tracker plus Stage 9, Stage 10 and the live operating constraint. **No stage
  is renumbered**: stages 1–8 remain Complete and Stage 9 remains next, exactly as before.
- The logs moved verbatim to `docs/history/status_log_through_2026-09-11.md` and
  `docs/history/plan_log_through_2026-09-11.md`, both indexed in `docs/history/README.md`.
- `docs/command_reference.md` documents `normalize-henex-directory`.
- `tests/test_cli_registry.py` gains a guard that every registered command is named in the command
  reference. It fails on the pre-fix tree naming `normalize-henex-directory` and passes after.
- `tests/test_project_metadata.py`'s availability-basis contract now reads `METHODOLOGY.md`, where
  the rule lives, instead of a copy of it in `PLAN.md`.

## 5. Two defects found and corrected in the moved text

Both were in `STATUS.md` and `PLAN.md`, and both are the class this project keeps finding — a
correct statement under a wrong label.

1. **A mislabelled section.** `STATUS.md` carried two sections titled *Stage 7, step 5*. They were
   not duplicates: the second recorded step 4's custody and acceptance preflight (PR #66, runs
   `34503398871`, `34504032804`, `34503999540`). It is titled step 4 in the archive.
2. **A contradiction inside `PLAN.md`.** Line 27 recorded Stage 7 complete with benchmark run
   `34524611285`, while lines 640–643 stated that the run "has never been dispatched" and that "no
   benchmark figure exists". The second was true when written and false by 11 September 2026. This
   is precisely what Stage 10's acceptance check forbids, and it is why that check exists.

No figure, run id, digest or date was altered in either move.

## 6. Validation

Ruff clean, mypy clean over 71 source files, full suite 757 passed (756 + 1 added guard), clean
wheel build. No source module changed, so no analytical output can have moved; the fixture-level
check is that the suite that pins those outputs is unchanged and still passes.

## 7. Limitations and what is not claimed

- This milestone consolidated documentation. **It removed no code, because the evidence supported
  removing none** — not because code was not examined.
- `DECISIONS.md` (1,757 → 1,784 lines) and `CHANGELOG.md` (1,634 → 1,655) grew by this change's
  own entry and were not otherwise touched. Both are dated append-only records where length is a
  property of the history rather than duplication of it, so neither was archived. Whether the
  decision log wants periodic archiving is a separate question with its own evidence, and this
  milestone did not gather it.
- `docs/command_reference.md` remains the largest active document at 1,352 lines. It is a
  per-command reference and its length tracks the 38 commands; no duplication was measured in it.
- `normalize-henex-directory` is now documented and guarded, but still has no behavioural test.
  Its four helpers are shared with commands that do.
