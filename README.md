# Greek Battery Investment Stress Tester

**A Greek Day-Ahead Market battery replay and research benchmark.** The tool replays
provenance-verified official Greek DAM prices against an explicitly configured standalone
battery and compares a historical perfect-foresight gross-margin upper bound with
leakage-safe causal forecast backtests.

**See the output immediately:** open the
[synthetic-only sample report](docs/sample_report.html), or regenerate it from a clone with
`greek-bess demo --output docs/sample_report.html`. It uses no token or official data and is
not investment evidence, expected revenue, financial advice or a bankable study.

## Accepted official-history findings

These are **historical replay and backtest results, not expected revenue, a forecast or
investment evidence**. The accepted history covers 1 November 2020 through 25 August 2026;
2020 and 2026 are partial years. Every figure below is transcribed from the
[accepted decomposition](docs/official_annual_decomposition_2026-08-28.md).

| Delivery year | Accepted official market days | Daily-composed perfect-foresight gross-margin ceiling (EUR) | Historical causal-method capture ratio on each method's own backtested days | Negative-price intervals | Mean within-day price range (EUR/MWh) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 **(partial: 61 days)** | 61 | 230,141 | 0.7461-0.8554 | 2 | 52.07 |
| 2021 | 365 | 1,960,658 | 0.6587-0.7709 | 5 | 76.63 |
| 2022 | 365 | 5,859,178 | 0.5548-0.6937 | 1 | 210.52 |
| 2023 | 365 | 3,577,481 | 0.6468-0.7427 | 0 | 121.75 |
| 2024 | 366 | 4,775,370 | 0.7905-0.8600 | 11 | 162.59 |
| 2025 | 365 | 5,151,831 | 0.7772-0.8724 | 177 | 171.90 |
| 2026 **(partial: 237 days)** | 237 | 3,420,070 | 0.6402-0.7578 | 1,571 | 181.30 |
| **Accepted-history total** | **2,124** | **24,974,729.59** | — | **1,767** | — |

The capture range in each row is the lowest and highest recorded ratio across
`daily_persistence`, `weekly_persistence`, `rolling_mean` and `ensemble`; methods cover
different days. The source report provides the like-for-like common-day comparison. Negative
interval counts across the 1 October 2025 change from hourly to quarter-hour delivery are not
directly comparable; they show the recorded market shift, not a normalized frequency.

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

**Current release:** `v0.9.1` — point-in-time fundamentals ingestion and the availability audit:
one chosen source read by byte range, a typed feature table carrying the publication instant and
byte digest behind every value, and a per-delivery-interval audit against a declared decision
cutoff. Nothing it retrieves is accepted for forecasting, and no surface runs until the operator
declares the cutoff, the decision lead and the sampling geography.

## Quickstart

Python 3.12 or 3.13. No API key and no official data are needed for this; it runs on the
deterministic synthetic series the repository generates for demonstrations.

```bash
python -m pip install -e .

greek-bess demo
```

That single command generates a labelled synthetic year, solves the daily perfect-foresight
ceiling, applies a declared 30% spread compression about each daily mean, solves the stressed
path, evaluates illustrative one-year unlevered project-finance screening arithmetic, records
every result under the manifest contract and composes them into `demo-report.html`. It normally
finishes in well under one minute. The committed
[sample](docs/sample_report.html) is byte-checked against this command by the test suite.

The equivalent first two stages can be run individually:

```bash

greek-bess generate-synthetic \
  --start-day 2025-01-01 --end-day 2026-01-01 \
  --output prices.csv

greek-bess optimize-perfect-foresight prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --daily-solves \
  --output dispatch.csv
```

The second command writes `dispatch.csv` and `dispatch.summary.json`, and prints:

```json
{
  "result_label": "Perfect-foresight Greek DAM gross-margin upper bound composed from independent daily solves; not expected or forecast investment revenue.",
  "solve_mode": "daily_independent_solves",
  "solve_path_counts": {"relaxation_accepted": 365},
  "market_day_count": 365,
  "net_market_margin_eur": 2162101.190159156,
  "grid_charge_mwh": 61918.854685378,
  "grid_discharge_mwh": 54711.5,
  "equivalent_full_cycles": 547.115,
  "nominal_round_trip_efficiency": 0.8836
}
```

That number is what a 50 MW / 100 MWh battery would have made on that synthetic year if it had
known every price in advance. It is a ceiling on one revenue stream, on data that is not real.
`result_label` says so, and travels with every result the tool produces. Reaching a defensible
figure from here means supplying official prices, replacing the illustrative battery, and reading
what the ceiling does and does not bound.

**Where to go next**

