# Pending narrative updates — accepted-replay report publication

This is the conflict-free staging record for shared documentation. The prose below is intended
to be merged into each named destination after the GitHub Pages deployment succeeds. Replace the
single bracketed deployment-run placeholder with the successful run identifier before merging.

## For README.md

Add this link near the top of the repository landing page, adjacent to the accepted official
findings:

> **Rendered accepted replay:** [Open the custody-gated aggregate report](https://theislander-oly.github.io/Greece-bess-Investment-stress-tester/accepted-replay/).
> It presents verified aggregate historical-replay and forecast-backtest summaries. Perfect
> foresight is a labelled gross-margin upper bound, not expected revenue; the report is not
> financial advice, a forecast or investment evidence, and contains no interval-level official
> price or schedule.

## For CHANGELOG.md

### Changed

- Exercised the v0.8 renderer against accepted decomposition run `33147448666`, with custody
  verification and all six run manifests passing in render run `33609809770`, and published only
  its aggregate HTML report and machine-readable index at a stable GitHub Pages path. The complete
  evidence bundle remains a private Actions artifact; no interval-level official price, schedule,
  manifest or custody record enters Pages.

## For STATUS.md

Replace **“Open — render the accepted replay, awaiting a dispatch”** and the corresponding status
summary wording with:

> ## Closed — accepted replay rendered and aggregate report published
>
> `Render a report from the accepted replay` run `33609809770` consumed the still-live accepted
> decomposition run `33147448666`. Its custody-verification refusal gate recorded `True`, all six
> manifests verified, the report self-check passed and the nine-file complete evidence bundle was
> retained as the private `accepted-replay-report` artifact. This is the first accepted exercise
> of the v0.8 renderer against official-history aggregate summaries
> (`docs/rendered_accepted_replay_acceptance_2026-09-02.md`).
>
> Deployment run `[DEPLOYMENT_RUN_ID]` published the aggregate HTML report and report index at
> [the stable accepted-replay URL](https://theislander-oly.github.io/Greece-bess-Investment-stress-tester/accepted-replay/).
> The publication job depends on the custody-gated render job and refuses any public file beyond
> those two aggregate outputs. It publishes no interval-level official price, schedule, manifest
> or custody record. The report is presentation of accepted historical evidence, not expected
> revenue, a forecast, financial advice or an investment-grade study.

## For DECISIONS.md

## 2026-09-02 — Permit one custody-gated aggregate report on GitHub Pages

- **Decision:** Make a narrow exception to the default prohibition on publishing generated
  research outputs for the accepted-replay renderer's self-contained HTML report and
  machine-readable report index. Publication is permitted only when the source replay passes its
  committed custody-verification gate, every input manifest verifies, and the report contains no
  interval-level official price or schedule. Publish those two aggregate outputs at the stable
  `accepted-replay/` GitHub Pages path; keep manifests, custody records and the complete evidence
  bundle private and keep generated outputs uncommitted.
- **Reason:** The report adds no evidence and computes no analytical result. Every displayed
  figure is already recorded in aggregate in
  `docs/official_annual_decomposition_2026-08-28.md`, and the renderer retains its result label,
  basis and standing exclusions. A stable presentation URL makes the accepted evidence
  reviewable without disclosing the official interval history. Treating this as a scoped
  publication exception is more transparent than silently contradicting the repository's
  generated-output rule.
- **Consequence:** The Pages job depends on the successful custody-gated render job, receives the
  only Pages write permission, and applies a two-file allow-list. This exception does not permit
  publishing interval series, schedules, manifest or custody evidence, other research outputs or
  reports assembled outside the verified-manifest doorway. Any broader publication needs a new
  dated decision. Perfect foresight remains a gross-margin upper bound and the public report is
  not a forecast, financial advice, investment evidence or an investment-grade study.

## Version recommendation

A patch bump from 0.8.3 to 0.8.4 is warranted. This is a backward-compatible operational and
documentation change that exercises and publishes the existing report contract; it changes no
manifest schema, renderer output, analytical behavior or runtime dependency. No version is
changed in this branch as requested.
