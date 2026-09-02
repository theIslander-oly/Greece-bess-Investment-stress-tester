# Greek Battery Investment Stress Tester — Implementation Report v0.5

**Date:** 25 August 2026  
**Status:** Cohort-based degradation and augmentation-aware dispatch implemented  
**Scope:** Greek Day-Ahead Market standalone BESS only

## Outcome

Version 0.5 converts battery capacity from a static input into an auditable state that
evolves with calendar age, realized cell discharge and dated augmentation or replacement. The state is
fed into a day-by-day perfect-foresight dispatch path so every market-day solve uses the
energy and power available at the beginning of that day.

The release does not turn the project into an investment model. Generic fade rates are
not OEM evidence, augmentation cost is not yet a project cash flow, and perfect foresight
remains a labelled gross-margin upper bound.

## Cohort state model

The initial battery is one cohort. Every augmentation event creates a new cohort with its
own commissioning date, nominal energy, nominal charge power, nominal discharge power and
cumulative cell-discharge history. Existing cohorts are never reset or rejuvenated by an
augmentation.

For cohort `i` on day `d`:

```text
age_years_i = days_since_commissioning_i / 365.25
calendar_fade_i = min(1, age_years_i × annual_calendar_fade)
cumulative_EFC_i = cumulative_cell_discharge_i / nominal_energy_i
cycle_fade_i = min(1, cumulative_EFC_i × fade_per_EFC)
retained_fraction_i = max(0, 1 - calendar_fade_i - cycle_fade_i)
usable_energy_i = nominal_energy_i × retained_fraction_i
usable_power_i = nominal_power_i × retained_fraction_i ^ power_exponent
```

Fleet energy and power are sums of the cohort quantities. Calendar and cycle fade are
linear and additive by design. The formulas are deliberately visible so a later model can
replace them without changing the state and reporting contracts.

## Throughput accounting

Cycle fade uses cell-side discharged energy. For a daily dispatch schedule:

```text
cell_discharge_MWh = grid_discharge_MWh / discharge_efficiency
```

Daily cell discharge is allocated among cohorts in proportion to their
beginning-of-day usable energy. This is deterministic and auditable, but it is not a
claim about any specific battery-management-system rack dispatch policy.

Current-day throughput is applied only after the day is dispatched. Therefore a day
cannot use capacity fade caused by its own future dispatch, and the following day sees
the resulting reduced capacity.

## Warranty screening and constraints

The model can record:

- a retained-capacity threshold during a configured warranty duration;
- a maximum cumulative equivalent-full-cycle assumption per cohort;
- a fleet retirement-capacity threshold.

These values produce transparent breach indicators. They are not legal interpretations
of an OEM warranty.

When hard throughput enforcement is enabled, the model calculates the maximum additional
cell discharge that can be proportionally allocated without any cohort crossing its EFC
ceiling. That headroom is converted to grid discharge using discharge efficiency and
passed to the existing daily cycle constraint. Augmentation adds a new cohort and its own
remaining headroom; it does not erase the older cohort's limit.

## Augmentation and replacement

An event is applied at the beginning of its date and records:

- event identifier;
- added nominal energy;
- added nominal charge and discharge power;
- event cost.

With no retired cohort identifiers, the event is an augmentation. When one or more
existing cohort identifiers are supplied, those cohorts are removed before the new
cohort is commissioned, creating an explicit replacement. Unknown or duplicate
retirement identifiers are rejected rather than ignored.

The cost is reported separately from Day-Ahead Market margin. Version 0.5 does not assign
cash-flow timing, inflation, discounting or tax treatment; those belong to v0.6.

## Degradation-aware dispatch

`simulate-degradation-dispatch` groups a canonical price history by complete market day.
For each day it:

1. applies any due augmentation;
2. calculates beginning-of-day usable energy and power;
3. calculates warranty throughput headroom when configured;
4. creates a temporary dispatch configuration with those physical limits;
5. solves the existing mixed-integer perfect-foresight problem;
6. restores the configured initial SOC fraction at day-end;
7. converts grid discharge to cell discharge;
8. updates cohort throughput and end-of-day capacity;
9. writes interval and daily audit fields.

The workflow retains the original grid limits, efficiencies, SOC limits, fees, optional
monetary degradation adder, availability assumptions and non-simultaneous operation
constraint. It does not weaken the v0.2 physical model.

The result remains a sum of daily perfect-foresight gross-margin upper bounds. It is not a
forecast of achievable revenue. A forecast-planned degraded-capacity path can be added
later using the same state engine after official multi-year acceptance.

## Outputs

The CLI writes:

- interval dispatch with beginning-of-day degraded limits;
- daily capacity, power, throughput, margin, warranty and augmentation records;
- final per-cohort age, fade, capacity, power and warranty state;
- a JSON summary containing every policy label and input configuration.

Physical fade and the existing monetary degradation adder are reported separately. The
adder should remain zero unless a documented use case justifies including both.

## Verification

The suite contains 53 tests. Eleven v0.5 tests cover:

- exact additive calendar and cycle fade;
- separately aged augmentation cohorts;
- explicit replacement of a retired cohort;
- proportional cohort throughput allocation;
- invalid warranty and augmentation inputs;
- enforced EFC headroom;
- degraded energy and power passed into daily dispatch;
- augmentation capacity and cost records;
- required daily SOC restoration;
- a 92-quarter-hour spring DST market day;
- end-to-end CLI artifacts.

All earlier ingestion, DST, optimizer, forecast, leakage and like-for-like dispatch tests
remain green.

## Known limitations

- Generic example values are illustrative and have no OEM status.
- Linear additive fade omits temperature, C-rate, depth-of-discharge segmentation,
  state-of-charge dwell, nonlinear degradation knees and cell dispersion.
- Proportional cohort allocation may differ from an actual rack controller.
- Retained-capacity breach does not automatically repair or retire equipment.
- Augmentation cost has no finance treatment until v0.6.
- No CAPEX, OPEX, tax, subsidy, debt, NPV, IRR, payback or Monte Carlo layer exists.
- Only Greek Day-Ahead Market gross margin is modeled.

## Next milestone

Version 0.6 will build an explicit unlevered project-finance layer over auditable annual or
daily operating outputs: CAPEX, OPEX, augmentation/replacement cash flows, project life,
NPV, IRR, payback and break-even analysis. Tax, subsidy and leveraged-finance claims will
remain excluded until independently validated.
