# Implementation report — Stage 7 step 4: custody and acceptance preflight

**Date:** 10 September 2026
**Execution-plan stage:** 7, step 4 only. Step 5 is not started; the reason is stated at the end.

This report records aggregates only. No feature value, price or interval-level record appears in
it or in any committed file it names. It accepts nothing, evaluates no model skill and is not
investment evidence.

## Where step 3 left the evidence

Retrieval run `34476720910` retrieved all 23 slices of the declared window as private
`fundamentals-shard-*` artifacts, and stopped before combination on the shard-glob defect fixed
since. Step 3's combination and timing audit were reproduced from those slices outside Actions, so
the combined table that custody, the preflight and the benchmark read did not exist as a workflow
artifact. Re-retrieving the window would not have reproduced the slices: a re-retrieval carries new
receipt times, and the archive may have moved.

`Fetch point-in-time fundamentals` therefore gained `shards_from_run_id`. When set, retrieval is
skipped and the combine job reads the named run's slice artifacts under the unchanged slice-count
guard and official reconciliation. Run `34503398871` was dispatched that way with the same window
and slice size as the retrieval run, `fail_on_finding=false` so that the four known availability
findings would be recorded rather than fail the run, and combined the 23 slices into the private
`point-in-time-fundamentals` artifact (ID `10162918335`, 35,864,973 bytes archived, published
digest `3d988aba…dbe74b`, expires 9 December 2026). Its summary states that nothing was retrieved
by that run.

The combination reproduces step 3's reconciliation exactly: 2,005 built delivery days, 144,357
feature rows and 200,496 traced source documents; one delivery day excluded by name
(`sidecar_object_mismatch`, 2022-12-01); and for each of the three variables 2,002 of 2,006 days
provider-declared before cutoff, with a minimum declared lead of 196.2 minutes.

## Custody

| Run | Workflow | Outcome |
| --- | --- | --- |
| `34504032804` | Record official artifact custody | History verified against its committed record; feature table recorded |
| `34504409514` | Record official artifact custody (push) | Both committed records verified: zero differences each |
| `34504908065` | Publish encrypted custody copies | Both artifacts verified, encrypted to the operator's recipient `age1ma3l0fx…`, attached to release `custody-2026-09-10` |

`docs/custody/accepted-fundamentals-feature-table.json` is committed as run `34504032804` emitted
it: seven files, 360,769,797 bytes, source workflow `Fetch point-in-time fundamentals`, published
archive digest recorded as provenance. Its `content` section is empty by construction, because no
file in the artifact is a canonical price history; the record is per-file byte digests, which is
the right instrument for a stored copy.

Three corrections were needed to run the procedure as written, and none changes what a record
compares:

- the feature-table custody step in the record, publish and benchmark workflows named the
  benchmark as the artifact's source workflow; the benchmark consumes the artifact and the fetch
  workflow produces it, so the label now names the producer;
- the record and publish workflows defaulted the reconciliation run to `33073631530`, whose
  artifact expired on 3 September 2026 and cannot be regenerated while `ENTSOE_SECURITY_TOKEN`
  is unset, so every push touching a custody record and the first publish dispatch
  (`34504573673`) failed at a download before verifying anything; the defaults are empty and
  the inputs say why. That record stays verifiable against the decrypted release copy by the
  documented drill;
- the record workflow prints each generated record in its log, since a record holds digests and
  counts and no official value, and the artifact cannot be fetched from every environment that
  has to review it.

The encrypted copies are ciphertext; their digests authenticate the stored copy and say nothing
about its contents. What the copy contains is guaranteed by the verification that ran before
encryption. The operator still owes the second copy under separate control and the decryption
drill against the recovered plaintext, as for the earlier copies.

## Acceptance preflight — run `34503999540`

The preflight read the accepted price history (run `33483975614`) and the combined feature table
(run `34503398871`), verified both through the established custody step, and emitted only
aggregates. It accepted nothing, computed no benchmark and produced no figure.

### Identity

| Input | SHA-256 |
| --- | --- |
| Accepted feature set (revision-aware join, admitted grades `witnessed` and `provider_declared`) | `a718f46265678cf1e37c31fca439b9f2f03479901fe8f0ac126766431b99aefc` |
| Decision-cutoff schedule `config/decision_cutoff.json` (`greek-dam-gate-closure-2026-09-03`, lead 0 min) | `6382f112c39115c70c799014d134f16e3e97985ba62652bcc65082749e763aa6` |
| Sampling geography `config/fundamentals_geography.json` (`greek-wind-capacity-regions-2023-12-31`) | `9bd6741b70a2ad594d2c6490c75df087f4be247fca2ea073181be833a207d84f` |

### Availability against the declared cutoff

- Window `2021-02-27` to `2026-08-25`: 2,006 delivery days audited, 144,357 observations.
- Evidence basis `provider_declared_publication_instants`; witnessed variable-days: 0. This is a
  historic retrieval and creates no witnessed evidence.
- Accepted variable-days 6,006 (3 × 2,002); quarantined observations 0; findings 12 (4 days × 3
  variables); availability accepted: false, on those four days.

| Variable | Days | Accepted | Witnessed | Late | Min lead (min) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dswrf_surface` | 2,006 | 2,002 | 0 | 3 | 196.2 |
| `temperature_2m` | 2,006 | 2,002 | 0 | 3 | 196.2 |
| `wind_speed_10m` | 2,006 | 2,002 | 0 | 3 | 196.2 |

The three late days are 2021-03-23, 2021-06-15 and 2022-01-18 (`incomplete_before_cutoff`); the
one absent day is 2022-12-01 (`no_publication`; the retrieval excluded it by the named cause
`sidecar_object_mismatch`). Nothing is filled or imputed.

### Join and exclusions

- Delivery days in the join: 2,124, the accepted price history from 2020-11-01.
- Complete days: 2,002. Excluded days: 122 = the 118 accepted delivery days before the first
  GFS-usable day, 27 February 2021, which carry no feature by declaration, plus the four days
  above.

### Complete-season classification

Season DJF 2025-26, 90 days; days not common: 0. **Exploratory: false** under the pre-registered
rule "exploratory unless every day of one complete meteorological season is common"
(`docs/fundamentals_declarations_2026-09-03.md`, section 5). This is a coverage classification
decided before any result exists. It says nothing about skill, and it is not an acceptance.

## Step 5 is not started, and why

The dated acceptance document must name primary-source support that the repository tooling
cannot verify and that this session was not supplied:

1. the HWEA/ELETAEN wind-capacity statistics at 31 December 2023 behind the geography weights;
2. the HEnEx isolated-market rulebook text for the regime before delivery day 2020-12-16;
3. the SDAC operating procedure and effective-date notices for the regime from 2020-12-16.

Both declarations state that those documents must be retained with the acceptance evidence. No
acceptance document is committed, so `Benchmark point-in-time fundamentals` still refuses, which
is the intended state. Everything else the document must state is recorded above, and the
document must also carry the recorded limitation that the wind-weighted geography is applied to
irradiance and temperature as well, because the fetch contract admits one common geography.

## What this does and does not establish

Custody proves that a copy is this artifact. The preflight establishes coverage and identity. No
feature value is accepted, no forecast skill is measured, no revenue is estimated, and nothing
here is financial advice, a bankable forecast or an investment-grade study.

## Validation

Ruff, mypy over 65 source files, 696 passing tests and a clean wheel build on the final head.
Three tests cover the combine-from-run mode and the producer label.
