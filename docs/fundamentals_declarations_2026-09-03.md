# The v0.9 operator declarations, and what they rest on — 3 September 2026

## Scope and interpretation

This document records the research behind the three declarations the v0.9 point-in-time
fundamentals path has refused to run without since v0.9.1, the price-regime bands the forecast
ablation requires, a researched representative Greek battery unit, and one structural finding
about the validation/test boundary that the operator asked to be flagged and quantified rather
than waved through.

**Nothing here is a result.** No figure in this document comes from a run of this project. The
market-rule statements are about market rules; the capacity statements are about installed
capacity; the day counts are calendar arithmetic over the accepted history's coverage. No price,
margin, forecast error or investment conclusion appears, and declaring these inputs produces
none: it makes a run possible, not credible.

## 1. The evidence limitation that qualifies sections 2 and 3

The research was carried out from an environment whose egress proxy refused every primary
domain this question needs: `enexgroup.gr`, `nemo-committee.eu`, `epexspot.com`, `entsoe.eu`,
`admie.gr`, `eletaen.gr` and `en.wikipedia.org` all returned a blocked-egress error on direct
retrieval. The market-rule and installed-capacity statements below therefore rest on
**search-result summaries of those primary documents, not on the documents themselves.**

That is below this project's normal standard for a declaration, and it is recorded rather than
hidden. Two things keep it admissible:

- Each declared `reference` states, in the declaration itself, that it has not been checked
  against the primary rulebook text. A reader of any run that uses these declarations sees the
  limitation beside the rule.
- The one regime that could not be corroborated at all governs no day that can carry a feature
  (§2), so the unverified statement is inert for every v0.9 surface.

Reading the primary documents and replacing these references with rulebook version and article
numbers is an open item, listed in `PLAN.md`. It is a strengthening of the record, not a
correction pending: no accepted figure depends on it, because no figure exists.

## 2. The decision cutoff — `config/decision_cutoff.json`

### What was found

The Greek spot market opened on **1 November 2020** under the target model in **isolated**
operation, with explicit allocation of interconnector capacity. The Greek bidding zone entered
the Single Day-Ahead Coupling on **trading day 15 December 2020, first delivery day 16 December
2020**, via the GR-IT border. From that day the Greek day-ahead order book closes at the SDAC
day-ahead gate closure, **12:00 CET/CEST on the day before delivery**.

The 15-minute market time unit went live across SDAC on **trading day 30 September 2025 for
delivery day 1 October 2025** — the same boundary as the accepted price history's resolution
change. It changed the market time unit and not the gate closure. **No third regime is declared
for it**, and that absence is a finding, not an omission.

The isolated-period closure (delivery days 2020-11-01 to 2020-12-15) is the weakest link:
secondary reporting supports 12:00 Greek time, and one retrieved snippet quoted 14:00 CET, which
on inspection describes the member-test environment rather than production.

### What is declared

| Effective from delivery day | Offset | Local time | Clock | Resolves to |
|---|---:|---|---|---|
| 2020-11-01 | −1 | 12:00:00 | `Europe/Athens` | 10:00 UTC |
| 2020-12-16 | −1 | 12:00:00 | `Europe/Brussels` | 11:00 UTC winter, 10:00 UTC summer |

Two properties make the weak first regime safe:

1. **It is the conservative direction.** 12:00 `Europe/Athens` is one hour *earlier* than the
   coupled-era closure, so if the isolated-era rule was in fact the later one, the declaration
   under-admits. A leakage control must fail in that direction.
2. **It governs no feature-bearing day.** The 0.25 degree GFS product is 3-hourly before
   26 February 2021, so the first delivery day that can carry an hourly feature is 2021-02-27
   (`docs/fundamentals_source_assessment_2026-09-02.md`, §4.1) — after the first regime has
   ended. `tests/test_declarations.py` asserts this, so a later decision that moves the feature
   start earlier fails the suite instead of silently promoting an unverified rule into use.

### Why the choice of clock does not change which days are admitted

`docs/fundamentals_source_assessment_2026-09-02.md` §4.3 verifies the upload lag of the 00 UTC
cycle's `f048` object at **3 h 41 m to 4 h 10 m** across three samples, with 365 of 365 days of
calendar 2025 clearing. The declared cutoffs sit 600 minutes (summer) to 660 minutes (winter)
after the cycle instant. A single-regime `Europe/Athens` alternative would sit at 540 to 600.
Both clear the observed normal lag by at least 90 minutes, and the one observed late run —
14 June 2021, 699 minutes — fails under both and is excluded by named cause either way.

The consequence is that the CET-versus-EET question, which could not be settled from primary
sources here, **is not load-bearing for admissibility** on the evidence this project has
gathered. It is load-bearing for the accuracy of the record, which is why it stays an open item.

### The decision lead

`config/decision_lead_minutes.txt` holds `0`: the bid decision is taken at the gate. This is the
operator's standing decision, restated here because the effective cutoff is the declared closure
minus this lead, and zero is a declaration rather than the absence of one. The file is the
record; the value reaches the code as a required CLI argument with no default.

### Operational consequence of declaring at all

