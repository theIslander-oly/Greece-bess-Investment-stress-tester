# Greek Battery Investment Stress Tester

**A Greek Day-Ahead Market battery replay and research benchmark.** The tool replays
provenance-verified official Greek DAM prices against an explicitly configured standalone
battery, computes the historical perfect-foresight gross-margin upper bound, and measures how
much of that ceiling leakage-safe causal forecasts would have captured. Deterministic, named
stress scenarios and transparent screening arithmetic (degradation, unlevered cash flows) build
on that replay core.

This is not financial advice, an investment-grade forecast, a bankable revenue study or a
substitute for legal, tax, grid-connection and market-access diligence.

**Current release:** `v0.8.0` — a deterministic report renderer over verified run manifests,
and only verified run manifests.

## What this tool cannot tell you

Read this before interpreting any output:

- **It does not predict prices or revenue.** Every result is either a historical
  perfect-foresight upper bound or a historical forecast benchmark on one selected period.
- **The replayed history predates battery competition.** Storage units were only integrated
  into the Greek Day-Ahead and Intraday Markets in April 2026, so nearly all replayed prices
  come from a market with no operating batteries. As the supported ~1 GW fleet and merchant
  projects enter, price spreads are widely expected to compress, so historical replay tends to
  overstate what a future merchant DAM-only battery could earn.
- **It models one revenue stream only.** Real Greek battery projects typically combine DAM and
  intraday arbitrage with balancing-market participation, and most near-term projects hold
  state availability-support contracts from the 2023-2024 storage tenders. None of that is
  modeled here, by design, until it can be independently validated.
- **Illustrative inputs stay illustrative.** The example battery, degradation and finance
  configurations are placeholders. Any number computed from them is arithmetic, not evidence.

## Current implementation

The current implementation provides:

- a canonical Greek Day-Ahead Market interval schema;
- an ENTSO-E A44 day-ahead price client for the Greek bidding zone;
- a HEnEx `EL-DAM_Results_EN` workbook parser;
- UTC, CET/CEST market-clock and Europe/Athens timestamp views;
- correct 23/25-hour and 92/100-quarter-hour daylight-saving days;
- publication revision and raw-file SHA-256 provenance;
- missing-price, duplicate, resolution and daily-completeness checks;
- HEnEx-versus-ENTSO-E interval comparison;
- deterministic synthetic data for public demonstrations and tests;
- automated tests covering parsing, negative prices, DST and source mismatches;
- a mixed-integer perfect-foresight Greek DAM dispatch optimizer;
- explicit grid-meter charge/discharge conventions and one-way efficiencies;
- power, energy, SOC, availability, grid and terminal-energy constraints;
- optional daily equivalent-cycle limits, market fees and degradation cost;
- interval-level dispatch and revenue decomposition;
- a mandatory result label identifying perfect foresight as an upper bound;
- strictly causal daily, weekly and rolling-seasonal naïve price forecasts;
- a leakage-safe blended forecast baseline;
- signed-price-safe forecast metrics, including negative-price detection;
- daily forecast-planned dispatch settled against realized prices;
- a like-for-like perfect-foresight ceiling, value capture and regret comparison;
- explicit disclosure of incomplete forecast days and backtested coverage;
- causal calendar, lag and rolling-price feature engineering;
- ridge and histogram-gradient-boosting ML benchmarks;
- explicit training, validation and held-out test periods;
- deterministic walk-forward model refitting with training-date audit logs;
- validation-only model selection and separate held-out test rankings;
- like-for-like held-out dispatch comparison against every naïve baseline;
- additive calendar and equivalent-cycle capacity fade with explicit assumptions;
- separately aged initial and augmentation cohorts;
- usable energy and charge/discharge power evolution;
- proportional cell-throughput allocation across cohorts;
- retained-capacity, throughput-warranty and retirement-threshold screening;
- optional hard per-cohort EFC warranty constraints;
- dated augmentation or replacement capacity and separately recorded event cost;
- day-by-day perfect-foresight dispatch using beginning-of-day degraded limits;
- an explicit continuous daily operating-path contract for project finance;
- separately itemized initial CAPEX, fixed OPEX, variable OPEX and augmentation costs;
- OPEX escalation, residual value and decommissioning assumptions;
- exact-date discounted unlevered cash flows, NPV and IRR;
- simple and discounted payback;
- maximum initial CAPEX and market-margin break-even outputs;
- mandatory operating-margin labels that preserve upper-bound and backtest limitations;
- a daily-composed perfect-foresight mode that restores SOC at every day end;
- a per-delivery-year decomposition of an accepted replay on the CET/CEST market clock, with
  partial-year labelling, per-method capture and a like-for-like common-day comparison;
