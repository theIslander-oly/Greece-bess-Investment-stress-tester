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
