# Fundamentals source assessment — 2 September 2026

**Status:** the v0.9.0 source-selection spike, run and recorded. This document converts the
external facts that `docs/v0.9_design.md` Section 3 labels `[Inference]` into `[Verified]` facts
or `[Unknown]` items with a named closing step, and it is the evidence behind the dated decision
that names the v0.9 fundamentals source.

**What this document is not.** It is not a data-acceptance document. Nothing here is an accepted
feature table, and no figure in it enters a model, a manifest or a report. Section 7 of the design
governs acceptance and comes later, at v0.9.1 and v0.9.5. Nor does it declare a decision cutoff:
the cutoff and the decision lead remain operator declarations the repository refuses to supply,
and the cutoff used below for sensitivity arithmetic is explicitly illustrative.

---

## 1. Outcome

| Gate | Result | Where |
|---|---|---|
| Archive coverage across 2021-2026 | **Pass, with a correction to the usable start date** | §4 |
| Byte-range subsetting through the `.idx` sidecars | **Pass** | §5 |
| A pip-installable ecCodes binding passing the four gates on 3.12 and 3.13 | **Pass** | §6 |
| Licence text | **Pass, text captured verbatim** | §7 |

The first three are the checks `v0.9_design.md:146` makes the source choice conditional on; the
licence is the fourth item `PLAN.md` requires of this spike.

**G0 is not triggered.** The primary candidate passes every check the design made the source
choice conditional on, so the EEX EU ETS fallback is not selected. Its own external facts remain
unverified (§8) — the design selects the fallback only on a primary failure, and this spike did
not produce one. If the primary later fails in implementation, the fallback needs its own spike
before it may be adopted; it may not be reached for silently.

**Decision this supports:** adopt NOAA GFS 0.25° forecast vintages from the AWS Open Data archive
as the single v0.9 fundamentals source, restricted to delivery days from 27 February 2021 onward,
with `s3_last_modified` as the `provider_declared` availability instant and the witness workflow
adding `witnessed` days from v0.9.1 forward. Recorded as the decision entry of 2 September 2026.

---

## 2. Method and environment

Every check below was performed from the development environment against the live public archive.
The archive probes used only the Python standard library and `curl`; the decoder gate of §6
installed the binding under test into throwaway virtual environments, which is the point of that
gate. The probes were throwaway scripts, not merged:
v0.9.0 adds no source code, and §9 records each probe precisely enough to re-run it.

**A correction to `PLAN.md`.** The plan stated that live endpoints are reachable only from Actions
runners and that this spike therefore had to be a workflow dispatch. That is true of
`www.admie.gr`, which the egress policy refuses, and it is not true of this source.
`noaa-gfs-bdp-pds.s3.amazonaws.com`, `pypi.org` and `raw.githubusercontent.com` are all reachable
from a working checkout, so the spike ran locally and the plan is corrected rather than the
finding being deferred. The same policy did refuse `www.eex.com`, `eur-lex.europa.eu`,
`data.ecmwf.int`, `archive-api.open-meteo.com` and `registry.opendata.aws`, which is why §8
carries the unknowns it does.

**Interpreters.** The four gates ran on CPython 3.12.3 and 3.13.12 installed in this environment,
not on the `actions/setup-python` images the CI matrix uses. That residual is named in §8 and is
closed by CI itself the moment the dependency is declared, which happens in v0.9.1.

**The illustrative cutoff.** Where this document reports how much margin a publication had, it
compares against 12:00 `Europe/Brussels` on the cycle day. That instant is used because the design
already names it as widely reported context (`v0.9_design.md:156`), and it is used here only to
show the *size* of the margin. It is not a declaration, nothing is accepted against it, and every
v0.9 surface will still require `--decision-cutoff` with a real rulebook citation (G3).

---

## 3. What the archive holds

