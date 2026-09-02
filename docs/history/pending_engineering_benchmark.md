# Pending narrative updates — engineering evidence and benchmark

This is the implementation report for the engineering-evidence documentation and synthetic
dispatch benchmark change. It also holds the exact prose intended for shared narrative files;
those files were deliberately not edited so concurrent changes remain mergeable. No analytical
result, model assumption, runtime dependency or accepted official-data figure changes.

## Implementation report

### Scope

- Added `scripts/benchmark_dispatch.py`, an opt-in JSON-emitting benchmark for independent daily
  perfect-foresight solves over deterministic synthetic prices.
- Recorded the benchmark command and interpretation in `scripts/README.md`.
- Added two focused tests for the benchmark's reproducibility fields and invalid-day refusal.
- Re-verified the test and mypy counts instead of carrying older figures forward.

### Measurements and attribution

- The accepted-history run documented in
  `docs/official_annual_decomposition_2026-08-28.md` solved 2,124 independent market days over
  74,663 accepted intervals in 69 seconds. That document attributes the measurement to GitHub
  Actions run `33147448666`; it is not a local timing.
- The same accepted decomposition run reported a ceiling reconciliation residual of EUR
  0.000000 and a maximum common-day ceiling spread of EUR 0.000000, as recorded in
  `docs/official_annual_decomposition_2026-08-28.md`.
- The exactness argument and the separate CI-image benchmark for relaxation-first dispatch are
  recorded in `docs/history/implementation_report_v0.8.3_review_response.md`: the relaxation is
  an upper bound on the integer optimum, and a relaxed solution with no simultaneous charge and
  discharge is already integer-feasible, so it is optimal and can be returned unchanged.
- A local 2 September 2026 run of
  `.venv/bin/python scripts/benchmark_dispatch.py --days 366 --resolution-minutes 15 --seed 42
  --negative-price-share 0.02` on Python 3.12.13, NumPy 2.5.2, SciPy 1.18.1 and
  Linux 6.18.35 x86-64 completed 366 relaxation-accepted daily solves over 35,136 synthetic
  intervals in 14.350277 seconds: 25.5047 daily solves/s and 2,448.45 intervals/s. This is a
  local engineering measurement on synthetic data, not an official-history rerun, a CI timing or
  evidence for an investment conclusion.
- A local 2 September 2026 `.venv/bin/pytest -v` run collected and passed 389 tests in 62.55
  seconds. The v0.8.3 review response recorded 387 tests, not 361; this change adds two, so 389 is
  the current count.
- A local 2 September 2026 `.venv/bin/mypy` run reported success over 55 source files. The older
  43-source-file figure in `STATUS.md` described v0.8.1 and no longer represents the refactored
  package; 55 is mypy's current reported count.
- Property-based tests spanning 2015-2035 hourly and quarter-hourly market calendars found and
  led to the correction of the canonical timestamp-resolution defect, as recorded in
  `docs/history/implementation_report_v0.8.3_review_response.md`.

### Version recommendation

A patch bump from 0.8.3 to 0.8.4 is warranted because this adds documentation and opt-in
developer tooling without changing the public analytical behavior or adding a runtime
dependency. No version was changed in this branch, as requested.

## For README.md

Insert the following short section after the limitations and before the quickstart:

### Measured engineering evidence

The accepted official-history decomposition processed 74,663 intervals as 2,124 independent
daily MILP solves in 69 seconds. This was measured by GitHub Actions run `33147448666`, not on a
developer workstation; see
[`docs/official_annual_decomposition_2026-08-28.md`](docs/official_annual_decomposition_2026-08-28.md).
That run reconciled its daily-composed ceiling with a residual of EUR 0.000000 and found a
maximum common-day ceiling spread of EUR 0.000000 across the four like-for-like forecast
comparisons.

Dispatch uses a relaxation-first path that is exact by construction, not accepted within a
heuristic objective tolerance: the relaxation bounds the integer optimum from above, and when
its solution has no simultaneous charge and discharge it is itself integer-feasible and
therefore optimal. The proof and CI-image measurements are in
[`docs/history/implementation_report_v0.8.3_review_response.md`](docs/history/implementation_report_v0.8.3_review_response.md).

The current Python 3.12 validation run passes 389 tests, including property-based market-calendar
tests that previously found a canonical timestamp-resolution defect, and mypy checks 55 source
files. These counts were re-measured locally on 2 September 2026 by `.venv/bin/pytest -v` and
`.venv/bin/mypy`; they supersede the older 387-test and 43-file records. Reproduce a synthetic
throughput measurement on the machine being reported with:

```bash
.venv/bin/python scripts/benchmark_dispatch.py --days 366 --resolution-minutes 15 \
  --seed 42 --negative-price-share 0.02
```

The benchmark emits its environment, assumptions, solve paths, wall-clock time and throughput as
JSON. It uses synthetic prices and is engineering evidence only, never evidence for an investment
conclusion. See [`scripts/README.md`](scripts/README.md) for interpretation and a shorter smoke
run.

## For CHANGELOG.md

Add under the current unreleased section:

- Document measured engineering scale with direct provenance: the accepted 74,663-interval,
  2,124-daily-solve run and its 69-second GitHub Actions timing, exact relaxation-first argument,
  and zero ceiling reconciliation residuals.
- Add an opt-in synthetic dispatch benchmark that emits reproducibility metadata, solve-path
  counts and throughput without entering the default test run or adding a runtime dependency.
- Re-verify the Python 3.12 validation inventory at 389 passing tests and 55 mypy-checked source
  files; no analytical result changes.

## For STATUS.md

Add the following dated status item:

## Engineering evidence is visible and reproducible — 2 September 2026

The previously recorded engineering measurements now have landing-page prose with direct
provenance, and an opt-in synthetic benchmark makes daily dispatch throughput reproducible on
the machine being reported. The accepted official-history evidence remains unchanged: GitHub
Actions run `33147448666` solved 2,124 independent market days over 74,663 intervals in 69
seconds and reported both a ceiling reconciliation residual and maximum common-day ceiling spread
of EUR 0.000000. A local Python 3.12 re-verification passes 389 tests and mypy checks 55 source
files. The benchmark is synthetic engineering evidence only; no analytical result, dependency,
scope or accepted official-data finding changed
(`docs/history/pending_engineering_benchmark.md`).

Where `STATUS.md` currently says "mypy over 43 source files, 355 tests" in the v0.8.1 historical
section, leave that historical measurement intact. Where the current top-level status refers to
the review response without a current validation count, append "with the present tree
re-verified at 389 tests and 55 mypy-checked source files".

## For DECISIONS.md

Add the following dated decision:

## 2026-09-02 — Keep performance claims attributable and reproducible

- **Decision:** Every published engineering timing names the run and environment that measured
  it. Provide an opt-in benchmark over deterministic synthetic prices that emits its full
  configuration, environment, solve-path counts and wall-clock throughput; keep it outside the
  default test suite.
- **Reason:** An elapsed time without its workload and execution context becomes folklore, and a
  GitHub Actions timing must not be presented as a local measurement. Synthetic prices make the
  engineering path reproducible without distributing official data, but cannot support an
  investment conclusion.
- **Consequence:** The accepted official-history 69-second result remains attributed to run
  `33147448666`. New benchmark results must be attributed to the machine and invocation that
  produced them, and comparisons must use equivalent configurations. The benchmark changes no
  dispatch result or modeling assumption and adds no runtime dependency.
