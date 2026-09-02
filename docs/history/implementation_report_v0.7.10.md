# Implementation report v0.7.10 — ADMIE pre-auction publication-timing acceptance

**Date:** 31 August 2026

## Scope

Adds `greek_bess.data.admie_timing`, the `audit-admie-publication-timing` CLI command, the
`Audit ADMIE publication timing` workflow, `config/admie_gate_closure.example.json` and
`docs/admie_publication_timing_policy.md`.

This is parallel acceptance work, not a modeling milestone. No dispatch mode, forecast method,
stress transformation, degradation model, finance treatment or price-ingestion behaviour is added
or changed, and no v0.8 research interface or exportable report is implemented, stubbed or
prepared. No ADMIE file is parsed and no exogenous field enters any forecast.

## The problem

The 2026-08-26 decision quarantined ADMIE load and RES forecasts: retrieve and timestamp them,
but do not parse them into features until their publication sequence is proven to precede the
target-day bid decision. Retrieval manifests carried that quarantine as the string
`requires_pre_auction_timing_validation`, and nothing in the repository could turn the string
into a pass or a fail. The exclusion therefore rested on nobody forgetting it — the weakest form
a modeling invariant can take in a project whose other invariants are executable.

## What the audit does

It reads ADMIE retrieval manifests the existing client already writes and answers one question
per filetype and delivery day: was a file published strictly before that day's declared
day-ahead gate closure?

Every requested filetype is audited over every day of the window, so a day no record covers is
reported as `no_record` rather than passing silently. A file covering several delivery days is
judged separately for each of them, so a monthly publication is late for the days already
delivered and early for the rest.

## The gate closure is declared, never assumed

There is no default closure time and no built-in constant. A schedule is one or more dated
regimes, each declaring a day offset from delivery, a local time, the clock that time is stated
on, and a required reference to the market rule it comes from.

A built-in constant was rejected deliberately. It would be invisible in the evidence file, could
not express a rule change across a history that starts in November 2020, and would make an
unverified assumption look like a validated one. The repository can compare a timestamp against a
declared rule; it cannot verify the rule. `config/admie_gate_closure.example.json` therefore ships
the format with a placeholder reference that must be replaced before use, and the audit summary
records the schedule it was given.

Two refusals keep the declaration exact:

- a delivery day earlier than the first declared regime is refused, rather than audited against a
  rule that was not in force for it;
- a closure resolving to a local time that does not exist, or exists twice, on a daylight-saving
  transition day is refused rather than resolved by a convention.

## Evidence is graded, and the grades do not merge

`file_published` is provider metadata read at retrieval time — what ADMIE says today about the
past, not an observation of when a file became reachable. A restated or backdated timestamp
would be believed.

When the retrieval itself happened before the closure of the day in question, the catalog entry is
a contemporaneous witness that the file existed by then. The audit records `witnessed_pre_gate`
and `asserted_pre_gate` separately on every observation (`evidence_strength`) and in the summary
(`evidence_basis`), and never promotes the weaker to the stronger. Both count as accepted for
timing; only one is independent of the publisher's own record.

This is why the workflow is worth dispatching before a delivery day as well as over history. A
historical run establishes asserted compliance for a whole window in one pass; each pre-closure
run adds one witnessed day that no retrospective query can reproduce.

A publication exactly at the closure instant counts as late. A tie is not evidence of availability
before the decision, and the conservative reading is the one that cannot manufacture skill.

## The decision-time revision

For each accepted day the audit names the latest revision published strictly before closure —
its URL, revision number, publication time and lead in minutes — and counts the revisions that
superseded it afterwards.

This is the audit's operative caution rather than a detail. Reading "the published file" for a
past delivery day ordinarily returns the provider's latest revision, which is post-decision
information even on a day that passes on timing. A feature built from these files must read the
decision-time revision by URL. Retrieval feeding the audit must therefore pass
`fetch-admie-files --all-revisions`: the default latest-revision selection is correct for a price
history and discards exactly the evidence this audit needs.

One ADMIE URL carrying two different digests across manifests is refused outright: that is a file
replaced in place, which no revision number records. So is one URL carrying two different
publication timestamps, which is a restated publication time. Either can change a verdict, and
keeping whichever copy was read first would hide it.

## What is refused rather than approximated

- A schedule with no regime, unordered regimes, two regimes on one effective day, a closure at or
  after the start of the delivery day, an undeclared clock, a missing reference, or any unknown
  configuration field.
- A record that is not an ADMIE record, is missing a required field, carries a naive publication
  or retrieval timestamp, claims publication after its own retrieval, or reverses its coverage.
- An empty or duplicated filetype request, and a reversed audit window.
- A manifest that is not an object with a `records` list.

## What passing does not establish

The summary states its own limits in its own output — `establishes_only_publication_timing`,
`does_not_establish` and `quarantine_lifted` — so a reader of the evidence file does not depend on
this report. Passing does not establish the file format, column schema or units of any audited
file; that the published values are the values a bidder observed; that any audited variable
carries forecasting skill; or that a file absent from the audited manifests was never published.

**Timing acceptance does not lift the forecast-feature quarantine.** Lifting it additionally
requires format acceptance against real files and a separate recorded decision.

## Test and validation evidence

`tests/test_admie_timing.py` adds 29 tests covering closure resolution on the declared clock
across both DST regimes, regime selection and the pre-first-regime refusal, the daylight-saving
refusal, every schedule and record refusal, decision-time revision selection with a superseded
later revision, the witnessed-versus-asserted distinction, the at-closure tie, uncovered days,
per-day judgment of a multi-day file, filetype coverage, manifest de-duplication, the in-place
replacement and restated-timestamp refusals, integral revision export, and the CLI's `0`/`2`/`1` exit codes with its
written evidence files.

Ruff, mypy, the complete pytest suite and a clean wheel build pass. Exact command results are
recorded in the pull request.

## Roadmap consequence

`PLAN.md` keeps the ADMIE acceptance item open and now names its remaining parts: the operator's
declared gate-closure schedule, a live audited window recorded as evidence, and file-format
acceptance. v0.8 remains gated on explicit user design approval and is untouched by this
milestone.