`[Verified]` The bucket `noaa-gfs-bdp-pds` serves anonymous HTTPS `GET`, `HEAD`, `Range` and
`ListObjectsV2` requests with no credential. Each GFS cycle lives under a key carrying the cycle
date and hour, and the 0.25° pressure-level product carries a `.idx` sidecar per forecast step:

- `gfs.YYYYMMDD/HH/atmos/gfs.tHHz.pgrb2.0p25.fFFF` from 23 March 2021 onward, and
- `gfs.YYYYMMDD/HH/gfs.tHHz.pgrb2.0p25.fFFF` before that date.

`[Verified]` The layout change on 23 March 2021 is a second key shape, not a second dataset: a
reader must try both prefixes for any day before April 2021. This was not in the design and is
recorded here because an ingestion client that hard-codes `atmos/` silently returns nothing for
the earliest 25 usable days rather than failing.

`[Verified]` Every one of the 69 probed monthly objects had its `.idx` sidecar present.

`[Verified]` All four proposed variables are present, one GRIB2 message each, in every step
inspected: `DSWRF:surface`, `UGRD:10 m above ground`, `VGRD:10 m above ground` and
`TMP:2 m above ground`.

`[Verified]` Objects carry `Last-Modified`, `ETag` and `Content-Length` on `HEAD`.

---

## 4. Gate 1 — archive coverage

### 4.1 The archive begins in 2021, and the *hourly* record begins later

`[Verified]` The earliest `gfs.*` prefix in the bucket is `gfs.20210101/`. A monthly probe of the
first of each month from November 2020 to September 2026 (71 days) found 69 objects; the two
misses are 1 November 2020 and 1 December 2020, both before the archive starts. So far this
matches the design.

`[Verified]` **The design's inference that the archive start costs "the first months" of the
accepted history understates it, because before 26 February 2021 the 0.25° product is 3-hourly.**
A step inventory of the whole cycle shows 129 forecast steps (`f000` to `f384` by 3) on
1 February 2021 against 209 steps (`f000` to `f120` hourly, then 3-hourly to `f384`) on
1 April 2021 and on 15 July 2026. In the step range a Greek delivery day needs — see §4.2 — that
is 9 steps against 26.

`[Verified]` A bisection over 1 February to 20 March 2021 pins the transition exactly: **25
February 2021 is the last 3-hourly day and 26 February 2021 is the first hourly day.** The
transition is not the same date as the key-layout change, and neither date can be inferred from
the other.

`[Verified]` Consequently the first delivery day that can carry hourly features is **27 February
2021** (from the 00 UTC cycle of 26 February). Against the accepted history's 2,131 delivery days
from 1 November 2020 to 1 September 2026, **118 days have no hourly feature and 2,013 do**. Those
118 days are disclosed and excluded by named cause; nothing is filled.

A coarser 3-hourly feature over the earliest window is *technically* admissible under the schema's
`broadcast_coarser_feature` relation (`v0.9_design.md:247`), and is deliberately not proposed. It
would change the definition of a feature part-way through the training window — the same column
meaning a 1-hour mean after February 2021 and a 3-hour mean before it — to recover 5.5% of the
record at the far end of the history, where the accepted price evidence is also thinnest. The
design's rule is that a day is complete or excluded, not padded, and 118 excluded days stated
plainly cost less than a column whose meaning depends on the date.

### 4.2 Which cycle and which steps a Greek delivery day needs

`[Verified]` A delivery day `D` in `Europe/Athens` spans 21:00 UTC on `D-1` to 21:00 UTC on `D`
in summer, and 22:00 to 22:00 in winter. From the 00 UTC cycle of `D-1` that is forecast steps
**21 through 46**, all of which exist hourly from 26 February 2021 onward, in one cycle, with all
four variables present. Steps `f021`, `f022`, `f045` and `f046` were checked directly. That range
covers both clock offsets and both DST transition days without widening — a 25-hour October day
spans steps 21 to 46 and a 23-hour March day spans 22 to 45 — and it covers a value read as an
instant at the interval start as well as one read as a mean over the interval ending at the step.

