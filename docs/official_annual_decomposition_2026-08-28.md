# Per-delivery-year decomposition of the accepted replay — 28 August 2026

## Scope and interpretation

This report records the first decomposition of the accepted official Greek DAM replay into
delivery years. It adds no model, market, transformation or data: it regroups results the
dispatch and backtest stages already produced and that were accepted on 27 August 2026.

Every annual perfect-foresight figure is a **historical gross-margin upper bound** under the
stated assumptions. Every annual capture ratio is a **historical backtest outcome on a selected
period**. Neither is expected revenue, a forecast for any year, a probability, or investment
evidence. No percentile, loss metric or ranking of delivery years is produced, and ordering
years by margin ranks nothing about the future.

Official prices and schedules remain outside Git. Only aggregate per-year statistics are
recorded here.

## Method and provenance

Workflow `Decompose the accepted replay by delivery year`, run
[`33147448666`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33147448666),
on `main` at `65e61f9`, 28 August 2026, 12m36s.

1. Downloaded the `greek-dam-official-history` artifact from run `32971677163`.
2. **Verified it against `docs/custody/greek-dam-official-history.json`.** The verification
   passed: per-file digests and the price-series digest are unchanged, so no official
   publication has been revised since acceptance. This was the first live exercise of the
   custody verification path against the source artifact.
3. Merged the archived and daily HEnEx files into the 74,663-interval accepted history.
4. Solved the perfect-foresight ceiling as **2,124 independent daily solves** (69 s), the mode
   published as `optimize-perfect-foresight --daily-solves`. Independent daily solves are the
   required basis for annual attribution: a single full-horizon solve may charge on 31 December
   and discharge on 1 January, splitting one trade across two delivery years.
5. Backtested all four causal naïve methods at a 28-day rolling window.
6. Decomposed by delivery year on the CET/CEST market clock.

Configuration: `examples/battery_50mw_100mwh.json`, unmodified — 50 MW / 100 MWh, SOC 5-95 %,
initial and terminal SOC 0.50, one-way efficiencies 0.94, availability a constant 1.0, zero fees
and zero degradation cost. These values are illustrative and are not project evidence.

Evidence artifact: `annual-replay-decomposition` (ID `9676575888`), zip SHA-256
`119e2465c272fdc4e6259d94813478360ee26520d23f0eef33d0909ec65d0291`, 90-day retention.

This artifact carries **no custody record**, deliberately. It holds no interval-level price and
has no provider that could revise it, and the three things that determine it — the custodied
history, `main` at `65e61f9` and the configuration named above — are already fingerprinted. If
it lapses it is regenerated, not recovered (decision entry 2026-08-28).

## Reconciliation against previously accepted figures

The decomposition is only credible if it sums back to results accepted independently. Every
figure does, to the euro:

| Check | Decomposed | Previously accepted |
|---|---:|---:|
| Daily-composed ceiling | 24,974,729 | 24,974,729.59 |
| Market days | 2,124 | 2,124 |
| Negative-price intervals | 1,767 | 1,767 |
| Zero-price intervals | 1,914 | 1,914 |
| `daily_persistence` days / realized / ceiling / loss days | 2,116 / 17,339,040 / 24,868,682 / 110 | 2,116 / 17,339,039 / 24,868,683 / 110 |
| `weekly_persistence` days / realized / ceiling / loss days | 2,104 / 16,943,803 / 24,743,656 / 110 | 2,104 / 16,943,803 / 24,743,656 / 110 |
| `rolling_mean` days / realized / ceiling / loss days | 2,122 / 19,134,059 / 24,946,806 / 62 | 2,122 / 19,134,060 / 24,946,807 / 62 |
| `ensemble` days / realized / ceiling / loss days | 2,122 / 19,492,322 / 24,946,806 / 52 | 2,122 / 19,492,323 / 24,946,807 / 52 |
| Common days across all four methods | 2,098 | 2,098 |
| Common-day shared ceiling | 24,665,532 | 24,665,532.17 |

Sub-euro differences are rounding in the reported table. The run's own internal checks report a
**ceiling reconciliation residual of EUR 0.000000** and a **maximum common-day ceiling spread of
EUR 0.000000**, so the like-for-like property that held in aggregate holds within every
delivery year.

## Market context and daily-composed ceiling

Delivery years use the CET/CEST market clock. **2020 (61 days) and 2026 (237 days) are partial**
and are not comparable with full years on totals; the per-day column is the comparable one and
is a within-period average, not an annualized figure.

