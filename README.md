# Greek Battery Investment Stress Tester

A research and pre-feasibility tool for standalone LFP batteries in the Greek Day-Ahead
Market. It replays provenance-verified official prices, compares causal forecasts through
realized settlement, and tests explicit battery, degradation, finance and stress assumptions.

**Current release:** `v0.9.7`

Perfect foresight is a labelled gross-margin upper bound, never expected revenue. Historical
backtests describe their selected period. Synthetic demonstrations cannot support an investment
conclusion. Outputs are not financial advice or a bankable commercial study.

## Quickstart

Use Python 3.12 or 3.13, preferably in a virtual environment:

```bash
python -m pip install -e .
greek-bess demo
```

Open `demo-report.html`. The command generates deterministic synthetic prices, compares a
perfect-foresight replay with a declared spread-compression stress, applies illustrative finance
assumptions and renders verified result manifests. No API token or official data is needed.
The [synthetic sample report](docs/sample_report.html) is checked byte for byte by the tests.

For an integrated comparison with separate battery ageing for each strategy:

```bash
greek-bess run-integrated-study --study-config examples/integrated_study_synthetic_demonstration.json --output-dir outputs/study --report outputs/integrated-study.html
```

This configuration declares its synthetic history and all study assumptions. The integrated
runner currently supports naive planners and perfect foresight; ML and weather benchmarks are
separate commands. See the [command reference](docs/command_reference.md) for all workflows and
[configuration guide](config/README.md) for declared inputs.

## Accepted official-history findings

These are **historical replay and backtest results, not expected revenue, a forecast or
investment evidence**. The accepted history covers 1 November 2020 through 25 August 2026;
2020 and 2026 are partial years. The delivery-year table is transcribed from the
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

**Point-in-time weather (fundamentals) ablation, held-out 320 common days (2025-10-08 to
2026-08-25), not exploratory.** Each challenger is compared against its own matched control —
identical rows, only the weather columns added — per
[the accepted benchmark](docs/fundamentals_benchmark_2026-09-11.md). The result is mixed and
recorded as mixed:

| Model family | Incremental settled margin vs. matched control (EUR) | Relative |
| --- | ---: | ---: |
| `ridge` | +4,899.71 | +0.14% |
| `hist_gradient_boosting` | −6,843.46 | −0.19% |

Both differences are small next to the day-to-day settlement swings recorded alongside them.
This is a historical research result, not a forecast, expected revenue or investment evidence.

**Stage 9 selection comparison, 329 complete evaluation days (2025-10-01 to 2026-08-25).**
Under the declared 50 MW / 100 MWh battery, validation-margin selection chose
`gradient_lr_005_leaf_15` and settled EUR 3,663,998.68; validation-RMSE selection chose
`ridge_alpha_1` and settled EUR 3,651,359.54. The recorded signed difference is
**EUR +12,639.14**, with more cycling under the margin-selected candidate. This is
`retrospective_supplementary` evidence from one inspected window spanning hourly validation
and quarter-hour evaluation. It changes no shipped selection policy. See the
[approved aggregate record](docs/selection_benchmark_2026-09-11.md) for assumptions, price
errors, cycling, comparator labels and reproducible provenance.

## Capabilities and limits

- **Data:** HEnEx and ENTSO-E ingestion, source reconciliation and artifact custody; UTC interval
  keys with market and Greece views; negative and zero prices retained; missing observations
  reported without interpolation; hourly and quarter-hour daylight-saving transitions.
- **Dispatch and forecasting:** constrained dispatch without simultaneous charge/discharge;
  causal naive and ML benchmarks; point-in-time weather ablation; comparison of forecast
  selection by price error versus validation settled margin.
- **Degradation and finance:** separate capacity cohorts, stored-energy accounting, explicit
  augmentation and operating costs, dated unlevered cash flows and certified IRR where defined.
- **Stress and reporting:** declared price and availability scenarios, bootstrap paths and
  verified-manifest HTML reports. Integrated strategies each carry their own degradation state
  and conditional daily ceiling; the report does not invent a shared ceiling or ranking.

Battery and cost examples are illustrative. A historical ranking does not establish a recurring
advantage, optimal battery size or lifetime return. Intraday, balancing, reserves, taxes,
subsidies, debt, grid feasibility and revenue stacking remain excluded. ADMIE load and RES
forecasts remain excluded; the accepted weather benchmark uses point-in-time GFS inputs.
Read [LIMITATIONS.md](LIMITATIONS.md) before interpreting results and
[METHODOLOGY.md](METHODOLOGY.md) for the calculations and comparison constraints.

## Current work and next step

The core workflows and historical benchmarks are implemented. The
[Stages 1–9 audit](docs/history/implementation_report_stages1-9_audit_2026-09-15.md) verifies retained
evidence and repairs inconsistent selection inputs. Stage 8's runner has synthetic validation;
its original official-data acceptance remains outstanding under Stage 10's prepared
50 MW/100 MWh and 25 MW/100 MWh study. Review the repair before completing the release.
[STATUS.md](STATUS.md) records the current evidence and external blockers;
[PLAN.md](PLAN.md) owns the next steps.

## Data policy

Official downloads, credentials and generated research outputs stay outside Git. Accepted
artifacts are verified against committed price-free custody records before use. The single
committed synthetic sample is a documented exception; other reports are generated locally.
See [data sources](docs/data_sources.md), [the data dictionary](docs/data_dictionary.md),
[official retrieval](docs/official_data_retrieval.md), and
[artifact custody](docs/official_artifact_custody.md). Source terms apply to redistribution.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest -v
python -m build --wheel
```

CI runs on Python 3.12 and 3.13 using synthetic fixtures, without private credentials or official
datasets. [CONTRIBUTING.md](CONTRIBUTING.md) describes the contribution workflow.

## Reference

| Topic | Record |
| --- | --- |
| Scope and interpretation | [Approved brief](PROMPT.md), [limitations](LIMITATIONS.md) |
| Methods and assumptions | [Methodology](METHODOLOGY.md), [decisions](DECISIONS.md) |
| Commands and configuration | [Command reference](docs/command_reference.md), [configuration](config/README.md) |
| Current work | [Status](STATUS.md), [plan](PLAN.md) |
| Changes and validation history | [Changelog](CHANGELOG.md), [implementation reports](docs/history/) |
| Private-data handling | [Security](SECURITY.md) |

## License

Copyright is reserved. See [LICENSE](LICENSE). The repository is available for viewing,
educational evaluation and portfolio demonstration; reuse requires prior permission.
