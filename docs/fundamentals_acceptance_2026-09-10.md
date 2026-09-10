# Fundamentals data acceptance — 10 September 2026

## Scope and interpretation

- **Acceptance verdict: `accepted`.**
- Scope: suitability of the declared point-in-time feature table for the registered v0.9 benchmark
  only.
- This acceptance establishes data suitability only. It establishes neither forecast skill,
  investment value, expected revenue, future format stability, financial advice, a bankable
  forecast, nor an investment-grade study. It is not a result and predicts nothing about one.
- Nothing in this document is filled, interpolated, backdated or repaired. Every day the audit
  could not admit is named and counted below.

## Workflow run and artifact identity

| Field | Evidence |
| --- | --- |
| Retrieval | `Fetch point-in-time fundamentals` run [`34476720910`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34476720910) at commit `c4c4a52`; 23 slices, every job succeeded |
| Combination | Same workflow, run [`34503398871`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34503398871) at commit `2fe1f81`, `shards_from_run_id=34476720910`; the 23 retrieved slices recombined, nothing re-retrieved |
| Preflight | `Preflight point-in-time fundamentals acceptance` run [`34519415488`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/34519415488) at commit `8de678f`, superseding run `34503999540` at `2fe1f81` after the cutoff correction below |
| Private artifact / published digest | `point-in-time-fundamentals`, artifact ID `10162918335`, 35,864,973 B archived; `sha256:3d988aba2b003f43f735fb5b935c9779670cda299b4fc6cc6758f52565dbe74b`; expires 9 December 2026 |
| Retrieval window / parser version | 2021-02-27 to 2026-08-25; NOAA GFS 0.25°, 00 UTC cycle of D-1; feature-semantics version 2 with per-message receipt times (the stage 2 and stage 3 corrections) |
| Source attribution | NOAA Global Forecast System 0.25 degree product, retrieved from the NOAA Open Data Dissemination archive on Amazon S3. Values reported by this project are derived from that product and are not unaltered NOAA data; NOAA does not endorse this project or its results. |

## Identity digests

