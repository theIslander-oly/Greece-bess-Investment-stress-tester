# Implementation report v0.9.1 — one-source ingestion and the availability audit

**Date:** 2 September 2026

## What this phase is

The first v0.9 code. It builds everything that can be built without the operator declarations
v0.9 waits on, and it stops exactly where those declarations begin. Four modules, one CLI module
with two commands, two workflows, one manifest kind, two renderer checklist entries and one new
dependency. Nothing here accepts a value, admits a source to a benchmark or changes an accepted
figure.

It also closes the source spike's one open residual, and that is now a result rather than a plan.
`eccodes` is declared in `pyproject.toml` for the first time, so CI installs and imports it on the
`actions/setup-python` images rather than on the two locally built interpreters the spike used.
CI run `33630855958` passed on 2 September 2026 on both matrix entries, `validate (3.12)` and
`validate (3.13)`, each running install, Ruff, mypy, the suite under coverage and the wheel build
as separate gating steps. Two things follow from that and the workflow's step order: `eccodes` is
a hard runtime dependency, so the install step could not have succeeded without resolving it on
the runner image, and
`tests/test_gfs.py::DecoderTests::test_the_binding_reports_its_library_version` imports the
binding and asserts a version string, so a decoder that installed but would not load could not
have reached the wheel-build step. A failure on either count would have returned the source choice
to the G0 branch and sent the EEX fallback for the spike it has never had; neither occurred, and
the fallback stays unselected and unassessed.

## What landed

**`src/greek_bess/data/decision_cutoff.py`** — `GateClosureRegime`, `GateClosureSchedule` and
`DECLARABLE_CLOSURE_TIMEZONES`, moved verbatim out of `admie_timing.py`, which now re-exports
them. The reason for the move is stated in the design and asserted in the tests: a live feature
path must not import its decision rule from a module whose own docstring says it is retained and
unused. Added in front of them: `read_decision_cutoff_schedule`, which refuses the committed
example by name; `validate_decision_lead_minutes`, where zero is a declaration and absence is
not; and `effective_cutoff_utc`, which is closure minus lead.

`AdmiePublicationTimingError` is now an **alias** of `DecisionCutoffError`, not a subclass. A
subclass would have meant that a refusal raised by the moved schedule code was no longer caught
by `except AdmiePublicationTimingError`, which is what every existing caller, workflow and test
does. `tests/test_admie_timing.py` passes untouched, which is the evidence that the move changed
nothing.

**`src/greek_bess/data/point_in_time.py`** — the typed feature schema of design Section 5: the
closed column set, the closed source set, the closed variable registry with its units, the four
evidence grades, `ensure_point_in_time`, the CSV reader and writer, coverage counting, and the
declared `SamplingGeography` with its own placeholder refusal. A missing value is an absent row
and never a `NaN`; a unit that is not the registry's unit is refused; two rows sharing the
uniqueness key and disagreeing are refused with both named; validation is idempotent and
independent of row order.

**`src/greek_bess/data/gfs.py`** — the NOAA GFS client. Both archive key layouts, `.idx` sidecar
parsing into inclusive byte ranges, byte-range retrieval, GRIB2 decoding through `eccodes`,
sampling at declared grid nodes, radiation de-averaging, and one `RetrievalRecord` per message
retrieved. The fetcher, the HEAD reader and the decoder are injectable, so the suite exercises
the client's logic rather than the provider's uptime.

Two failure modes are refused rather than absorbed. An object that exists but carries no
`Last-Modified` is named as such and not retried under the other key layout: an object that is
there without a publication instant is a different fact from an object that is not there, and
availability inferred from anything but the datum is the quarantined grade. And the declared
points are resolved to flat grid indices once, from the first decoded message's grid header,
with every later message checked against that grid — a step published on a different grid would
otherwise be sampled at the right index of the wrong array, which is the only failure here that
produces plausible-looking numbers.

**`src/greek_bess/data/availability_audit.py`** — per-delivery-interval verdicts against the
declared cutoff, the derived evidence grade, per-day statuses that each name a cause, and a
summary carrying what the audit does and does not establish.

**`src/greek_bess/cli/fundamentals.py`** — `fetch-fundamentals` and
`audit-feature-availability`. The audit exits 2 on any unaccepted day and writes its evidence
anyway, following the ADMIE timing audit's convention that a finding is a result.

**`src/greek_bess/data/http.py`** — `fetch_https_bytes` gained an optional `byte_range`, and a
new `head_https_headers` reads response headers without a body. A server that answers 200 to a
range request is refused rather than accepted as the requested slice.

**`reporting/contract.py`** gained the `point_in_time_availability_audit` result kind on the
`data_acceptance_evidence` basis, with seven guaranteed summary keys. `reporting/render.py`
gained two `DeclarationRequirement` entries, so the landing checklist now names the decision
cutoff, the decision lead and the sampling geography with their decision date and the command
that records a result with them.