### 4.3 When the objects actually appear, and how much margin that leaves

`[Verified]` The upload lag of the 00 UTC cycle's `f048` object, measured as `Last-Modified` minus
the cycle instant:

| Sample | Days probed | Found | Lag: min / median / max |
|---|---|---|---|
| Daily, 2021-01-01 to 2021-06-30, excluding the re-upload window of §4.4 | 125 | 125 | 223.1 / 229.6 / **699.4** min |
| Weekly, 2021-07-04 to 2026-08-30 | 270 | 270 | 221.8 / 227.4 / 249.5 min |
| Daily, calendar 2025 | 365 | 365 | 223.4 / 230.1 / 246.4 min |

`[Verified]` The normal lag is between 3 h 41 m and 4 h 10 m. Against the illustrative 12:00
`Europe/Brussels` cutoff — 600 minutes after the 00 UTC cycle in summer, 660 in winter — the 00 UTC
cycle of `D-1` clears by roughly six hours, and **not one of the 365 days of 2025 failed**.

`[Verified]` **The 06 UTC cycle does not clear that margin and must not be used.** In the cycle
sample, `f048` of the 06 UTC cycle appeared at 10:00:22 UTC on 15 July 2025 — after 12:00 CEST,
which is 10:00 UTC. The design left the cycle unstated; this document fixes it at 00 UTC of `D-1`,
and any later cycle is a separate decision with its own evidence.

`[Verified]` **One genuinely late run exists in the sample.** On 14 June 2021 the 00 UTC `f048`
object appeared at 11:39:22 UTC, 1 h 39 m after the illustrative cutoff. Under the strict rule the
day is incomplete and excluded by named cause. This is the case that makes the difference between
the admissible grades concrete: a nominal-latency assumption of "about four hours" would have
admitted that day and been wrong, which is exactly why the `assumed` grade is quarantined.

`[Verified]` **Upload order is not monotone in forecast step.** On 1 August 2026 the 06 UTC cycle's
`f024` object appeared at 09:53:54 UTC and its `f048` object at 09:46:04 UTC — the later step
first. An availability audit may therefore not infer one step's availability from another's; every
required step is checked on its own, as the design's per-value audit table already requires.

`[Verified]` **One whole cycle is missing.** The 0.25° product for the 00 UTC cycle of
2 February 2021 is absent from the archive entirely — the prefix returns zero `pgrb2.0p25` keys,
while the 06 and 12 UTC cycles of the same day hold 130 `pgrb2.0p25` objects each. Falling back to an earlier cycle
that is still strictly before the cutoff is a legitimate design option; it is *not* taken silently.
Until a dated decision admits a fallback cycle rule, the day is excluded by named cause.

### 4.4 A restated-timestamp finding, and why it is safe

`[Verified]` Every one of the 55 daily probes in **1 January to 25 February 2021** — the whole
window bar 2 February, which is missing — carries a `Last-Modified` between 5 March and 30 April
2024, 1,107 to 1,215 days after its cycle. From 26 February 2021 onward every probed instant is
contemporaneous with its cycle. The re-uploaded window
coincides exactly with the 3-hourly window of §4.1, which is consistent with a later backfill of a
different product generation.

This is G7 ("a revision in-place replacement or restated timestamp is found") and it is recorded
rather than resolved by choosing a copy. It changes nothing about admissibility, for a reason worth
stating plainly:

> `[Inference]` `Last-Modified` is set when an object is written, so a re-upload can only move
> the recorded instant **later**. The `provider_declared` grade built on it can therefore under-claim
> availability — excluding a day that was in fact published on time — but it cannot over-claim it.
> The error direction is conservative, which is the direction a leakage control must fail in.

Those 55 days are excluded on availability grounds and the 56th, 2 February, on absence; all 56
are, independently, already outside the usable hourly record of §4.1, so this finding removes no
day that §4.1 had not removed already. No day is admitted because of it.