| Input | SHA-256 or stable identifier |
| --- | --- |
| Accepted official price history | `greek-dam-official-history` from run `33483975614`, published digest `de30f4cc5938751dc00b8f08c2dbdbf24e2b23910ce6e59a6ccb3ff1dce48009`; record `docs/custody/greek-dam-official-history.json` |
| Accepted feature table | Record `docs/custody/accepted-fundamentals-feature-table.json`: 7 files, 360,769,797 B |
| **Accepted feature set** | **`a718f46265678cf1e37c31fca439b9f2f03479901fe8f0ac126766431b99aefc`** |
| Decision-cutoff schedule | `config/decision_cutoff.json`, `greek-dam-gate-closure-2026-09-10`; `7f04024766a5169412c5e1c1ff773e92d7cd335455711d8d8246814f9cb2c4b0` |
| Decision lead | `config/decision_lead_minutes.txt`, 0 minutes; `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| Sampling geography | `config/fundamentals_geography.json`, `greek-wind-capacity-regions-2023-12-31`; `9bd6741b70a2ad594d2c6490c75df087f4be247fca2ea073181be833a207d84f` |
| Benchmark configuration | Fixed in `.github/workflows/benchmark-fundamentals.yml` at this commit: admitted grades `witnessed provider_declared`; `--price-regime-bands 0 50 100 200`; validation from 2024-10-01; test from 2025-10-01; battery `examples/battery_50mw_100mwh.json` (`c9156ef29f9e364d84cf1d74fb32c789c0ff612180b47d7a43f0c77d187079f2`); arms per `docs/fundamentals_matched_control_amendment_2026-09-10.md` |

The accepted feature set is the digest a benchmark must declare. `Benchmark point-in-time
fundamentals` refuses to run unless the joined frame it builds digests to exactly this value and
this document names it.

## Acceptance findings

| Check | Verdict | Aggregate finding / evidence |
| --- | --- | --- |
| Retrieval and parser | pass | 23 slices, every retrieval job succeeded; 200,496 source documents traced by digest, byte count and URL in the retrieval manifest. Raw GRIB2 messages were not retained. Decoded parameter, unit, level, cycle, valid time, forecast step and averaging semantics are validated per message against the request and the index; a mismatch is a named refusal (stage 2). |
| Schema and provenance | pass | Combined in `--official` mode, which requires a retrieval manifest per slice and refuses any slice set that is not an exact tiling of the window. 2,005 built days + 1 excluded = 2,006 declared days, no overlap and no gap. The combined summary records every slice and its own retrieval instant. |
| Revisions and decision-time selection | pass | Revision-aware, whole-day-atomic as-of join: for each delivery day the latest revision published strictly before the declared closure minus the 0-minute lead is selected, and grade admission is applied after that selection. |
| Completeness and duplicates | pass with named exclusions | 144,357 feature rows over 2,005 built days. No duplicate delivery day; the tiling guard refuses one. Exclusions are enumerated below. |
| Units and ranges | pass | Unit identity is enforced at decode: `dswrf_surface` in W m⁻², `temperature_2m` in K, `wind_speed_10m` in m s⁻¹. Wind speed is the weighted mean of local point speeds, not the magnitude of separately weighted components; radiation is de-averaged per point before weighting (stage 2). |
| UTC, Greece/market views and DST | pass | Delivery intervals are validated by duration value against the declared resolution; the market-day partition is on the CET/CEST clock, and the joined price history spans 2,124 market days including 23- and 25-hour days. |
| Native resolution and hourly-to-quarter-hour broadcast | pass, recorded limitation | GFS values are hourly. From delivery day 2025-10-01 each hourly value is broadcast over four quarter-hour market intervals. The declarations record this regime-transfer limitation (section 4) and it travels with any result. |
| Publication time and strict cutoff | pass with findings | Evidence basis `provider_declared_publication_instants`. Minimum declared lead over accepted observations is 196.2 minutes. Three delivery days per variable are incomplete before the cutoff and one has no publication; all four are excluded by name, not filled. |
| Availability grade and quarantine | pass | 6,006 accepted variable-days, every one `provider_declared`; 0 `witnessed`; 0 `assumed`; 0 quarantined observations. |
| Exclusions | pass | 122 of 2,124 joined delivery days excluded by name, enumerated below. None is a transport fault in disguise: a day is excluded only on a condition the archive asserted, and an unanswered request fails the slice instead. |
| Custody, verification and encrypted copy | pass | Record run `34504032804`; verification run `34504409514` reported zero differences for the price history and the feature table; run `34504908065` verified both, encrypted them to the operator's recipient `age1ma3l0fx…` and published release `custody-2026-09-10`. |
| Primary-source support | pass with one correction | Nine publisher documents retained and cited with digests in `docs/primary_sources/README.md`. One contradicted the declaration and the declaration was corrected; see below. |

## Availability-grade counts

| Grade | Observation count | Delivery-day count | Admitted? |
| --- | ---: | ---: | --- |
| `witnessed` | 0 | 0 | yes |
| `provider_declared` | 144,357 retrieved; 6,006 accepted variable-days | 2,002 complete | yes |
| `assumed` | 0 | 0 | no; quarantine unless explicitly exploratory |

**No observation in this table is witnessed, and no later run can change that.** A witnessed
observation is one this project saw published before the cutoff at the time; a historic retrieval
cannot produce one. The daily witness workflow accumulates them going forward only.

## Structured exclusions

| Named cause | Day count | Affected span | Disposition |
| --- | ---: | --- | --- |
| `missing_observation` — before the first GFS-usable delivery day | 118 | 2020-11-01 to 2021-02-26 | excluded; declared in the source assessment, no admitted GFS feature exists |
| `missing_observation` — provider published nothing (retrieval cause `sidecar_object_mismatch`) | 1 | 2022-12-01 | excluded |
| `late_publication` — incomplete before the declared cutoff | 3 | 2021-03-23, 2021-06-15, 2022-01-18 | excluded |
| `inadmissible_grade` | 0 | — | — |
| `revision_conflict` | 0 | — | — |
| `duplicate_conflict` | 0 | — | — |
| `unit_or_range_failure` | 0 | — | — |
| `resolution_or_dst_failure` | 0 | — | — |

Total excluded: 122 delivery days. Complete: 2,002. Joined: 2,124.

## Complete-season classification

| Item | Value |
| --- | --- |
| Season | DJF 2025-26, 1 December 2025 to 28 February 2026 |
| Days in season | 90 |
| Days not common | 0 |
| **Exploratory** | **false** |

The predeclared rule is "exploratory unless every day of one complete meteorological season is
common" (declarations, section 5). Every one of the 90 winter days is common, so the rule does not
require the exploratory label. **This is a coverage classification decided before any result
exists.** It says nothing about skill, and it does not make a future result general beyond the
declared window and the recorded limitations.

## Declarations, and the correction this acceptance forced

The declared inputs are those of 3 September 2026
(`docs/fundamentals_declarations_2026-09-03.md`), with one correction made before any benchmark
run and required by that declaration's own terms.

**The cutoff correction.** The 3 September declaration set two regimes: 12:00 Europe/Athens on
D-1 for delivery days from 2020-11-01, and 12:00 Europe/Brussels from 2020-12-16. It called the
isolated-period value the weakest element and required that, if the retained primary text
contradicted it, the declaration be corrected before any test run. The retained HEnEx Decision 10
of 20 October 2020 — the day-ahead timeline in force at the 1 November 2020 launch — states "The
Day-Ahead Market Gate Closure Time" at 12:00 (CET) / 13:00 (EET) on D-1, one hour later than
declared, and its September 2021 and March 2026 successors state the same. One regime is now
declared, 12:00 Europe/Brussels from 2020-11-01, under the id `greek-dam-gate-closure-2026-09-10`.
The correction affects only delivery days before 2020-12-16, none of which carries an admitted
feature, and the re-run preflight reproduced the accepted feature-set digest unchanged
(`DECISIONS.md`, 2026-09-10; `docs/primary_sources/README.md`, document 8).

**What the retained text supports.**

| Declared element | Primary source | Verdict |
| --- | --- | --- |
| Geography: 2,293 / 639 / 534 MW at 31 December 2023, renormalised | HWEA/ELETAEN Wind Energy Statistics 2023 | confirmed exactly |
| Closure 12:00 CET/CEST on D-1 from 2020-11-01 | HEnEx Decision 10 of 20 Oct 2020, 20 Sep 2021, 31 Mar 2026 | confirmed after correction |
| Coupling from delivery day 2020-12-16 | NEMO Committee notice of 15 Dec 2020; RAE Decision 1574/2020 | confirmed |
| 15-minute market time unit from 2025-10-01, gate unchanged | SDAC notices of 12 Sep and 7 Oct 2025 | confirmed |
| Decision lead of 0 minutes | none | an operator choice, not a published rule |

**Recorded limitations that travel with any result built on this feature set.**

1. **The geography is a wind-capacity weighting applied to irradiance and temperature as well**,
   because the v0.9 fetch contract admits one common geography per run. It is not a solar-capacity,
   demand, population or area weighting. This is a recorded limitation, not an oversight.
2. Three grid nodes represent three regions. Selecting a node is not a claim that one node
   resolves the meteorology of a region.
3. A zero-minute decision lead models a decision taken at the gate. It does not claim a real
   bidder needs no time to forecast, optimise, submit or correct an order.
4. Model selection happens entirely on hourly delivery days and evaluation entirely on
   quarter-hour ones; each hourly GFS value is broadcast over four intervals in the test block.
5. Every admitted observation is `provider_declared`, not `witnessed`. The evidence is that the
   provider states it published before the cutoff, not that this project saw it do so.
6. The HWEA statistics carry the publisher's own caveat that it does not guarantee their accuracy.
7. HEnEx Decision 10 of 20 October 2020 describes the coupled procedure; whether every step of it
   was exercised during the six isolated weeks is not settled by the text, and no admitted feature
   falls in that period.

## Custody conclusion

The feature table is fingerprinted in `docs/custody/accepted-fundamentals-feature-table.json`,
committed as the tooling emitted it, and verified with zero differences by the push-triggered run
`34504409514`. Its record holds per-file byte digests only: no file in the artifact is a canonical
price history, so the content-fingerprint section is empty by construction. An encrypted copy is
attached to release `custody-2026-09-10`
(`accepted-fundamentals-feature-table.tar.gz.age`, 37,800,815 B, ciphertext digest
`c7b0f2b5…0ac831`). The operator still owes the second copy under separate control and the
decryption drill against this release, as recorded in `docs/official_artifact_custody.md`.

## Reproduction

```bash
# 1. Combination from the retrieved slices — Fetch point-in-time fundamentals
#    start_day=2021-02-27  end_day=2026-08-25  days_per_shard=90
#    variables="dswrf_surface temperature_2m wind_speed_10m"
#    geography_config=config/fundamentals_geography.json
#    decision_cutoff_config=config/decision_cutoff.json  decision_lead_minutes=0
#    fail_on_finding=false  shards_from_run_id=34476720910