| Year | Market days | Partial | Mean price | Mean daily range | Negative | Zero | Ceiling EUR | Ceiling EUR/day |
| ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 | 61 | yes | 55.85 | 52.07 | 2 | 3 | 230,141 | 3,773 |
| 2021 | 365 | no | 116.44 | 76.63 | 5 | 9 | 1,960,658 | 5,372 |
| 2022 | 365 | no | 279.90 | 210.52 | 1 | 4 | 5,859,178 | 16,053 |
| 2023 | 365 | no | 119.11 | 121.75 | 0 | 24 | 3,577,481 | 9,801 |
| 2024 | 366 | no | 100.88 | 162.59 | 11 | 18 | 4,775,370 | 13,047 |
| 2025 | 365 | no | 106.19 | 171.90 | 177 | 357 | 5,151,831 | 14,115 |
| 2026 | 237 | yes | 98.47 | 181.30 | 1,571 | 1,499 | 3,420,070 | 14,431 |

Prices are EUR/MWh; mean daily range is the mean over market days of the within-day maximum
minus minimum.

## Forecast capture on each method's own backtested days

| Year | Method | Days | Realized EUR | Ceiling EUR | Regret EUR | Capture | Loss days |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 | daily_persistence | 60 | 173,242 | 225,737 | 52,495 | 0.7675 | 0 |
| 2021 | daily_persistence | 364 | 1,289,007 | 1,956,920 | 667,913 | 0.6587 | 39 |
| 2022 | daily_persistence | 364 | 3,354,793 | 5,848,430 | 2,493,638 | 0.5736 | 41 |
| 2023 | daily_persistence | 364 | 2,324,216 | 3,562,759 | 1,238,543 | 0.6524 | 20 |
| 2024 | daily_persistence | 365 | 3,767,751 | 4,766,359 | 998,609 | 0.7905 | 3 |
| 2025 | daily_persistence | 363 | 4,143,565 | 5,111,532 | 967,967 | 0.8106 | 3 |
| 2026 | daily_persistence | 236 | 2,286,466 | 3,396,945 | 1,110,479 | 0.6731 | 4 |
| 2020 | weekly_persistence | 54 | 155,997 | 209,075 | 53,078 | 0.7461 | 1 |
| 2021 | weekly_persistence | 364 | 1,322,566 | 1,955,980 | 633,414 | 0.6762 | 39 |
| 2022 | weekly_persistence | 364 | 3,238,957 | 5,837,559 | 2,598,603 | 0.5548 | 39 |
| 2023 | weekly_persistence | 364 | 2,307,652 | 3,567,726 | 1,260,074 | 0.6468 | 17 |
| 2024 | weekly_persistence | 365 | 3,852,143 | 4,768,251 | 916,108 | 0.8079 | 10 |
| 2025 | weekly_persistence | 357 | 3,889,050 | 5,003,936 | 1,114,886 | 0.7772 | 3 |
| 2026 | weekly_persistence | 236 | 2,177,438 | 3,401,129 | 1,223,691 | 0.6402 | 1 |
| 2020 | rolling_mean | 60 | 193,093 | 225,737 | 32,644 | 0.8554 | 1 |
| 2021 | rolling_mean | 365 | 1,452,887 | 1,960,658 | 507,771 | 0.7410 | 20 |
| 2022 | rolling_mean | 365 | 3,850,849 | 5,859,178 | 2,008,329 | 0.6572 | 24 |
| 2023 | rolling_mean | 365 | 2,564,460 | 3,577,481 | 1,013,021 | 0.7168 | 10 |
| 2024 | rolling_mean | 366 | 4,056,782 | 4,775,370 | 718,588 | 0.8495 | 4 |
| 2025 | rolling_mean | 364 | 4,424,101 | 5,128,312 | 704,212 | 0.8627 | 3 |
| 2026 | rolling_mean | 237 | 2,591,887 | 3,420,070 | 828,183 | 0.7578 | 0 |
| 2020 | ensemble | 60 | 190,156 | 225,737 | 35,581 | 0.8424 | 0 |
| 2021 | ensemble | 365 | 1,511,483 | 1,960,658 | 449,176 | 0.7709 | 15 |
| 2022 | ensemble | 365 | 4,064,465 | 5,859,178 | 1,794,713 | 0.6937 | 19 |
| 2023 | ensemble | 365 | 2,657,006 | 3,577,481 | 920,475 | 0.7427 | 12 |
| 2024 | ensemble | 366 | 4,106,989 | 4,775,370 | 668,381 | 0.8600 | 2 |
| 2025 | ensemble | 364 | 4,474,137 | 5,128,312 | 654,176 | 0.8724 | 2 |
| 2026 | ensemble | 237 | 2,488,086 | 3,420,070 | 931,984 | 0.7275 | 2 |

Each method's ceiling covers only the days that method backtested, so ceilings differ between
methods within a year. Excluded days are the documented structural causes: first-day warm-up,
causal-lag warm-up, spring DST, and the 2025-10-01 resolution change.

## Like-for-like capture on the days every method backtested