---

## 5. Gate 2 — byte-range subsetting

`[Verified]` For `gfs.20260715/00/atmos/gfs.t00z.pgrb2.0p25.f036`:

- the `.idx` sidecar is 41,260 bytes and 743 lines, one line per GRIB2 message, giving the message
  number, byte offset, cycle, variable, level and step;
- the four wanted variables resolve to exactly one message each;
- a `Range: bytes=461967658-462936171` request returns **HTTP 206** with
  `Content-Range: bytes 461967658-462936171/538649530` and 968,514 bytes;
- the returned bytes begin `GRIB` and end `7777`, and the length declared in the GRIB2 header
  equals the number of bytes retrieved, so the message is complete and self-framing;
- two independent retrievals of the same range produced the identical SHA-256
  `175439374684a7611c3a6fb34190aa9a6263476325759d61f18719dd51c94acd`.

`[Verified]` Message sizes and the volume this implies:

| Message | Bytes |
|---|---|
| `TMP:2 m above ground` | 520,745 |
| `UGRD:10 m above ground` | 984,195 |
| `VGRD:10 m above ground` | 956,245 |
| `DSWRF:surface` | 968,514 |
| **Four variables, one step** | **3,429,699 (3.27 MiB)** |

Against the 538,649,530-byte whole-step object that is a **157× reduction**. One delivery day is
26 steps, so **85.0 MiB transferred per delivery day** and **167 GiB across the 2,013 usable
days** — the design's "of the order of 10² GB" inference, confirmed. Without subsetting the same
history would be 25.6 TiB and the milestone would not be feasible on a runner; with it, a year of
delivery days is about 30 GiB, and the design's "slice by year" risk control is enough. Runner
throughput was not measured and is not claimed here.

`[Verified]` The object exposes an `ETag` (`"bfcb28ad71e5c1c0d68f414898ccb28c"` for the step
above) with no multipart suffix. This is recorded as an observation of one object and is **not**
adopted as the content identity: a multipart-uploaded object's ETag is not a digest of its
content, and nothing here establishes that every object in a five-year archive was uploaded the
same way. The schema's `raw_sha256` stays what it is — a digest this project computes over the
exact bytes it decoded.

`[Verified]` **Radiation is bucketed, and the buckets reset every six hours.** The `.idx` step
field states the averaging window directly: `f021` is `18-21 hour ave fcst`, `f024` is
`18-24 hour ave fcst`, `f025` is `24-25 hour ave fcst`, `f036` is `30-36 hour ave fcst`, `f037` is
`36-37 hour ave fcst`. So for a step `f = 6k + j` with `j ≥ 1` the message holds the mean over
`[6k, f]`, and the hourly mean over `(f−1, f]` is
`A_f·(f − 6k) − A_(f−1)·(f − 1 − 6k)`, which reduces to `A_f` when `f − 1 = 6k`. De-averaging is
therefore a stated arithmetic rule over two adjacent steps, verifiable from the sidecar without
decoding, and the design is right to treat getting it wrong as a parser-acceptance failure rather
than a detail. `TMP` and the wind components are `stepType = instant` and need no de-averaging.

---

## 6. Gate 3 — the decoder, on both interpreters

`[Verified]` `python -m pip install eccodes cfgrib` succeeds on 3.12 and 3.13 with no system
package and no compiler. The resolved set is `eccodes 2.48.0` (a pure-Python `py3-none-any`
binding) plus `eccodeslib 2.48.0.26` and `eckitlib 2.1.1.26`, which carry the ecCodes C library as
binary wheels, plus `findlibs`, `cffi` and `numpy`. The design's inference that "recent `eccodes`
wheels bundle the library" is verified in substance and corrected in detail: the binding wheel is
pure Python and the library arrives in a separate wheel that the binding depends on. On Linux
there is no `cpXXX` wheel of `eccodes` itself, so a reader checking wheel filenames alone would
wrongly conclude a source build is required.