- a deterministic spread compression about a declared daily reference level, with a declared
  basis, exact per-day range scaling and preserved zero and negative prices;
- an executable pre-auction publication-timing audit, retained but **unused**: ADMIE load and RES
  forecasts are out of scope, and the audit stands as the executable form of that refusal;
- a versioned run manifest and report contract that carries any result summary verbatim under a
  stable projection — declared result kind, the basis it reports on, its required non-empty
  result label and the project's standing exclusions — refusing an unlabelled result and a
  manifest from a schema version it does not understand;
- a `render-report` command that renders verified run manifests, and only verified run
  manifests, into one self-contained static HTML report plus a machine-readable index: figures
  grouped by basis, each carrying its recorded label, its basis in reader-facing words and the
  standing exclusions beside it, with the declaration checklist as the landing state when no
  manifest is supplied. It computes nothing, reads no environment and makes no network
  request.

The first v0.7 foundation also provides deterministic, seeded seasonal block-bootstrap price
paths with sampled-block provenance. Each validated path can now be dispatched independently
under one shared battery configuration and availability assumption. Probability outputs,
additional shocks, finance integration and the user interface remain excluded.

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
[the source-era policy](docs/bootstrap_source_era_policy.md) before choosing, and use
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
[`LIMITATIONS.md`](LIMITATIONS.md).

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
week and a great deal in a high-spread one. See [`LIMITATIONS.md`](LIMITATIONS.md).

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

## Repository guide

- [`PROMPT.md`](PROMPT.md) — approved mission, scope and interpretation rules.
- [`PLAN.md`](PLAN.md) and [`STATUS.md`](STATUS.md) — milestones and current progress.
- [`DECISIONS.md`](DECISIONS.md) — dated analytical and repository decisions.
- [`METHODOLOGY.md`](METHODOLOGY.md) — end-to-end analytical method.
- [`LIMITATIONS.md`](LIMITATIONS.md) — consolidated cautions and exclusions.
- [`docs/data_sources.md`](docs/data_sources.md) and
  [`docs/data_dictionary.md`](docs/data_dictionary.md) — official-source provenance and schema.

The first GitHub snapshot imports the already completed v0.1-v0.6 implementation. Its earlier
history is preserved in the versioned implementation reports; no historical commits are
fabricated.

## Data policy

Real research runs use official data fetched privately by the user. Official raw prices are not bundled with this project.

- HEnEx data is imported from a workbook obtained by the user.
- ENTSO-E data is fetched with the user's personal API token.
- Public demonstrations and automated tests use clearly labelled synthetic prices.
- A real token must never be committed or printed in logs.

The HEnEx parser has been production-checked against the official English v01 result
workbooks for 24 and 25 August 2026. Both files passed the complete-day and continuity
checks without code changes. See
[`docs/official_data_acceptance_2026-08-25.md`](docs/official_data_acceptance_2026-08-25.md)
for hashes, boundaries and acceptance results. The workbooks themselves are not
redistributed by this repository.

The repository also includes reproducible acquisition commands for the verified 2020-2025
HEnEx annual archives, incremental daily HEnEx publications, and ADMIE's public Operation &
Market Files API. Every retrieval writes a manifest with source URL, coverage, retrieval time,
SHA-256 and publication metadata where the provider exposes it. Raw and normalized official
data remain ignored by Git.

**ADMIE's load and RES forecasts are out of scope** (decision entry 2026-09-01). The 2026-08-26
quarantine is closed as never accepted rather than discharged: no ADMIE field ever entered
forecasting, and none may. Forecasting uses causal price-history features only.

The retrieval client and `audit-admie-publication-timing` are retained and documented as unused.
They are the executable form of the refusal, kept so a future declaration could be tested without
rebuilding them, and are not dead code to be pruned. The audit checks only a *declared* gate
closure and the repository still refuses to supply the market rule; see
[`docs/admie_publication_timing_policy.md`](docs/admie_publication_timing_policy.md). Reopening
the question needs that declaration, a contemporaneous audited window, format acceptance and a new
dated decision.

Accepted official artifacts are held outside Git as encrypted assets on a release in the
private repository, and each is fingerprinted by a price-free custody record committed under
`docs/custody/`. `verify-custody` re-derives that fingerprint from a stored copy, so a copy can
be proven to be the accepted artifact and a re-retrieval that differs is detected rather than
silently adopted — which matters because official publications are revised. The procedure and
the operator steps are in
[`docs/official_artifact_custody.md`](docs/official_artifact_custody.md).