# 2. Custody — Record official artifact custody
#    history_run_id=33483975614  reconciliation_run_id=""  feature_run_id=34503398871
#    feature_digest=3d988aba2b003f43f735fb5b935c9779670cda299b4fc6cc6758f52565dbe74b
#    record_mode=auto

# 3. Encrypted copies — Publish encrypted custody copies
#    age_recipient=age1ma3l0fx…  release_tag=custody-2026-09-10
#    history_run_id=33483975614  reconciliation_run_id=""  feature_run_id=34503398871

# 4. Preflight — Preflight point-in-time fundamentals acceptance
#    history_run_id=33483975614  feature_run_id=34503398871
#    start_day=2021-02-27  end_day=2026-08-25

# Verify the retained feature table against its committed custody record:
greek-bess verify-custody accepted-fundamentals-feature-table \
  --record docs/custody/accepted-fundamentals-feature-table.json
```

## What this acceptance permits, and what it does not

It permits one thing: dispatching `Benchmark point-in-time fundamentals` against the accepted
feature-set digest named above, with the declared arms, bands, split and battery. The result of
that benchmark is to be committed whichever way it goes. Favourable performance is not an
acceptance criterion and was not used as one here: no benchmark had been run when this document
was written, and no forecast, margin or cash flow had been computed from this feature set.
