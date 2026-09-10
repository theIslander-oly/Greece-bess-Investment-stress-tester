# Command reference

This reference holds the detailed, per-command workflows for the Greek Battery Investment
Stress Tester. Start with the [README](../README.md) for the accepted official-history findings,
their limitations, installation and the repository map. Commands using synthetic inputs are
for tests and public demonstrations only; their outputs are not investment evidence.

## Scenario and transformation commands

## Generate synthetic bootstrap paths

Create a JSON configuration (the end day is exclusive):

```json
{
  "start_day": "2027-01-01",
  "end_day": "2028-01-01",
  "path_count": 100,
  "block_days": 7,
  "random_seed": 42,
  "source_resolution_minutes": 15,
  "source_start_day": "2025-10-01",
  "source_end_day": "2026-08-26"
}
```

The three `source_*` fields declare the **source era** to sample from. An era is a maximal
contiguous run of market days at one delivery resolution, and the bootstrap samples from exactly
one. A history with a single era needs no declaration; the accepted 2020-2026 history holds two,
because the Greek DAM moved from hourly to quarter-hour delivery on 1 October 2025, so it must
be declared. There is no default: passing an undeclared multi-era history fails with a message
listing the available eras and their windows.

Neither era is the right answer on its own. The quarter-hour era is the operating regime but
contains exactly one occurrence of each meteorological season, so resampling it expresses no
inter-annual variation; the hourly era spans five or six occurrences of every season but is a
superseded delivery regime. Read
[the source-era policy](bootstrap_source_era_policy.md) before choosing, and use
`greek_bess.stress.detect_source_eras` to list what a history contains.

Then run the generator against a complete canonical price history held outside Git:

```bash
greek-bess generate-bootstrap-paths data/processed/henex_prices.csv \
  --config config/bootstrap.json \
  --output data/processed/bootstrap_paths.csv
```

Dispatch the generated paths with identical physical assumptions (the optimizer retains each
`path_id` and canonical interval key):

```bash
greek-bess dispatch-bootstrap-paths data/processed/bootstrap_paths.csv \
  --config examples/battery_50mw_100mwh.json \
  --availability 1.0 \
  --output data/processed/bootstrap_dispatch.csv
```

The command writes interval dispatch, a sibling `.paths.csv` operational/revenue summary, and a
JSON method summary. All results are synthetic perfect-foresight gross-margin upper bounds—not
forecasts, probabilities, expected revenue, or investment evidence.

The command writes the labelled synthetic paths, a block-level `.provenance.csv`, and a
`.summary.json`. It samples with replacement from contiguous blocks in the same meteorological
season, inside the declared source era only, and requires the source block to have the target
block's exact interval-count pattern. The summary records every available era, the selected
era and whether it was declared; the provenance records the era on every sampled block, and the
summary reports minimum and median block-candidate counts so scarcity is visible rather than
smoothed.
It copies prices without smoothing or interpolation, including zero and negative values. Missing
prices, gaps, overlaps, incomplete market days and unavailable DST-compatible blocks fail
explicitly. These paths are synthetic scenarios—not forecasts, probability-calibrated outcomes,
or investment evidence—and generated artifacts must not be committed.

## Apply one explicit price-level shock

The `apply-price-level-shock` command applies the same configured additive EUR/MWh shift to every
interval without clipping zero or negative results. For example, `config/price-shock.json` may
contain `{"shift_eur_per_mwh": -20.0, "transformation_id": "down_20_eur_mwh"}`.

```bash
greek-bess apply-price-level-shock data/processed/bootstrap_paths.csv \
  --config config/price-shock.json \
  --output data/processed/shocked_paths.csv
```

The command also writes sibling `.provenance.csv` and `.summary.json` artifacts. Provenance is
one-to-one with intervals and retains path ID, canonical UTC key, original price, shocked price,
shift, transformation ID and input source metadata. Inputs with missing prices, duplicate keys,
gaps or incomplete DST-aware market days are rejected. These synthetic shocked paths are not
forecasts, calibrated scenarios or investment evidence.

## Compress within-day spread

The `compress-spread` command pulls every interval of a market day toward that day's reference
level, which is what makes it the first-order stress for a battery: a level shift leaves spreads
untouched, while compression changes the quantity being arbitraged. For example,
`config/spread-compression.json` may contain:

```json
{
  "compression_factor": 0.7,
  "reference_basis": "daily_mean",
  "transformation_id": "spreads_down_30_percent"
}
```

```bash
greek-bess compress-spread data/processed/bootstrap_paths.csv \
  --config config/spread-compression.json \
  --output data/processed/compressed_paths.csv
```

Each interval becomes `reference + factor * (price - reference)`, so every within-day range is
scaled by exactly the factor. A factor of 1.0 is the identity and 0.0 flattens each day onto its
reference level; widening (above 1.0) is out of scope.

`reference_basis` is **declared with no default**, like the source era. `daily_mean` preserves
each day's mean exactly, making the result a pure spread change; `daily_median` does not, and the
summary reports the resulting maximum daily-mean shift so the difference is visible.

Zero and negative results are preserved and never clipped. Compression pulls prices toward the
reference level, so an interval on the far side can cross zero and change sign — a real
consequence of compressing spread, counted in the summary as `sign_change_interval_count` rather
than suppressed. The summary also reports mean and maximum daily range before and after, and
negative and zero interval counts before and after.

The command writes sibling `.provenance.csv` and `.summary.json` artifacts. Provenance is
one-to-one with intervals and retains path ID, canonical UTC key, market day, transformation ID,
compression factor, reference basis, the reference level applied, original and compressed prices,
and input source metadata. Inputs with missing prices, duplicate keys, gaps or incomplete
DST-aware market days are rejected.

**The compression factor is a declared judgmental scenario, not an estimate.** Nothing in the
replayed history calibrates it: the 2020-2026 record predates operating battery competition
almost entirely, so it contains no episode from which a competitive spread response could be
inferred. No probability, percentile, loss metric or ranking attaches to a factor. See
[`LIMITATIONS.md`](../LIMITATIONS.md).

## Apply declared negative-price events

The `apply-negative-price-events` command replaces prices only in explicitly declared,
interval-aligned UTC windows. Each event declares its identifier, inclusive start, exclusive end
and strictly negative replacement price in EUR/MWh; none has a default. An empty event list is
the exact identity. For example, `config/negative-price-events.json` may contain:

```json
{
  "transformation_id": "declared_midday_events",
  "events": [
    {
      "event_id": "day_one_midday",
      "start_utc": "2026-06-01T09:00:00+00:00",
      "end_utc": "2026-06-01T12:00:00+00:00",
      "price_eur_per_mwh": -50.0
    }
  ]
}
```

```bash
greek-bess apply-negative-price-events data/processed/bootstrap_paths.csv \
  --config config/negative-price-events.json \
  --output data/processed/negative_event_paths.csv
```

