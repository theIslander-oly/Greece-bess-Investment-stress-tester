# Implementation report v0.9.7 — three defects the first real retrieval exposed

**Date:** 4 September 2026

## What this milestone is

v0.9.6 made the declared window retrievable in principle: it removed a disk ceiling and tiled
forty hours of sequential retrieval into 23 parallel slices. On 4 September 2026 that plan was
dispatched against the real archive for the first time, over the full pre-registered window
2021-02-27..2026-08-25. It failed.

This milestone is what the failure showed. It changes no analytical result, retrieves no accepted
feature table and computes no benchmark figure. It removes three defects in how the retrieval
reads its source, in an order that matters.

## The measurement

Run `33843070945`, 23 slices of 90 delivery days. **Six of 23 slices failed on attempt 1 and four
on attempt 2** (slices 4, 7, 11 and 20), so the `combine` job was skipped and the run produced
nothing. The four surviving failures were four distinct events:

| Slice | Window | How it died |
| --- | --- | --- |
| 4 | 2022-02-22..2022-05-22 | `Official-data connection failed: [Errno 104] Connection reset by peer` |
| 7 | 2022-11-19..2023-02-16 | `The .idx sidecar describes an offset past the end of the object it indexes` |
| 11 | 2023-11-14..2024-02-11 | `http.client.IncompleteRead(504341 bytes read, 432836 more expected)`, as an uncaught traceback |
| 20 | 2026-02-01..2026-05-01 | `No 0.25° object for the 00 UTC cycle of 2026-04-17 at forecast step 42` |

Each of those ended 90 delivery days of retrieval. Slice 7 reproduced its sidecar mismatch
**identically on both attempts**, which makes it a property of the archive rather than a race.

## The three defects

### A. Absence and transport failure were indistinguishable

`head_https_headers` and `fetch_https_bytes` collapsed HTTP 404, HTTP 5xx and connection or TLS
failures into one untyped `OfficialDataDownloadError` carrying no status. The NOAA GFS client's
key-layout loop caught every one of them, tried the other archive key layout, and — when both had
been tried — raised

> No 0.25° object for the 00 UTC cycle of … both archive key layouts were tried … A missing cycle
> or step makes the delivery day incomplete and it is excluded by name

That sentence is a finding about the provider. It could be reached from two transient 503s.
Slice 20 died with exactly that message, and **nothing in the run records which of the two it
was.** Slice 11's `IncompleteRead` was worse: it is neither `HTTPError` nor `URLError`, so it
escaped the module entirely and reached the operator as a traceback.

Every failure now carries a **kind** — `absent`, `client_error`, `server_error`, `transport`,
`unsafe_request`, `unusable_response` — and the HTTP status when the server answered one. Only
`404` and `410` are absence. `head_step_object` moves to the second key layout on absence alone
and raises by name on anything else, because an unanswered request is not evidence about what the
provider published.

### B. There was no retry

The declared window is roughly **200,000 HTTPS round trips** issued with no retry of any kind, so
one reset discarded 90 delivery days. Transport faults and 5xx answers are now retried up to five
attempts with 1, 2, 4 and 8 second backoff — bounded at fifteen seconds for a request that never
succeeds.

Absence is never retried: it is an answer, and re-asking cannot change it. Neither is the `.idx`
sidecar mismatch, nor any other refusal this project makes deterministically. The retrieval stays
sequential: making it concurrent would change how an accepted evidence path talks to the provider,
which is a change to the evidence rather than to its schedule.

At the observed rates this is expected to remove slices 4 and 11 as failure modes outright. It
cannot rescue a genuine outage, and is not meant to.

### C. A source condition aborted the window instead of excluding one day

The refusals for a genuinely missing object and for a mismatched `.idx` sidecar both promised the
delivery day "is excluded by name" — but the exception propagated out of `run_fetch_fundamentals`
and killed the whole slice. Only `day < FIRST_HOURLY_DELIVERY_DAY` was ever actually recorded as
an exclusion. Slices 7 and 20 each lost 90 days to one delivery day's condition.

`fetch-fundamentals` now catches exactly two new causes — `missing_object` and
`sidecar_object_mismatch`, carried as a typed `cause` attribute on `NoaaGfsError` rather than
matched from message text — records the day in `excluded_days_by_cause`, and continues.

**Every other refusal still stops the retrieval.** A message on a different grid, an undecodable
message, a non-finite sample, an object with no publication instant, an unreadable sidecar, a
byte-range slice shorter than the sidecar declares: each is a statement about how a value would be
*built* by this client, not about what the provider published. An excluded day is recorded as a
provider non-publication inside a pre-registered benchmark window, so the set of conditions that
can produce one is closed and stated. Two of those refusals could arguably be assigned to the
sidecar mismatch, and are deliberately not: a short byte-range read and an empty sidecar cannot be
told apart from a truncated transfer. Erring toward aborting costs a re-run; erring the other way
writes a false finding about the source.

**C does not ship without A.** Without typed absence, a network blip would permanently exclude a
real delivery day from a pre-registered window, record it as a provider non-publication, and
nothing downstream could detect it. That is the one failure this milestone must not create while
fixing the ones it found.

## Accounting

The retrieval and combined summaries now carry `excluded_day_count_by_cause` beside the capped
`excluded_days_by_cause` list. The combined count is summed from each slice's own total rather
than recounted from its capped list, so an exclusion cannot become invisible in the aggregate.

## What was validated

Ruff, mypy over 65 source files, **625 tests** and a clean wheel build pass. Twenty-six new tests
cover the three fixes on synthetic fixtures only: the failure-kind vocabulary and its retry
consequences with `urllib.request.urlopen` replaced and the backoff sleeping into a list; a fake
archive that answers `404` for a key it does not hold and `503` for one it will not answer,
proving that a 5xx never becomes "no object at either layout"; the typed causes on both source
conditions and their absence on every other refusal; and the retrieval command itself excluding
one delivery day by name over a three-day window while retrieving the other two, aborting instead
on an unanswered request and on a grid change, and still refusing a window excluded in its
entirety rather than writing an empty table.

## What this milestone does not do

It retrieves no accepted feature table, records no availability finding against official data,
writes no custody record, produces no acceptance document and computes no benchmark figure. It
makes the first step of the official run capable of finishing; it does not perform the run.
Perfect foresight remains a labelled gross-margin upper bound, and every figure this repository
reports still comes from the accepted price history alone.
