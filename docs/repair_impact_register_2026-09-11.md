# Impact of the numerical and accounting repair on recorded results

The repair merged as #71 (`ed884e6`) changed how five quantities are computed. This register
says, for every recorded result, whether the repair moves it — with the evidence, not an
assumption. It answers one question and stops: **is any figure this repository currently
presents as current now stale?**

**Answer: one, and it was already regenerated inside the repair itself.** No accepted
official-history result changes. Nothing is indeterminate.

## Method

`a733372` is `main` immediately before the repair. Both revisions were installed into separate
Python 3.12 environments and run over identical deterministic synthetic prices
(`generate_synthetic_prices(2025-01-01, 2025-04-01, resolution_minutes=60, seed=11)`) through
every code path that produces a recorded result. Whole result frames were compared column by
column, not just headline totals. Synthetic prices are adequate here because the question is
whether the arithmetic changed, which does not depend on which prices enter it.

| Frame compared | Rows | Shared columns | Largest absolute difference |
| --- | ---: | ---: | --- |
| Perfect-foresight interval schedule | 2,159 | 29 | 0 (exact) |
| Forecast backtest daily results, each of 4 methods | 83–89 | 13 | 0 (exact) |
| Forecast backtest interval schedule, each of 4 methods | 1,991–2,135 | 38 | 0 (exact) |
| Annual decomposition: overview, forecast, common-day | 1 / 4 / 4 | 31 / 19 / 13 | 0 (exact) |
| Degradation dispatch, fade only, no capacity change | 90 | 34 | 5.5e-12 on `cumulative_cell_discharge_mwh_end` |
| Degradation dispatch, with a capacity addition | 90 | — | **material; see below** |

Every difference other than the last row is either exactly zero or floating-point
reassociation twelve orders of magnitude below the reported precision. Where columns were
added — `market_cash_margin_eur` and the energy-ledger columns — nothing existing was removed
or altered.

## The five impact channels, and what each can reach

| Channel | Reachable only through | Recorded results it touches |
| --- | --- | --- |
| IRR uniqueness certificate | `evaluate_project_finance` | The synthetic demonstration only |
| Annual break-even margin on a partial horizon | `evaluate_project_finance` | The synthetic demonstration only |
| Realization fraction applied to losses | `evaluate_project_finance` | None: see below |
| Wear penalty treated as cash | `evaluate_project_finance`, `run-integrated-study` | None |
| Stored-energy accounting | `simulate-degradation-dispatch`, `run-integrated-study` | None |

No workflow in `.github/workflows/` runs `simulate-degradation-dispatch`,
`evaluate-project-finance` or `run-integrated-study`. Every accepted official result is
produced by `optimize-perfect-foresight`, `backtest-forecast-dispatch`,
`decompose-annual-replay`, `benchmark-fundamentals-forecast` or
`benchmark-fundamentals-dispatch`, and the table above shows all of those are bit-exact.

## Register

| Recorded result | Producer | Verdict | Evidence |
| --- | --- | --- | --- |
| Annual perfect-foresight ceilings 2020–2026 and the EUR 24,974,729.59 accepted-history total (`README.md`, `docs/official_annual_decomposition_2026-08-28.md`) | `optimize-perfect-foresight --daily-solves`, `decompose-annual-replay` | **Unaffected** | Schedule and all three decomposition tables bit-exact across revisions |
| Causal-method capture ratios per method per year | `backtest-forecast-dispatch`, `decompose-annual-replay` | **Unaffected** | Daily and interval frames bit-exact for all four methods |
| Fundamentals ablation: `ridge` +EUR 4,899.71, `hist_gradient_boosting` −EUR 6,843.46 (`docs/fundamentals_benchmark_2026-09-11.md`) | `benchmark-fundamentals-dispatch` | **Unaffected** | `fundamentals_dispatch.py` is untouched by the repair and settles on `realized_margin_eur`, which is bit-exact |
| Forecast-error (RMSE) table in the same document | `benchmark-fundamentals-forecast` | **Unaffected** | No forecast module was touched |
| Rendered accepted-replay report (`docs/rendered_accepted_replay_acceptance_2026-09-02.md`, render run `33609809770`) | `render-report` over decomposition run `33147448666` | **Unaffected figures; digests would move on re-render** | It renders decomposition figures, which are bit-exact. Manifests now carry additional keys, so a fresh render records different manifest digests for identical figures. Re-rendering is not required; if it is re-rendered, the digest change is not a result change |
| Synthetic demonstration ceilings in `docs/sample_report.html` | `optimize-perfect-foresight --daily-solves` | **Unaffected figures; digests changed** | Net market margin identical (EUR 1,362,102.7236630027 and EUR 2,162,101.190159156). Digests moved only because `market_cash_margin_eur` and the wear-penalty policy string were added |
| Synthetic demonstration finance screen in `docs/sample_report.html` | `evaluate-project-finance` | **Changed — already regenerated in `cffdcb4`** | One figure moved, detailed below |
| Any degradation-dispatch result | `simulate-degradation-dispatch` | **None recorded** | No workflow runs it; no committed document carries its output |
| Any integrated-study result | `run-integrated-study` | **None recorded** | The command landed on 11 September 2026 and has not produced a recorded run |