The event times are declarations, never draws or estimates. The command does not accept a
frequency, likelihood, fitted rate, expected count, percentile, ranking or threshold search. A
window is applied to every path and must begin and end on interval edges, cover at least one
interval and not overlap another event. A partial, empty or overlapping window is refused rather
than rounded, prorated or ignored.

This is not a level shift or spread compression in disguise: only named windows are replaced by
absolute declared negative prices. Every other price, including an existing zero or negative
price, stays numerically unchanged. No price is clipped or floored. The sibling provenance CSV
has one row per path interval, including untouched intervals, and the summary reports negative
and zero interval counts before and after. Outputs remain labelled synthetic, non-probabilistic,
non-forecast and unsuitable as investment evidence.

## Declare an availability or outage path

`dispatch-bootstrap-paths --availability-schedule` applies a declared availability schedule to
every path of a run. A schedule is a baseline available fraction plus zero or more declared
outage windows:

```json
{
  "schedule_id": "planned_maintenance_2026",
  "baseline_available_fraction": 1.0,
  "windows": [
    {
      "outage_id": "summer_maintenance",
      "start_utc": "2026-07-06T00:00:00+00:00",
      "end_utc": "2026-07-13T00:00:00+00:00",
      "available_fraction": 0.0
    }
  ]
}
```

```bash
greek-bess dispatch-bootstrap-paths data/processed/bootstrap_paths.csv \
  --config examples/battery_50mw_100mwh.json \
  --availability-schedule config/availability-schedule.json \
  --output data/processed/outage_dispatch.csv
```

`baseline_available_fraction` is **declared with no default**, like the source era and the
compression reference basis: availability is one of the assumptions the project requires to be
explicit. A window list of `[]` is the declared full-availability scenario, which is preferable
to an implied one. `--availability` and `--availability-schedule` are mutually exclusive.

**Outages are declared, never sampled.** A forced-outage rate would be a probability, and
nothing calibrates one — no Greek merchant battery has operated, and no fleet maintenance record
or warranty series is in scope — so a configuration carrying one is refused by name. A schedule
states what to examine; it is not a rate, a guarantee, a maintenance plan or a reliability model.

A window applies whole to every interval it covers. A boundary falling strictly inside a delivery
interval is refused, naming the interval, rather than prorated — prorating would apply a schedule
finer than the one declared. Overlapping windows, a window covering no dispatched interval,
reversed windows, naive timestamps and out-of-range fractions are refused too.

The run writes an `.availability.csv` sidecar recording the schedule, the baseline, the outage
covering each interval and the applied fraction, and the dispatch summary records the schedule by
identity, so a margin traces back to the outage assumption behind it.

Availability scales grid-side charge and discharge power only, and dispatch retains perfect
foresight, so it positions the battery for a declared outage and the margin stays an upper bound.
Timing is the whole content of the scenario: the same outage costs almost nothing in a low-spread
week and a great deal in a high-spread one. See [`LIMITATIONS.md`](../LIMITATIONS.md).

## Report a range across named scenarios

The `report-scenario-ensemble` command composes scenarios that have **already been dispatched**
and reports the minimum, maximum and spread of their margin outcomes. It computes no price,
dispatch, forecast or finance quantity of its own.

Every scenario is named by the caller in a manifest. There is no default scenario set and no
implicit baseline: an untransformed replay states `"transformation_summary_json": null` and takes
its place in the ensemble like any other named judgment.

```json
{
  "scenarios": [
    {
      "name": "baseline_replay",
      "run_id": "bootstrap-2026-08-31-seed-42",
      "path_summaries_csv": "baseline.paths.csv",
      "dispatch_summary_json": "baseline.summary.json",
      "bootstrap_summary_json": "bootstrap_paths.summary.json",
      "transformation_summary_json": null
    },
    {
      "name": "spreads_down_30_percent",
      "run_id": "bootstrap-2026-08-31-seed-42",
      "path_summaries_csv": "compressed.paths.csv",
      "dispatch_summary_json": "compressed.summary.json",
      "bootstrap_summary_json": "bootstrap_paths.summary.json",
      "transformation_summary_json": "compressed_paths.summary.json"
    }
  ]
}
```

```bash
greek-bess report-scenario-ensemble \
  --manifest config/scenario-ensemble.json \
  --output data/processed/scenario_ensemble.csv
```

The range is taken **per bootstrap path**: for each path the scenarios share, the report gives the
lowest and highest margin any named scenario produced, the spread between them, and which
scenario attained each end. Nothing is aggregated across paths, because a total or an average over
sampled paths would read as an expectation the uniform block resampling cannot support.

The command writes sibling `.margins.csv` and `.summary.json` artifacts. Every margin row carries
its scenario name, transformation method and parameters, the selected source era and the input run
identity, so any reported figure traces back to the runs that produced it.

**A range across named scenarios is a range across judgments, not a distribution.** No
probability, percentile, likelihood, expected value, loss metric, ranking or central case is
produced, and the rule is executable: an emitted column or summary key matching
`greek_bess.stress.FORBIDDEN_REPORT_TERMS` raises rather than being written.

Scenarios are combined only on an **equivalent basis**, and the basis is the asset and the
sample: differing battery parameters, terminal-energy constraint, source-era selection or path
identity are refused by name rather than reconciled, because comparing strategies only under
equivalent physical and terminal-energy constraints is a standing project invariant.

The price transformation and the availability schedule are on the other side of that line. They
are the judgments under examination, are expected to differ, and are carried as provenance on
every reported figure — so a declared outage can be ranged against a baseline, and each end of a
range names the availability it was solved under.


## End-to-end command workflows

## 1. Generate public-demo data

```bash
greek-bess generate-synthetic \
  --start-day 2025-01-01 \
  --end-day 2026-01-01 \
  --resolution-minutes 60 \
  --seed 42 \
  --output data/curated/synthetic_prices.csv
```

This produces:

- `data/curated/synthetic_prices.csv`
- `data/curated/synthetic_prices.quality.json`

Synthetic data is always marked with `source=synthetic` and the quality flag `synthetic_demo_data`.

## 2. Import HEnEx results

```bash
greek-bess parse-henex \
  path/to/YYYYMMDD_EL-DAM_Results_EN_v01.xlsx \
  --output data/curated/henex_prices.csv
```

The parser:

1. locates a worksheet containing the documented result columns;
2. selects the latest publication version per delivery day;
3. verifies one unique MCP per MTU despite repeated asset-level rows;
4. reconstructs DST-safe timestamps from `DDAY`, `SORT` and `DELIVERY_DURATION`;
5. writes normalized data and a quality report.

Use `--allow-partial-days` only when a deliberately incomplete workbook is being inspected. Incomplete days are rejected by default.

### Retrieve the complete archived HEnEx history