`[Verified]` `codes_get_api_version()` reports `2.48.0` on both interpreters — the binding is
bound to the bundled library, not to a system ecCodes.

`[Verified]` Decoding the byte-ranged messages from §5 gives identical results on 3.12.3 and
3.13.12: `regular_ll`, `Ni = 1440`, `Nj = 721`, first grid point 90.0 N / 0.0 E, increments 0.25°
in both directions, 1,038,240 values per message. `DSWRF` decodes as
`Surface downward short-wave radiation flux` in `W m**-2` with `stepType = avg`,
`startStep = 30`, `endStep = 36`, and values `min 0.000 / max 960.928 / mean 165.144`. `TMP`
decodes as `2 metre temperature` in `K` with `stepType = instant` and
`min 197.811 / max 324.211 / mean 281.255`. Sampling three illustrative Greek grid points gives
834.048, 807.536 and 851.760 W m⁻² and 307.411, 308.111 and 301.511 K, bit-identical between the
two interpreters.

Those three points are arithmetic on a decoded grid, not a geography declaration. The sampling
points and their weights remain an operator declaration with no default
(`config/fundamentals_geography.example.json`).

`[Verified]` **The four gates pass with the decoder installed, on both interpreters.** The
dependency was installed into a virtual environment alongside `-e ".[dev]"` and the repository's
own validation commands were run unchanged:

| | 3.12.3 | 3.13.12 |
|---|---|---|
| `ruff check .` | All checks passed | All checks passed |
| `mypy` | no issues in 56 source files | no issues in 56 source files |
| `pytest` | 403 passed | 403 passed |
| `python -m build --wheel` | built | built |

`[Verified]` The dependency does not constrain the existing resolution: installing it alongside
`-e ".[dev]"` reported no conflict and resolved `numpy 2.5.2`, `pandas 2.3.3`, `scipy 1.18.1` and
`scikit-learn 1.9.0`, all inside the ranges `pyproject.toml` declares. The binding's own
requirements — `numpy`, `attrs`, `cffi`, `findlibs` and the two library wheels — carry no upper
bounds that could hold the existing stack back. `mypy` needs no new configuration because
`ignore_missing_imports` is already set, and the untyped binding raised no warning that the
project's `filterwarnings` gate would fail on.

`[Verified]` `cfgrib` installs cleanly but is not required: the low-level `eccodes` binding reads a
single message from a file object without `xarray`. v0.9.1 should declare `eccodes` alone and
leave `cfgrib` and `xarray` out, which is the smaller dependency and the one actually exercised
above.

---

## 7. Gate 4 — licence

`[Verified]` The AWS Open Data registry entry for this bucket
(`datasets/noaa-gfs-bdp-pds.yaml` in `awslabs/open-data-registry`, retrieved 2 September 2026)
states the licence as follows, quoted verbatim with the entry's HTML line breaks removed:

> NOAA data disseminated through NODD are open to the public and can be used as desired. NOAA
> makes data openly available to ensure maximum use of our data, and to spur and encourage
> exploration and innovation throughout the industry. NOAA requests attribution for the use or
> dissemination of unaltered NOAA data. However, it is not permissible to state or imply
> endorsement by or affiliation with NOAA. If you modify NOAA data, you may not state or imply
> that it is original, unaltered NOAA data.

`[Verified]` The entry names NOAA as the managing party and gives the update frequency as four
cycles a day from midnight UTC, consistent with the cycle structure observed in §4.

Three obligations follow, and each maps onto something the repository already has or the design
already requires: attribution to NOAA wherever a feature figure appears, which the manifest and
report contract carries today as a source label; no statement or implication of NOAA endorsement
or affiliation, which nothing here makes; and, because de-averaging and point sampling *are*
modification, no presentation of a derived feature as unaltered NOAA data, which the schema's
provenance columns and the `FUNDAMENTALS_FEATURE_PROVENANCE` sentence are specified to carry from
v0.9.1. None of the three is discharged by this document, because no NOAA-derived figure exists
yet; they are obligations v0.9.1 onward must meet, and they are named here so that meeting them is
not left to be noticed later.

