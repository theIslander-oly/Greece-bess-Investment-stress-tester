# First report rendered from the accepted replay — 2 September 2026

## Scope and interpretation

This document records the first render of a report from the accepted official Greek DAM replay.
It adds no model, market, transformation or data, and it computes no figure. The v0.8 renderer
reads run manifests and lays out the values those manifests already recorded; every figure in the
rendered report is a value the accepted decomposition run had already produced and that was
accepted on 28 August 2026.

Rendering is a presentation step, so nothing here changes an analytical result. What this run
establishes is narrower and was the open question: that the reporting layer, previously exercised
only on synthetic manifests and real module summaries, works end to end against accepted official
evidence and refuses what it is required to refuse.

Every rendered figure remains a **historical gross-margin upper bound** or a **historical
backtest outcome on a selected period**. Neither is expected revenue, a forecast, a probability,
or investment evidence.

## Method and provenance

Workflow `Render a report from the accepted replay`, run
[`33609809770`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/33609809770)
(run number 1, attempt 1), on `main` at `2a6bd80`, dispatched 2 September 2026 at 08:38:41 UTC and
completed at 08:39:39 UTC — 58 seconds. Python 3.12.14.

Inputs: `decomposition_run_id` `33147448666`; `report_id` left empty, so the manifest identifier
prefix defaulted to `accepted-replay-33147448666`.

1. Downloaded the `annual-replay-decomposition` artifact (ID `9676575888`) from run
   `33147448666`. The expected and the downloaded digest both read
   `sha256:119e2465c272fdc4e6259d94813478360ee26520d23f0eef33d0909ec65d0291`, which is the digest
   `docs/official_annual_decomposition_2026-08-28.md` records for that artifact. The evidence
   rendered here is the evidence that was accepted, unchanged.
2. **Applied the custody gate.** The run read the decomposition's own custody verification result
   and logged `Custody verification recorded by run 33147448666: True`. A missing or failed
   verification would have stopped the run before any manifest was recorded; this is the first
   live exercise of that refusal path against accepted evidence.
3. Read the accepted summaries from `artifacts/annual-replay-decomposition/replay`.
4. Recorded six run manifests under the manifest contract, each carrying the same declared input
   provenance naming the source workflow, source run and source artifact.
5. Verified all six manifests before rendering any of them.
6. Rendered one indexed report and its machine-readable index.

## Manifests recorded and verified

| Manifest ID | Result kind | Source summary | Produced by |
| --- | --- | --- | --- |
| `accepted-replay-33147448666-ceiling` | `daily_perfect_foresight_dispatch` | `perfect_foresight_daily.summary.json` | `optimize-perfect-foresight` |
| `accepted-replay-33147448666-annual` | `annual_replay_decomposition` | `annual_summary.json` | `decompose-annual-replay` |
| `accepted-replay-33147448666-backtest-daily_persistence` | `forecast_dispatch_backtest` | `backtest_daily_persistence.summary.json` | `backtest-forecast-dispatch` |
| `accepted-replay-33147448666-backtest-weekly_persistence` | `forecast_dispatch_backtest` | `backtest_weekly_persistence.summary.json` | `backtest-forecast-dispatch` |
| `accepted-replay-33147448666-backtest-rolling_mean` | `forecast_dispatch_backtest` | `backtest_rolling_mean.summary.json` | `backtest-forecast-dispatch` |
| `accepted-replay-33147448666-backtest-ensemble` | `forecast_dispatch_backtest` | `backtest_ensemble.summary.json` | `backtest-forecast-dispatch` |

Every one of the six passed `verify-run-manifest` before the render step ran. The run logs record
each `Recording …` line and each `verified …` line individually.

## What the run's self-check established

The workflow checks the rendered report against the manifests it claims to render, and every
assertion passed:

- the index state is `rendered_manifests`;
- the index manifest count equals the number of manifest files actually recorded, so the report
  does not claim a manifest it did not read, or silently drop one;
- the figure count is greater than zero;
- both `historical_replay_upper_bound` and `historical_forecast_backtest` appear in the rendered
  bases, so the report carries the ceiling and the settled backtests under separate bases rather
  than merged;
- the rendered document contains `not a probability-calibrated estimate` and `not investment
  evidence, financial advice or a bankable study`, so the standing exclusions survived rendering.

The run also wrote its index — manifest count, figure count, contract and renderer versions,
bases rendered and bases absent, and the per-manifest digests — to its job step summary. That
summary carries no figure, deliberately, for the same reason the report's own index carries none.

## Evidence artifact

Artifact `accepted-replay-report`, ID `9838522404`, nine files, 18,657 bytes, zip SHA-256
`272f43ba2cad44193a2de37859eb123ae912dbe3d72a361b16e7ab857d82f3e9`, 90-day retention expiring
1 December 2026 at 08:38:42 UTC. It holds the rendered report, its index, the six manifests and
the source custody verification result.

The artifact carries no custody record, for the same reason the decomposition artifact does not:
it holds no interval-level price, it has no provider that could revise it, and everything that
determines it — the custodied history, `main` at `2a6bd80`, the accepted decomposition run and its
fingerprinted artifact — is already recorded. If it lapses it is regenerated, not recovered.

## Limits of this acceptance

- **The rendered HTML was not inspected outside the runner.** The session that dispatched this run
  could not retrieve the artifact: its egress policy denies the artifact storage host. The
  evidence for the report's content is therefore the run's own self-check, quoted above, which
  asserts the structural and label properties that matter, rather than a human reading of the
  document. A reader who downloads the artifact should confirm it presents as expected.
- **The figure count and the contract and renderer versions are not restated here.** They went to
  the run's step summary and were not independently read back, and this project does not restate a
  number it did not read.
- This acceptance covers rendering only. It re-accepts no analytical result, and it does not
  publish the report anywhere.

## Standing after this run

The open item that asked for a dispatch is closed. The reporting layer has been exercised against
accepted official evidence end to end, including the custody refusal it exists to enforce, and
this document is the acceptance record it required.