The verified annual-results register currently covers the beginning of the current Greek DAM
on 1 November 2020 through the end of 2025:

```bash
greek-bess fetch-henex-archives \
  --start-year 2020 \
  --end-year 2025 \
  --raw-dir data/raw/henex \
  --manifest data/raw/henex/archive_manifest.json \
  --output data/processed/henex_archived_prices.csv
```

The command downloads the official ZIPs, rejects unsafe archive paths, extracts only English
`EL-DAM_Results` workbooks, retains the latest publication revision per interval, normalizes
DST-safe timestamps and writes a quality report. The annual URLs are pinned in source code and
recorded in `config/official_sources.json`.

For the current unarchived year, use the incremental catalog command:

```bash
greek-bess fetch-henex-daily \
  --start-day 2026-01-01 \
  --end-day 2026-08-26 \
  --raw-dir data/raw/henex \
  --manifest data/raw/henex/daily_manifest.json \
  --output data/processed/henex_2026_prices.csv
```

HEnEx's daily catalog is a website interface rather than a documented data API. The command
therefore fails visibly if the catalog or document-link layout changes. A successful download
still requires the normal parser and quality checks; discovery alone is not acceptance evidence.

The `Fetch official Greek market history` GitHub Actions workflow runs automatically once when
the workflow file first reaches `main` and is manually reusable afterward. It publishes
normalized data, manifests and quality reports as a private seven-day artifact without
credentials. It never commits the data, and ordinary code pushes do not trigger it.

### Retrieve ADMIE/IPTO source files

> ADMIE load and RES forecasts are **out of scope** (decision entry 2026-09-01). These commands are
> retained and runnable so a future declaration can be tested, but nothing they retrieve may enter
> a forecast, feature set, dispatch plan or reported result.

First snapshot the provider's live filetype catalog:

```bash
greek-bess list-admie-filetypes \
  --output data/raw/admie/filetypes.json
```

Then retrieve candidate day-ahead load and RES forecast publications:

```bash
greek-bess fetch-admie-files \
  --filetypes ISP1DayAheadLoadForecast ISP1DayAheadRESForecast \
    ISP2DayAheadLoadForecast ISP2DayAheadRESForecast \
  --start-day 2020-11-01 \
  --end-day 2026-08-26 \
  --raw-dir data/raw/admie \
  --manifest data/raw/admie/retrieval_manifest.json
```

The default selects the latest publication for each filetype and coverage period. Pass
`--all-revisions` for a revision-history audit and whenever the retrieval feeds the timing audit
below. The manifest retains both delivery coverage and publication time. These files are
quarantined from forecasting until their pre-auction availability and changing historical formats
are validated; retrieval does not make a variable leakage-safe.

### Audit ADMIE pre-auction publication timing

> Retained but unused — see the scope note above. This audit was never run over the confirmed
> filetypes against a verified gate closure, and its passing would no longer admit any ADMIE
> field into forecasting.

The audit compares each retrieved file's publication time against a **declared** day-ahead gate
closure, per delivery day, without parsing any file:

```bash
greek-bess audit-admie-publication-timing \
  data/raw/admie/retrieval_manifest.json \
  --gate-closure config/admie_gate_closure.json \
  --filetypes ISP1DayAheadLoadForecast ISP1DayAheadRESForecast \
    ISP2DayAheadLoadForecast ISP2DayAheadRESForecast \
  --start-day 2026-08-01 \
  --end-day 2026-08-25 \
  --output acceptance/admie/delivery_days.csv
```

The closure has **no default**: a schedule declares one or more dated regimes, each naming its
clock and carrying a required reference to the market rule it comes from, because the rule can
change over the audited history. `config/admie_gate_closure.example.json` shows the format and
must have its placeholder reference replaced before use.

