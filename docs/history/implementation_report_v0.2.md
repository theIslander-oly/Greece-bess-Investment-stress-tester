# Greek Battery Investment Stress Tester — Implementation Report v0.2

**Date:** 24 August 2026  
**Status:** Data ingestion foundation retained; perfect-foresight dispatch implemented and tested  
**Scope:** Standalone Greek utility-scale LFP BESS, Greek Day-Ahead Market energy arbitrage only

## Outcome

Version 0.2 adds a solver-backed battery dispatch layer to the accepted v0.1 data
foundation. The implementation maximizes Day-Ahead Market energy margin over a supplied
canonical price horizon while enforcing the main physical and operating constraints of a
standalone battery.

Every output is explicitly labelled as a **perfect-foresight gross-margin upper bound**.
It is not a forecast of achievable revenue and it is not an investment recommendation.

## What was implemented

### Optimization variables

For every market time unit, the model chooses:

- grid import power for charging, in MW;
- grid export power for discharging, in MW;
- stored energy at the start and end of the interval, in MWh;
- a binary charge/discharge mode.

The binary mode prevents simultaneous charging and discharging. This is essential when
prices are negative because a continuous two-flow formulation can otherwise manufacture
revenue by deliberately wasting energy through efficiency losses.

### Stored-energy balance

For interval `t` with duration `dt`:

```text
energy[t+1]
  = retention[t] * energy[t]
  + charge_efficiency * charge_mw[t] * dt
  - discharge_mw[t] * dt / discharge_efficiency
```

Charge and discharge quantities are measured at the grid meter. This means market
settlement uses grid MWh directly, while conversion losses appear only in the stored-energy
balance.

### Enforced constraints

- charge and discharge power ratings;
- absolute grid import and export limits;
- interval-specific availability between zero and one;
- minimum and maximum state of charge;
- fixed initial state of charge;
- fixed terminal state of charge, defaulting to the initial value;
- one-way charge and discharge efficiencies;
- optional self-discharge;
- mutual exclusion of charging and discharging;
- optional daily equivalent-cycle limit;
- canonical-data validity and, by default, complete market days.

### Objective and revenue decomposition

The objective maximizes:

```text
discharge energy revenue
- charging energy cost
- buy-side fees
- sell-side fees
- degradation throughput cost
```

Charging energy cost remains signed. At a negative price, it is negative and therefore
correctly represents payment to consume. Each term is also written per interval so the
aggregate result can be audited.

### Outputs

The interval schedule includes:

- charge, discharge and net-export MW;
- start/end stored energy and SOC;
- charged and discharged grid MWh;
- charging cost and discharge revenue;
- buy fee, sell fee and degradation cost;
- net market margin;
- charge, discharge or idle operating mode.

The summary includes:

- gross discharge revenue;
- charging energy cost;
- fees and degradation cost;
- net market margin;
- charged and discharged energy;
- equivalent full cycles;
- average captured charge and discharge prices;
- initial and terminal energy;
- nominal round-trip efficiency;
- solver status and result label.

## Solver choice

The implementation uses `scipy.optimize.milp`, backed by the open-source HiGHS solver.
This avoids a commercial solver dependency while providing a genuine mixed-integer model.
Solver relative gap and time limit are editable configuration fields.

## Configuration

`BatteryDispatchConfig` validates all assumptions before a solve. The example file
`examples/battery_50mw_100mwh.json` is illustrative only. Its 50 MW / 100 MWh rating and
all other values are placeholders, not assumptions about a specific Greek project.

## Verification completed

The full test suite contains 24 tests after this release. Optimizer coverage includes:

1. simple profitable arbitrage and exact terminal SOC;
2. no simultaneous charge/discharge under a negative price;
3. correct one-way efficiency and grid-meter accounting;
4. interval-specific unavailability;
5. daily equivalent-cycle caps;
6. quarter-hour energy accounting;
7. rejection of incomplete market days by default;
8. rejection of invalid availability values;
9. end-to-end CLI schedule and summary generation;
10. row-aligned availability with unsorted input prices;
11. rejection of a wholly missing market day through UTC continuity checks.

An engineering-only run over 744 hourly synthetic intervals completed with an optimal
HiGHS status in approximately 0.8 seconds in the development environment. This indicates
that the implementation path is workable; it is not an official-data result, an investment
performance figure or a guaranteed runtime for annual quarter-hour data.

The pre-existing ENTSO-E, HEnEx, DST, canonical-schema, quality and cross-source tests also
remain passing.

## What remains unvalidated

No official price file or personal API credential is bundled. Therefore:

- the HEnEx parser has not yet been run against a user-supplied production workbook;
- the ENTSO-E client has not yet been run with the user's private token;
- a real HEnEx-versus-ENTSO-E overlap comparison is still pending;
- the optimizer has not yet been benchmarked over a complete official multi-year history.

Synthetic data is used only for deterministic tests and public demonstrations. It is not
used to support an investment conclusion.

## Excluded from v0.2

- forecast-based dispatch and forecast error;
- intraday, balancing and reserve revenues;
- bid acceptance, imbalance costs and route-to-market constraints;
- calendar/cycle capacity fade and augmentation state transitions;
- CAPEX, OPEX, taxes, subsidies and financing;
- NPV, IRR, payback and DSCR;
- Monte Carlo and market-cannibalization scenarios;
- grid connection feasibility;
- Streamlit interface.

## Recommended next step

Proceed to forecast-based dispatch with time-ordered training, validation and test splits.
The perfect-foresight result should serve only as the ceiling against which feasible
forecast dispatch is compared. In parallel, complete live-data acceptance once either an
official HEnEx workbook or a privately configured ENTSO-E token is available.

## User action

No user action is required to continue software development. Optional actions that would
unlock live validation are:

1. obtain an ENTSO-E Transparency Platform token and keep it in a private environment
   variable named `ENTSOE_SECURITY_TOKEN`; or
2. provide one legitimately obtained HEnEx `EL-DAM_Results_EN` workbook.

The token must never be pasted into chat, committed, printed or included in an artifact.
