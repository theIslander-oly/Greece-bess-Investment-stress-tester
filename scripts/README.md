# Reproduction scripts

This directory is reserved for small, reviewable orchestration scripts that reproduce official
downloads, cleaning, audits and reports. Reusable analytical logic belongs in `src/greek_bess`.

Scripts must:

- read secrets from environment variables;
- avoid printing credentials;
- write downloaded and derived data only below ignored data/output directories;
- record source URL, retrieval time, publication version and SHA-256 where applicable; and
- fail clearly rather than silently filling missing official observations.

Current ingestion entry points are exposed through the `greek-bess` CLI and documented in the
README. Manual GitHub retrieval workflows are in `.github/workflows/fetch-entsoe.yml` and
`.github/workflows/fetch-official-history.yml`.

## Synthetic dispatch throughput benchmark

`benchmark_dispatch.py` measures the relaxation-first daily dispatch path without official data:

```bash
.venv/bin/python scripts/benchmark_dispatch.py --days 366 --resolution-minutes 15 \
  --seed 42 --negative-price-share 0.02
```

The command prints JSON containing the complete synthetic-data and battery configuration,
Python/platform and numerical-library versions, solve-path counts, elapsed wall-clock time and
throughput. Run it on the machine whose timing is being reported: elapsed times are
hardware- and environment-specific and must not be transferred between local and CI runs.

This deliberately slow benchmark is outside the default test suite. Its deterministic synthetic
prices reproduce no official series and its output is engineering evidence only, never evidence
for an investment conclusion. Use fewer `--days` for a quick smoke measurement; the default is
30 days.
