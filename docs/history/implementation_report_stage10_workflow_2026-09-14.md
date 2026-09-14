# Stage 10 reproducible release and official-workflow preparation — 14 September 2026

## Change

Stage 9 result PR #77 had already merged as `abfac6a`; CI run `34824236600` passed on Python
3.12 and 3.13. Stage 10 therefore opened on `release-integrated-research-study`.

`run-integrated-study` now supports a self-contained synthetic release run. A configuration may
declare the history start, interval resolution, seed, negative-price share and fixed retrieval
timestamp under `synthetic_price_generation`; the command can then generate those prices, run the
study and render its verified manifest with no separate price file. Official studies cannot use
that path. Automatic configuration and price/generation digests are recorded in the manifest;
additional controlled-run provenance can extend but cannot replace them.

The renderer now lays every field of every integrated-study strategy out side by side. Each cell
walks back to an exact manifest path. It derives no ranking, cross-configuration difference or
shared ceiling, and refuses a ragged strategy table rather than rendering a blank as a value.

The committed synthetic example now ends on 28 March 2026. Its former end date crossed the spring
23-hour market day; `daily_persistence` correctly lacked one same-position prior-day observation
on 30 March, and the integrated study correctly refused it. The narrower demonstration changes no
method and invents no interval.

The dated official declaration preregisters accepted history run `33483975614`, the 329-day
1 October 2025 through 25 August 2026 study window, three fixed planners, and two separate studies
using the committed 50 MW/100 MWh and representative 25 MW/100 MWh batteries. Degradation and
illustrative finance are held identical. This is configuration sensitivity, not evidence of an
optimal size or cost optimisation.

The prepared workflow verifies the declaration digest and existing custody before reading
prices, checks the complete accepted calendar, runs both configurations with private logs,
verifies and renders only their manifests, checks the aggregate report, and seals exact evidence
digests. It publishes nothing. Official dispatch and publication remain separate approval gates.

## Validation to date

Focused validation passed first, followed by the complete repository gates on Python 3.13.7:
Ruff reported no findings, mypy reported no issues across 75 source files, all 804 pytest tests
passed, and an isolated wheel build produced
`greek_bess_investment_stress_tester-0.9.7-py3-none-any.whl`. Two executions of the committed
synthetic configuration produced
byte-identical daily, strategy, cash-flow and summary artifacts. The rendered report was
self-contained, script-free and carried the strategy composition and standing labels.

No official run has been dispatched and no official result has been produced.

## Next gate

The complete diff, secret, attribution and generated-file review passed. Open and review the
Stage 10 workflow PR. After merge, the operator may approve the unchanged declaration digest and
authorize one official dispatch. Result publication remains separately gated.
