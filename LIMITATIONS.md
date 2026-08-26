# Limitations and required cautions

## Interpretation

- This is research and pre-feasibility software, not financial advice or an investment-grade
  study.
- Perfect foresight is a gross-margin ceiling, not expected or achievable revenue.
- Historical replay and forecast backtests do not establish future profitability.
- Synthetic demonstrations test software behavior; they are not market evidence.

## Market coverage

- Only Greek Day-Ahead Market energy arbitrage is modeled.
- Price taking and full acceptance of planned quantities are assumed.
- Intraday, balancing, reserves, imbalance exposure, route-to-market constraints, taxes,
  subsidies, permitting, licensing and grid feasibility are excluded.
- The legality and practical feasibility of a specific project require current Greek legal,
  market-access, licensing, grid-connection and contractual review.

## Data

- Only two recent HEnEx workbooks have been production-accepted so far; the multi-year downloader
  is tested synthetically but has not yet completed a live 2020-2026 acceptance run.
- HEnEx incremental daily discovery depends on a website asset-catalog layout rather than a
  documented data API and may need maintenance when the site changes.
- ADMIE catalog retrieval is implemented, but file-format and publication-time acceptance is
  pending before any exogenous field can enter forecasting.
- The ENTSO-E client still requires private-token acceptance and overlapping-source
  reconciliation.
- A complete official multi-year history has not yet been run end to end.
- Official publication revisions, terms and formats may change.
- Missing official prices are not silently interpolated; this can make a run incomplete.

## Forecasting and backtests

- Current ML models use calendar and historical prices only; validated weather, demand, fuel,
  renewable and interconnector forecasts are not yet included.
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