`witness-fundamentals.yml` has refused to run since v0.9.1 because these files did not exist.
They exist now, so the daily 06:00 UTC job will begin retrieving. That schedule sits after the
observed publication window (03:41 to 04:10 UTC) and before every declared cutoff (10:00 or
11:00 UTC), so a run that lands is graded `witnessed` rather than `provider_declared`. Every day
between v0.9.1 and this commit is a witnessed day that cannot be recovered.

## 3. The sampling geography — `config/fundamentals_geography.json`

### The constraint that shapes it

`fetch-fundamentals` accepts **one** geography per run and applies it to every requested
variable. One declaration must therefore serve `wind_speed_10m`, `dswrf_surface` and
`temperature_2m` at once. There is no per-variable geography surface, and merging separate runs
by hand has no command and would break the join's digest checks. The declaration below is
therefore a compromise, and says so in its own `reference` rather than in a footnote.

### The basis

Each point's share of Greek installed **wind** generating capacity at **31 December 2023**, from
the HWEA/ELETAEN annual wind statistics: Central Greece (Sterea Ellada) 2,293 MW, Peloponnese
639 MW, Eastern Macedonia and Thrace 534 MW, of a national 5,226 MW. Those three mainland
regions hold 66.3 per cent of national wind capacity; the weights are their shares renormalised
over that 66.3 per cent.

| `point_id` | Latitude | Longitude | Weight |
|---|---:|---:|---:|
| `sterea-ellada-evia-boeotia` | 38.50 | 23.50 | 0.661569532602 |
| `peloponnese-arcadia-laconia` | 37.50 | 22.25 | 0.184362377380 |
| `east-macedonia-thrace-rodopi` | 41.00 | 25.25 | 0.154068090018 |

Every coordinate is an exact 0.25 degree grid node, checked against a reproduction of the GFS
grid in `tests/test_declarations.py`; the retrieval refuses a point between nodes rather than
interpolating, and the committed example's 40.6 is exactly such a refusal.

### Why the vintage is 2023 and not the latest

31 December 2023 precedes the end of the benchmark's training block (30 September 2024), so no
information from the validation or held-out test period enters the declaration. The 2025 wind
statistics were available and were deliberately not used: choosing where to sample using
knowledge of the capacity mix during the test period is a small, real contamination of a split
that may never be revised.

### What this geography is not

- It is **not** solar-weighted or demand-weighted. Irradiance and temperature are sampled on a
  wind-capacity geography. The regional split of Greek installed photovoltaic capacity could not
  be obtained from an accessible primary source (§1); the one figure that surfaced — Central
  Greece holding roughly a quarter of national PV — is too coarse to weight with.
- It carries **no demand centre**. Attica, the largest, has no weight. A four-point variant
  adding Attica at some share was drafted and rejected: the Attica weight would have had no
  source, and a mixed basis with one undefended number is the kind of input this project refuses
  everywhere else. One stated basis with a stated limitation is the more honest declaration.
- It represents **nothing the tooling can check.** The aggregate is computed exactly as declared.
  Whether these three points and these weights represent the Greek bidding zone is the
  operator's judgment and no code verifies it.

## 4. Price-regime bands

The declared bands are `0 50 100 200`, giving the reported regimes `<= 0`, `(0, 50]`,
`(50, 100]`, `(100, 200]` and `> 200` EUR/MWh.

**They are proposed from the training block only, and they slice reported metrics only.** The
bands appear in `metrics_by_slice`; they select no model, weight no fit and enter no headline
figure. Zero separates the negative-and-zero regime this project preserves rather than clips.
100 sits at the level of the training years' mean prices (2021: 116.44, 2023: 119.11, 2024:
100.88 EUR/MWh, from the accepted per-delivery-year decomposition of 28 August 2026). 200
separates the 2022 crisis regime, whose mean was 279.90 EUR/MWh.

A quantile-derived alternative — terciles or quartiles of the training block — was considered
and not adopted. It would require a live run over official prices restricted to days on or
before 2024-09-30, with a hard constraint that the test block is never touched, in exchange for
a more defensible cut of a purely descriptive slice. The structural bands cost nothing and carry
no risk of reaching past the training block.

One consequence is recorded now so that it cannot be mistaken for a fault later: the `<= 0`
regime is nearly empty in the training block (5, 1, 0 and 11 negative intervals in 2021, 2022,
2023 and 2024 respectively) and heavily populated in the test block (1,571 negative and 1,499
zero intervals in 2026). That asymmetry is the correct consequence of choosing bands without
looking at the test distribution. **The bands may not be revised after a test run.**

## 5. The validation/test boundary — flagged, quantified, and not waved through

With the held-out test block starting 2025-10-01 and the design's split rules
(`docs/v0.9_design.md` §10), and with the accepted price history running 2020-11-01 to
2026-08-25:

| Block | Span | Delivery days | Quarter-hour days |
|---|---|---:|---:|
| Training | 2021-03-27 to 2024-09-30 | 1,284 | **0** |
| Validation | 2024-10-01 to 2025-09-30 | 365 | **0** |
| Held-out test | 2025-10-01 to 2026-08-25 | 329 | **329 (100 %)** |

