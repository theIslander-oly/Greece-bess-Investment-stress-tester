# Integrated study design — connecting forecasts, ageing and cash flows

**Proposed 10 September 2026**, against `main` at `196a5c1`. This document is the design of
record for the integrated study runner (execution-plan stage 8, review finding 9). Adopting it
is a decision; changing it afterwards requires a further dated decision entry, as
`docs/v0.8_design.md` and `docs/v0.9_design.md` require for their milestones.

**What this document is.** A specification of one study configuration and the contracts between
the modules it drives. It is the reviewable decision that precedes implementation, not a request
to choose among architectures. The implementation unit (`build-integrated-study`) follows it.

**What this document is not.** It adds no source code, no dependency, no workflow and no data
source. It accepts no dataset, produces no figure, and changes no analytical behaviour. It does
not authorize an official-data run.

Labels used throughout:

- **[Verified]** — read directly from the repository at the cited location.
- **[Recommendation]** — a design choice this document proposes.
- **[Deferred]** — deliberately out of scope for the first version, with the reason.

---

## 1. The gap this closes

The repository can already do each step of the analytical chain. It cannot do them together.

[Verified] `backtest_forecast_dispatch` (`src/greek_bess/backtest/forecast_dispatch.py`) plans
each day on a causal forecast and settles it at realized prices — but against a **fixed** battery.
Its config is one `BatteryDispatchConfig` for the whole horizon, and nothing ages.

[Verified] `simulate_degradation_dispatch`
(`src/greek_bess/backtest/degradation_dispatch.py`) evolves a cohort degradation state across
days and dispatches under each day's beginning-of-day limits — but plans with **perfect
foresight**. It reads the day's realized prices to decide.

[Verified] `evaluate_project_finance` (`src/greek_bess/finance/model.py`) turns a continuous
daily operating path into dated cash flows — but the path arrives as a CSV somebody produced
elsewhere.

So the question the project exists to ask — *does a better forecast pay for itself once the
battery ages under the throughput that forecast causes?* — currently requires a human to run
three commands and join their outputs by hand. That join is where an error would be invisible,
because no contract governs it.

## 2. Scope of the first version

**One declared continuous window.** The study runs over a window with complete official prices
and complete forecasts for **every** compared strategy.

**Gaps are refused, never bridged.** A missing delivery day fails the run with a named cause. No
no-trade day is invented, no price is filled, no forecast is imputed. [Recommendation] This is
the single most important constraint in this document: a fill policy is the one change that
would let a short replay quietly become a long one.

**Finance uses exactly that horizon and no more.** If the window is 18 months, the study reports
18 months. It does not annualise, extrapolate to a project life, or repeat a year.
[Verified] `finance/model.py` already refuses a path with missing calendar days
(`_validate_daily_operating_results`); this design does not relax that and adds the horizon rule
above it.

**[Deferred]** Multi-year extrapolation, a terminal-value model beyond the existing configured
residual, strategy-specific batteries, intraday or ancillary revenue, and any lifetime-optimal
dispatch policy. Each is a scope change requiring its own decision.

## 3. Study configuration

One configuration object, one file, one command.

```
IntegratedStudyConfig
  study_id: str                      # names the study in every artifact it produces
  window_start_day: date             # inclusive
  window_end_day: date               # inclusive
  price_source: str                  # official | synthetic; recorded, never inferred
  strategies: tuple[StrategySpec, ...]
  battery: BatteryDispatchConfig     # one battery, shared initial conditions
  degradation: DegradationConfig     # one ageing model, instantiated per strategy
  finance: FinanceConfig             # one cost and discounting basis
  result_label: str
```

```
StrategySpec
  strategy_id: str                   # unique within the study
  planner: str                       # a forecast method name, or perfect_foresight
  decision_information: str          # which information set the planner may read
```

**One battery and one degradation model, instantiated separately per strategy.** The
configuration declares them once so that every strategy starts from identical initial
conditions. Each strategy then owns a private `DegradationState` from that shared starting point.
[Recommendation] This is what makes the comparison a comparison: the strategies differ in what
they knew, not in what they were.

