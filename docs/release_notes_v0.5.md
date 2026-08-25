# Release Notes — v0.5.0

## Cohort-Based Degradation and Augmentation

Version 0.5.0 adds explicit physical capacity evolution to the Greek Battery Investment
Stress Tester while retaining its Day-Ahead Market-only, research and pre-feasibility
scope.

### Highlights

- Calendar and equivalent-cycle fade are modeled separately and combined transparently.
- Initial capacity and each augmentation are tracked as independently aged cohorts.
- Usable energy and charge/discharge power evolve day by day.
- Cell-side discharge throughput is allocated proportionally across usable cohorts.
- Retained-capacity, EFC warranty and retirement-threshold indicators are reported.
- Optional hard EFC headroom can constrain daily dispatch.
- Dated augmentation or replacement energy, power and cost are recorded; replacement
  retires only explicitly named cohorts.
- `simulate-degradation-dispatch` runs daily perfect-foresight dispatch using degraded
  beginning-of-day limits.
- Interval, daily, cohort and JSON summary artifacts expose the complete state path.
- All 53 automated tests pass, including a 92-quarter-hour spring DST degradation run.

### Important interpretation

The included degradation configuration is illustrative. Its fade rates, warranty
thresholds, augmentation size, timing and zero placeholder cost are not OEM evidence and
must be replaced for a real project.

The degradation-aware dispatch still knows each market day's future prices. Its margin
is therefore a labelled gross-margin upper bound—not expected revenue, a bankable
forecast or financial advice.

Augmentation cost is recorded separately from DAM margin. Version 0.6 can place this
dated cost into the unlevered project cash flow.

### Command

```bash
greek-bess simulate-degradation-dispatch \
  data/curated/henex_prices.csv \
  --config examples/battery_50mw_100mwh.json \
  --degradation-config examples/illustrative_degradation_with_augmentation.json \
  --output outputs/degradation_dispatch.csv
```

### Still pending

- Private-token ENTSO-E acceptance and HEnEx reconciliation.
- Complete official multi-year forecast and dispatch benchmarking.
- Probabilistic stress testing and research interface.
