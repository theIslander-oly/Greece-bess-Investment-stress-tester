# Release Notes — v0.6.0

## Unlevered Project Finance

Version 0.6.0 connects explicit daily battery operating results to an auditable project
cash flow while retaining the Greek Day-Ahead-Market-only, research and pre-feasibility
scope.

### Highlights

- Initial CAPEX is separated into battery, power-conversion, grid,
  development/construction and other components.
- Fixed OPEX, insurance, asset management and discharge-linked variable OPEX are explicit.
- Augmentation costs recorded by v0.5 enter cash flow on their actual modeled date.
- Decommissioning cost and residual value occur at project end.
- Daily and annual outputs report nominal and discounted cash flows.
- Summary outputs include NPV, IRR status, simple payback, discounted payback, maximum
  initial CAPEX and market-margin break-even values.
- Missing project days are rejected rather than extrapolated or valued at zero.
- All 60 automated tests pass.

### Required revenue interpretation

Every run must label its operating path as one of:

- `perfect_foresight_upper_bound`;
- `historical_forecast_backtest`;
- `user_supplied_scenario`.

This label is carried into the summary. Applying a margin-realization fraction does not
convert perfect foresight into expected revenue.

### Command

```bash
greek-bess evaluate-project-finance \
  outputs/degradation_dispatch.daily.csv \
  --finance-config examples/illustrative_finance_not_project_specific.json \
  --output outputs/project_cash_flows.csv
```

### Important interpretation

The calculation is unlevered, nominal, pre-tax and pre-subsidy. It is not a bankable
model, financial advice or a recommendation to build. The included example contains
illustrative round numbers and must be replaced with project-specific evidence.

### Still pending

- Private-token ENTSO-E acceptance and HEnEx reconciliation.
- Complete official multi-year forecast and dispatch benchmarking.
- Probabilistic stress testing, market-saturation sensitivities and research interface.
- Independently validated tax, subsidy, debt and broader market modules.