## The one changed figure

In the synthetic finance screen, **break-even average annual market margin moves from
EUR 53,908,552.73552773 to EUR 51,903,102.77104751**, −EUR 2,005,449.96 or −3.72%. That is the
partial-horizon repair doing exactly what it was written to do: the run covers 365 days, or
0.999315537 project years, and the old whole-year denominator (1.08)^−0.999315 = 0.925975
understated the discounted exposure that the corrected daily basis puts at 0.961753.

The change is arithmetically closed, which is the check worth doing: the ratio of the two
recorded figures is 0.962799039, and the ratio of the two denominators is 0.962799039. They
agree to nine decimal places, so the whole move is the denominator and nothing else drifted.

Everything else in that manifest is unchanged, which is worth stating explicitly because it
bounds the repair rather than advertising it:

- NPV −EUR 49,065,454.21437615 — unchanged.
- IRR −0.9800653165183428, status `calculated` — unchanged. The series has one sign change, so
  the new certificate resolves it exactly as the old rule did.
- Realized market margin EUR 885,366.7703809516, maximum initial CAPEX for zero NPV
  EUR 934,545.7856238508, break-even realization fraction 38.06052908482951 — unchanged.

**The realization channel did not bite here, and that is evidence rather than luck.** Realized
margin is exactly 0.65 × the input margin to sixteen significant figures, which is only possible
if no daily margin in that scenario was negative. Had one been, the corrected treatment would
have retained it in full and the product would not match.

`docs/sample_report.html` was regenerated inside the repair commit `cffdcb4`, so the committed
file already carries the corrected figure. Nothing is stale in the repository today.

## Reproducing this register

Two revisions, two environments, one probe:

```bash
git worktree add /tmp/pre a733372
python3.12 -m venv /tmp/venv-pre && /tmp/venv-pre/bin/pip install -e "/tmp/pre[dev]"
python3.12 -m venv /tmp/venv-post && /tmp/venv-post/bin/pip install -e ".[dev]"
# then run the same probe script under each interpreter and diff the emitted frames
```

The probe calls `optimize_perfect_foresight`, `backtest_forecast_dispatch` for each of the four
methods, `decompose_annual_replay` over those results, and `simulate_degradation_dispatch` with
and without an `AugmentationEvent`, writing every result frame to CSV for column-by-column
comparison. It is deliberately not committed: it is a one-off comparison between two revisions,
not a test the repository needs to keep running. The regressions that must keep running are in
`tests/test_accounting_regressions.py`.

## What would require a rerun, if it ever exists

Nothing recorded today needs one. A future result requires rerunning under the corrected
conventions if any of the following holds. This is the checklist to apply, not a claim about
present outputs:

1. It reports IRR, break-even average annual margin, or any figure derived from
   `evaluate_project_finance`.
2. It applies a realization fraction other than 1.0 **and** its operating path contains at
   least one negative daily margin.
3. Its dispatch used a non-zero `degradation_cost_eur_per_mwh_discharged` **and** the result
   passed through finance.
4. Its degradation configuration contains an augmentation or retirement event. Fade alone is
   not sufficient: with terminal SOC equal to initial SOC, carried energy scales exactly with
   usable capacity and the dispatch is unchanged, which the fade-only comparison above confirms.

For reference, a capacity addition is the case that moves. Over the probe window, adding
50 MWh and 25 MW mid-horizon on a 100 MWh battery moved the degradation-dispatch net margin
from EUR 626,821.81 to EUR 625,107.97, −EUR 1,713.84 or −0.27%, with grid discharge falling
22.90 MWh. The pre-repair run sold stored energy that the capacity addition had created from
nothing; the repaired run charges it from the grid first.

## Limitation of this register

It establishes that the repaired code paths return identical values on identical inputs for
everything except finance outputs and capacity-changing degradation runs. It does not re-derive
the accepted official figures from the official price history — that would need the
custody-gated inputs and the official-run authorization, and it is not necessary, because the
code paths that produced them are demonstrably unchanged.