## 4. The per-day contract

For each delivery day `D`, for each strategy `s`, in this order:

**4.1 Read only what was available.** The planner for `s` receives price history strictly before
`D` and, where the strategy declares exogenous inputs, only values whose recorded receipt
satisfies the declared decision cutoff for `D`.

[Verified] The receipt semantics this depends on landed in stage 3:
`retrieved_at_utc` is the instant a message was successfully received, and a derived value
inherits the latest receipt among its inputs (`docs/point_in_time_feature_contract.md`,
`src/greek_bess/data/availability_audit.py`). The study reads that field; it does not re-derive
availability.

**4.2 Plan under this strategy's own beginning-of-day state.** `prepare_degradation_day` returns
the usable energy, charge power and discharge power that strategy `s` begins `D` with. The
planner solves against **those** limits, not the nameplate ones.

**4.3 Settle at realized prices.** The planned schedule is valued at the prices that actually
occurred. [Verified] `_settle_day` in `forecast_dispatch.py` already implements exactly this
separation — planned quantities, realized prices — and this design reuses it rather than
restating it.

**4.4 Age this strategy's state from its own realized throughput.** `complete_degradation_day`
receives the **cell discharge that strategy's settled schedule actually produced**, and returns
its end-of-day state. Calendar fade applies to every strategy alike; cycle fade does not.

**4.5 Emit one dated operating row.** `market_day`, `market_cash_margin_eur`,
`net_market_margin_eur`, `monetary_degradation_adder_eur`, `grid_discharge_mwh`,
`augmentation_cost_eur`, `commissioning_energy_cost_eur`, the cohort energy ledger and
strategy id. Cash margin equals legacy net margin plus the separately reported wear penalty.

**4.6 Finance and record.** After the window completes, each strategy's operating path goes to
`evaluate_project_finance` unchanged, and the run is recorded under the report contract.

## 5. Contracts this design fixes

### 5.1 Per-strategy state isolation

**No strategy may read or write another strategy's degradation state.** Each holds its own
`DegradationState` instance, advanced only by its own settled throughput.

This is the defect most likely to be introduced by a naive implementation, because sharing one
state object across a strategy loop is the obvious way to write it and produces plausible
numbers. The acceptance test is explicit: two strategies with different throughput must reach
different end-of-window capacities, and swapping their order in the configuration must not change
either result.

### 5.2 No shared conditional ceiling after divergence

Once strategies have aged differently, **there is no single perfect-foresight ceiling to quote
across them.** A ceiling is conditional on a physical state, and after day one the states differ.

[Verified] This follows directly from the stage 5 finding already recorded in
`METHODOLOGY.md` §5.1: a day-by-day aggregate under an evolving state is a simulation, not a
bound. The study may record a per-strategy, per-day ceiling under that strategy's own state. It
must not present one number as the ceiling for the study.

### 5.3 Physical fade and monetary degradation are distinct

[Verified] `BatteryDispatchConfig` carries a `degradation_cost_eur_per_mwh_discharged` adder that
enters the dispatch objective (`src/greek_bess/dispatch/perfect_foresight.py`), and
`DegradationConfig` carries physical fade that changes usable capacity.
These are different quantities and the study reports them separately.

**Costs are not double-counted.** Finance reads `market_cash_margin_eur`, which excludes the
shadow wear penalty. Actual augmentation and additional commissioning-energy costs are
cash flows applied once. The acceptance test reconciles these quantities independently.

### 5.4 Terminal SOC

Every strategy targets the configured terminal SOC on its own beginning-of-day usable capacity.
The fixed-capacity forecast backtests require terminal SOC equal to initial SOC. Under changing
capacity, that target must not reset opening energy: each strategy carries its own cohort energy,
records retirement and fade losses, and explicitly declares commissioning energy and cost.
An empty capacity addition must be charged through settled grid purchases to reach the target.

### 5.5 Coverage

