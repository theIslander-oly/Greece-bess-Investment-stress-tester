# Limitations and required cautions

## Interpretation

- This is research and pre-feasibility software, not financial advice or an investment-grade
  study.
- Perfect foresight is a gross-margin ceiling, not expected or achievable revenue.
- Historical replay and forecast backtests do not establish future profitability.
- Synthetic demonstrations test software behavior; they are not market evidence.

## Market coverage

- Only Greek Day-Ahead Market energy arbitrage is modeled.
- The replayed 2020-2026 history predates operating battery competition: storage units were
  only integrated into the Greek Day-Ahead and Intraday Markets in April 2026. As the
  tendered, availability-supported fleet (about 1 GW awarded in the 2023-2024 auctions) and
  merchant projects enter operation, price spreads are widely expected to compress, so
  historical replay tends to overstate what a future merchant DAM-only battery could earn.
- Balancing-market participation and state availability-support payments — major revenue
  components for real Greek battery projects — are excluded and would require their own
  data-acceptance track before inclusion.
- Price taking and full acceptance of planned quantities are assumed.
- Intraday, balancing, reserves, imbalance exposure, route-to-market constraints, taxes,
  subsidies, permitting, licensing and grid feasibility are excluded.
- The legality and practical feasibility of a specific project require current Greek legal,
  market-access, licensing, grid-connection and contractual review.

## Data

- The accepted private HEnEx history from 1 November 2020 through 25 August 2026 passes
  continuity, duplicate, DST and price-preservation checks; it is not committed to Git.
- In 980 historical intervals, one or two cross-border asset rows differ from the dominant
  Greek-zone MCP by EUR 0.01/MWh. The bounded consensus is retained and explicitly flagged;
  larger or ambiguous disagreements remain errors.
- HEnEx incremental daily discovery depends on a website asset-catalog layout rather than a
  documented data API and may need maintenance when the site changes.
- ADMIE catalog retrieval is implemented, but file-format and publication-time acceptance is
  pending before any exogenous field can enter forecasting.
- The ENTSO-E series is reconciled against HEnEx for 1 November 2020 through 25 August 2026, with
  one 29 October 2023 interval differing by EUR 0.01/MWh. ENTSO-E A44 `A03` documents state a
  price once and imply its repeats; those implied intervals are materialized and flagged, not
  interpolated.
- Official publication revisions, terms and formats may change. Accepted artifacts are intended
  to be held outside Git as encrypted release assets and are fingerprinted by committed custody
  records. The operator upload is still outstanding, so those records currently have no durable
  copy to verify. Once uploaded, a revision can be detected rather than silently adopted; the
  encryption key is consequently part of the custody chain, and a lost key forces a re-retrieval
  that may not reproduce the accepted baseline.
- A custody record proves that a stored copy is the accepted artifact. It says nothing about
  whether that artifact supports any analytical or investment conclusion.
- Missing official prices are not silently interpolated; this can make a run incomplete.

## Forecasting and backtests

- Seasonal bootstrap paths reuse historical price blocks and are synthetic scenarios, not
  forecasts, probability-calibrated samples or evidence of future market behavior.
- Meteorological-season matching is a coarse dependence assumption. Sparse histories or unusual
  DST block positions can leave no compatible source block, which fails explicitly.
- The bootstrap foundation does not model structural change, outages, cannibalisation, spreads,
  or negative-price shocks, and does not produce percentiles or loss probabilities.
- The bootstrap samples one declared source era and cannot mix delivery regimes. Neither era of
  the accepted history is a good basis on its own: the quarter-hour era (1 October 2025 to
  25 August 2026) is the operating regime but contains exactly one occurrence of each
  meteorological season, so resampling it expresses no inter-annual variation at all, and its
  autumn is only 61 days; the hourly era (1 November 2020 to 30 September 2025) spans five or
  six occurrences of every season but is a superseded delivery regime whose blocks can only be
  mapped onto hourly target days. The era is a declared judgment about relevance and carries no
  probability.
- Block-candidate scarcity is reported, not corrected. A minimum candidate count of 1 means
  every path repeats the same source block at that position, which is a property of the chosen
  era rather than of the random seed.
- Bootstrap dispatch knows every price within each synthetic path and is therefore only a
  gross-margin upper bound. Paths are solved independently with shared assumptions; no path
  probability, percentile, ranking, degradation, finance or investment conclusion is produced.

- Current ML models use calendar and historical prices only; validated weather, demand, fuel,
  renewable and interconnector forecasts are not yet included.
- The Greek DAM moved from hourly to quarter-hour delivery on 1 October 2025. Persistence lags have
  no matching wall-clock slot on that day, and models trained on hourly history forecast
  quarter-hour delivery later in the held-out test period. This is disclosed rather than corrected.
- Accepted historical dispatch assumes constant full availability. No outage, derating or
  auxiliary-load path exists, so the accepted margins do not reflect unavailability.
- The daily-composed perfect-foresight mode restores the configured SOC at every day end, so
  it is at or below the single full-horizon bound by construction. Neither is achievable
  revenue; the composed mode exists because it is the ceiling the forecast backtests are
  measured against and the only basis on which a trade cannot span a year boundary.