**Workflows.** `fetch-fundamentals.yml` retrieves a window and audits it, refusing at its guard
step without the declared geography and cutoff. `witness-fundamentals.yml` runs daily and
retrieves tomorrow's delivery day before the declared cutoff.

**Configuration.** `config/decision_lead_minutes.example.txt` documents the third declaration and
deliberately contains no number — any integer would be a syntactically valid lead, so a
placeholder integer would be the one placeholder a reader could not tell from a declaration.
`config/official_sources.json` records the chosen source with
`availability_classification: requires_point_in_time_acceptance` and the three licence
obligations. `.gitignore` now excludes `acceptance/`, the directory the workflows write retrieved
provider content and derived evidence into.

## Why the witness workflow starts now

Witnessed evidence is the only evidence in v0.9 that cannot be produced later. A
provider-declared publication instant can be read at any point in the future; a witnessed one
exists only if a retrieval actually happened before the cutoff of the day in question. Every day
the workflow does not run is a day the witnessed subset can never recover, so it starts in the
first code phase rather than at the acceptance run.

Its schedule is `0 6 * * *`, and that is an operator setting recorded in the file with its
reasoning: the 00 UTC cycle was observed publishing between 3 h 41 m and 4 h 10 m after the
cycle, so 06:00 UTC is after the objects appear and before any midday CET gate. The workflow does
not assert that it was in time — it runs the audit for the day it retrieved and reports whether
the day came out `witnessed_before_cutoff`, so a schedule that is too late for the declared
cutoff announces itself rather than quietly producing provider-declared rows.

## Two corrections to the source assessment, both verified

**The required forecast steps are 22–47, not 21–46.** The assessment computed the step range from
the *Athens* delivery day (21:00 to 21:00 UTC in summer). This project's delivery day is the
**CET/CEST market day** — the same day `market_day_starts` and the canonical price schema use —
which begins an hour later, so the range a market day actually needs is 22 through 47. Rather
than replace one written-down constant with another, `required_forecast_steps` derives the set
from each market day, so a 23-hour or 25-hour day produces its own set; a test walks every market
day of the usable record and asserts the widest range is exactly (22, 47) and lies inside the
hourly product. Nothing in the assessment's availability evidence is weakened by this: it
measured the lag on step 48, which is later than any step now required, and availability is
checked per step in any case.

**A derived value's provenance is the union of its inputs.** The design's schema assumes one
value comes from one message. Two of the three variables do not: wind speed combines the two 10 m
components, and a de-averaged radiation hour combines two adjacent step objects. So for a derived
value, `published_at_utc` is the **latest** contributing object's instant — the value became
available when its last input did — `source_document_id` names every contributing object and
message, and `raw_sha256` is taken over the contributing message digests in a stated order, with
each contributing message listed separately in the retrieval manifest. Taking the earliest
instant, or one input's digest, would have over-claimed availability and broken traceability.

## Verification

Ruff, mypy, pytest and the wheel build were run on the project's development interpreter with
`eccodes` installed as a declared dependency. The suite grew from 403 tests to 520: four new test
modules — `tests/test_decision_cutoff.py`, `tests/test_point_in_time.py`,
`tests/test_availability_audit.py` and `tests/test_gfs.py` — plus the render fixture extension
that the new manifest kind requires. Design Section 11 cases 5, 6, 9, 12, 13 and 24 are covered
by name; the schema property tests generate the market calendar from 2021 to 2035 rather than
enumerating the transition days somebody thought to write down.

The client was also exercised once against the live archive during development, building one
complete delivery day (20 August 2026) for two variables from 50 byte-ranged messages: 24 hourly
rows per variable, radiation zero overnight and peaking near 909 W m⁻², temperature between 296.5
and 307.2 K. That run is evidence the pipeline works end to end; it is **not** an accepted
figure, no part of it is committed, and it used a throwaway geography that is not a declaration.

## What is blocked, and by what

Every runnable surface in this phase needs a declaration the repository refuses to supply
(gate G3), so v0.9.1's code is complete and tested but cannot be run against real data:

- **the decision-cutoff schedule** — `config/decision_cutoff.json`, with a real rulebook citation
  and one dated regime per rule change;
- **the decision lead in minutes** — `config/decision_lead_minutes.txt`, one non-negative integer;
- **the sampling geography** — `config/fundamentals_geography.json`, named points, weights that
  sum to one, and a stated basis with its vintage.

Until all three exist, `fetch-fundamentals` and `audit-feature-availability` refuse at their
readers, both workflows stop at their guard steps, and the witness workflow accumulates no
witnessed days. The phase's own acceptance criteria that depend on a dispatched run — a
one-month `fetch-fundamentals` window with its audit recorded, and a witness run producing a
witnessed day — are therefore outstanding for that reason and no other.

## What this phase deliberately did not do

No join, no model, no manifest recorded from real data, no acceptance document. `cfgrib` and
`xarray` were not added: the low-level single-message read needs neither, and the smaller
dependency is the one the spike exercised. ADMIE-originated forecasts were not reopened by any
route, including through ENTSO-E. No accepted price-history figure changed.
