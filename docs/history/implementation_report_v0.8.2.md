# Implementation report v0.8.2 — Interactive viewer decision

**Date:** 1 September 2026

## Decision

Do not add Streamlit or another local interactive viewer in v0.8. Complete the milestone with
the deterministic static renderer delivered in v0.8.0 and its multi-run composition delivered
in v0.8.1.

This is a deliberate scope decision, not deferred implementation. A future interactive proposal
must identify a user need the static report cannot meet, say whether that need changes the
approved scope, and receive its own dated decision and milestone. Interactivity is therefore
neither prohibited forever nor retained as implicit unfinished v0.8 work.

## Evidence considered

The approved interface has to be read-only, exportable and bound to verified run manifests. The
existing renderer already provides:

- one self-contained HTML document and one machine-readable index;
- deterministic output from deterministic manifest inputs;
- an indexed multi-run layout with stable links to every manifest block;
- adjacent result labels, basis wording and standing exclusions for every figure;
- no computation, environment read, network read or access to a path named by a manifest;
- no server process and no new runtime dependency; and
- executable refusal of unverified manifests, unlabeled figures, forbidden distributional
  vocabulary, duplicate manifest identities and cross-manifest or cross-basis arithmetic.

An interactive viewer cannot create new evidence within those constraints. Controls that
compute a derived value, reach through a manifest to an interval file, merge figures across
bases or silently select judgmental defaults would break the approved design. Controls that do
none of those things can only navigate or hide information already present in the report, whose
index and in-document links already provide navigation without a running service.

The marginal benefit is therefore presentation convenience, while the marginal cost is a new
dependency, a server lifecycle and a second surface on which every manifest check, label,
basis boundary, exclusion and vocabulary refusal must remain synchronized. That trade does not
improve the transparency, reproducibility or evidentiary value of the tool.

## What changed

No source behaviour changed. There is no viewer package, server command, network route, stateful
session, client-side computation or new report format. Version 0.8.2 records the completed
decision milestone and keeps the package, report footer and official-retrieval user agent on one
declared version.

The project records were reconciled to the decision:

- `DECISIONS.md` records the decision, reason and consequence;
- `docs/v0.8_design.md` records the design amendment and the condition for reconsideration;
- `PLAN.md` and `STATUS.md` close v0.8 rather than carrying a viewer as an open item;
- `README.md` states the completed interface and links this report; and
- `CHANGELOG.md` records the decision-only release and absence of runtime change.

## What remains unchanged

The renderer still reads verified run manifests, and only verified run manifests. It does not
compute dispatch, forecast, stress, degradation or finance results; it does not open official
price series; and it does not combine values across manifests or bases. Perfect foresight remains
a labelled gross-margin upper bound, synthetic scenarios remain non-probabilistic and unsuitable
as investment evidence, and all standing market and commercial exclusions remain in force.

The two operator items also remain untouched: a second custody copy under separate control does
not exist, and `ENTSOE_SECURITY_TOKEN` is not configured. Neither is a reporting-layer task.

## Validation evidence

Because this milestone deliberately changes no runtime path, no new behavioral test was invented
to create the appearance of implementation. The complete existing suite remains the regression
evidence: Ruff passed, mypy passed over 43 source files, all 355 tests passed, and a clean isolated
wheel build produced the 0.8.2 wheel with the typed-package marker present. The version-consistency
tests cover `pyproject.toml`, the package constant, the README release line and the official-data
user agent. The complete diff, generated-file set, official-data paths and secret patterns were
also reviewed before commit; no generated research output, official dataset or secret enters the
change.

## Roadmap consequence

v0.8 is complete. The static report is the sole presentation surface in the approved scope.
AI-generated explanations remain outside v0.8, and no later phase is opened by this decision.