Built days and excluded days must partition the declared window exactly, by count.
[Verified] The same rule and the same reasoning as stage 3 unit 2
(`METHODOLOGY.md`, "Shard reconciliation"): a day that is neither built nor excluded by a named
cause is a gap nothing downstream could attribute.

For this study the rule is stricter, because there is no capped list: **every** excluded day
fails the run. Exclusion is a diagnostic, not an outcome.

### 5.6 Provenance and labels

The study records: the price source and its digest, each strategy's planner and information set,
the battery, degradation and finance configurations, the window, and the commit.

[Recommendation] A new result kind, `integrated_study`, on the
**`historical_replay_simulation`** basis added in stage 5 — not on
`historical_replay_upper_bound`. The study evolves state day by day under a policy, which is
precisely what that basis was introduced to describe.

Its label states that the result is one policy's outcome over a declared historical window under
illustrative cost assumptions; not expected revenue, not a forecast, not investment evidence.

## 6. Determinism

Repeated execution must preserve scientific results and content identity. Run timestamps may
differ; nothing else may.

[Verified] The manifest writer already forces LF newlines so digests are platform-independent
(`docs/history/implementation_report_windows_determinism_2026-09-09.md`). The study inherits
that. Seeds, refit cadences and solver settings are recorded in the configuration and reproduced
from it.

## 7. Acceptance checks

Restating the execution plan's checks as testable statements:

1. **One command, one configuration** produces a complete synthetic demonstration, then a
   declared official-history study.
2. **Zero-fade reproduction.** With calendar and cycle fade set to zero, each strategy reproduces
   the corresponding fixed-battery backtest within stated solver tolerances. This is the check
   that proves the new path did not change the old arithmetic.
3. **Separate evolution.** Two strategies with different throughput evolve separately; neither
   borrows the other's state; configuration order is irrelevant.
4. **Causality.** Modifying future information cannot change an earlier forecast or decision.
   Implemented as a test that mutates prices after day `D` and asserts every decision up to `D`
   is byte-identical.
5. **Reconciliation.** Initial and terminal energy, augmentation and fees reconcile against
   configured inputs. Physical fade and the monetary adder are reported separately.
6. **Missing-day input fails clearly**, naming the day and the cause.
7. **Repeated execution** preserves results and content identity.
8. **No shared ceiling** is asserted across strategies after their states diverge.

## 8. Proposed layout

```
src/greek_bess/study/__init__.py
src/greek_bess/study/config.py       # IntegratedStudyConfig, StrategySpec, validation
src/greek_bess/study/runner.py       # the per-day loop of section 4
src/greek_bess/study/results.py      # per-strategy tables, summary, manifest assembly
src/greek_bess/cli/study.py          # one command: run-integrated-study
```

[Recommendation] A new package rather than an addition to `backtest/`. The existing backtest
modules each answer one question about a fixed configuration; this one drives them. Putting the
loop inside either would make that module depend on finance and reporting, which today it does
not.

**Nothing in `dispatch/`, `degradation/`, `finance/` or `reporting/` changes.** The study is a
composition of existing contracts. If implementation finds that one of them must change, that is
a finding to record and review, not a change to make quietly.

## 9. Artifacts

```
outputs/<study_id>.daily.csv          # one row per strategy per delivery day
outputs/<study_id>.strategies.csv     # per-strategy summary, including end-of-window state
outputs/<study_id>.cash_flows.csv     # dated cash flows per strategy
outputs/<study_id>.summary.json       # the recorded result, under the report contract
outputs/<study_id>.manifest.json      # the run manifest
```

The existing renderer consumes the manifest unchanged.

## 10. What could make this design wrong

Recorded now, so that finding one of them later is a check on the design rather than a surprise:

- **If the zero-fade reproduction fails**, the composition is not equivalent to the existing
  backtests and the difference must be explained before anything else proceeds.
- **If a strategy's planner needs information the point-in-time contract cannot express**, the
  contract is the thing to revisit, not the planner.
- **If the declared window has no continuous span with complete forecasts for every strategy**,
  the study cannot run as specified, and the answer is a narrower declared window — not a fill
  policy.
