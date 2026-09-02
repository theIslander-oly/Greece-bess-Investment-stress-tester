# Implementation report v0.9.0 — v0.9 opened: point-in-time fundamentals forecast benchmark

**Date:** 2 September 2026

## What this phase is

The design and the two declaration formats for v0.9, and nothing else. No source code under
`src/`, no dependency, no workflow, no data source, no retrieval and no analytical change. The
phase exists so that the question v0.9 asks, the evidence standard it must meet and the gates that
can stop it are on the record before any code is written against them.

## The question, and why it is this one

`LIMITATIONS.md` names one open analytic question in the forecasting layer: validated weather,
demand, fuel, renewable and interconnector forecasts are not included, so every accepted forecast
figure in this repository comes from price history alone. v0.9 asks whether an independently
validated exogenous input improves the realized settled dispatch value of a day-ahead battery over
price-history models alone.

The alternatives were weighed and set aside. An interactive viewer was declined by dated decision
and a one-command demonstration already exists; neither adds evidence. A third price-history model
answers nothing the accepted evidence leaves open: the held-out comparison puts the two existing
model families and a naive rolling mean within half a percentage point of capture of each other,
which says the binding constraint is the information available to the models rather than the
function class. A leveraged finance layer and a second revenue stream are excluded until
independently validated, and the revenue-stream item was deferred by the user.

The primary metric is realized settled margin on common days, expressed as the incremental margin
of the challenger over its own control, because the accepted evidence contains a case where price
error and settled value disagree — `rolling_mean` has worse RMSE than `ridge` and captures more
value. Price error is reported because it explains the mechanism, not because it decides.

## What landed

- `docs/v0.9_design.md`, the design of record. It carries the current-state architecture
  assessment and the four places a new abstraction is genuinely required; the candidate-source
  assessment; the decision-time and gate-closure contract; the point-in-time feature schema; the
  join algorithm with its pre- and postconditions and invariants; the data-acceptance milestone;
  the benchmark and evaluation design; what may and may not be concluded; the adversarial test
  plan; the module layout, CLI surfaces and manifest kinds; the phase sequence; the risk register;
  and the go/no-go gates.
- `config/decision_cutoff.example.json` — the existing dated-regime gate-closure format under a
  neutral name, because the cutoff v0.9 needs is not an ADMIE question and a live feature must not
  read its format from a module documented as retained and unused. The ADMIE example is unchanged
  and stays.
- `config/fundamentals_geography.example.json` — the declared sampling points and weights for a
  gridded fundamentals variable, with a stated basis for the choice.
- `tests/test_config_examples.py` — six tests holding two properties at once for every committed
  example: it still parses through the reader that will read the real declaration, so the format
  cannot drift away from the code; and it stays recognisable as an example, so it cannot be copied
  into a run and mistaken for a declaration. A parsed schedule must also resolve a closure instant,
  so an example cannot pass the reader while declaring a regime no delivery day can be audited
  against.
- Project records: the decision entry, the `PROMPT.md` scope amendment, the v0.9 plan section with
  its phase sequence and its two new waiting-on items, the status section and the changelog entry.

## What the design commits to

**The cutoff is declared, never defaulted.** A declared closure schedule and a declared decision
lead in minutes — which may be zero — are required arguments of every v0.9 surface where
availability matters. The effective cutoff for delivery day D is the declared closure minus the
declared lead, and a feature is available for D only if its publication instant is *strictly*
before it. A publication at the cutoff is late. This is the refusal the gate-closure schedule
already records, applied to a live feature path rather than a quarantined one: the tooling reports
whatever closure is declared and cannot check the declaration against the market rules.

**Three instants, with distinct roles.** The provider's publication instant decides availability;
this project's own retrieval instant grades it, and witnesses availability when the retrieval
happened before the cutoff; the revision identity selects which publication of the same datum a
backtest may read. Delivery coordinates describe what the value is about and never enter the
availability comparison. A model issue time is provenance and never substitutes for a publication
instant.

**Evidence grades that never merge.** `witnessed` and `provider_declared` are admissible and
reported separately. `assumed` — availability inferred from a regulatory deadline or a nominal
latency rather than from the datum itself — is quarantined, usable only in an explicitly labelled
exploratory run that is never recorded as accepted. The distinction is the whole point: a
provider's timestamp read after the fact asserts availability, while a retrieval performed before
the cutoff witnesses it, and witnessed days accumulate one delivery day at a time and cannot be
backfilled. The witness workflow therefore starts in v0.9.1 rather than at the benchmark.

**Leakage ruled out by construction rather than by assertion.** The store keeps every revision, so
the evidence that a revision was superseded is never discarded. The join selects the latest
revision published strictly before the cutoff, counts the later ones and excludes them, records an
audit row naming the source document, revision and byte digest behind every feature value, and
marks a day complete or excluded by named cause. Nothing is forward-filled, interpolated or
imputed; a missing value is an absent row, never a `NaN` reaching a fit. Realized target-day
quantities are refused by name as well as by timestamp, so the label cannot be smuggled in under a
timestamp error.

**Acceptance before modelling.** Successful retrieval is not accepted use. A dated acceptance
document covering retrieval, parsing, schema, provenance, revision identity, completeness,
duplicates, units, DST, publication timing, the cutoff audit, reconciliation and custody must
exist before any benchmark document, and no benchmark manifest may declare a feature-set digest
that no acceptance document names.

