# Pending narrative updates — deterministic report SVG charts

**Implementation report, 2 September 2026.** This file is both the implementation report for
the change and the exact narrative staging area requested for shared project records.

## For README.md

The self-contained report now includes a deterministic inline SVG view of the minimum, maximum
and spread values already recorded for each path by a single scenario-ensemble manifest. The
chart reports no new quantity, reads no file named by the manifest, and never combines manifests
or bases. It remains inside the manifest's labelled block and is distinguishable by exact text,
opacity, outline, dash and shape in both light and dark colour schemes.

## For CHANGELOG.md

### Changed

- Bumped the report renderer contract from version 2 to version 3. Scenario-ensemble reports now
  include a deterministic, dependency-free inline SVG of their already-recorded per-path minimum,
  maximum and spread values. Charts retain the manifest label, basis and standing exclusions,
  add no derived result, use no external asset or script, and state missing or unusable chart
  fields instead of failing.

## For STATUS.md

**Report renderer version 3 — deterministic charts:** the static report now adds a
manifest-local inline SVG for the values a scenario-ensemble manifest already records under
`path_ranges`. Plot coordinates are presentation geometry, not a newly reported quantity; exact
recorded values remain visible as text. The renderer still reads verified manifests only, opens
no path a manifest names, reads no environment or network, plots no interval-level official
price series, and combines neither manifests nor bases. Missing, empty and non-object chart
fields are stated without crashing. No runtime dependency or analytical result changed.

## For DECISIONS.md

## 2026-09-02 — Treat manifest-local plotting as rendering, with a closed chart doorway

- **Decision:** Permit deterministic inline SVG charts only when they plot values already
  recorded inside the single verified manifest whose labelled block contains them. SVG
  coordinates and lengths are presentation geometry, not reportable results; a chart may not
  derive or display a new quantity. The initial closed chart maps only
  `scenario_ensemble_range.path_ranges` and shows its recorded per-path minimum, maximum and
  spread values.
- **Reason:** A visual encoding can make a recorded table more legible without changing the
  evidence. Treating any coordinate calculation as analytical computation would prohibit all
  plotting, while allowing arbitrary chart inputs would create a route around the manifest-only
  design. A closed result-kind and summary-key mapping preserves the distinction: visible values
  come from one verified summary, and geometry only places them.
- **Consequence:** Renderer version 3 emits project-owned, byte-deterministic inline SVG with no
  dependency, script, network or external asset. It opens no manifest-declared file, accepts no
  interval series, never merges manifests or bases, and keeps each chart inside the existing
  block carrying that manifest's result label, basis and standing exclusions. Missing, empty,
  non-sequence, non-object or non-numeric chart data produces an explicit absence statement,
  never an invented value or crash. Text labels plus opacity, outline, dash and shape keep the
  chart readable without colour alone and under light or dark colour schemes.

## Version recommendation

A patch bump from 0.8.3 to 0.8.4 is warranted because this adds a backward-compatible renderer
capability and increments only the renderer contract from 2 to 3; it does not change the run
manifest schema, analytical behaviour or runtime dependencies. No project version was changed
in this branch, as requested.

## Validation record

The implementation adds regression coverage for byte-identical output, inline self-containment,
label/basis/exclusion retention, missing guaranteed keys and non-object chart fields. On Python
3.12.13, Ruff passed, mypy passed over 55 source files, all 391 tests passed, and a clean wheel
build succeeded. The final diff, secret scan and generated-artifact review found only the intended
source, test and documentation changes; ignored build products were removed before commit.
