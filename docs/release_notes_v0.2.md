# Release v0.2.0 — Perfect-Foresight Dispatch

**Release date:** 24 August 2026

Version 0.2.0 adds the first battery optimization layer to the Greek Battery Investment
Stress Tester. It retains the v0.1 official-data ingestion foundation and introduces a
mixed-integer dispatch model for Greek Day-Ahead Market energy arbitrage.

## Highlights

- Solver-backed perfect-foresight dispatch using SciPy and HiGHS.
- Explicit charge, discharge, stored-energy and binary operating-mode variables.
- Correct SOC dynamics with grid-meter settlement and one-way efficiencies.
- Power, energy, availability, grid, terminal-SOC and optional cycle constraints.
- Correct negative-price behavior without simultaneous charging and discharging.
- Interval-level revenue, cost, fee and degradation decomposition.
- CLI workflow and illustrative battery configuration.
- Stronger data-quality protection against missing intervals, whole missing days and
  interval overlaps.

## Verification

- 24 automated tests pass.
- The Python 3.12 package builds successfully.
- The optimizer reached an optimal HiGHS status on a 744-hour synthetic engineering run.

Synthetic prices support testing only. They do not support an investment conclusion.
Live validation against a production HEnEx workbook or ENTSO-E API response remains
pending.

## Scope and interpretation

The optimizer result is a **perfect-foresight Greek DAM gross-margin upper bound**. It is
not expected revenue, a bankable forecast, financial advice or a recommendation to build.

Version 0.2.0 excludes forecast error, intraday, balancing, reserves, bid acceptance,
imbalance exposure, CAPEX, OPEX, taxes, financing, grid feasibility, degradation state
evolution, Monte Carlo analysis and the user interface.

## Next release direction

The next phase is forecast-based dispatch with time-ordered train/validation/test periods,
walk-forward evaluation and realized settlement against observed prices. Its performance
will be compared with the v0.2.0 perfect-foresight ceiling.