Each delivery day is reported as `witnessed_pre_gate` (a retrieval performed before the closure
observed the file), `asserted_pre_gate` (only the publisher's timestamp says so),
`no_pre_gate_publication`, or `no_record`. A publication exactly at the closure counts as late.
For accepted days the audit names the **decision-time revision** — the latest one published
before closure, the only revision a backtest may read — and counts the revisions that superseded
it afterwards. The command exits `2` on any unaccepted day.

Passing establishes publication timing and nothing else. It accepts no file format and proves no
forecasting skill, and the summary says so in its own output. It would not now admit any ADMIE
field into forecasting either: those forecasts are out of scope, so the quarantine it was built to
discharge is closed rather than pending. See `docs/admie_publication_timing_policy.md`.

### Retrieve point-in-time fundamentals

Retrieve NOAA GFS 0.25° forecast vintages for a window of delivery days and build a
point-in-time feature table, one row per delivery interval per variable, each carrying the
publication instant, the retrieval instant, the documents it came from and a byte digest:

```bash
greek-bess fetch-fundamentals \
  --source noaa_gfs \
  --variables dswrf_surface temperature_2m wind_speed_10m \
  --geography config/fundamentals_geography.json \
  --start-day 2026-08-01 \
  --end-day 2026-08-31 \
  --output acceptance/fundamentals/features.csv \
  --manifest acceptance/fundamentals/retrieval_manifest.json
```

The sampling geography has **no default**. A gridded variable has a value at every grid node;
which nodes represent the Greek bidding zone, and with what weights, is an operator judgment.
`config/fundamentals_geography.example.json` shows the format and is **refused by name** while
its placeholder reference remains, so an example cannot be copied into a run and mistaken for a
declaration. A declared point that does not land on a grid node is refused rather than
interpolated, and the refusal names the nearest node.

Only the 00 UTC cycle of D-1 is read: the 06 UTC cycle was observed publishing after a midday
cutoff. A window holding no usable day is refused rather than written as an empty table.

The selected byte range is decoded and checked independently against the request and sidecar.
Parameter identity, units, level, cycle, valid time, hourly forecast step and
instant/average/accumulation semantics must all agree; a mismatch stops with a named integrity
refusal. No unit, level or time interpretation is inferred or converted.

For `wind_speed_10m`, the U/V magnitude is calculated at each declared grid point before the
declared weights are applied. For `dswrf_surface`, the source bucket means are de-averaged to
local one-hour means before weighting, including at six-hour bucket resets. The retrieval summary
records the full geography, decoded-message contract and `feature_semantics_version`. Tables made
before version 2 must be rebuilt and cannot retain an earlier acceptance identity. Shard
recombination refuses a missing or mixed semantics identity.

**Three conditions exclude a delivery day by name and let the window continue**, and they are the
only three:

| Cause | What the provider said |
| --- | --- |
| `before_hourly_product_start` | The 0.25° product is 3-hourly before 27 February 2021, so the day carries no hourly feature and no coarser value is broadcast into one. |
| `missing_object` | Both archive key layouts were asked for a forecast step the day needs, and the store answered that neither holds an object. |
| `sidecar_object_mismatch` | The `.idx` sidecar beside a step object indexes a different publication, so no message byte range can be resolved from it. |

The summary records each excluded day under `excluded_days_by_cause` — capped at 100 entries so a
long window cannot become a day-by-day log — and every cause's total under
`excluded_day_count_by_cause`, which is never capped.

**Every other refusal stops the retrieval.** A message on a different grid, an undecodable
message, a non-finite sample at a declared point, an object with no publication instant, a
byte-range slice shorter than the sidecar declares, an unreadable sidecar — each of those is a
statement about how a value would be *built*, not about what the provider published. An excluded
day is recorded as a provider non-publication in a pre-registered window, so recording one of
these as an exclusion would put a false finding into the evidence that nothing downstream could
detect. A retrieval that stops costs a re-run; one that excludes the wrong day does not announce
itself.

**A request the archive did not answer is not absence either.** HTTP failures are classified by
kind: only `404` and `410` mean the object is not there. A `403`, a `5xx`, a connection reset, a
TLS failure or a body that stops short of its declared length says nothing about whether the
object exists, so the client raises rather than moving on to the other key layout — because two
"failures" from two layouts would otherwise read as absence. Transport faults and 5xx answers are
retried up to five attempts with 1, 2, 4 and 8 second backoff before that raise; a `404` is never
retried, because absence is an answer and re-asking cannot change it, and neither is the sidecar
mismatch or any other deterministic refusal. The retrieval remains sequential by construction:
making it concurrent would change how an accepted evidence path talks to the provider.

`--raw-dir` retains every retrieved GRIB2 message and is optional. It is useful over a short
window and unaffordable over the declared one — the measured 83 MB per delivery day is about
163 GB across 2,006 days — so the retrieval workflow omits it and relies on the retrieval
manifest, which records the digest and byte count of every message each value was decoded from.

Everything this command writes is private: any retained GRIB2 messages, the feature table, its
coverage table, its retrieval manifest and its summary. None of it is committed.

### Combine point-in-time feature shards

The declared v0.9 window cannot be retrieved in one job. The first dispatched retrieval, run
`33760441164` on 3 September 2026, took 36 minutes for 30 delivery days — **72 seconds per
delivery day**, because the source is read as one HTTPS round trip per forecast step. The
declared window is 2,006 delivery days, so one job would need roughly **40 hours** against a
per-job ceiling of six, and would retain about **163 GB** if it kept its raw messages. The
window is pre-registered and may not be shortened, so it is retrieved in slices instead:

```bash
greek-bess combine-feature-tables \
  shards/features_0.csv shards/features_1.csv shards/features_2.csv \
  --output acceptance/fundamentals/features.csv \
  --manifest acceptance/fundamentals/retrieval_manifest.json
```

This is sound only because a delivery day is retrieved independently of every other one: the
client reads that day's own forecast cycle and derives nothing from a neighbour. The command
holds the invariant that makes the recombination checkable rather than assumed — the slices must
**tile** the window, covering every delivery day exactly once — and it refuses anything else:

- **An overlap is refused, never deduplicated.** Two retrievals of one delivery day are two
  revisions of the same observation, and choosing between them is the point-in-time join's
  decision under a declared cutoff, not a concatenation's.
- **A gap is refused**, naming the missing span. A silently short window is indistinguishable
  downstream from a provider that published nothing.
- **Slices that disagree on the source, the variable set or the declared geography are refused**,
  naming the fields that differ, because combining them would give one column two meanings.
- A slice without its retrieval summary is refused; a shard is combined on the evidence of what
  it retrieved, not on a CSV happening to sit beside it.

A slice declares the window it was asked to retrieve, so a delivery day it excluded by name is
inside its window and carries no feature row. The combined summary carries every slice's
exclusions under `excluded_days_by_cause` and their totals under `excluded_day_count_by_cause`,
and it sums each slice's own count rather than recounting its capped list, so an exclusion is
never invisible in the aggregate.

The combined table is exactly what a single retrieval of the whole window would have written:
the test suite asserts the equality on synthetic fixtures, and it was checked on real retrieved
NOAA GFS data before the surface was adopted. The combined summary records every slice, its
window and its own retrieval instant, so a reader who doubts the table can re-retrieve any one
slice on its own, and the combined retrieval manifest carries every document digest and byte
count from every slice.

Feature tables are read with round-trip float precision wherever a digest is taken over them.
The parser default is accurate to within one unit in the last place, which is far below anything
meteorological or monetary this project reports — but the feature set is identified downstream by
a SHA-256 over its own values, and a digest has no tolerance.

### Audit point-in-time feature availability

The audit asks, per delivery interval, whether a value was published strictly before that day's
**declared** decision cutoff — the declared gate closure minus the declared decision lead:

```bash
greek-bess audit-feature-availability \
  acceptance/fundamentals/features.csv \
  --decision-cutoff config/decision_cutoff.json \
  --decision-lead-minutes 90 \
  --variables dswrf_surface temperature_2m wind_speed_10m \
  --start-day 2026-08-01 \
  --end-day 2026-08-31 \
  --output acceptance/fundamentals/delivery_days.csv
```

Neither the cutoff nor the lead has a default, and both are refused rather than guessed: the
committed `config/decision_cutoff.example.json` is refused by name, and the lead must be declared
as a non-negative integer, where `0` is a declaration and absence is not.

Availability is established **per delivery interval**, never per day. Upload order is not
monotone in forecast step — a later step of one cycle was observed appearing before an earlier
one — so one step's availability says nothing about another's, and one late step makes the whole
day `incomplete_before_cutoff` rather than a day with fewer intervals.

Each day is reported as `witnessed_before_cutoff` (this project retrieved the values before the
cutoff), `provider_declared_before_cutoff` (a provider instant attached to the datum places it in
time), `incomplete_before_cutoff`, `all_publications_after_cutoff`, `grade_not_admitted` or
`no_publication`. A publication exactly at the cutoff is late. `--admit-assumed-grade` admits the
quarantined grade and makes the run exploratory: such days carry their own status and can never
be counted as accepted. The command exits `2` on any unaccepted day.

Passing establishes availability and nothing else. It accepts no value and no unit, proves no
forecasting skill, and does not admit the source to any benchmark — the data-acceptance document
of the v0.9 design's Section 7 does that. See `docs/point_in_time_feature_contract.md`.

## Record a result under the report contract

Every result summary can be recorded under a versioned run manifest, so a consumer reads a
stable projection rather than one of sixteen modules' incidental summary keys:

```bash
greek-bess record-run-manifest dispatch.summary.json \
  --result-kind perfect_foresight_dispatch \
  --manifest-id 2026-08-31-replay \
  --produced-by optimize-perfect-foresight \
  --output dispatch.manifest.json

greek-bess verify-run-manifest dispatch.manifest.json
```

The manifest carries the producing module's summary verbatim and adds the declared result kind,
the basis it reports on (`historical_replay_upper_bound`, `historical_forecast_backtest`,
`synthetic_scenario`, `screening_arithmetic` or `data_acceptance_evidence`), the required
non-empty result label and the project's standing exclusions. A result whose summary lacks its
label is refused, as is a manifest whose schema version or result kind this build does not
understand. See `docs/run_manifest_contract.md`.

## Render a report from verified manifests

A report renders verified run manifests, and only verified run manifests. `render-report` is a
presentation layer: it formats values that a validated module already computed and recorded, and
there is no side channel through which a figure can reach a report any other way.

```bash
greek-bess render-report \
  dispatch.manifest.json ensemble.manifest.json finance.manifest.json \
  --output reports/generated/report.html
```

The command writes one self-contained HTML file — no scripts, no external assets, no network
fetches — and a machine-readable index beside it naming every manifest rendered, its kind,
basis, label and SHA-256 digest, so a report is auditable back to the exact manifests behind it.
Reports and indexes are generated research outputs and stay outside Git.

What the report guarantees:

- **Every figure carries its label.** The manifest's `result_label`, its basis in reader-facing
  words and the project's three standing exclusions are rendered adjacent to the figure, never
  in a global footer. The label is read from the manifest and never re-declared, so it cannot
  drift from what the producing module wrote.
- **Figures are grouped by basis.** A perfect-foresight ceiling, a settled backtest, a synthetic
  scenario, screening arithmetic and data-acceptance evidence are separate sections, so the
  distinction is the structure of the document rather than a footnote. Figures of different
  bases are never merged into one row, total or derived value.
- **Nothing is computed while rendering.** No dispatch, forecast, transformation, degradation or
  finance call is reachable from the renderer, and no value is derived across manifests.
- **A manifest that fails verification refuses the whole report.** There is no partial render: a
  report that silently omitted a failing manifest would present the remainder as the whole.
- **Identical inputs render byte-identical documents.** Manifests are ordered by basis, then
  kind, then manifest ID — never by the order they were supplied. The only timestamp the
  renderer adds is `rendered_at_utc`, and it lives in the index rather than the document.
- **An export cannot carry interval-level official prices.** The renderer's only input is the
  manifest list, and a manifest carries the producing module's summary; a path named in
  `declared_inputs` is displayed, never opened.

### Composing many manifests

Composition is layout. Nothing is computed across manifests, and figures of different bases are
never merged into one row, total or derived value.

- **An index across every manifest, grouped by basis.** It names each manifest by ID, kind,
  recorded label, producing command, recorded time and SHA-256 digest, and links to the block
  that holds its figures. It also names the bases the report does *not* cover, because a reader
  cannot otherwise tell an absent basis from an absent question.
- **The index carries no figure at all.** That is the point of it. A summary table spanning the
  whole report is the one place a figure of one basis would first sit beside a figure of another
  and then be combined with it, so every number stays inside its own manifest's block, beside
  its label. A test asserts that every cell of the index is one of the manifest's identity,
  label or provenance fields.
- **A scenario ensemble is laid out side by side.** One column per named scenario with the
  provenance each figure has to carry, the equivalent-basis evidence the ensemble recorded — the
  battery parameters, terminal-energy basis, source era and path identity every scenario was
  required to share — and one row per bootstrap path giving the lowest and highest margin any
  named scenario produced for that path, which scenario attained each end, and the spread. The
  scenario name joins the two, and nothing is totalled across paths.
- **What a manifest does not record is not shown.** A manifest recorded before its module
  carried a key renders an explicit "records no ..." note. A report reads the manifest and
  nothing else; it never opens the CSV a run wrote beside it.

Run it with no manifests to see the landing state:

```bash
greek-bess render-report --output reports/generated/landing.html
```

Every judgmental input in this project has no default by recorded decision — the bootstrap
source era, the spread-compression factor and reference basis, the availability baseline, the
negative-price event list and the scenario set of an ensemble. So the landing state is the
declaration checklist itself: each default-free input, the dated decision that made it so, and
the command that records a result once it is declared. It contains no figures and no example
numbers, because an example shown before anything is declared becomes the de facto default.

### Rendering the accepted replay

Official price data lives outside Git and live endpoints are reachable only from GitHub Actions
runners, so a report over the accepted official history is produced by workflow rather than from
a working checkout. The
[`Render a report from the accepted replay`](../.github/workflows/render-accepted-replay-report.yml)
workflow takes the run ID of a completed `Decompose the accepted replay by delivery year` run,
refuses one whose custody verification did not pass, records each accepted summary that run wrote
— the daily-composed perfect-foresight ceiling, the per-delivery-year decomposition and every
forecast backtest — under the run-manifest contract, verifies each manifest, renders them into one
indexed report and uploads it as a private artifact.

It renders an accepted analysis rather than re-running one: the decomposition workflow already
verified the official history against its committed custody record, and re-solving would take
hours and could produce figures differing from the ones the acceptance document records. Nothing
is computed by the workflow either — every figure is a value one of those summaries already
recorded. The report and its index are generated research outputs and are never committed.

See `docs/v0.8_design.md`.

## 3. Fetch ENTSO-E prices

Register on the ENTSO-E Transparency Platform and obtain REST API access. Store the personal token in the environment:

```bash
export ENTSOE_SECURITY_TOKEN="your-personal-token"
```

Then fetch a full market-clock-aligned period:

```bash
greek-bess fetch-entsoe \
  --start 2025-12-31T23:00Z \
  --end 2026-01-31T23:00Z \
  --output data/curated/entsoe_prices.csv
```

The ENTSO-E endpoint uses UTC request periods. For complete local market days, calculate the correct UTC boundary for CET/CEST rather than assuming every day begins at `00:00Z`.

Raw XML responses are cached under `data/raw/entsoe/` by default. The token is never included in filenames, output rows or error messages.

If local command-line execution is unavailable, the manual
[`Fetch official ENTSO-E prices`](../.github/workflows/fetch-entsoe.yml) GitHub Actions
workflow performs the same retrieval using an encrypted repository secret and publishes
only the normalized CSV and quality JSON as a short-lived artifact. See the
[`secure GitHub retrieval guide`](entsoe_github_retrieval.md).

## 4. Compare HEnEx and ENTSO-E

After normalizing an overlapping period from each source:

```bash
greek-bess compare-sources \
  data/curated/henex_prices.csv \
  data/curated/entsoe_prices.csv \
  --tolerance 0.000001 \
  --output data/curated/source_comparison.csv
```

Each interval is classified as `match`, `price_mismatch`, `missing_henex` or `missing_entsoe`. A comparison containing anything other than matches exits with code `2` so it can fail an automated validation job.

The accepted HEnEx history is normally produced in two parts: the annual archives and the
unarchived daily results. Merge them into one series from a single source before comparing:

```bash
greek-bess merge-canonical \
  data/curated/henex_archived_prices.csv \
  data/curated/henex_daily_prices.csv \
  --output data/curated/henex_prices.csv
```

`merge-canonical` refuses to mix two sources, never removes a repeated interval and reports the
usual deterministic quality assessment, so an overlap or a gap between the two files fails
loudly instead of being absorbed.

If neither the personal ENTSO-E token nor the accepted history can leave GitHub, the manual
[`Reconcile HEnEx and ENTSO-E prices`](../.github/workflows/reconcile-henex-entsoe.yml) workflow
performs the whole comparison inside Actions: it reads the accepted history artifact from an
earlier run, derives the reconciliation window from that history, retrieves ENTSO-E prices for
exactly the same window and uploads the interval-level classification. Only interval counts,
classification counts and aggregate difference statistics reach the job log. See the
[`secure GitHub retrieval guide`](entsoe_github_retrieval.md).

## 5. Optimize perfect-foresight dispatch

The included example battery configuration is deliberately illustrative. Replace every
technical and commercial assumption with project-specific evidence before interpreting a
result.

```bash
greek-bess optimize-perfect-foresight \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --output outputs/perfect_foresight_dispatch.csv
```

This produces:

- `outputs/perfect_foresight_dispatch.csv`, with interval-level power, SOC, energy,
  settled energy value, fees, degradation cost and net margin;
- `outputs/perfect_foresight_dispatch.summary.json`, with aggregate energy,
  equivalent cycles, captured prices and margin components.

Add `--daily-solves` to solve every market day independently and compose the schedules
instead of optimizing the whole horizon in one solve:

```bash
greek-bess optimize-perfect-foresight \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --daily-solves \
  --output outputs/perfect_foresight_daily.csv
```

Each day then starts and ends at the configured SOC, which is the convention the forecast
backtests are measured against, and requires `terminal_soc_fraction` to equal
`initial_soc_fraction`. The composed margin is necessarily at or below the single
full-horizon margin, because restoring SOC every day removes inter-day arbitrage. Both
remain labelled upper bounds. The composed schedule carries a `market_day` column and its
summary records the per-day solver statuses and the largest terminal-energy error.

The optimizer uses these conventions:

- charge MW and MWh are grid imports settled at the DAM price;
- discharge MW and MWh are grid exports settled at the DAM price;
- stored energy increases by grid charge multiplied by charge efficiency;
- stored energy falls by grid discharge divided by discharge efficiency;
- a binary operating mode prevents simultaneous charging and discharging;
- the terminal SOC defaults to the initial SOC, preventing free end-of-horizon depletion;
- an optional daily cycle cap limits grid-delivered discharge MWh divided by nameplate MWh;
- availability scales battery power capability, while grid limits remain absolute;
- negative charging costs are preserved when the battery is paid to consume energy;
- the summary's `equivalent_full_cycles` is grid-side (grid discharge divided by nameplate
  energy); the degradation model separately uses cell-side cycles (grid discharge divided by
  discharge efficiency, then by nominal energy), so the two figures intentionally differ.