Training starts at the first GFS-usable delivery day (2021-02-27) plus the 28-day price-feature
warm-up; 118 accepted delivery days carry no feature at all.

**The mismatch is structural, not a tuning choice.** Every quarter-hour delivery day in the
accepted history falls on or after 2025-10-01 and is therefore inside the test block. No
admissible validation block can contain a single quarter-hour day. Shortening, lengthening or
moving the validation block cannot fix it; only revising the test start could, and that decision
is taken and may not be revised.

Three consequences follow, all of which belong in the acceptance document when the run happens:

1. **Model selection is made entirely in one resolution era and reported entirely in the other.**
   The choice between the ridge and the gradient-boosting model is made on validation RMSE
   alone, over 365 hourly days, and reported over 329 quarter-hour days. Nothing at selection
   time carries evidence about which model handles the quarter-hour regime.
2. **Arm B's feature column changes meaning at the split boundary.** The point-in-time join
   labels every training and validation row `equal` and every test row
   `broadcast_coarser_feature`: the hourly GFS value repeated across four 15-minute intervals.
   The augmented arm is fitted on per-interval features and tested on broadcast ones, 0 per cent
   against 100 per cent.
3. **The non-exploratory label depends on one season being complete.** A result may be labelled
   anything but exploratory only when the common held-out days cover every day of a
   meteorological season of quarter-hour deliveries. MAM 2026 contains the spring DST day
   2026-03-29, which the persistence baselines exclude by the documented wall-clock-slot cause;
   JJA 2026 is cut short by the accepted history ending 2026-08-25. **DJF 2025-26 — all 90 days
   from 2025-12-01 to 2026-02-28, with zero exclusions — is the only available route.** One
   missing GFS object, one late cycle, one day excluded on availability makes the entire
   acceptance run exploratory.

Two recommendations follow, and neither is adopted here because both are the operator's:

- **Pre-flight those 90 days** for coverage and availability before the official run. It is
  cheap and it is the difference between an exploratory label and a settled one.
- **If an hourly-era control arm is wanted, it must be pre-registered before any test run.** A
  second benchmark on an hourly test block declared in advance is legitimate; the same benchmark
  declared after seeing test results contaminates both, and the split may not be revised after a
  test run. This document does not declare one.

## 6. A representative Greek utility-scale LFP unit

`examples/battery_representative_gr_25mw_100mwh.json` is added **beside**
`examples/battery_50mw_100mwh.json`, which is unchanged. The v0.9 dispatch comparison continues
to run on the 50/100 example so its result stays comparable with accepted-history figures.

Greek standalone-storage auctions moved to a **four-hour** duration requirement — the third
auction sought 200 MW providing 800 MWh — with per-plant limits of 1 MW to 100 MW and a minimum
of 2 MWh per MW. Nine four-hour projects totalling 188.9 MW were awarded in March 2025, among
them a 25 MW / 100 MWh unit in Western Macedonia, an 18 MW / 72 MWh unit and a 10 MW / 40 MWh
unit. **25 MW / 100 MWh** is the largest of the reported awarded sizes and exactly four hours,
which is why it is the representative unit.

Every other field is the accepted example's, so the two differ only in what is being varied:
sizing, the matching grid limits, and the daily cycle limit, which is 1.0 rather than 1.5
because one deep cycle a day is the four-hour convention. That cycle limit is a judgment, and it
is the one number in the file that is not sourced. One-way efficiencies stay at 0.94, a 88.36
per cent round trip, inside the 86 to 90 per cent AC round-trip efficiency reported for
well-designed utility-scale LFP systems.

The file is illustrative, exactly as the accepted example is. It describes a plausible unit shape
from public auction outcomes; it is not a project, a cost estimate or evidence about any asset.

## 7. Sources

Market rules and market design:

- HEnEx Spot Trading Rulebook, `https://www.enexgroup.gr/documents/20126/144557/Spot_Trading_Rulebook_v2.2_en.pdf`
- EPEX SPOT, "Extension of Single Day-Ahead Coupling (SDAC) to Greece — go-live planned for 15 December 2020"
- ENTSO-E, "Extension of Single Day-Ahead Coupling (SDAC) to Greece", 17 December 2020
- NEMO Committee, "Extension of Single Day-Ahead Coupling (SDAC) to Greece"
- EPEX SPOT / Nord Pool / APG, "Market Coupling Steering Committee confirms go-live of 15-Minute
  MTU in SDAC on trading day 30 September 2025 for delivery day 1 October 2025"
- SDAC "Timings and Market Messages — normal processes"

Installed capacity:

- HWEA/ELETAEN annual wind energy statistics for Greece, 2023 and 2025 editions
- Renewables Now, "Greece's wind deployments rise 11.6% Y/Y in 2023" (regional breakdown)

Storage market and technology:

- pv magazine and ESS News reporting on the third Greek battery storage auction, March 2025
- ESS News, "Greece launches 200 MW battery storage auction", November 2024
- Published AC round-trip efficiency ranges for utility-scale LFP systems

Every entry in the first two groups was read as a search-result summary rather than as the
primary document, for the reason given in §1.