- Daily backtests restore initial SOC at day end and do not optimize energy across days.
- Daylight-saving slot differences can make persistence forecasts incomplete; exclusions are
  disclosed.
- Forecast accuracy does not guarantee dispatch value, and backtested value does not guarantee
  executable bids or settlement outcomes.

## Battery model

- Fade rates, warranty thresholds and costs are illustrative until replaced by OEM and EPC
  evidence.
- Linear additive degradation omits temperature, C-rate, depth-of-discharge bins, SOC dwell,
  nonlinear knees and cell dispersion.
- Cohort throughput allocation is proportional, not a rack-level controller simulation.
- Availability and efficiency are assumptions rather than a full auxiliary-load and outage
  model.

## Finance

- Inputs remain illustrative until supported by project-specific EPC, grid, O&M, insurance,
  land, market-access and decommissioning evidence.
- Results are unlevered and pre-tax; debt, tax, subsidy, inflation-basis consistency and working
  capital require separate treatment.
- Finance does not repair or extrapolate incomplete operating paths.
- Scenario probability estimates are excluded unless an independently validated calibration
  methodology is approved; v0.7 reports only non-probabilistic ranges across named scenarios.

## Software

- Solvers and third-party package behavior can vary by platform and version.
- The command-line interface is research-oriented; no user interface exists yet.
- The first GitHub snapshot imports already completed v0.1-v0.6 work, so earlier development
  history is represented by implementation reports rather than fabricated Git commits.

## Per-delivery-year decomposition limitations

- A delivery year is a regrouping of an already-accepted replay, not new evidence. Splitting a
  historical upper bound by year does not make any year's figure a forecast, an expectation or
  a probable outcome for a comparable future year.
- Years of unequal coverage are not comparable on totals alone. Partial years are flagged and
  carry their market-day count; per-market-day figures are within-period averages and are
  deliberately not annualized.
- A year's figures are conditioned on that year's market regime, on the illustrative battery
  and fee assumptions, and on the fixed availability of 1.0. A high-spread year says what the
  replayed battery would have captured in that regime under those assumptions, not what a
  battery operating in that year would have earned.
- The 2020-2026 accepted history mixes hourly and quarter-hour delivery, with the change on
  1 October 2025. Years on either side of that change differ in interval structure as well as
  in price regime, and the per-year interval counts by resolution disclose this rather than
  correcting for it.
- Annual capture ratios compare a method against the ceiling on the days that method
  backtested. Methods exclude different days for structural reasons, so cross-method
  comparison uses the common-day table, whose recorded ceiling spread is the like-for-like
  evidence.
- No probability, percentile, loss metric or ranking of delivery years is produced, and a year
  ordering by margin is not a ranking of anything about the future.

## Spread-compression limitations

- The compression factor is a declared judgmental scenario, not an estimate, a calibration or a
  probability-weighted view. Nothing in the replayed history estimates it: the 2020-2026 record
  predates operating battery competition in the Greek DAM almost entirely, so it contains no
  episode from which a competitive spread response could be inferred. A factor of 0.7 is a
  statement of what to examine, not a claim that spreads will compress by 30 %.
- The transformation represents cannibalisation pressure only in the loose sense that
  cannibalisation compresses spreads. It is not a causal model of entry, bidding behaviour,
  fleet size or market clearing, and it says nothing about when or whether compression occurs.
- Compression scales every within-day range by the same factor. Real spread compression would
  not be uniform across days, seasons, hours or price regimes, and it would interact with the
  negative-price and duck-curve structure the accepted history shows growing since 2023.
- The daily reference level is a declared choice with no default. A daily mean preserves each
  day's mean exactly; a daily median does not, and the summary reports the resulting daily-mean
  shift. Neither is a claim about which level a compressing market would converge on.
- Zero and negative prices are preserved and never clipped. Because compression pulls prices
  toward the daily reference, intervals can cross zero and change sign; the count is reported.
  A scenario that materially changes the number of negative intervals is changing the market's
  character, not only its spread, and should be read accordingly.
- Spread widening is out of scope, so the accepted factor range is closed at 1. This is a
  deliberate scope limit, not a judgment that widening is unlikely — the per-delivery-year
  decomposition found mean daily range rising every year since 2023.
- Compressed paths are synthetic scenarios. No likelihood, percentile, loss metric or ranking
  is attached to a factor, and no dispatch, finance or investment conclusion follows from one.

## Price-level shock limitations

- The additive constant is a user-configured sensitivity, not an estimated price process or a
  probability-calibrated market view.
- Applying one shift to every interval does not change within-path spreads or temporal shape and
  does not represent negative-price events, outages, cannibalisation or structural market change.
- Because spreads are unchanged, a constant level shift alters battery arbitrage economics only
  through round-trip efficiency losses and per-MWh fees; it is therefore a weak stress for
  storage value, and spread transformations are the economically first-order sensitivity.
- Shocked paths are not forecasts, expected prices, investment evidence or dispatch/finance
  results. No likelihood, percentile, loss metric or ranking is attached to them.
