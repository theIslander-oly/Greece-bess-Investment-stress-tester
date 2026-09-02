# Custody-gated accepted-replay publication — 2 September 2026

## Scope

This change turns the already exercised accepted-replay renderer into a stable GitHub Pages
publication without re-running analysis. It adds no runtime dependency and changes no model,
manifest, renderer, accepted figure or analytical assumption.

## Publication design

The existing `render` job retains read-only repository and Actions permissions. It downloads the
accepted decomposition artifact, refuses absent or failed custody verification, records and
verifies all manifests, renders the report, checks its contract and uploads the complete evidence
bundle as a private 90-day Actions artifact.

A separate `publish` job depends on successful completion of `render`. Only that job receives
`pages: write` and `id-token: write`. It downloads the report artifact from the same workflow run
and stages exactly two files under the stable `accepted-replay/` path: the aggregate HTML report
as `index.html` and its machine-readable report index. An allow-list check refuses any additional
file. The verified manifests and source custody record remain in the private artifact; official
interval prices and schedules never enter either report input or the Pages artifact.

The dependency is the publication gate: a missing or false custody-verification record, a failed
manifest verification, a report self-check failure or an artifact upload failure prevents the
Pages job from running.

## Policy boundary

Publishing a generated research output is a narrow exception to the repository's default rule.
It is limited to a renderer output derived exclusively from verified aggregate summaries and
carrying no interval-level official price or schedule. It does not permit committing generated
reports, publishing private evidence bundles, or publishing any interval series. The exact dated
decision prose is staged in `docs/history/pending_publish_accepted_replay.md` for conflict-free
integration into the shared records.

## Acceptance evidence

The first render itself is recorded in
`docs/rendered_accepted_replay_acceptance_2026-09-02.md`. Pages publication remains operationally
pending until the workflow version in this change is merged, dispatched successfully and its
deployment URL is checked. That distinction prevents implementation from being presented as live
evidence.

## Validation

Workflow-contract tests pin the dependency on the refusal-gated render job, the Pages permissions,
the two-file public allow-list and retention of the complete private artifact. The Python 3.12
development environment is prepared with `scripts/bootstrap-dev-env.sh`; Ruff, mypy, pytest and a
clean wheel build are run before submission. The final diff, ignored build outputs, tracked files
and secret patterns are reviewed before commit.