Review the source terms before any deployment or redistribution:

- [HEnEx Terms of Use](https://www.enexgroup.gr/web/guest/terms-of-use)
- [ENTSO-E Legal Terms](https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions)

## Installation

Python 3.12 is required.

```bash
python -m venv .venv
```

Activate the virtual environment, then install the package:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development and the same checks used by GitHub Actions:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest -v
python -m build --wheel
```

CI runs these checks on every pull request without private API keys or official datasets. Tests
use deterministic synthetic or purpose-built small inputs.

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
[`Fetch official ENTSO-E prices`](.github/workflows/fetch-entsoe.yml) GitHub Actions
workflow performs the same retrieval using an encrypted repository secret and publishes
only the normalized CSV and quality JSON as a short-lived artifact. See the
[`secure GitHub retrieval guide`](docs/entsoe_github_retrieval.md).

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
[`Reconcile HEnEx and ENTSO-E prices`](.github/workflows/reconcile-henex-entsoe.yml) workflow
performs the whole comparison inside Actions: it reads the accepted history artifact from an
earlier run, derives the reconciliation window from that history, retrieves ENTSO-E prices for
exactly the same window and uploads the interval-level classification. Only interval counts,
classification counts and aggregate difference statistics reach the job log. See the
[`secure GitHub retrieval guide`](docs/entsoe_github_retrieval.md).

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

## Package layout

```text
src/greek_bess/
  cli.py
  data/
    admie.py
    admie_timing.py
    entsoe.py
    henex.py
    quality.py
    schema.py
    synthetic.py
    timezones.py
  dispatch/
    perfect_foresight.py
  analysis/
    annual.py
  forecast/
    naive.py
    ml.py
  degradation/
    model.py
  finance/
    model.py
  backtest/
    degradation_dispatch.py
    forecast_dispatch.py
    ml_dispatch.py
  reporting/
    contract.py
    render.py
  stress/
    availability.py
    bootstrap.py
    bootstrap_dispatch.py
    ensemble.py
    price_level.py
    spread.py
examples/
  battery_50mw_100mwh.json
  illustrative_degradation_with_augmentation.json
  illustrative_finance_not_project_specific.json
tests/
```

## Next phase

The approved v0.7 deterministic scenario scope is complete: source-era selection, additive
level sensitivity, spread compression, declared availability/outage paths, non-probabilistic
scenario ranges and declared negative-price events have landed. The formal completed-v0.7 review
found no correctness or data-integrity defect and reconciled one roadmap wording contradiction
about availability provenance. The v0.8 research interface and exportable reports were opened on
1 September 2026 by explicit user approval, with the approved scope amended and the design
recorded in `docs/v0.8_design.md`. v0.8.0, the report rendering foundation, has landed: a
deterministic `render-report` CLI that renders verified run manifests — and only verified run
manifests — into self-contained static reports with a machine-readable index, adding no runtime
dependency, no server and no computation. The next milestones are v0.8.1, multi-run composition,
and v0.8.2, a separate dated decision on whether any interactive viewer is added on top of the
static renderer. AI-generated explanations remain outside v0.8.
Percentile outputs (P5/P50/P95) and loss probabilities were removed from the roadmap because
the seasonal bootstrap resamples a non-stationary 2020-2026 history uniformly and therefore
supports no calibrated probability interpretation; see the 2026-08-27 decision entries.
Tax, subsidy and leveraged financing remain excluded until
their jurisdiction-specific assumptions are independently validated. HEnEx workbook and complete
official-history acceptance have passed, and both the perfect-foresight optimizer and the
forecast-dispatch backtests have now been accepted over that full history. Private-token ENTSO-E
retrieval and the cross-source reconciliation passed on 27 August 2026: 74,662 of 74,663 official
intervals match exactly and neither source omits an interval the other publishes. ADMIE exogenous
variables are no longer part of this track at all: those forecasts were removed from scope on
1 September 2026, so the gate-closure declaration, the live audited window and the file-format
acceptance are questions the project no longer asks. The audit and retrieval client remain in the
repository, documented as unused.

## Development

Development setup is deliberately contributor-neutral. The supported environment and the
validation gates are defined by `pyproject.toml`, `scripts/bootstrap-dev-env.sh`, `AGENTS.md`
and `CONTRIBUTING.md`; editor- and service-specific session configuration is not tracked.
Repository content — commits, pull requests, comments and documentation — carries no tool or
assistant attribution, a record-keeping convention described in `CONTRIBUTING.md`.
Pytest fails on warnings attributed to `greek_bess` or to the tests, because those are the
project's to fix; a warning attributed to a dependency is reported without failing the run, since
dependencies are installed from ranges and an upstream release should not decide when validation
breaks.

```bash
scripts/bootstrap-dev-env.sh
ruff check . && mypy && pytest -v && python -m build --wheel
```

## Project records

- [Changelog](CHANGELOG.md)
- [Release notes v0.2.0](docs/release_notes_v0.2.md)
- [Implementation report v0.2](docs/implementation_report_v0.2.md)
- [Release notes v0.3.0](docs/release_notes_v0.3.md)
- [Implementation report v0.3](docs/implementation_report_v0.3.md)
- [Release notes v0.3.1](docs/release_notes_v0.3.1.md)
- [Implementation report v0.3.1](docs/implementation_report_v0.3.1.md)
- [Release notes v0.4.0](docs/release_notes_v0.4.md)
- [Implementation report v0.4](docs/implementation_report_v0.4.md)
- [Release notes v0.5.0](docs/release_notes_v0.5.md)
- [Implementation report v0.5](docs/implementation_report_v0.5.md)
- [Release notes v0.6.0](docs/release_notes_v0.6.md)
- [Implementation report v0.6](docs/implementation_report_v0.6.md)
- [Release notes v0.6.1](docs/release_notes_v0.6.1.md)
- [Implementation report v0.6.1](docs/implementation_report_v0.6.1.md)
- [Release notes v0.6.2](docs/release_notes_v0.6.2.md)
- [Implementation report v0.6.2](docs/implementation_report_v0.6.2.md)
- [Release notes v0.6.3](docs/release_notes_v0.6.3.md)
- [Implementation report v0.6.3](docs/implementation_report_v0.6.3.md)
- [Implementation report v0.7 foundation](docs/implementation_report_v0.7.md)
- [Implementation report v0.7.1 price-level shock](docs/implementation_report_v0.7.1.md)
- [Implementation report v0.7.2 bootstrap dispatch](docs/implementation_report_v0.7.2.md)
- [Implementation report v0.7.4 per-year replay decomposition](docs/implementation_report_v0.7.4.md)
- [Implementation report v0.7.5 bootstrap source-era policy](docs/implementation_report_v0.7.5.md)
- [Implementation report v0.7.6 spread compression](docs/implementation_report_v0.7.6.md)
- [Implementation report v0.7.7 scenario-ensemble range reporting](docs/implementation_report_v0.7.7.md)
- [Implementation report v0.7.8 availability and outage paths](docs/implementation_report_v0.7.8.md)
- [Implementation report v0.7.9 declared negative-price events](docs/implementation_report_v0.7.9.md)
- [Implementation report v0.7.10 ADMIE publication-timing acceptance](docs/implementation_report_v0.7.10.md)
- [Implementation report v0.7.11 run manifest and report contract](docs/implementation_report_v0.7.11.md)
- [ADMIE filetype acceptance implementation report](docs/implementation_report_admie_filetype_acceptance_2026-08-31.md)
- [Official annual-history acceptance](docs/official_history_acceptance_2026-08-26.md)
- [Official multi-year operational acceptance](docs/official_multiyear_operational_acceptance_2026-08-27.md)
- [Official HEnEx to ENTSO-E reconciliation](docs/official_source_reconciliation_2026-08-27.md)
- [Per-delivery-year replay decomposition](docs/official_annual_decomposition_2026-08-28.md)
- [Durable custody of accepted official artifacts](docs/official_artifact_custody.md)
- [Bootstrap source-era and resolution policy](docs/bootstrap_source_era_policy.md)
- [ADMIE pre-auction publication-timing policy](docs/admie_publication_timing_policy.md)
- [ADMIE day-ahead forecast filetype acceptance](docs/admie_filetype_acceptance_2026-08-31.md)
- [Run manifest and report contract](docs/run_manifest_contract.md)
- [Current status](STATUS.md)
- [Implementation plan](PLAN.md)
- [Contributing guidance](CONTRIBUTING.md)
- [Security and private-data guidance](SECURITY.md)

## License

Copyright is reserved. See [LICENSE](LICENSE). The repository is available for viewing,
educational evaluation and portfolio demonstration; reuse requires prior permission.
