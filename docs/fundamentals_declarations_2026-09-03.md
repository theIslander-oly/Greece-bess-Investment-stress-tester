# v0.9 fundamentals declarations and pre-registration

**Decision date:** 3 September 2026

**Evidence status:** operator-approved research declaration; primary documents must accompany
the acceptance evidence before an official run is accepted

This record fixes the judgmental inputs for the v0.9 benchmark before any test result exists. It
does not accept a feature table, run a benchmark or produce a market or investment figure.
Nothing here is financial advice or an investment-grade study.

## 1. Declared decision point

`config/decision_lead_minutes.txt` declares **0 minutes**: the modeled decision is taken at the
declared gate. Zero is an operator decision, not a software default, and does not claim that a
real bidder needs no time to forecast, optimize, submit or correct an order.

`config/decision_cutoff.json` records two historical regimes:

| First delivery day | Closure relative to delivery | Declared clock | UTC in winter | UTC in summer |
|---|---:|---|---:|---:|
| 2020-11-01 | D-1 12:00 | Europe/Athens | 10:00 | 09:00 |
| 2020-12-16 | D-1 12:00 | Europe/Brussels | 11:00 | 10:00 |

The first regime covers the isolated Greek DAM period. The second begins with Greece's SDAC
delivery-day go-live. The 15-minute market-time-unit change on 1 October 2025 does not create a
third closure regime: it changes delivery resolution, not the declared SDAC order-book gate.

> **Amendment, 10 September 2026 — the pre-coupling closure was corrected before any test run.**
> The retained HEnEx Decision 10 of 20 October 2020 (ref. 2205/20.10.2020), the day-ahead
> timeline in force at the 1 November 2020 launch, states "The Day-Ahead Market Gate Closure
> Time" at 12:00 (CET) / 13:00 (EET) on D-1 — one hour later than the 12:00 Europe/Athens
> declared above for delivery days before 2020-12-16. As this section requires, the declaration
> was corrected before any benchmark run: `config/decision_cutoff.json` now declares one regime
> from 2020-11-01 at 12:00 Europe/Brussels under the schedule id
> `greek-dam-gate-closure-2026-09-10`; the superseded id `greek-dam-gate-closure-2026-09-03`
> named the two-regime schedule tabulated above. No admitted feature exists before 2021-02-27,
> so no accepted observation changes. The primary text, its digests and the reading are in
> `docs/primary_sources/README.md`; the decision is recorded in `DECISIONS.md`. The table above
> is kept as the record of what was declared on 3 September 2026.

The isolated-period value is the weakest element of this declaration. Research located the
HEnEx/EnExGroup trading rulebook and SDAC notices, but the primary text was not retrievable from
the research environment. The operator approved the two-regime schedule with that limitation.
Before an official acceptance, the retained evidence must include the applicable HEnEx rulebook
section and effective dates. If it contradicts this schedule, the declaration must be corrected
before any test run; after a test run, a correction creates a newly identified benchmark and may
not silently revise this one.

Relevant primary publications to retain are the EnExGroup Spot Trading Rulebook and trading
schedule for the 1 November 2020 launch, the SDAC Greece go-live notice for delivery day
16 December 2020, the SDAC operational timings, and the SDAC 15-minute MTU go-live notice for
delivery day 1 October 2025.

The source assessment observed normal publication of the selected 00 UTC GFS cycle well before
all declared cutoffs. That observation does not validate the market rule: availability and gate
closure remain separate evidence claims.

## 2. Declared sampling geography

`config/fundamentals_geography.json` declares three exact NOAA GFS 0.25-degree grid nodes:

| Point | Latitude | Longitude | Weight |
|---|---:|---:|---:|
| Sterea Ellada / Evia / Boeotia | 38.50 | 23.50 | 0.661569532602 |
| Peloponnese / Arcadia / Laconia | 37.50 | 22.25 | 0.184362377380 |
| East Macedonia / Thrace / Rodopi | 41.00 | 25.25 | 0.154068090018 |

The weights are the reported installed wind capacities of the three largest regions at
31 December 2023—2,293 MW, 639 MW and 534 MW—renormalised over those regions. The vintage ends
before the validation block and therefore does not learn a spatial weighting from validation or
test-period deployment.