`[Verified]` No credential, token, account or click-through is involved, so nothing about this
source touches the secret-handling constraints that hold `ENTSOE_SECURITY_TOKEN`-dependent work
shut.

`[Unknown]` The design also called the data "US Government work, public domain". The registry text
above is what the provider actually states and it is what this project relies on; the public-domain
characterisation is not repeated as a verified fact because no primary licence statement asserting
it was retrieved. Nothing in the plan depends on the difference — the registry text alone permits
the intended use under the three obligations above.

---

## 8. The inference ledger

Every `[Inference]` in Section 3 of the design, resolved:

| Design claim | Resolution |
|---|---|
| GFS: objects keyed by issue cycle, `.idx` sidecars allow byte-range retrieval | `[Verified]` §3, §5 |
| GFS: archive back to early 2021 | `[Verified]` first prefix `gfs.20210101/`; **but** the hourly record starts 2021-02-26 (§4.1) |
| GFS: 0.25° output is hourly to 120 h | `[Verified]` from 2021-02-26; 3-hourly before it (§4.1) |
| GFS: DSWRF, 10 m U/V, 2 m temperature present | `[Verified]` §3 |
| GFS: objects have an upload `Last-Modified` header | `[Verified]` §3; with the restated-timestamp window of §4.4 |
| GFS: archive start "leaves the first months" without features | `[Verified] with correction` — 118 delivery days, not the ~60 the archive start alone implies (§4.1) |
| GFS: radiation is time-averaged over reset buckets | `[Verified]` §5, with the de-averaging rule stated |
| GFS: raw volume of the order of 10² GB | `[Verified]` 167 GiB transferred across the usable history (§5) |
| GFS: recent `eccodes` wheels bundle the library | `[Verified] with correction` — the binding is pure Python and the library ships in `eccodeslib` (§6) |
| GFS: a decoder must be proven on the CI image for 3.12 and 3.13 | `[Verified]` on 3.12.3 and 3.13.12 locally; `[Unknown]` on the `actions/setup-python` images until v0.9.1's CI run (§2) |
| ENTSO-E (1-4): no per-datum publication history through the API | `[Unknown]` — not testable here; the token is unset and the endpoint was not exercised. Track B, and no part of v0.9 depends on it |
| Regulation (EU) 543/2013 Art. 6(1)(b) and 14(1)(d) deadlines | `[Unknown]` — `eur-lex.europa.eu` is refused by the egress policy. Track B only; the design's conclusion that a regulatory deadline can at best yield the quarantined `assumed` grade does not depend on the article numbers being right |
| ECMWF open data (9): archive from 2022, 0.4° until 2024 | `[Unknown]` — `data.ecmwf.int` refused. Not selected; not needed |
| Open-Meteo (10): historical forecast API from 2022 | `[Unknown]` — `archive-api.open-meteo.com` refused. Not selected; fallback-of-a-fallback at most |
| EEX (12): auctions clear late morning CET, results published shortly after | `[Unknown]` — `www.eex.com` refused. **The fallback is unassessed**; it is not selected because the primary passed, and it may not be adopted later without its own spike (§1) |
| Fuel (13): no free licensed primary daily TTF series | `[Unknown]` — unchanged, and quarantined by the design regardless |

**Residual unknowns that matter to the chosen source, and what closes each:**

1. *The decoder on the actual CI images.* Closed by the v0.9.1 CI run that first declares
   `eccodes` in `pyproject.toml`. If it fails there, the source choice returns to this document's
   G0 branch and the fallback needs the spike §8 says it has not had.
2. *Whether the archive persists.* Not closable by any check. Reproducibility of a v0.9 result
   rests on a third-party archive remaining available, and that is disclosed in the acceptance
   document and carried on every figure derived from it, exactly as the design requires.
