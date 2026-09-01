# Replacement retrieval of the accepted official history — 1 September 2026

## Why this retrieval happened

The accepted `greek-dam-official-history` artifact from workflow run `32971677163` was created
on 26 August 2026 under the original seven-day artifact retention and was due to expire on
**2 September 2026 at 13:07:24 UTC**. The retention increase to 90 days does not apply
retroactively, so the accepted baseline had a dated expiry that no operator declaration could
lift. `PLAN.md` recorded this as the project's only hard deadline and the only open item the
repository could retire on its own.

This document records the replacement retrieval, the verification of the replacement against
the committed custody record, and the one finding that verification produced.

## What was retrieved

The replacement was produced by dispatching `Fetch official Greek market history` with the
**same inputs that produced the accepted baseline**, so that the comparison is like-for-like
rather than a comparison against a different requested range:

| Input | Value |
|---|---|
| `archive_start_year` | 2020 |
| `archive_end_year` | 2025 |
| `daily_start` | 2026-01-01 |
| `daily_end` | 2026-08-25 |

| | Accepted baseline | Replacement |
|---|---|---|
| Workflow run | `32971677163` | [`33483975614`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33483975614) |
| Head commit | `bf9e5d8` | `164557a` |
| Created | 2026-08-26 13:07:24Z | 2026-09-01 07:58:40Z |
| Expires | 2026-09-02 13:07:24Z | **2026-11-30 07:49:14Z** |
| Artifact id | `9608073418` | `9791289581` |
| Published archive digest | `sha256:127915bc…4b198` | `sha256:de30f4cc…e48009` |
| Archive size | 1,293,875 B | 1,294,916 B |

Both retrieval stages succeeded: the 2020-2025 annual archives in 3 m 23 s and the
1 January - 25 August 2026 daily range in 5 m 30 s.

## Verification against the committed custody record

Verification ran inside Actions as workflow run
[`33484823956`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33484823956),
which downloaded the replacement artifact, confirmed GitHub's published archive digest on
arrival, and ran `verify-custody` against `docs/custody/greek-dam-official-history.json`.

**The result was `difference_count: 4`, `verified: false`, and every one of the four
differences is a per-file byte digest. Not one content-level invariant differs.**

| Difference | Recorded | Observed |
|---|---|---|
| `archive_manifest.json` sha256 | `92d866f0…d361fd` | `fdbe48c2…a39a89` |
| `daily_manifest.json` sha256 | `ffa96b05…078579` | `de970e60…79ab41` |
| `henex_archived_prices.csv` sha256 | `9ac9fbe4…1e097d` | `2dc854a0…aa1616` |
| `henex_daily_prices.csv` sha256 | `1ebea398…5dba65c1` | `142d3950…190a293` |

### What did not differ, which is the load-bearing part

`verify_custody_record` reports every content-fingerprint field that differs, by name. It
reported none. For both price files the following are therefore identical to the committed
record:

- **`price_series_sha256`** — `f4698c15…694c31` for `henex_archived_prices.csv` and
  `f4ccb35e…1cd2e2` for `henex_daily_prices.csv`. This is the digest of the sorted
  `(delivery_start_utc, delivery_end_utc, price)` triples at six fixed decimals, so it is
  independent of CSV formatting and float repr. **The price series is unchanged, interval for
  interval.**
- Interval counts: 51,915 archived and 22,748 daily, 74,663 combined.
- First and last interval, market-day counts, and interval counts by delivery year, by
  resolution and by source.
- Negative, zero and missing price counts: 196 / 415 / 0 archived and 1,571 / 1,499 / 0 daily.
- Quality-flag counts by name, including the 980 `henex_mcp_rounding_consensus` flags.

Two further observations corroborate this. **No file changed size** — the recorded and observed
`size_bytes` match for all six files, which is what a fixed-width timestamp substitution
produces and what a revised price would not reliably produce. And both
`*.quality.json` reports are **byte-identical** to the accepted ones; they carry counts and no
retrieval timestamp, so an unchanged byte digest there is independent evidence that the
underlying observations did not move.

### The finding: this is a fourth case, and the procedure does not name it

`docs/official_artifact_custody.md` lists three causes for a verification difference: a
corrupted copy, a revised official publication, or a change in this project's own
normalization. **This difference is none of them.** It is a faithful re-retrieval of unchanged
official data, and it is not avoidable:

- `retrieved_at_utc` is a canonical column (`data/schema.py`), so **every** re-retrieval writes
  a different byte into every row of both price CSVs and changes their digests.
- The retrieval manifests record per-file retrieval timestamps, so they change for the same
  reason.

The consequence matters for anyone reading a future verification: **for a re-retrieval, the
per-file digests carry no information and only the content fingerprints are diagnostic.** The
procedure's tests for cases 2 and 3 both lean on per-file digests, so as written they would
lead a reader to classify this run as a possible provider revision. The fourth case is now
recorded in that document.

A revised publication was independently unlikely here for a second reason: normalization has
not changed since the accepted run either. The only data-layer edit to `data/henex.py` between
`bf9e5d8` and `164557a` is `pd.Timedelta(minutes=N)` to `pd.Timedelta(N, unit="min")`, which is
behaviourally identical, and `data/schema.py` only gained new functions. So neither the input
nor the transformation moved.

## What was not done, and why

**The committed custody record was not replaced.** `docs/custody/greek-dam-official-history.json`
still names `source_run_id` `32971677163` and still carries that artifact's per-file digests.
Replacing a record is a decision that belongs in `DECISIONS.md` (`docs/custody/README.md`), and
the record remains correct in the part that describes the data: every content fingerprint in it
verifies against the replacement.

This does leave a known and dated consequence, recorded here rather than resolved silently:
**once the `32971677163` artifact expires on 2 September 2026, no obtainable copy will match the
committed per-file digests, so `verify-custody` will return exit code 2 on every future run
against the replacement.** Three responses are available and the choice is the operator's:

1. Re-record against run `33483975614` with a decision entry, accepting that per-file digests
   describe the replacement from then on.
2. Keep the record as the fingerprint of the originally accepted artifact and read the four
   expected differences as such.
3. Change what a custody record compares, so that provenance-only columns are separated from the
   data they annotate.

Nothing here chooses between them, and the `Record official artifact custody` workflow still
defaults its `history_run_id` to the expiring run `32971677163`; updating that default is part
of whichever response is chosen.

## Incidental result: the reconciliation artifact

The same verification run also re-verified `henex-entsoe-reconciliation` from run
`33073631530`. The workflow's `if` condition tests a defaulted variable, so an empty
`reconciliation_run_id` input falls back to the default rather than skipping the step. That
artifact verified with **`difference_count: 0`** — it was downloaded rather than re-retrieved,
so its bytes are the accepted bytes. Its own expiry, 3 September 2026, is unaffected by this
work and the encrypted operator upload for it remains outstanding.

## Standing exclusions

This is data-acceptance evidence about retrieval and custody. It establishes no market, dispatch
or financial result, revises no accepted figure, and changes no analytical behaviour. The
replacement artifact holds the same accepted history the previously recorded acceptances
describe, and every interpretation limit recorded in `LIMITATIONS.md` continues to apply
unchanged.
