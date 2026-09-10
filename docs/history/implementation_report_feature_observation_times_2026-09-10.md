# Implementation report — feature observation times

**Date:** 10 September 2026
**Execution-plan stage:** 3, first of two units
**Review finding:** 5

## Scope

This unit corrects what a point-in-time feature row's `retrieved_at_utc` means. It changes no
declared source, cycle, geography, decision cutoff, feature set, held-out period or feature
value, and it launches no retrieval, acceptance or benchmark workflow. Shard reconciliation,
the second unit of this stage, is not part of it.

## The defect

`retrieved_at_utc` was the instant the *retrieval run began*. `run_fetch_fundamentals` read the
clock once, before its first request, and stamped that one instant onto every row of every
delivery day the run produced; `build_delivery_day_features` did the same for a single day.

The availability audit grades a row `witnessed` when its `retrieved_at_utc` falls strictly
before the delivery day's declared decision cutoff — that is, when this project observed the
value contemporaneously rather than reading the provider's word for it afterwards. A run-start
stamp made that grade unearnable in the wrong direction: a retrieval that started one minute
before a cutoff and went on receiving messages for an hour after it recorded every one of those
late values as witnessed.

`witnessed` is the one grade in this scheme that cannot be reconstructed later. A provider
publication instant can be read from the object at any time in the future; a contemporaneous
observation exists only if a retrieval actually happened in time. So the defect could not be
detected downstream, and nothing reading the table afterwards could have checked it.

## The correction

The receipt instant is now read once per message, immediately after its transfer has succeeded
and its declared length has been checked, and never before a request is issued. Transport
retries happen inside the fetch, so this is by construction the instant of the attempt that
delivered the bytes; a failed earlier attempt observed nothing and contributes no instant.

Each `RetrievalRecord` carries its own message's receipt. A derived feature row inherits the
**latest** receipt among its contributing messages, on the same argument that already governs
its publication instant and its digest: a wind speed has not been observed until both the
eastward and the northward component have arrived, and an hourly radiation mean has not been
observed until both bucket ends have.

Provider publication time is unchanged and remains a separate field. `published_at_utc` is the
provider's instant, read from the object; `retrieved_at_utc` is this project's. Neither
substitutes for the other, and the audit continues to require both.

Run start is still recorded, as a property of the run rather than of any value. The per-day and
per-run summaries now carry `run_started_at_utc`, `first_message_received_at_utc` and
`last_message_received_at_utc` as three separate instants, so a run's span is visible without
any row claiming it.

The receipt clock is a fourth injectable seam on `NoaaGfsClient`, beside the fetcher, head
reader and decoder. It exists because that instant is evidence: a test that cannot move it
cannot exercise a request answered on the wrong side of a cutoff. A clock returning a naive
timestamp is refused rather than assumed to be UTC.

## Invalidation

`GFS_OBSERVATION_SEMANTICS_VERSION` is 2 and is recorded in every retrieval summary and added to
the shard identity fields. A table built under version 1 carries run-start stamps and cannot be
read as evidence of when anything was observed, so version 1 and version 2 shards are refused as
slices of one window rather than combined. A summary carrying no observation-semantics identity
at all predates the contract and is refused with a rebuild message.

The strict-before comparison itself was already correct and is unchanged: a receipt exactly at
the cutoff is late. It is now covered by a test, because it is the boundary this stage's
acceptance checks name.

## Review of existing witness records

The daily witness workflow has run eight times. Each run witnesses the following delivery day,
so the eight cover delivery days 2026-09-04 through 2026-09-11. The run of 2026-09-03 failed,
leaving delivery day 2026-09-04 unwitnessed; the seven successful runs of 2026-09-04 through
2026-09-10 cover delivery days 2026-09-05 through 2026-09-11. All seven recorded their features
under the run-start semantics corrected here, so each was reviewed against the declared cutoff.

The declared cutoff is 12:00 Europe/Brussels on D-1 with a zero-minute lead
(`config/decision_cutoff.json`, `config/decision_lead_minutes.txt`), which in CEST is 10:00 UTC
on D-1. The workflow is scheduled at 06:00 UTC. The seven successful runs started between
06:14:55 and 06:17:52 UTC and reached their upload step between 06:17:02 and 06:23:49 UTC, so
every message in each of them was received before the run ended and therefore before 06:24 UTC —
at least three hours and thirty-six minutes before that day's cutoff.

The correction therefore changes no witnessed classification for any existing record: under both
the old and the corrected semantics every value in those seven runs was received strictly before
its cutoff. This is a review outcome supported by the recorded run timings, not a re-derivation
of more precise historic receipt instants, which the retained evidence does not contain and which
this stage does not invent. Witness runs made after this change lands record real per-message
receipts and need no such review.

No reclassification was required and none was performed.

## Out of scope

`entsoe.py`, `henex_archive.py`, `henex_daily.py` and `admie.py` also stamp a single
`retrieved_at_utc` per retrieval. They produce official price observations, which are not graded
against a decision cutoff by `audit_feature_availability`; only the point-in-time feature path
feeds that audit. Leaving them unchanged keeps this unit to the demonstrated defect.

## Validation

- Ruff
- mypy (65 source files)
- pytest: 648 passed, up from 637
- isolated wheel build

New regression tests cover: a row stamped with a receipt rather than the run start; a run
beginning before a cutoff and finishing after it producing both witnessed and provider-declared
rows from one retrieval; a receipt exactly at the cutoff failing the strict-before rule; a
derived value inheriting the later of its two contributing receipts; the clock being read after
a transfer rather than before it; a naive clock being refused; and shard combination refusing
mixed or absent observation-semantics identities.