Perfect foresight assumes every future price is known. Its result is therefore a
deterministic gross-margin upper bound under the supplied constraints—not a forecast and
not expected investment revenue. It excludes forecast error, imbalance exposure, bid
acceptance, market access, taxes, financing, subsidies, grid feasibility, and revenues
outside the Day-Ahead Market.

## 6. Generate walk-forward naïve forecasts

```bash
greek-bess forecast-naive \
  data/curated/henex_prices.csv \
  --methods daily_persistence weekly_persistence rolling_mean ensemble \
  --rolling-window-days 28 \
  --start-day 2025-02-01 \
  --output outputs/naive_forecasts.csv
```

This writes the interval forecasts and `outputs/naive_forecasts.metrics.json`.

All intervals for a target market day are forecast before any realized price from that
day is added to history. The methods are:

- `daily_persistence`: same wall-clock market slot on the previous day;
- `weekly_persistence`: same slot seven days earlier;
- `rolling_mean`: prior values for the same slot within the selected window;
- `ensemble`: mean of the causal forecasts available for that interval.

Wall-clock slots and occurrence ranks handle 23/25-hour and 92/100-quarter-hour DST days.
The metrics exclude MAPE because zero and negative electricity prices make it unstable or
misleading. MAE, RMSE, mean error, median absolute error, WAPE, correlation and
negative-price precision/recall are reported instead.

