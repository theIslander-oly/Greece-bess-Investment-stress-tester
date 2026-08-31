# ADMIE pre-auction publication-timing policy — 31 August 2026

## The problem this policy exists to solve

ADMIE publishes day-ahead load and RES forecasts that look like ideal features for a
day-ahead price model. The 2026-08-26 decision quarantined them: they are retrieved and
timestamped, but never parsed into features, until their publication sequence is proven to
precede the target-day bid decision. A variable that was published *after* the decision point
is not a forecast input; using one produces a backtest that quietly knows the future and an
apparent skill that cannot be reproduced in operation.

Until now that quarantine was an assertion. Retrieval manifests carried the label
`requires_pre_auction_timing_validation`, and nothing in the repository could turn it into a
pass or a fail. `audit-admie-publication-timing` is that missing step. It reads retrieval
manifests the ADMIE client already writes, and answers one question for every delivery day:
was a file published strictly before that day's gate closure, and how strong is the evidence
that it was.

## The gate closure is declared, not assumed

The audit has **no default closure time and no built-in constant**. A closure time is a market
rule, and a rule can change over a history that starts in November 2020. A schedule is
therefore one or more dated regimes:

```json
{
  "schedule_id": "greek-dam-gate-closure",
  "regimes": [
    {
      "effective_from_delivery_day": "2020-11-01",
      "closure_day_offset": -1,
      "closure_local_time": "12:00:00",
      "closure_timezone": "Europe/Athens",
      "reference": "<rulebook section and effective dates>"
    }
  ]
}
```

- `closure_day_offset` counts days from the delivery day and must not be positive.
- `closure_local_time` is naive; `closure_timezone` names the clock it is stated on
  (`Europe/Athens`, `Europe/Brussels` or `UTC`), so a summer closure and a winter closure
  resolve to different UTC instants without anyone converting by hand.
- `reference` is required. An accepted delivery day carries the rule that accepted it.
- A regime that resolves to a local time that does not exist, or exists twice, on a
  daylight-saving transition day is refused rather than guessed.
- A delivery day earlier than the first regime is refused. A day is never audited against a
  rule that was not declared for it.

`config/admie_gate_closure.example.json` shows the format. Its `reference` is a placeholder
that must be replaced before the file is used: the repository does not declare the market rule
on the operator's behalf, and the audit cannot check a declaration against the rulebook. It
reports whatever closure it is given.

## What each verdict means

The unit of judgment is one **filetype and delivery day**. Every requested filetype is audited
over every day of the window, so a day that no file covers is a reported gap rather than a
silent absence.

| Day status | Meaning |
|---|---|
| `witnessed_pre_gate` | A file was published before closure **and** a retrieval before that closure observed it in the catalog. |
| `asserted_pre_gate` | A file's publication timestamp precedes closure, but every retrieval happened afterwards. |
| `no_pre_gate_publication` | Files cover the day, and all of them were published at or after closure. |
| `no_record` | No supplied manifest record covers the day. |

A run is `timing_accepted` only when every audited filetype and day is `witnessed_pre_gate` or
`asserted_pre_gate`. The command exits `2` on any other outcome, in the same way as the
existing quality and reconciliation commands, so a workflow can record a finding without
crashing.

**A publication exactly at the closure instant counts as late.** A tie is not evidence of
availability before the decision, and the conservative reading is the one that cannot
manufacture skill.

## Asserted is weaker than witnessed, and stays weaker

`file_published` is provider metadata read at retrieval time. It is what ADMIE says today
about the past — not an independent observation of when the file became reachable. A publisher
that restates a timestamp, or backdates one during a site migration, would be believed.

When the retrieval itself happened before the closure of the day in question, the catalog
entry is a contemporaneous witness: the file demonstrably existed by then, whatever its
metadata says. The audit records the two separately on every row (`evidence_strength`) and in
the summary (`evidence_basis`), and never promotes one to the other.

This is why the audit is worth dispatching *before* a delivery day as well as after one.
Running it over history establishes asserted compliance across six years in a single pass.
Running it the day before delivery adds one witnessed day, and repeated runs accumulate a body
of witnessed evidence that no retrospective query can produce.

## The decision-time revision is the only usable one

ADMIE republishes forecasts as numbered revisions. For each delivery day the audit names the
**decision-time revision**: the latest revision published strictly before closure, with its
URL, publication time and lead in minutes. Every later revision is post-decision information.

The count of those later revisions is reported per day as
`superseded_after_gate_closure_count`, and it is the audit's most important caution. A day can
be fully accepted on timing and still produce a leaking backtest, because reading "the
published file" for that day ordinarily means reading the provider's latest revision. A
feature built from these files must read the decision-time revision by URL. Retrieval must
therefore use `fetch-admie-files --all-revisions`; the default latest-revision selection is
correct for a price history and wrong for this audit, because it discards exactly the evidence
that shows a revision was superseded.

The same URL appearing in two manifests with two different digests is refused outright: that is
a file replaced in place, which no revision number records. So is the same URL appearing with two
different publication timestamps, which is a restated publication time. Either can change a
verdict, and keeping whichever copy was read first would hide it.

## What passing this audit does not establish

Acceptance here is about timing and nothing else. The summary carries the exclusion in its own
output (`establishes_only_publication_timing`, `does_not_establish`, `quarantine_lifted`), so a
reader of the evidence file sees it without consulting this document. Passing does **not**
establish:

- the file format, column schema or units of any audited file;
- that the published values are the values a bidder observed;
- that any audited variable carries forecasting skill;
- that a file absent from the audited manifests was never published.

**Timing acceptance does not lift the forecast-feature quarantine on its own.** Lifting it
additionally requires format acceptance against real files, and a recorded decision. Until
both exist, `PLAN.md` keeps the ADMIE acceptance item open and no ADMIE field enters a
forecast.

## Running it

The `Audit ADMIE publication timing` workflow retrieves every revision covering a declared
window and runs the audit against the committed gate-closure schedule, uploading the manifest,
the per-day verdicts, the per-observation evidence and the summary for 90 days. Locally:

```bash
greek-bess audit-admie-publication-timing data/raw/admie/retrieval_manifest.json \
  --gate-closure config/admie_gate_closure.json \
  --filetypes DayAheadLoadForecast DayAheadRESForecast \
  --start-day 2026-08-01 --end-day 2026-08-25 \
  --output acceptance/admie/delivery_days.csv
```

The window is retrieved before it is audited, so a multi-year window downloads a file per
filetype per day. Audit the history in slices rather than in one request.
