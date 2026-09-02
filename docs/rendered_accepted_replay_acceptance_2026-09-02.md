# First rendered accepted-replay report — 2 September 2026

## Acceptance statement

Workflow `Render a report from the accepted replay`, run
[`33609809770`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33609809770),
completed successfully on `main` on 2 September 2026 in 58 seconds. It consumed decomposition
run `33147448666`; no substitute run or regenerated analysis was used.

This accepts the first exercise of the v0.8 renderer against the accepted official-history
replay. It accepts presentation machinery and label retention, not an investment conclusion.
Every perfect-foresight figure remains a historical gross-margin upper bound, every forecast
figure remains a historical backtest outcome, and neither is expected revenue or a forecast.

## Source evidence and custody gate

The source `annual-replay-decomposition` artifact was still live when dispatched. Its recorded
expiry was 26 November 2026 and its zip SHA-256 was
`119e2465c272fdc4e6259d94813478360ee26520d23f0eef33d0909ec65d0291`, matching the accepted
decomposition record exactly.

The render run downloaded that artifact and found its
`greek-dam-official-history.verification.json`. The refusal step recorded custody verification
as `True` before any manifest was recorded. All six generated manifests then passed
`verify-run-manifest` before rendering. The run would have stopped before rendering if the
verification record were absent or false, or if any manifest failed verification.

## Rendered output

The run produced and uploaded the private `accepted-replay-report` artifact with nine files:

- the self-contained `accepted_replay_report.html`;
- the machine-readable `accepted_replay_report.index.json`;
- six verified run manifests covering the daily-composed ceiling, annual decomposition and four
  causal forecast-dispatch backtests; and
- the source custody-verification result.

The report self-check passed. Its index declared rendered manifests, contained figures, covered
both `historical_replay_upper_bound` and `historical_forecast_backtest`, and the HTML retained
the required probability and investment-evidence exclusions. The renderer read the accepted
aggregate summaries; it did not read or publish interval-level official prices or schedules and
did not recompute an analytical result.

## Scope of acceptance

This document closes the missing first-render acceptance item. It does not accept GitHub Pages
publication: public deployment is a separate, narrowly scoped disclosure step and is accepted
only after its deployment workflow succeeds. It also does not extend the model beyond Greek
Day-Ahead Market energy arbitrage or change any accepted analytical figure.
