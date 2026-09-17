# Frozen ML selection in the integrated study

## Purpose and scope

The next research question is whether the previously observed validation-margin selection gain
survives physical ageing and declared operating costs. The first implementation unit connects
the two existing frozen selections to the integrated runner and verifies the connection on
synthetic fixtures. It adds no model family, refit, feature, source, candidate or selection rule.

The operator requested continuation after merging the Stage 10 documentation and clarified that
the report has not been published. Stage 10 publication remains open; implementation of this
next unit proceeds under that continuation instruction. Publication is not treated as complete.
Existing stages are not renumbered.

## Contract

Add two named planners, `frozen_validation_rmse` and `frozen_validation_margin`, with information
set `accepted_frozen_causal_forecasts`. Both must be declared together. They replay the selected
candidate columns from an accepted Stage 9 evidence bundle; they never select or refit again.
The existing naive and perfect-foresight planners and configurations retain their behavior.

A study using these planners must declare `selection_evidence_index_sha256`, obtained from the
independently accepted original evidence record. The CLI takes `--selection-evidence-dir` as the
local location of that bundle. Before reading forecast values, verify the pinned evidence index
and every indexed file, refusing missing files, digest mismatches or paths outside the bundle.
Require the original selection summary, forecasts and frozen selection seal. Check that the
summary, seal and evidence index agree, and that the candidate-forecast semantic digest matches.
This unit accepts retrospective supplementary evidence only; it cannot promote an already
inspected evaluation window into confirmatory evidence.

The accepted upstream experiment supplies the causal training and freeze evidence. A matching
hash proves byte identity, not absence of look-ahead by itself. Official use therefore requires
an independently accepted source index; a self-authored index is not independent acceptance.

Require the exact frozen evaluation window. Validation dates must precede it. UTC starts must
be unique and timezone-aware, each recorded market day and duration must match canonical prices,
and the evaluation keys must equal the complete study calendar. Copied actual prices must agree
with canonical settlement prices; selected forecasts must be finite. Zero and negative values
are preserved. No interpolation, missing-day exclusion or evaluation-outcome switching is allowed.

Join forecasts by canonical UTC key, never row order. Each strategy has its own degradation and
stored-energy state, and the same initial physical conditions and terminal-energy rule. Planning
uses the recorded forecast; settlement uses canonical realized prices. Declared physical fade,
the non-cash wear penalty and cash operating/augmentation costs retain their separate meanings.

Record source run/commit, pinned evidence index, frozen seal, candidate forecast identity,
selected candidates and evidence class in the study summary and manifest provenance. The existing
renderer consumes those records without deriving a shared ceiling or cross-configuration figure.
Legacy study summaries and configuration serialization remain unchanged when no replay is declared.

## Acceptance

1. Zero-fade replay reproduces each selected candidate's existing fixed-battery dispatch margins
   and grid flows within the declared numerical tolerance, including zero/negative prices.
2. Different candidate throughput produces independent capacity histories; reversing strategy
   order does not alter either path.
3. Missing or changed evidence, a broken selection seal, wrong window, inconsistent actuals,
   duplicate/missing UTC keys, incorrect market dates/durations and non-finite forecasts fail.
4. The forecasts used by a strategy are exactly the original selected column. A test changes
   later realized outcomes without changing those forecasts and establishes earlier-path invariance.
5. Native DST calendars are retained. No interval is invented or dropped by the adapter.
6. CLI output carries selection provenance through manifest verification and report rendering.
   Existing naive study regressions remain unchanged.

## Official measurement after implementation review

Prepare a separate prospective declaration using the accepted Stage 9 artifact and unchanged
candidate identities, evaluation window and battery. First establish zero-fade reproduction;
then apply explicitly declared physical-fade and cash-cost assumptions. Preserve all outcomes.
Do not rerun the repaired forecasting generator to replace original forecasts: this would
confound the ageing/cost experiment with forecast changes across the resolution transition.

The implementation unit does not silently dispatch that experiment. Its acceptance is synthetic
regression coverage and source-admission checks. Review the concrete experiment declaration,
final-head CI and existing official-run authorization requirements before official measurement.
The result remains retrospective research, not expected revenue or a lifetime return forecast.

## How charging and discharging are chosen

For each next-day interval, the planner chooses grid charge power `c[t]`, grid discharge power
`d[t]` and stored energy `E[t]`. It maximizes forecast sale proceeds minus purchases, trading fees
and the configured non-cash wear penalty. For duration `h[t]` and no self-discharge:

`E[t+1] = E[t] + eta_charge * c[t] * h[t] - d[t] * h[t] / eta_discharge`.

Power, grid, SOC and daily cycle limits apply; charge and discharge cannot occur simultaneously.
The final SOC must equal the declared initial fraction. The optimizer chooses the whole daily
schedule together: no fixed clock time or universal price threshold is used. A small numerical
throughput tie-break is not an economic fee. Fixed operating expenses do not change the current
dispatch, and the current variable finance OPEX is applied after dispatch, not added to its
objective. Physical fade changes the next day's limits; it is not a complete future-life value.

For one isolated trade importing 1 MWh, with zero fees and no wear penalty, a positive forecast
spread after losses requires `eta_charge * eta_discharge * sale_price > purchase_price`.
At 94% efficiency each way, 1 MWh imported returns 0.8836 MWh exported. A synthetic EUR 50/MWh
purchase followed by a EUR 70/MWh sale yields EUR 11.852 before other costs. EUR 50 to EUR 55
yields EUR -1.402. This is an explanatory arithmetic example, not official evidence. The full
optimizer also accounts for competing trades, capacity and terminal SOC.

Forecast-planned quantities are settled at realized DAM prices under the current assumption of
full acceptance. Actual bid acceptance, imbalance settlement and live order submission are not
implemented; a forecast schedule is not an executable market bidding strategy.
