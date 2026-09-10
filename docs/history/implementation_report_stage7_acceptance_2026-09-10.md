# Implementation report — Stage 7 step 5: the dated acceptance document

**Date:** 10 September 2026
**Execution-plan stage:** 7, step 5. Steps 6 and 7, the benchmarks and their result, are not
started.

Aggregates only. No feature value, price or interval-level record appears here or in any file
this report names. This accepts data suitability and nothing else.

## What step 5 required that step 4 could not supply

Step 4 left every figure the acceptance document must state already computed, and one thing
missing: primary-source support. Two declarations rest on publications the tooling cannot verify
and both require the primary text to be retained with the acceptance evidence — the HWEA/ELETAEN
wind statistics behind the geography weights, and the day-ahead gate-closure rule behind the
cutoff. Writing the document without them would have been inventing its support.

The publishers' sites are unreachable from this project's working environments, and the runner is
where every live retrieval already happens, so retention became a workflow. `Retain primary
sources` reads a committed declaration, `config/primary_sources.json`: pages whose links it lists,
documents it downloads. For each document it records byte size and SHA-256, prints the metadata
and the passages matching declared search terms for a person to read, uploads the files privately
and attaches them to a declared release. It reads no operator declaration and decides nothing.

**An asset already on the release is never overwritten.** A retained copy that differs from a
fresh download is a finding, and the job stops naming both digests.

## Retention

Nine documents are retained on release `primary-sources-2026-09-10` by runs `34517968860` and
`34518723361`, cited with digests and quoted passages in `docs/primary_sources/README.md`:
the HWEA/ELETAEN Wind Energy Statistics 2023; the NEMO Committee notice extending SDAC to Greece;
RAE Decision 1574/2020 on the commencement of coupled operation; the SDAC timings note of
26 May 2021; HEnEx Decision 10 in its versions of 20 October 2020, 20 September 2021 and
31 March 2026; and the two 15-minute MTU notices of September and October 2025.

The guard was exercised without being asked. Run `34518625198` received a 12,113-byte non-PDF
response from the HWEA statistics URL; the digest did not match the retained copy, nothing was
overwritten, and the job stopped. The next run received the document again with the retained
digest.

## The finding the retention produced

**The declared pre-coupling gate closure was one hour early.** The 3 September 2026 declaration
set the closure at 12:00 Europe/Athens for delivery days from 2020-11-01 until the SDAC coupling
on 2020-12-16, called that value the weakest element of the declaration, and required that a
contradiction with the retained text be corrected before any test run.

HEnEx Decision 10 of 20 October 2020 (ref. 2205/20.10.2020) is the day-ahead timeline in force at
the 1 November 2020 launch and the only version before September 2021 in the HEnEx library. It
states that all its times refer to CET and EET, and tabulates "12:00 (CET), D-1 / 13:00 (EET),
D-1 — The Day-Ahead Market Gate Closure Time". Its September 2021 and March 2026 successors state
the same. The declared Athens-clock closure was an hour before the published one.

The declaration was corrected before any benchmark, as its own terms required. One regime is now
declared, 12:00 `Europe/Brussels` on D-1 from 2020-11-01, under the id
`greek-dam-gate-closure-2026-09-10`; two regimes carrying one closure would have been a label
with no rule change behind it, so the coupling and 15-minute-MTU dates are recorded in the
regime's reference as events that did not move the gate. The id changed because the content did.

**No accepted observation changed.** The first GFS-usable delivery day is 2021-02-27, so no
admitted feature falls in the corrected period. Preflight run `34519415488` confirmed this rather
than assuming it: the accepted feature-set digest
`a718f46265678cf1e37c31fca439b9f2f03479901fe8f0ac126766431b99aefc` is identical to run
`34503999540`'s, as are all 2,002 complete days, 6,006 accepted variable-days, 122 named
exclusions and the complete-season classification. Only the schedule's own digest moved, to
`7f04024766a5169412c5e1c1ff773e92d7cd335455711d8d8246814f9cb2c4b0`.

This is the sixth defect of the class this project keeps finding: a correctly computed number
under a wrong label. The audit arithmetic was right; the rule it audited against was not the one
in force.

## The acceptance

`docs/fundamentals_acceptance_2026-09-10.md` records the verdict `accepted` for the registered
benchmark, naming the accepted feature-set digest, the identity of every declared input, the
availability-grade counts, the structured exclusions, the complete-season classification, the
custody outcome and what each retained primary source does and does not support. It carries seven
recorded limitations, including that the wind-weighted geography is applied to irradiance and
temperature because the fetch contract admits one common geography.

The verdict rests on data suitability alone. No benchmark had been run when it was written, and
no forecast, margin or cash flow had been computed from this feature set, so favourable
performance could not have been an acceptance criterion and was not one.

## What this does not establish

Not forecast skill, investment value, expected revenue, format stability, financial advice, a
bankable forecast or an investment-grade study. It permits one thing: dispatching `Benchmark
point-in-time fundamentals` against the accepted digest, whose result is to be committed whichever
way it goes.

## Validation

Ruff, mypy over 65 source files, the full test suite and a clean wheel build pass. New tests bind
the citation record to the declared document set and the acceptance document to the declarations
committed beside it, so a declaration changed without a new acceptance fails rather than leaving a
stale acceptance in force.
