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
- Official publication revisions, terms and formats may change.
- Missing official prices are not silently interpolated; this can make a run incomplete.

## Forecasting and backtests

- Seasonal bootstrap paths reuse historical price blocks and are synthetic scenarios, not
  forecasts, probability-calibrated samples or evidence of future market behavior.
- Meteorological-season matching is a coarse dependence assumption. Sparse histories or unusual
  DST block positions can leave no compatible source block, which fails explicitly.
- The bootstrap foundation does not model structural change, outages, cannibalisation, spreads,
  or negative-price shocks, and does not produce percentiles or loss probabilities.
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
- Scenario probability estimates are not implemented until v0.7.

## Software

- Solvers and third-party package behavior can vary by platform and version.
- The command-line interface is research-oriented; no user interface exists yet.
- The first GitHub snapshot imports already completed v0.1-v0.6 work, so earlier development
  history is represented by implementation reports rather than fabricated Git commits.

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
