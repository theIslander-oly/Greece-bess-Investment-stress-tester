# Stage 10 release preparation — 18 November 2026

## Outcome and scope

Continue the recorded publication-review gate after merged PR #85 on main
`0327c55a658d16501d7c93ac466c13ec7f21b6fa`. The earlier continuation conversation establishes
the ordered experiment and separate Stage 10 publication steps; the current plan and 19 September
acceptance report establish that the frozen-selection experiment has since completed privately.
Do not repeat either accepted experiment or start a new model unit.

Branch `prepare-stage10-publication` adds a helper, a manual read-only preparation workflow,
synthetic refusal tests and the [concrete publication review](../stage10_publication_review_2026-11-18.md).
It changes no analytical package module, dependency, configuration, historical declaration,
accepted finding or selection rule. Neither a report nor a new numerical outcome is committed.
Stage 10 remains in review and no deployment is performed.

## Recovered evidence

Recover original artifact `10510326086` from accepted run `35252229873`, not a new scientific
execution. Its ZIP matches SHA-256
`9aaa06804b7baf3079c24d76ee7b8dbce45264f85b7dddb5f387a7d11c20f4a9` recorded by GitHub
and the [original acceptance report](implementation_report_stage10_private_study_2026-09-17.md).
The evidence index matches
`214a4caaf52d16f9bd7cb508eb9334f94bfa3a98696cc4820b89eec612daf938`; all 18 indexed
files match, the historical declaration is unchanged, custody verified and both manifests
match their recorded summaries. Report-index entries identify the correct manifests and basis.

Re-rendering with current code produces the original HTML SHA-256
`5fb8ccc56b083d9f2cc3a1fdf05b0252c86a4599da1cec29913d3bbb9bdbd342` exactly. The
staged report index retains SHA-256
`08e58ca064b5b99575d8da1f5d1a6dd7e105f62228802e275f498970beb2da84`. No dispatch,
forecast fitting, selection or financial calculation is repeated. The prior scientific audit
remains the acceptance evidence; this continuation verifies retained identity and rendering.

## Release preparation behavior

The helper admits only the pinned source run, commit, evidence index, declaration and report.
It verifies every indexed file before reading the two manifests and their summaries, then
requires exact HTML reproduction and a matching report index apart from its render timestamp.
All checks pass before creating a new output directory outside the source bundle. It refuses
symlinks and path traversal, and preserves any existing destination by refusing to overwrite it.

Only the original aggregate HTML and index are staged. The receipt carries hashes and keeps
`publication_authorized` false. The manual workflow downloads the fixed accepted source and
retains those two files and the receipt separately. It has no deployment job or write permission
to repository contents or Pages. It does not repeat the official-study workflow.

The local review surface and private brief are ignored files in `private/`. No raw prices,
daily schedules, finance tables, logs, manifests or custody records enter the aggregate package
or Git. The full source artifact's 16 December expiry and independent-custody limitation remain
explicit; an aggregate package is not a backup of the full evidence.

## Validation

- Fifteen new synthetic regression cases pass, covering the two-file output, original-byte
  preservation, changed or missing indexed files, an unaccepted index, a validly hashed report
  that fails to re-render, wrong manifest hashes, failed custody, existing output, source/output
  separation, symlinks and path traversal. Fixture acceptance pins are replaced only inside
  disposable tests; the command exposes no override for official pins.
- Ruff passes. Mypy passes for 76 package modules and separately for the new helper.
- The clean isolated wheel build succeeds from a fresh exported source tree.
- The helper succeeds on the original retained artifact and writes the expected two-file
  aggregate plus a separate receipt. Re-rendering is byte identical.
- All 854 tests pass locally in 370.25 seconds with numerical-library threads set to one.
  The latest fixture-only newline adjustment also passes its 15-case focused suite.
  Final-head Python 3.12 and 3.13 CI results are recorded with the PR validation.
- Complete diff, documentation links, whitespace, generated-file, credential and contributor-neutral
  attribution checks pass. The analytical source, configurations and declarations are unchanged.

Local validation uses Python 3.12.14, NumPy 2.5.5, pandas 2.3.3, SciPy 1.18.1,
scikit-learn 1.9.1 and ecCodes 2.50.1. The numerical runtime differs from the original
experiment; no claim of scientific re-execution under the original runtime is made.

## Remaining gates

Review the exact aggregate and decide separately whether and where to publish it. Preserve
existing public reports, deploy only the approved files and compare served hashes before
closing Stage 10. This PR and the preparation command confer no publication authorization.

The separate frozen-selection acceptance record names
`private/frozen-selection-experiment-2026-09-19/` in the previous workspace and seals it under
`f7cb1203898844a1539c0dd63e28415ac96252753b0c5c5c150b755f09ae4a4c`. That bundle has
not been recovered here. No aggregate or outcome sign is inferred from the acceptance prose,
and Stage 10's different experiment is not substituted for it. Its publication review stays open.
