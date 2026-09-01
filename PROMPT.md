# Approved project brief

## Purpose

Build a transparent, reproducible stress-testing tool for a standalone utility-scale LFP
battery participating in the Greek Day-Ahead Market (DAM). The tool is for research and
pre-feasibility analysis. It is not financial advice, a bankable forecast, an investment
recommendation or a substitute for legal, tax, grid-connection and market-access diligence.

## Core question

Under explicit technical, market and financial assumptions, how resilient could a Greek
standalone battery project be to historical conditions, forecast error, degradation and
adverse scenarios?

## Approved scope

- Greece and the Greek bidding zone.
- Standalone, grid-connected LFP battery.
- Day-Ahead Market energy arbitrage only until other revenue streams are independently
  researched and validated.
- Official HEnEx and ENTSO-E price data when available to the user.
- Synthetic data only for deterministic tests and public demonstrations.
- Transparent physical constraints, forecast timing, degradation state and unlevered cash
  flows.
- Reproducible stress scenarios with all assumptions exposed.
- A read-only research interface and exportable reports that render verified run manifests,
  and only verified run manifests: no computation, no defaults for judgmental inputs, every
  figure carrying its label, basis and the standing exclusions (amended 1 September 2026 by
  user approval; design in `docs/v0.8_design.md`).

## Required interpretation

- Perfect-foresight dispatch is a gross-margin upper bound, not expected revenue.
- Historical replay describes the selected historical period; it does not predict the future.
- Forecast backtests must be strictly time ordered and settled on realized prices.
- Model outputs must retain their source and limitation labels through downstream analysis.
- Missing official observations must be reported, never silently invented.
- Results based on illustrative inputs or synthetic data cannot support an investment decision.

## Excluded until validated

Intraday trading, balancing, ancillary services, capacity remuneration, subsidies, taxes,
debt, bid acceptance, imbalance costs, route-to-market constraints, grid feasibility and
project-specific permitting or licensing conclusions.

## Repository contract

The repository stores code, tests, methodology, provenance metadata and project history. It
does not store secrets, official raw/processed market datasets, large model files, solver
artifacts or generated investment outputs. See `AGENTS.md`, `METHODOLOGY.md`,
`LIMITATIONS.md` and `DECISIONS.md` before changing analytical behavior.
