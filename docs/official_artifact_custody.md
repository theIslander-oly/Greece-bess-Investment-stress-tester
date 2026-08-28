# Durable custody of accepted official artifacts — 27 August 2026

## Why this procedure exists

The accepted official Greek DAM history exists only as a private GitHub Actions artifact
with a finite retention. Official data may not be committed to Git (decision entry
2026-08-26), so the repository cannot hold the history itself, and the artifact will expire.
Without a documented custody procedure an accepted acceptance baseline simply evaporates.

Re-running the retrieval workflow is a fallback, not the plan. HEnEx replaces publications:
the superseded 16 December 2020 workbooks corrected by `v03` are the precedent already
recorded in this repository. A re-retrieval is therefore **not reproducible in principle**,
and without a fingerprint a provider revision would silently replace an accepted baseline.

So two things must survive, and they live in different places:

| What survives | Where it lives | Why there |
|---|---|---|
| The artifact bytes | Private, encrypted, outside Git | Official data must not enter Git |
| The fingerprint of those bytes | Committed in `docs/custody/` | Lets any future copy be proven, or shown to differ |

## What is under custody

| Artifact | Run | Size | Published digest | Original expiry |
|---|---|---:|---|---|
| `greek-dam-official-history` | `32971677163` | 1,293,875 B | `sha256:127915bc…4b198` | 2026-09-02 13:07Z |
| `henex-entsoe-reconciliation` | `33073631530` | 1,648,760 B | `sha256:bee557ea…3b816a` | 2026-09-03 12:50Z |

The first holds the 74,663-interval accepted history. The second holds the interval-level
ENTSO-E series and cross-source comparison behind the passed reconciliation, and is what
records the ENTSO-E retrieval metadata that the acceptance track still lists as outstanding.

The digests above are the ones GitHub publishes for each artifact archive through the
Actions API. The history digest is identical to the SHA-256 accepted in `DECISIONS.md` on
2026-08-26, so a download can be authenticated on arrival rather than trusted.

## The store

Accepted artifacts are to be stored as **encrypted assets attached to a release in this private
repository** (decision entry 2026-08-27). The committed custody records under `docs/custody/` are
fingerprints, not that store: they describe a copy, they are not one. The operator upload is not
verified complete in the repository record, and nothing in this repository reads live GitHub
release state, so custody is not recorded as complete and a record here should not be read as
evidence that a stored copy exists.

The assets are encrypted before upload with a key held by the operator. This matters: a
release asset is durable and easy to re-fetch, but an unencrypted one would place official
HEnEx and ENTSO-E data into a repository asset under redistribution terms this project has
not assessed. Encrypting first means the release carries ciphertext, so no official data is
redistributed, and the redistribution question does not arise at all.

The consequence is that **the encryption key becomes part of the custody chain**. A lost key
is a lost copy, and recovery then falls back to re-retrieval with the drift consequences
described below. Hold the key in a password manager, not beside the ciphertext, and never in
this repository.

## Operator procedure

These steps require repository and key access, so they are performed by the operator rather
than by any automation in this repository.

### 1. Download and authenticate

```bash
gh run download 32971677163 --name greek-dam-official-history --dir greek-dam-official-history
gh run download 33073631530 --name henex-entsoe-reconciliation --dir henex-entsoe-reconciliation
```

`gh run download` extracts the archive, so compare per-file digests against the committed
custody record rather than re-hashing a zip you no longer have:

```bash
greek-bess verify-custody greek-dam-official-history \
  --record docs/custody/greek-dam-official-history.json
```

Exit code `0` means the copy is the accepted artifact. Exit code `2` means it is not — stop
and read "When verification fails" below.

### 2. Encrypt