**A result recorded whichever way it falls.** One feature set, two fixed model families, no tuning,
validation-only selection, and no re-splitting, re-tuning or cutoff change after seeing test
results — any such change is a new benchmark under a new decision entry. If the accepted coverage
yields fewer than one full meteorological season of quarter-hour common test days, the run is
labelled exploratory and no general conclusion reaches the README.

## What was deliberately not built

Templating the renderer, generalizing the existing ML dispatch benchmark, changing the canonical
price schema, and adding a feature store, plugin registry or abstract data-source base class. One
source needs one client module, as HEnEx and ENTSO-E each have today. The one genuine abstraction
the benchmark requires of existing code is a feature-column parameter on the walk-forward fitter,
with the current module constant as its default, so that the control arm provably reproduces
today's behaviour through the new path.

## What is not established

- **~~No data source is chosen.~~ Resolved later the same day.** The spike ran and the source is
  NOAA GFS 0.25° forecast vintages; see the addendum below and
  `docs/fundamentals_source_assessment_2026-09-02.md`. The assumption recorded here that live
  endpoints are reachable only from Actions runners was wrong for this archive, and the plan is
  corrected.
- **No declaration exists.** The decision cutoff, the decision lead and the sampling geography are
  operator declarations with no defaults. Both committed examples carry placeholder references and
  are refused as declarations while those placeholders remain.
- **Nothing about skill or value.** Recording this design accepts no source, lifts no quarantine,
  admits no figure as evidence and changes no accepted result.

## What did not change

No accepted figure, analytical behaviour, dependency, workflow, manifest kind, contract version or
report format. The 2026-09-01 removal of ADMIE load and RES forecasts from scope stands and is not
reopened by any route: ENTSO-E's Greek load and renewable forecasts originate from ADMIE, and
taking them through another publisher would be that reversal by another name. They are isolated as
a separate track requiring its own dated decision, the restored token and forward-witnessed
acceptance, and no phase of v0.9 depends on them. Perfect foresight remains a labelled upper bound,
forecast backtests remain historical research results, and every standing exclusion in `PROMPT.md`
is unchanged.

## Validation

Ruff, mypy, the full test suite and a wheel build were run against the change. The suite gains six
tests and no existing test was modified.

---

# Addendum — the source-selection spike, 2 September 2026

The spike that the phase above left open ran the same day. Its evidence is
`docs/fundamentals_source_assessment_2026-09-02.md` and its decision is the DECISIONS.md entry
*Choose NOAA GFS forecast vintages as the v0.9 fundamentals source*. This addendum records what
changed in the phase, not the evidence itself.

## What the spike was, and where it ran

Three checks the design made the source choice conditional on, plus the licence: archive coverage
across 2021-2026, byte-range subsetting through the `.idx` sidecars, and a pip-installable ecCodes
binding leaving the repository's four gates green on 3.12 and 3.13. All four passed, so G0 is not
triggered and the EEX EU ETS fallback is not selected.

It ran from a working checkout, not from an Actions runner. The plan's operating constraint —
live endpoints are reachable only from runners — is true of `www.admie.gr` and false of this
archive, so the constraint is now recorded per host rather than universally. The same egress
policy did refuse `www.eex.com`, `eur-lex.europa.eu`, `data.ecmwf.int`,
`archive-api.open-meteo.com` and `registry.opendata.aws`, and the candidates behind those hosts
are recorded as unknowns rather than quietly verified.

The probe scripts were throwaway and are not merged, as the design said they would be. Section 9
of the assessment records each probe as a command anyone can re-run, which is the reproducibility
the repository actually needs; a merged spike module would be product code this phase does not
have.

## What it changed in the design

Four things move from recommendation to settled fact, and Section 3 of the design carries an
amendment note pointing at the assessment: the source is chosen; the decision-time cycle is fixed
at 00 UTC of D-1, which the design had left open; the usable hourly record begins at delivery day
27 February 2021 rather than at the archive start, so 118 of the accepted history's 2,131 delivery
days carry no feature; and two ingestion facts — both key layouts before April 2021, and a
per-forecast-step availability check because upload order is not monotone in step — become
requirements rather than details.

Nothing in the contract moves. The cutoff, the decision lead and the sampling geography remain
undeclared, and the 12:00 `Europe/Brussels` instant the assessment uses to size publication
margins is illustrative arithmetic against which nothing is accepted. The evidence grades are
unchanged, and the spike supplied the concrete case that justifies quarantining `assumed`: a run
on 14 June 2021 published 1 h 39 m after that illustrative cutoff, which a nominal-latency
assumption of about four hours would have admitted and been wrong about.

## What it did not change

No source code, no dependency, no workflow, no data source and no analytical behaviour. The
decoder was installed into a throwaway virtual environment to run the four gates against it;
`pyproject.toml` is unchanged and `eccodes` is first declared in v0.9.1. Nothing retrieved during
the spike is committed — no GRIB2 message, no listing, no index — consistent with the repository
contract that provider content stays out of Git. No figure became evidence: an assessment is not
an acceptance document, and the design's Section 7 acceptance still precedes any benchmark
document.

## What v0.9.1 inherits

It may start. It declares `eccodes` alone — not `cfgrib` or `xarray`, which the low-level
single-message read does not need — and its first CI run closes the one residual the spike could
not: the four gates passed on CPython 3.12.3 and 3.13.12 in the development environment, not on
the `actions/setup-python` images. A failure there returns the source choice to the G0 branch,
and the fallback would then need the spike it has not had.

## Validation

Ruff, mypy, the full suite and a wheel build were run on 3.12 and 3.13 with the decoder installed
alongside the project, and again on the committed tree, which is documentation-only. 403 tests
pass on both interpreters and no test was added or modified by this addendum.
