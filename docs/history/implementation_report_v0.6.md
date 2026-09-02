# Greek Battery Investment Stress Tester — Implementation Report v0.6

**Date:** 25 August 2026  
**Status:** Explicit unlevered project finance implemented  
**Scope:** Greek Day-Ahead Market standalone BESS only

## Outcome

Version 0.6 adds a finance layer over an explicit daily operating path. It converts
market margin, discharged energy and dated augmentation costs into daily and project-year
cash flows, then calculates unlevered NPV, IRR, payback and break-even outputs.

The release does not create a future price path. Finance results inherit the meaning and
limitations of the operating input. A perfect-foresight degradation-dispatch path remains
a gross-margin upper bound after discounting and cannot be called expected revenue.

## Operating-path contract

The input table requires:

- `market_day`;
- `net_market_margin_eur`;
- `grid_discharge_mwh`;
- optional `augmentation_cost_eur`, defaulting explicitly to zero when absent.

The table must contain one sorted row for every calendar day from the configured project
start through project end. Missing dates, duplicate dates, non-finite values and negative
discharge or augmentation cost are rejected. The model never repeats a historical year,
interpolates revenue or silently interprets a missing day as zero operation.

The v0.5 `simulate-degradation-dispatch` daily artifact satisfies this contract and its
augmentation events therefore pass directly into v0.6 cash flow.

## Finance assumptions

`FinanceConfig` records:

- project start and end dates;
- the operating-margin evidence category;
- nominal discount rate;
- battery-system, power-conversion, grid-connection,
  development/construction and other initial CAPEX;
- a transparent market-margin realization fraction;
- fixed OPEX, insurance and asset management;
- discharge-linked variable OPEX;
- nominal OPEX escalation;
- project-end decommissioning cost and residual value.

All monetary inputs are nominal EUR. Initial CAPEX must be positive. Costs must be finite
and nonnegative. Margin realization is constrained to zero through one.

## Cash-flow timing

- Initial CAPEX occurs at project start, time zero.
- Market margin and operating costs occur at each modeled market-day end.
- Augmentation costs occur on their recorded market day and are not escalated again.
- Decommissioning cost and residual value occur on the configured project-end day.
- Fixed annual costs are prorated over the actual number of days in each project year,
  including leap years.
- Daily cash flows use exact elapsed-day discount factors with a 365.25-day year.

The annual artifact retains a separate time-zero row, followed by project-year totals and
cumulative nominal and discounted cash flow.

## Investment metrics

The summary reports:

- total initial CAPEX and every operating cash-flow component;
- undiscounted project cash flow;
- NPV at the configured discount rate;
- IRR when the annualized cash-flow sequence has one sign change;
- an explicit IRR status when no root or multiple-sign-change ambiguity exists;
- simple and discounted payback date and elapsed years;
- maximum initial CAPEX producing zero NPV under the configured path;
- market-margin realization fraction producing zero NPV;
- whether that fraction lies within the modeled zero-to-one range;
- an equal-year-end average annual market-margin break-even value.

A positive-NPV Boolean is an arithmetic screening output only. It is not a recommendation.

## Outputs

`evaluate-project-finance` writes:

- annual cash-flow CSV;
- daily cash-flow CSV;
- JSON summary containing metrics, policies, exclusions and the complete configuration.

## Verification

The full suite contains 60 passing tests. New coverage includes:

- exact market-margin, OPEX, augmentation and terminal-value arithmetic;
- independent reconstruction of discounted NPV;
- calculated IRR and non-evaluable IRR statuses;
- simple and discounted payback behavior;
- break-even outputs;
- missing-day, duplicate-day and unsorted-input rejection;
- optional zero augmentation cost;
- invalid finance assumption rejection;
- end-to-end v0.5 degradation daily output into v0.6 finance CLI artifacts.

All earlier ingestion, DST, optimizer, forecast, leakage, ML and degradation regression
tests remain green.

## Known limitations

- The example finance values are illustrative and have no EPC, lender or Greek-market
  evidentiary status.
- Finance results are only as credible as the supplied operating path.
- Perfect foresight remains an upper bound; a realization fraction is a sensitivity, not
  a validated forecast.
- Revenue is limited to the Greek Day-Ahead Market.
- Tax, subsidies, debt, financing fees, working capital, construction draw schedules,
  grid feasibility and bid acceptance are excluded.
- IRR is intentionally not reported for ambiguous multiple-sign-change cash flows.
- No probability distribution is attached to NPV until v0.7.

## Next milestone

Version 0.7 will add reproducible probabilistic stress testing: seasonal block bootstrap,
spread and negative-price shocks, outages, degradation and cost uncertainty,
cannibalisation sensitivities, P5/P50/P95, loss probability and worst-path reporting.