## 7. Backtest forecast-planned dispatch

```bash
greek-bess backtest-forecast-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --method ensemble \
  --rolling-window-days 28 \
  --start-day 2025-02-01 \
  --output outputs/forecast_dispatch_intervals.csv
```

This produces:

- `outputs/forecast_dispatch_intervals.csv`;
- `outputs/forecast_dispatch_intervals.daily.csv`;
- `outputs/forecast_dispatch_intervals.summary.json`.

For each market day, the backtest optimizes dispatch using forecast prices, settles the
planned quantities against realized prices, and runs a perfect-foresight solve under the
same battery constraints. Initial SOC is restored at day-end for fair daily comparison.

Dispatch is run only for market days whose selected forecast is complete. The summary
retains metrics for the full requested evaluation period and separately reports metrics
for dispatched days, the fractions of days and intervals backtested, missing forecast
intervals, and every excluded date. For example, daily persistence cannot forecast the
spring clock slots that did not exist on the preceding 23-hour market day; those gaps are
reported rather than silently hidden. The ensemble normally remains complete because it
can use available weekly and rolling-history components.

The backtest assumes price-taking planned quantities are fully accepted. Bid acceptance,
imbalance exposure and route-to-market constraints remain excluded and must be modeled
before any commercial use.

## 8. Run the ML forecast benchmark

```bash
greek-bess forecast-ml \
  data/curated/henex_prices.csv \
  --validation-start-day 2024-01-01 \
  --test-start-day 2025-01-01 \
  --models ridge hist_gradient_boosting \
  --feature-window-days 28 \
  --refit-frequency-days 7 \
  --min-training-days 365 \
  --output outputs/ml_forecasts.csv
```

The training period contains only dates before `validation-start-day`. Model selection
uses validation RMSE only. The test period begins at `test-start-day` and is never used to
select the winning model. At each refit, only earlier realized market days are fitted;
the JSON summary records the exact training start, training end and forecast start for
every model refit.

Features include market-clock/calendar cycles, causal daily/two-day/weekly price lags,
and prior matching-slot rolling statistics. Missing historical features are imputed by a
transformer fitted only on the current training sample. No target-day realized price is a
feature. External weather, fuel, renewable and interconnector inputs remain excluded
until their publication timestamps and day-ahead availability can be validated.

The output CSV includes validation/test labels, all four naïve forecasts and both ML
forecasts. The summary contains forecast metrics, validation and test rankings, selected
model, feature provenance and refit logs.