This is one common geography for `dswrf_surface`, `temperature_2m` and `wind_speed_10m`, because
the admitted v0.9 retrieval and digest contract has one geography per run. It is explicitly a
wind-capacity proxy when used for irradiance and temperature: it is not a solar-capacity,
population, load-density or national-area weighting. Attica has no unsourced discretionary
weight. These limitations must travel with the benchmark.

The primary HWEA/ELETAEN 2023 wind-statistics publication must accompany the acceptance evidence.
The grid coordinates themselves are declared representative nodes; their selection is not a
claim that one node resolves all meteorology within a region.

## 3. Pre-registered price-regime bands

The forecast benchmark will use the following required argument, with no inferred or adaptive
replacement:

```text
--price-regime-bands 0 50 100 200
```

This yields `<= 0`, `(0, 50]`, `(50, 100]`, `(100, 200]` and `> 200` EUR/MWh slices. The edges
are structural rather than test-set quantiles: zero isolates the zero/negative regime the project
preserves; 50 and 100 separate ordinary positive price levels; and 200 separates the exceptional
high-price regime prominent in the hourly training history. The bands only slice already-recorded
metrics. They do not select observations, tune a model or determine the headline result.

The non-positive slice is sparse in the training years and materially more common in the
quarter-hour test period. That asymmetry is not grounds to revise the bands after viewing the
test result.

## 4. Fixed validation and test boundary

The held-out test block starts **1 October 2025**, the first quarter-hour delivery day. Under the
design's 365-day validation rule and 28-day price-history warm-up, the intended blocks through
the currently accepted price endpoint are:

| Block | Inclusive span | Calendar days | Quarter-hour days |
|---|---|---:|---:|
| Training | 2021-03-27 to 2024-09-30 | 1,284 | 0 |
| Validation | 2024-10-01 to 2025-09-30 | 365 | 0 |
| Test | 2025-10-01 to 2026-08-25 | 329 | 329 |

The first GFS-usable delivery day is 27 February 2021; the 28-day price-history warm-up moves the
first eligible model day to 27 March. The 118 earlier accepted delivery days have no admitted
GFS feature and remain excluded by named cause.

This boundary creates a material regime-transfer limitation:

1. Model selection is performed entirely on hourly observations and evaluation entirely on
   quarter-hour observations. No quarter-hour evidence informs the validation choice.
2. Each native hourly GFS value has an equal-resolution relation during training and validation,
   but is broadcast over four market intervals throughout the test block.
3. The split is fixed before the first test run and may never be moved in response to a result.

The benchmark must report the existing resolution-era slice prominently. A supplementary
hourly-era control may be run only as a separately identified, pre-registered benchmark; it does
not replace, widen or revise the fixed primary test block.

## 5. Complete-season pre-flight

Under the accepted history endpoint, winter 2025-26 is the only complete meteorological season
available as common quarter-hour test days: 90 days from 1 December 2025 through 28 February
2026. Spring contains the market-clock DST day that persistence may exclude, and summer is
truncated at 25 August.

Before the official run, the workflow must audit all 90 winter days for complete feature and
availability coverage. One absent or late required value means the run has no complete season
and must remain explicitly exploratory. The pre-flight cannot fill, interpolate, backdate or
otherwise repair a missing observation.

## 6. Representative Greek utility-scale example

`examples/battery_representative_gr_25mw_100mwh.json` adds a **25 MW / 100 MWh (four-hour)** unit
beside the existing 50 MW / 100 MWh comparison configuration. It does not replace or alter that
configuration, and the official v0.9 comparison continues to use the unchanged 50/100 example.

The 25/100 sizing reflects four-hour projects observed in Greece's third storage auction,
including an awarded 25 MW / 100 MWh unit. The efficiencies remain the repository's illustrative
0.94 charge and 0.94 discharge assumptions (88.36% combined). The one-equivalent-cycle daily cap
is a declared modeling convention, not an auction condition, warranty promise or operating
forecast. All zero fees, degradation cost, constant availability and other inherited values
remain illustrative.

The representative example supports sensitivity work only. It is not a project design, OEM
specification, bankable forecast, recommendation or evidence that DAM-only arbitrage is viable.

## 7. What remains unaccepted

These declarations remove configuration absence as a software blocker; they do not establish
that the referenced evidence is sufficient. No official feature table is accepted until the
primary documents are retained, availability grades are audited, the feature table is verified
and custodied, and the data-acceptance document is completed. No official benchmark may precede
that acceptance. No result from synthetic fixtures supports an investment conclusion.