| | |
| --- | --- |
| What the results mean and what they cannot | [LIMITATIONS.md](LIMITATIONS.md) |
| How each number is computed | [METHODOLOGY.md](METHODOLOGY.md) |
| Why the tool refuses what it refuses | [DECISIONS.md](DECISIONS.md) |
| Every command, in workflow order | [docs/command_reference.md](docs/command_reference.md) |
| Per-release implementation reports | [docs/history/](docs/history/) |

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
  request. Across many manifests it adds an index grouped by basis that carries no figure at
  all, and it lays a scenario ensemble out side by side: its per-path ranges, its per-scenario
  provenance and the equivalent-basis evidence it recorded.

The first v0.7 foundation also provides deterministic, seeded seasonal block-bootstrap price
paths with sampled-block provenance. Each validated path can now be dispatched independently
under one shared battery configuration and availability assumption. Probability outputs,
additional shocks, finance integration and the user interface remain excluded.

## Command reference

Detailed scenario, transformation and reporting commands have moved to the
[command reference](docs/command_reference.md).

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

Python 3.12 or 3.13. CI runs the suite on both.

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

## Command workflows

The numbered ingestion, validation, analysis, reporting and custody workflows are in the
[command reference](docs/command_reference.md).

## Package layout

```text
src/greek_bess/
  cli/
    _main.py          # parser assembly and the single dispatch point
    _registry.py      # the Command record every subcommand declares
    _support.py       # shared reading, writing and config helpers
    admie.py
    analysis.py
    custody.py
    dispatch.py
    finance.py
    forecast.py
    ingest.py
    manifests.py
    stress.py
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
dependency, no server and no computation. v0.8.1, multi-run composition, has landed on top of
it: an index across many manifests that carries no figure, a scenario ensemble laid out side by
side with its per-path ranges and per-scenario provenance, and explicit rendering of the
equivalent-basis evidence. Making the per-path ranges renderable required recording them in the
ensemble's own run summary rather than reading the CSV beside the run, under the 2026-09-01
decision that keeps the manifest the sole doorway. v0.8.2 closes v0.8 with the static renderer:
the interactive viewer was deliberately declined because it would duplicate a validated
rendering surface, add a dependency and server lifecycle, and create no new evidence. Any future
interactive proposal must identify a need the static report cannot meet and proceed as a
separately approved milestone. The formal completed-v0.8 review then found four defects in the
reporting layer and corrected them in v0.8.3: a verified manifest missing one of its kind's
guaranteed summary keys crashed the renderer instead of stating the absence; a manifest whose
summary contradicted a standing exclusion, or carried distributional vocabulary a kind forbids,
was refused when recorded but not when read and rendered; a non-object `declared_inputs` raised
an unhandled error rather than a contract refusal; and three distinct manifest IDs could reduce
to two in-document anchors, so one index link led to another manifest's block. No analytical,
dispatch, forecast, stress, degradation or finance behaviour changed.
AI-generated explanations remain outside v0.8.

v0.9 was opened on 2 September 2026 as a point-in-time fundamentals forecast benchmark, with the
design recorded in `docs/v0.9_design.md`. It addresses the one open analytic question the
forecasting layer carries: every accepted forecast figure here comes from price history alone,
because validated weather, demand, fuel, renewable and interconnector forecasts are not included.
The milestone asks whether an independently validated exogenous input improves *realized settled
dispatch value*, comparing the two existing model families with and without accepted features
under identical hyperparameters, refit cadence, splits, battery and realized prices. Every feature
value must be provably available before a declared decision cutoff — declared by the operator with
no default, strict, with a publication at the cutoff counting as late — with its availability
evidence graded, every revision stored, the decision-time revision selected, and weaker evidence
quarantined. The source-selection spike ran the same day
(`docs/fundamentals_source_assessment_2026-09-02.md`) and the source is NOAA GFS 0.25° forecast
vintages, taken from the 00 UTC cycle of the day before delivery; the usable record starts at
delivery day 27 February 2021, so 118 of the accepted history's 2,131 delivery days carry no
feature and are excluded rather than filled.

v0.9.1 landed the first code for it: a neutral home for the declared cutoff, the typed
point-in-time feature schema, the NOAA GFS client reading single GRIB2 messages by byte range,
the per-delivery-interval availability audit, the `fetch-fundamentals` and
`audit-feature-availability` commands, a fetch workflow and a daily witness workflow, and the
`point_in_time_availability_audit` manifest kind. `eccodes` is the one new dependency — not
`cfgrib` or `xarray`, which the low-level read does not need. The policy the code enforces is
`docs/point_in_time_feature_contract.md`. **No surface runs yet**: the decision cutoff, the
decision lead and the sampling geography are operator declarations with no defaults, the
committed examples are refused by name, and until all three exist nothing is retrieved, no day is
audited and the witness workflow accumulates no witnessed days — which are the one kind of
evidence here that cannot be produced later. A negative result would be recorded
under the same labels, and a thin accepted coverage makes the run exploratory rather than general.
ADMIE load and RES forecasts stay out of scope by any route, including through another publisher.
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

Per-release implementation reports and release notes live in
[docs/history/](docs/history/), indexed there. The full list follows.

- [Changelog](CHANGELOG.md)
- [Release notes v0.2.0](docs/history/release_notes_v0.2.md)
- [Implementation report v0.2](docs/history/implementation_report_v0.2.md)
- [Release notes v0.3.0](docs/history/release_notes_v0.3.md)
- [Implementation report v0.3](docs/history/implementation_report_v0.3.md)
- [Release notes v0.3.1](docs/history/release_notes_v0.3.1.md)
- [Implementation report v0.3.1](docs/history/implementation_report_v0.3.1.md)
- [Release notes v0.4.0](docs/history/release_notes_v0.4.md)
- [Implementation report v0.4](docs/history/implementation_report_v0.4.md)
- [Release notes v0.5.0](docs/history/release_notes_v0.5.md)
- [Implementation report v0.5](docs/history/implementation_report_v0.5.md)
- [Release notes v0.6.0](docs/history/release_notes_v0.6.md)
- [Implementation report v0.6](docs/history/implementation_report_v0.6.md)
- [Release notes v0.6.1](docs/history/release_notes_v0.6.1.md)
- [Implementation report v0.6.1](docs/history/implementation_report_v0.6.1.md)
- [Release notes v0.6.2](docs/history/release_notes_v0.6.2.md)
- [Implementation report v0.6.2](docs/history/implementation_report_v0.6.2.md)
- [Release notes v0.6.3](docs/history/release_notes_v0.6.3.md)
- [Implementation report v0.6.3](docs/history/implementation_report_v0.6.3.md)
- [Implementation report v0.7 foundation](docs/history/implementation_report_v0.7.md)
- [Implementation report v0.7.1 price-level shock](docs/history/implementation_report_v0.7.1.md)
- [Implementation report v0.7.2 bootstrap dispatch](docs/history/implementation_report_v0.7.2.md)
- [Implementation report v0.7.4 per-year replay decomposition](docs/history/implementation_report_v0.7.4.md)
- [Implementation report v0.7.5 bootstrap source-era policy](docs/history/implementation_report_v0.7.5.md)
- [Implementation report v0.7.6 spread compression](docs/history/implementation_report_v0.7.6.md)
- [Implementation report v0.7.7 scenario-ensemble range reporting](docs/history/implementation_report_v0.7.7.md)
- [Implementation report v0.7.8 availability and outage paths](docs/history/implementation_report_v0.7.8.md)
- [Implementation report v0.7.9 declared negative-price events](docs/history/implementation_report_v0.7.9.md)
- [Implementation report v0.7.10 ADMIE publication-timing acceptance](docs/history/implementation_report_v0.7.10.md)
- [Implementation report v0.7.11 run manifest and report contract](docs/history/implementation_report_v0.7.11.md)
- [ADMIE filetype acceptance implementation report](docs/history/implementation_report_admie_filetype_acceptance_2026-08-31.md)
- [Official annual-history acceptance](docs/official_history_acceptance_2026-08-26.md)
- [Official multi-year operational acceptance](docs/official_multiyear_operational_acceptance_2026-08-27.md)
- [Official HEnEx to ENTSO-E reconciliation](docs/official_source_reconciliation_2026-08-27.md)
- [Per-delivery-year replay decomposition](docs/official_annual_decomposition_2026-08-28.md)
- [Durable custody of accepted official artifacts](docs/official_artifact_custody.md)
- [Bootstrap source-era and resolution policy](docs/bootstrap_source_era_policy.md)
- [ADMIE pre-auction publication-timing policy](docs/admie_publication_timing_policy.md)
- [ADMIE day-ahead forecast filetype acceptance](docs/admie_filetype_acceptance_2026-08-31.md)
- [Run manifest and report contract](docs/run_manifest_contract.md)
- [Command reference](docs/command_reference.md)
- [Implementation report v0.8.0](docs/history/implementation_report_v0.8.0.md)
- [Implementation report v0.8.1](docs/history/implementation_report_v0.8.1.md)
- [Implementation report v0.8.2](docs/history/implementation_report_v0.8.2.md)
- [Completed-v0.8 review](docs/history/implementation_report_v0.8.2_review.md)
- [README findings-first restructuring](docs/history/implementation_report_readme_findings_first_2026-09-02.md)
- [Current status](STATUS.md)
- [Implementation plan](PLAN.md)
- [Contributing guidance](CONTRIBUTING.md)
- [Security and private-data guidance](SECURITY.md)

## License

Copyright is reserved. See [LICENSE](LICENSE). The repository is available for viewing,
educational evaluation and portfolio demonstration; reuse requires prior permission.