## 9. Compare held-out ML and naïve dispatch value

```bash
greek-bess backtest-ml-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --validation-start-day 2024-01-01 \
  --test-start-day 2025-01-01 \
  --min-training-days 365 \
  --output outputs/ml_dispatch.csv
```

This runs every ML model and naïve baseline over the identical held-out test days for
which all comparison forecasts are complete. It reports excluded dates, forecast error,
realized dispatch margin, the common perfect-foresight ceiling, value capture and regret.
The selected model's interval schedule is written to `ml_dispatch.csv`; forecasts, all
method/day results and both forecast and dispatch summaries are written beside it.

Forecast RMSE and dispatch value are both reported because the lowest price error does
not necessarily produce the most valuable battery schedule. Synthetic demonstrations
must not be interpreted as evidence of real project profitability.

## 10. Simulate degradation and augmentation-aware dispatch

```bash
greek-bess simulate-degradation-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --degradation-config examples/illustrative_degradation_with_augmentation.json \
  --output outputs/degradation_dispatch.csv
```

This writes:

- `outputs/degradation_dispatch.csv`, the interval dispatch schedule annotated with the
  beginning-of-day degraded energy and power limits;
- `outputs/degradation_dispatch.daily.csv`, daily throughput, margin, capacity, warranty
  and augmentation state;
- `outputs/degradation_dispatch.cohorts.csv`, the final state of the initial battery and
  every separately aged augmentation cohort;
- `outputs/degradation_dispatch.summary.json`, aggregate market margin, physical state,
  warranty indicators, assumptions and policy labels.

Calendar fade and cycle fade are linear and additive within each cohort. Equivalent full
cycles use cell-side discharged energy: grid discharge divided by discharge efficiency,
then divided by that cohort's nominal energy. Daily cell throughput is allocated across
cohorts in proportion to beginning-of-day usable energy. Retained capacity cannot fall
below zero, and power scales with retained capacity raised to the configured exponent.

A capacity event is applied at the beginning of its dated market day. With an empty
`retired_cohort_ids` list it is an augmentation and does not reset old cells. When named
cohorts are retired, the event becomes an explicit replacement: those cohorts leave the
fleet and the new capacity begins with zero age and throughput. Added nominal energy,
charge power, discharge power and event cost are recorded independently. The cost is not
subtracted from DAM market margin. The separate v0.6 finance workflow places it into the
dated project cash flow.

The warranty fields are screening assumptions, not an interpretation of an OEM contract.
When `enforce_warranty_throughput_limit` is `true`, the day-level optimizer limits grid
discharge so proportional cohort allocation cannot exceed the configured per-cohort EFC
ceiling. Retained-capacity warranty and retirement thresholds are reported as indicators;
they do not automatically repair, retire or replace the asset.

The included degradation JSON is intentionally illustrative. In particular, its fade
rates, warranty values, augmentation size, date and zero placeholder cost are not Greek
market facts or OEM evidence. Replace every value with documented project-specific
assumptions before interpreting a run.

The dispatch path still uses perfect foresight within each market day and restores the
initial SOC fraction at day-end. It is therefore a degraded-capacity gross-margin upper
bound—not expected revenue or an investment conclusion.

## 11. Evaluate unlevered project finance

The finance workflow consumes a complete daily operating-results file. The degradation
dispatch daily output already contains the required columns:

- `market_day`;
- `net_market_margin_eur`;
- `grid_discharge_mwh`;
- optional `augmentation_cost_eur`.

```bash
greek-bess evaluate-project-finance \
  outputs/degradation_dispatch.daily.csv \
  --finance-config examples/illustrative_finance_not_project_specific.json \
  --output outputs/project_cash_flows.csv
```

This writes:

- `outputs/project_cash_flows.csv`, with time-zero CAPEX and annual cash-flow totals;
- `outputs/project_cash_flows.daily.csv`, with daily market margin, OPEX, augmentation,
  terminal costs, discount factors and discounted cash flow;
- `outputs/project_cash_flows.summary.json`, with NPV, IRR status, simple and discounted
  payback, break-even margin realization and maximum initial CAPEX.

The operating path must contain every calendar day from `project_start_day` through
`project_end_day`. Missing days, duplicates and unsorted dates are rejected. The finance
engine never repeats a historical year, fills missing revenue with zero or invents a
future price path.

`operating_margin_case` must explicitly be one of:

- `perfect_foresight_upper_bound`;
- `historical_forecast_backtest`;
- `user_supplied_scenario`.

The configured `market_margin_realization_fraction` can reduce the supplied margin for a
transparent sensitivity, but it does not convert a perfect-foresight upper bound into an
expected forecast. The included finance JSON contains deliberately illustrative round
numbers and is not a Greek construction-cost estimate, financing offer or recommendation.

The calculation is unlevered, nominal, pre-tax and pre-subsidy. It excludes debt,
financing fees, working capital, grid feasibility, bid acceptance and revenues from the
Intraday, Balancing or reserve markets. A positive NPV flag is a mathematical result under
the inputs—not a build recommendation.

## 12. Decompose an accepted replay by delivery year

Aggregate multi-year margins conceal regime dependence: a gas-crisis year, a low-price year
and a negative-price year average into one number. `decompose-annual-replay` splits an
already-computed replay into delivery years without adding a model, a market or a
transformation.

```bash
greek-bess decompose-annual-replay \
  data/curated/henex_prices.csv \
  --perfect-foresight-schedule outputs/perfect_foresight_daily.csv \
  --daily-results ensemble=outputs/forecast_dispatch.daily.csv \
  --daily-results rolling_mean=outputs/rolling_mean_dispatch.daily.csv \
  --energy-capacity-mwh 100 \
  --output outputs/annual_overview.csv
```

This produces:

- `outputs/annual_overview.csv`, one row per delivery year with market-day coverage, a
  partial-year flag, interval counts by resolution, preserved negative, zero and missing
  price counts, price context including the mean daily price range, and the
  perfect-foresight ceiling for that year;
- `outputs/annual_overview.forecast.csv`, one row per delivery year and forecast method, with
  backtested-day coverage, realized margin, that method's own-days ceiling, regret, capture
  and loss-making days;
- `outputs/annual_overview.common_day.csv`, the same per-year comparison restricted to the
  market days every supplied method backtested, where the ceiling must be identical and the
  recorded spread proves it;
- `outputs/annual_overview.summary.json`, with the year list, the partial years, the
  ceiling-reconciliation residual and the labels below.

Conventions:

- **A delivery year is the calendar year of the interval's CET/CEST market-day start**, the
  same convention the committed custody records use. Grouping by UTC year instead moves the
  interval beginning 31 December 23:00Z into the earlier year.