| Year | Common days | daily_persistence | weekly_persistence | rolling_mean | ensemble | Shared ceiling EUR | Spread EUR |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 | 54 | 0.7689 | 0.7461 | **0.8631** | 0.8446 | 209,075 | 0 |
| 2021 | 363 | 0.6591 | 0.6758 | 0.7415 | **0.7705** | 1,952,242 | 0 |
| 2022 | 363 | 0.5747 | 0.5545 | 0.6590 | **0.6951** | 5,826,812 | 0 |
| 2023 | 363 | 0.6518 | 0.6459 | 0.7168 | **0.7430** | 3,553,004 | 0 |
| 2024 | 364 | 0.7903 | 0.8079 | 0.8495 | **0.8600** | 4,759,240 | 0 |
| 2025 | 356 | 0.8123 | 0.7779 | 0.8649 | **0.8749** | 4,987,156 | 0 |
| 2026 | 235 | 0.6730 | 0.6396 | **0.7586** | 0.7281 | 3,378,003 | 0 |

The shared ceiling is identical across all four methods in every year, with a spread of exactly
EUR 0.00, which is what makes the within-year comparison like-for-like.

## Findings

These are observations about the replayed period, not predictions.

**1. Regime dependence is large, and the aggregate conceals it.** The 2022 gas-crisis year
contributes EUR 5,859,178 — **23.5 % of the six-year ceiling from 17.2 % of the market days**.
Its EUR 16,053 per market day is 4.3 times the 2020 rate and 3.0 times 2021. Any figure quoted
as a 2020-2026 average is an average over regimes that differ by this much.

**2. Spread has decoupled from price level, and has risen every year since 2023.** Mean daily
range runs 121.75 (2023) → 162.59 (2024) → 171.90 (2025) → 181.30 (2026), while mean price falls
119.11 → 100.88 → 106.19 → 98.47. **2026 has the second-widest daily range in the whole history
on the lowest mean price since 2020.** Arbitrage value follows the spread, not the level: the
ceiling per market day in 2026 (EUR 14,431) is the highest of any non-crisis year despite the
lowest mean price. This is direct evidence for the project's existing position that spread
transformations, not level shocks, are the first-order stress for storage.

**3. Negative and zero prices are a recent and sharp development.** 2020-2024 together hold 19
negative intervals; 2025 holds 177 and the partial 2026 holds 1,571. Zero prices follow the same
shape (18 in 2024, 357 in 2025, 1,499 in 2026). **This count is confounded by resolution**: the
market moved to quarter-hour delivery on 1 October 2025, so a 2026 interval is a quarter of a
2024 interval and counts across that boundary are not directly comparable. Even after dividing
the 2026 count by four the direction and rough magnitude survive, but the per-year interval
counts by resolution regime in `annual_overview.csv` are the honest basis for any share
calculation, and no such share is asserted here.

**4. Forecast capture varies far more by year than the aggregate suggests.** The ensemble's
aggregate capture of 0.7814 spans **0.6937 (2022) to 0.8724 (2025)** across years — an
18-point range. Capture is worst in the two most volatile regimes, 2022 and 2026, and best in
the calmer 2024-2025 pair. A wider spread raises the ceiling faster than a causal naïve forecast
can track it.

**5. The method ranking is not stable across years.** The ensemble leads on common days in every
year from 2021 to 2025, but `rolling_mean` leads in 2020 (0.8631 vs 0.8446) and again in **2026
(0.7586 vs 0.7281)**. The aggregate ranking that puts the ensemble first therefore conceals that
its advantage disappeared, and reversed, in the most recent partial year.

**6. The 2026 break is confounded and must not be attributed.** Ensemble capture falls from
0.8724 to 0.7275 between 2025 and 2026, the largest year-on-year fall outside the crisis. Three
documented changes land in the same window: the quarter-hour resolution change of 1 October
2025, the negative-price surge, and the entry of storage into the Greek DAM in April 2026. This
decomposition separates none of them, and the fall must not be read as evidence for any one.

## Limitations carried forward

- Annual figures inherit every limitation of the aggregates they decompose: perfect foresight is
  a ceiling, the battery and fee inputs are illustrative, availability is a constant 1.0, and
  only Greek DAM energy arbitrage is modelled.
- Partial years 2020 and 2026 are labelled and carry their day counts. Per-market-day figures
  are within-period averages and are deliberately not annualized.
- A year's figures are conditioned on that year's regime and on the stated assumptions. A
  high-spread year says what the replayed battery would have captured in that regime, not what a
  battery operating then would have earned, and certainly not what one will earn.
- The replayed history predates operating battery competition in the Greek DAM, which began in
  April 2026, so it tends to overstate what a future merchant DAM-only battery could earn.
- Balancing-market and availability-support revenues, which dominate real Greek battery
  commerce, remain excluded.