Using [age](https://age-encryption.org), with a key generated once and stored in a password
manager:

```bash
tar -czf greek-dam-official-history.tar.gz greek-dam-official-history
age -r "$AGE_RECIPIENT" -o greek-dam-official-history.tar.gz.age greek-dam-official-history.tar.gz
shred -u greek-dam-official-history.tar.gz
```

`gpg --encrypt` is equally acceptable. What matters is that the uploaded asset is ciphertext
and that the key is not stored with it.

### 3. Attach to a private release

```bash
gh release create official-history-2026-08-26 \
  --title "Accepted official Greek DAM history (run 32971677163)" \
  --notes "Encrypted custody copy. Fingerprint: docs/custody/greek-dam-official-history.json" \
  greek-dam-official-history.tar.gz.age
```

Keep the release notes free of prices, counts that could be mistaken for results, and any
token. The fingerprint lives in the repository; the release note only points at it.

### 4. Keep a second copy

One release is one failure domain. Keep at least one further encrypted copy under separate
control — an external disk or a private object store. Both copies hold ciphertext, so the
choice of location carries no redistribution question.

## Verification drill

Run the drill before any milestone that consumes the accepted history, and whenever the
store is moved or the key is rotated:

```bash
age -d -i "$AGE_KEYFILE" greek-dam-official-history.tar.gz.age | tar -xzf -
greek-bess verify-custody greek-dam-official-history \
  --record docs/custody/greek-dam-official-history.json \
  --report verification.json
```

The `Record official artifact custody` workflow runs the same verification inside Actions
against the source run's artifact, for as long as that artifact still exists. Once a custody
record is committed, that workflow verifies rather than records, and fails on any difference.

## What the custody record contains

A custody record holds no official price. It carries, for every file in the artifact, the
relative path, byte size and SHA-256; and for every file that parses as a canonical price
history, content-level invariants: interval count, first and last interval, market-day count,
negative, zero and missing price counts, interval counts by delivery year, resolution and
source, quality-flag counts by name, and a digest of the interval and price series itself.

That last digest is the load-bearing one. It is computed over the sorted
`(delivery_start_utc, delivery_end_utc, price)` triples with prices formatted at six fixed
decimals, so it is independent of CSV column order, file formatting and float repr. A file
re-exported by a different pandas version digests the same; a single revised cent does not.
Byte digests alone are insufficient here, and not only in theory: a one-cent revision changes
the SHA-256 while leaving the file's byte size identical.

Missing prices digest as an empty field and are never replaced by a substituted number, and
`-0.0` is normalized to `0.0` so that a signed zero cannot produce a spurious difference.
Both follow the project's rule that zero and negative prices are preserved exactly.

## The recorded records, and how to read their counts

Both artifacts were recorded by run
[`33076229042`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33076229042).
GitHub verified each download against its published digest before the record was built, and
both matched the digests in the table above.

The fingerprints independently reproduce figures accepted earlier by separate exercises, which
is what makes them credible as a description of the accepted artifacts:

| Fingerprint | Value | Previously accepted as |
|---|---:|---|
| `henex_archived_prices.csv` intervals | 51,915 | v0.6.2 archive acceptance |
| `henex_daily_prices.csv` intervals | 22,748 | 2026 incremental acceptance |
| Both files combined | 74,663 | The accepted official history |
| `henex_mcp_rounding_consensus` flags | 980 | 2026-08-26 consensus bound |
| `entsoe_prices.csv` intervals | 74,663 | Reconciliation compared count |
| ENTSO-E negative / zero prices | 1,767 / 1,914 | Multi-year operational acceptance |
| `entsoe_variable_block_repeat` flags | 4,874 | The A03 curve-type correction |
| Market days | 2,124 | Multi-year operational acceptance |

**`interval_counts_by_delivery_year` counts on the market clock, not in UTC.** A delivery year
is the year of the interval's CET/CEST market-day start, which is the sense in which the Greek
DAM has delivery years at all. One consequence is worth stating so it is not misread as a
discrepancy: the custody records show **1,464** intervals for 2020, while
`docs/official_source_reconciliation_2026-08-27.md` shows **1,465** for the same data. The
reconciliation summary grouped by UTC year, which places the interval beginning
`2020-12-31T23:00Z` in 2020; on the market clock that interval is the first hour of market day
1 January 2021. 1,464 is exactly 61 days from 1 November to 31 December 2020 at 24 hours each.
Both counts describe the same intervals under different groupings, and neither is an error.

## When verification fails

A difference is a finding to investigate, never a check to re-run. Three causes are worth
separating:

1. **A corrupted or truncated copy.** Byte digests differ, the price-series digest differs,
   and the file often fails to parse. Re-fetch the copy from the other store.
2. **A revised official publication.** The copy parses cleanly, per-file digests differ, and
   the price-series digest differs on a re-retrieval rather than on a stored copy. This is
   the case the record exists to catch. Record it, identify the affected market days, and
   decide explicitly whether to accept a new baseline. Do not overwrite the committed record
   silently.
3. **A change in this project's own normalization.** Per-file digests differ and the
   price-series digest differs, but both differ for every historical artifact at once. The
   2026-08-27 ENTSO-E curve-type correction is exactly this class of change. Re-record with
   a decision entry explaining what changed and why the new normalization is correct.

## Deliberate exclusions

- No official price, and no data that could be reassembled into one, enters a custody record
  or a commit.
- Custody proves that a copy is the accepted artifact. It proves nothing about whether the
  accepted artifact is a good basis for any conclusion; the acceptance reports do that.
- Derived evidence this project computes from an already-custodied history is out of scope.
  The `annual-replay-decomposition` artifact of run `33147448666` is the worked case: it holds
  no interval-level price, has no provider that could revise it, and is fully determined by the
  custodied history, the pinned commit and the recorded configuration. It is guaranteed by
  reproduction, not by custody (decision entry 2026-08-28). Custody is for what cannot be
  reproduced.
- The procedure does not automate the upload. Encryption keys and release publication stay
  with the operator, so no automation in this repository holds a key that could decrypt an
  accepted artifact.