- Partial years are labelled and carry their market-day count. Per-market-day figures are
  within-period averages; **no annual figure is annualized, extrapolated or scaled to a full
  year**.
- The supplied schedule must settle every interval at the price the supplied history
  publishes, otherwise the decomposition is refused: that is what proves the schedule was
  solved on this history.
- Use `--daily-solves` for the schedule. A full-horizon solve may charge on 31 December and
  discharge on 1 January, which splits one trade across two delivery years.
- Annual perfect-foresight figures remain labelled gross-margin upper bounds and annual
  forecast figures remain historical backtest outcomes. No probability, percentile, loss
  metric or ranking of years is produced.

The `Decompose the accepted replay by delivery year` GitHub Actions workflow runs the whole
sequence against an accepted `greek-dam-official-history` artifact, after verifying it
against its committed custody record, and uploads the per-year tables as a private artifact.

## Record and verify custody of an accepted official artifact

An accepted official artifact lives outside Git, so the repository holds a fingerprint of it
rather than the data. `record-custody` builds that fingerprint and `verify-custody` checks a
stored copy against it:

```bash
greek-bess record-custody greek-dam-official-history \
  --artifact-name greek-dam-official-history \
  --source-run-id 32971677163 \
  --source-workflow "Fetch official Greek market history" \
  --output docs/custody/greek-dam-official-history.json

greek-bess verify-custody greek-dam-official-history \
  --record docs/custody/greek-dam-official-history.json \
  --report verification.json
```

A custody record contains no official price. It holds per-file digests and content-level
invariants of the normalized series, including a digest of the interval and price series that
is independent of CSV column order, file formatting and float repr — so a re-export verifies
while a single revised cent does not. `verify-custody` returns exit code `2` on any
difference, which is a finding to investigate rather than a check to re-run.

## Quality-result exit codes

- `0`: ingestion and quality checks passed;
- `1`: retrieval, parsing or configuration failed;
- `2`: data was parsed but failed required quality checks.

Missing prices are never silently interpolated. Negative and zero prices are preserved as valid values.

## Run the tests

The test suite uses only synthetic fixtures and temporary workbooks:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

No official prices or personal API credentials are required.


### Build point-in-time features

```bash
greek-bess build-point-in-time-features prices.csv acceptance/fundamentals/features.csv \
  --decision-cutoff config/decision_cutoff.json \
  --decision-lead-minutes 30 --admitted-grades witnessed provider_declared \
  --output acceptance/fundamentals/joined.csv
```

The cutoff, lead and evidence grades are required and have no defaults. The command writes the interval feature frame, a sibling revision/provenance audit and a summary, and exits `2` when any day is excluded. The committed example cutoff is refused. Outputs are private generated research artifacts and must not be committed.


### Benchmark the fundamentals ablation

```bash
greek-bess benchmark-fundamentals-forecast prices.csv \
  --features acceptance/fundamentals/joined.csv \
  --feature-set-sha256 <digest recorded by the join> \
  --decision-cutoff config/decision_cutoff.json \
  --decision-lead-minutes 30 --admitted-grades witnessed provider_declared \
  --price-regime-bands 0 50 150 \
  --validation-start-day 2024-01-01 --test-start-day 2025-01-01 \
  --output acceptance/fundamentals/benchmark.csv
```

Runs the control arm (`ridge`, `hist_gradient_boosting` on calendar and price-history features)
and the challenger arm (`ridge_fundamentals`, `hist_gradient_boosting_fundamentals`, the same
models with the accepted point-in-time columns appended) over the same delivery days, the same
fixed hyperparameters, the same seed and the same refit cadence. Within each arm the model is
chosen on validation RMSE alone; test metrics never select.

Every declaration is required and cross-checked against the join that produced the feature
frame: the command refuses to run when the feature-set digest, the cutoff schedule, the decision
lead or the admitted evidence grades differ from what the join recorded, or when the frame does
not hash to the digest its own summary states. `--price-regime-bands` has no default because
which price levels are worth separating is a judgment; the bands are ascending upper edges in
EUR/MWh and the run records the ones it used.

A delivery day missing any accepted feature is excluded from every arm by its named cause and is
never imputed, and the summary records the count per cause. A run whose common held-out days do
not cover a complete meteorological season of quarter-hour deliveries is labelled exploratory and
carries the suffix saying so. Outputs are private generated research artifacts and must not be
committed.


### Settle the ablation into euro

```bash
greek-bess benchmark-fundamentals-dispatch prices.csv \
  --config config/battery.json \
  --forecasts acceptance/fundamentals/benchmark.csv \
  --methods rolling_mean ensemble ridge ridge_fundamentals \
  --output acceptance/fundamentals/settled.csv
```

Plans each named arm from its own forecast and settles all of them at the same realized prices,
then records the incremental margin of every challenger over its own control. This is the primary
comparison of the milestone; the forecast benchmark's RMSE explains the mechanism but does not
decide, because the project's own accepted evidence shows price error and settled value disagree.

`--methods` is required and has no default: a comparison states which arms it settled. Every
challenger must be named beside its own control, and the command refuses a challenger named
alone — comparing it against anything but the identical model on price history alone is not the
ablation. Naming baselines as well adds a second set of incremental rows, recorded separately
from the control comparison.

The forecast benchmark's summary is read from beside the forecast CSV unless `--forecast-summary`
names it, and the comparison carries that run's feature-set digest, cutoff schedule, decision
lead, admitted evidence grades and exploratory label forward rather than restating them. The
settled days are exactly the held-out days the ablation recorded as common to every baseline and
both arms: a gap on one of those days contradicts the record and is refused rather than excluded,
and a table whose held-out common day count disagrees with its own summary is refused as well.

The comparison refuses to run unless it is like for like. One battery configuration plans every
arm, its terminal SOC must equal its initial SOC, and the perfect-foresight ceiling is asserted
identical across arms to `1e-6` EUR — a spread above that is reported by naming the two arms and
their ceilings, never reconciled. What every arm shared is written into the summary as
`equivalent_basis` so a reader need not take the equivalence on trust.

Four artifacts are written: the settled interval schedule for every method, the daily results, the
paired daily differences per comparison, and the summary. The paired differences carry both
settled margins and their difference for every common day, and the summary records the sign counts
and the total. No interval, dispersion or significance statistic is derived from them: they are a
series of historical outcomes on one period, not a sample from a distribution this project claims
to know. A challenger that settles less than its control is recorded exactly as one that settles
more. Outputs are private generated research artifacts and must not be committed.

## Custody-gated fundamentals benchmark

Dispatch `.github/workflows/benchmark-fundamentals.yml` only after a dated acceptance document is committed. Supply accepted official-history and feature-table run IDs, the accepted feature-set SHA-256, and the acceptance-document SHA-256. The workflow re-audits before benchmarking, records and verifies all v0.9 manifests, renders the generic report, and uploads interval evidence privately.
