# Stage 9 design — evaluate selection by battery value

This is the predeclared protocol for the Stage 9 supplementary experiment in
[`Greek_BESS_Execution_Plan.md`](../Greek_BESS_Execution_Plan.md). It is written before any
result is produced, so that the selection rule, the tie-break, the windows and the reporting
set are fixed rather than chosen once the numbers are visible.

It changes no existing benchmark. The Stage 7 fundamentals result stands exactly as recorded in
[`fundamentals_benchmark_2026-09-11.md`](fundamentals_benchmark_2026-09-11.md).

## The question

`greek_bess.forecast.ml` selects the model it reports as `selected_model` by one rule:

> `model_selection_policy`: "Lowest validation RMSE; test metrics are not used for selection"

RMSE is a price-error objective. This project's object is a battery, and a battery earns from
the *ordering and spread* of prices within a delivery day, not from the level of the price it
predicted. Those two things are not the same quantity, and this repository has already recorded
a case where they disagree: `rolling_mean` has a worse RMSE than `ridge` and captures more
value.

So the question is narrow and answerable:

> Among the same model families and candidate configurations, does selecting on validation RMSE
> or selecting on validation settled margin produce more settled margin on days neither rule
> was allowed to see?

The answer is evidence about which objective serves the battery study. It is not a claim that
either rule predicts prices better, and it is not investment evidence.

## What is compared

**Candidates.** A candidate is a name, a model family and an explicit set of hyperparameter
values. Candidates are declared in `greek_bess.selection.candidates` in a fixed order, and that
declared order is the tie-break, so it is part of the protocol rather than an implementation
detail. Both families already in `ML_MODELS` are represented; no family is added, because
adding models is not what this stage tests.

**Objectives.** Two, scored on validation days only:

| Objective | Quantity | Direction |
| --- | --- | --- |
| `validation_rmse` | Interval RMSE in EUR/MWh over validation days | Minimize |
| `validation_settled_margin` | Realized net market margin in EUR over validation days, settled at realized prices | Maximize |

Both are computed for every candidate, from the same forecasts, on the same days, under one
battery configuration. The only thing that differs between the two arms of this experiment is
which of the two numbers the selection rule reads.

**Settlement.** Margin is produced by
`greek_bess.backtest.ml_dispatch._backtest_precomputed_forecast`, which is the accepted path
the ML and fundamentals dispatch benchmarks already use. A candidate settled here is the
accepted computation with a different forecast column and nothing else.

## The selection schedule

Three windows, contiguous and disjoint, derived from one pair of dates:

```
[ training ............ ) [ validation ....... ) [ evaluation ....... )
                       validation_start_day   evaluation_start_day
```

- **Training** supplies the walk-forward fits. Every fit reads prior market days only; this is
  the existing `_walk_forward_predict` loop, unchanged.
- **Validation** is where both objectives are scored and where selection happens. Exactly once.
- **Evaluation** is scored after selection is frozen, and never feeds back into it.

Selection is a single freeze before the evaluation window, not a rolling re-selection.
Rolling re-selection is a different experiment with a different failure mode, and running one
policy over one declared evaluation window is the version whose result can be read without
argument about when each switch happened.

**Outcome-dependent switching is prohibited**, and the code enforces the ordering rather than
documenting it: the frozen selection record is built from validation quantities alone, hashed,
and passed into the evaluation step as an immutable input. The recorded
`frozen_selection_sha256` covers the candidate names, the objective values that chose them and
the window dates, so a selection that had been revised after seeing an evaluation number would
not reproduce its own digest.

## Deterministic tie-breaking

Floating-point objective values are compared against the best value with a declared absolute
tolerance, not for exact equality:

- `RMSE_TIE_TOLERANCE_EUR_PER_MWH = 1e-9`
- `MARGIN_TIE_TOLERANCE_EUR = 1e-6`

Every candidate within tolerance of the best value is tied. The winner is the tied candidate
with the **lowest declared index**. Declared order is fixed before any data is read, so a tie
resolves to the same candidate on every platform and every rerun. The summary records whether a
tie occurred and which candidates were in it; a tie that was broken silently would be a
selection nobody could reproduce.

## What is reported

For each objective, on the evaluation window:

- Realized settled margin (EUR) — the primary figure.
- Perfect-foresight margin, regret against it, and capture ratio.
- Regret against the **retrospective best candidate** — the candidate with the highest
  evaluation margin. This is a diagnostic ceiling, not a policy: it is chosen with knowledge of
  the evaluation outcome, so no selection rule can be expected to reach it, and it may never be
  reported as an achievable result.
- Equivalent full cycles and grid charge/discharge energy, beside the battery's power and
  energy capacity, because a margin difference bought with materially more cycling is a
  different trade, not a better one.
- Interval RMSE and MAE in EUR/MWh, so the price-error consequence of choosing on value is
  visible rather than assumed.

Alongside them, `candidate_forecast_sha256` names the candidate forecast table every figure was
computed from. The summary can describe the candidates but cannot see the schedule and feature
configuration that produced their predictions, so it names the table instead: two runs reporting
the same digest read identical forecasts, and two reporting different digests are not comparable
however alike their candidate lists look.

The headline comparison is one signed number: evaluation margin under margin-selection minus
evaluation margin under RMSE-selection. It is recorded by the module that owns the settlement
basis and never derived downstream by subtracting two reported totals.

## Acceptance checks, and how each is met

| Check | How |
| --- | --- |
| Selection uses validation data only, on common dates and equivalent physical assumptions | Objectives read validation rows only; one battery config plans and settles every candidate; the perfect-foresight ceiling is asserted identical across candidates to `CEILING_TOLERANCE_EUR` |
| The selected policy is frozen before its evaluation period | Frozen record built from validation quantities, hashed, passed as an immutable input to evaluation |
| A synthetic case proves the two objectives can select different policies | `tests/test_value_based_selection.py` constructs a day where the lower-RMSE candidate settles strictly less margin, and asserts the two objectives select different candidates |
| Report held-out settled margin, regret, cycling and capacity beside price errors | All are in the per-objective evaluation record above |
| Already inspected historical periods are labelled retrospective supplementary evidence | The summary carries `evidence_class`, which is `retrospective_supplementary` for any window already inspected; a confirmatory label requires a newly predeclared untouched or prospective window |
| An unfavourable result is retained | The experiment records the signed difference whatever its sign; nothing in the module prefers one outcome, and Stage 7's committed result is mixed by model family, which is the standard this matches |

## What this experiment cannot establish

- **It is one window, not a distribution.** One frozen selection over one evaluation window
  produces one signed difference. That is evidence about this window, and this repository does
  not convert it into a probability or a confidence interval it would have to calibrate.
- **A favourable result is not a licence to switch the shipped default.** Changing
  `model_selection_policy` in `forecast/ml.py` is a separate decision with its own gate, and
  this stage does not take it.
- **Candidate grids are a choice.** A different grid could produce a different sign. The grid is
  declared so that a reader can see exactly what was and was not offered to either rule.
- Everything in [`LIMITATIONS.md`](../LIMITATIONS.md) continues to apply. This is Greek
  Day-Ahead Market research and pre-feasibility scope, and a settled margin here is a
  historical research result, never expected investment revenue.