3. *Whether restated timestamps or missing cycles occur outside the sampled days.* The samples
   here are 69 monthly, 365 daily for 2025, 181 daily for 2021 H1 and 270 weekly probes — not the
   2,013 usable days. The full audit is the point of `audit-feature-availability` at v0.9.1, which
   examines every required step of every delivery day and reports rather than assumes. This
   document establishes that the audit is feasible and that it will have real findings to report;
   it does not stand in for it.

---

## 9. Reproducing this

Each probe is a few lines against the public archive; none needs a credential.

```bash
# Archive start, and the two key layouts
curl -s "https://noaa-gfs-bdp-pds.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=gfs.20&max-keys=10"

# Presence and upload instant of one cycle's step (00 UTC cycle, step 48)
curl -sI "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20250715/00/atmos/gfs.t00z.pgrb2.0p25.f048"

# Step inventory for a cycle: 129 keys (3-hourly) before 2021-02-26, 209 (hourly to f120) after
curl -s "https://noaa-gfs-bdp-pds.s3.amazonaws.com/?list-type=2&max-keys=1000&prefix=gfs.20210201/00/gfs.t00z.pgrb2.0p25."
curl -s "https://noaa-gfs-bdp-pds.s3.amazonaws.com/?list-type=2&max-keys=1000&prefix=gfs.20210226/00/gfs.t00z.pgrb2.0p25."

# The sidecar, and one message by byte range
curl -s "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20260715/00/atmos/gfs.t00z.pgrb2.0p25.f036.idx" | grep -E ":(DSWRF:surface|TMP:2 m above ground):"
curl -s -r 461967658-462936171 "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20260715/00/atmos/gfs.t00z.pgrb2.0p25.f036" -o dswrf.grib2
python -c "import hashlib;b=open('dswrf.grib2','rb').read();print(len(b),b[:4],b[-4:],hashlib.sha256(b).hexdigest())"

# The decoder, on each interpreter
python -m pip install eccodes
python -c "import eccodes as e;f=open('dswrf.grib2','rb');g=e.codes_grib_new_from_file(f);print(e.codes_get(g,'name'),e.codes_get(g,'units'),e.codes_get(g,'stepType'),e.codes_get(g,'startStep'),e.codes_get(g,'endStep'),e.codes_get_values(g).mean())"

# The licence text
curl -s https://raw.githubusercontent.com/awslabs/open-data-registry/main/datasets/noaa-gfs-bdp-pds.yaml | grep '^License:'
```

The coverage, timing and step-inventory scans were the same requests in a loop over a date range;
their results are quoted in full above rather than committed as data, because the repository does
not store retrieved provider content.

---

## 10. What this changes in the design

`docs/v0.9_design.md` stays the design of record. Four things in it are now settled by evidence
rather than recommendation, and Section 3 carries a pointer to this document:

1. **The source is chosen.** NOAA GFS 0.25°, not "recommended, pending a spike". The EEX fallback
   is not selected and is unassessed.
2. **The cycle is fixed at 00 UTC of `D-1`,** which the design left open. The 06 UTC cycle is
   ruled out by an observed publication after a midday cutoff.
3. **The usable window starts at delivery day 2021-02-27,** not at the archive start, and 118
   delivery days of the accepted history carry no feature.
4. **Two ingestion facts are now requirements, not details:** both key layouts must be tried for
   days before April 2021, and availability must be checked per step, because upload order is not
   monotone in forecast step.

Nothing else moves. The cutoff and the decision lead remain undeclared and no v0.9 surface will
run without them (G3). The evidence grades are unchanged, and §4.3 supplies the concrete case that
justifies quarantining `assumed`. The 2026-09-01 removal of ADMIE load and RES forecasts from
scope is untouched: the chosen source has no ADMIE content by any route, and the ENTSO-E
candidates stay isolated as Track B with their own unknowns intact.
