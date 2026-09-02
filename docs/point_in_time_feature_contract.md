# Point-in-time feature contract

**Status:** the executable policy behind v0.9.1 ingestion and the v0.9.2 join, landed 2 September 2026. It states Sections 4
and 5 of `docs/v0.9_design.md` in the form the code enforces, and it is the document to read
before adding a feature source, a variable or a grade. The design remains the design of record;
where this document is more specific, it is because implementation settled something the design
left open, and each such point is marked.

**What this contract is not.** It is not a data-acceptance document. Nothing in v0.9.1 accepts a
value, a unit or a source for forecasting. Section 7 of the design governs acceptance, it
requires a dated document, and it comes at v0.9.5. A feature table that passes everything here is
still an unaccepted table.

---

## 1. The two declarations, and what happens without them

| Declaration | Format | Read by | Without it |
|---|---|---|---|
| Decision-cutoff schedule | `config/decision_cutoff.example.json` — dated regimes, each with `closure_day_offset`, `closure_local_time`, `closure_timezone` and a required rulebook `reference` | `read_decision_cutoff_schedule` | No availability audit runs. There is no constant, no environment variable and no "SDAC default" |
| Decision lead, in minutes | one non-negative integer; `config/decision_lead_minutes.example.txt` explains the format and deliberately holds no number | `validate_decision_lead_minutes` | Same. Zero is a declaration and is accepted; absence is not |
| Sampling geography | `config/fundamentals_geography.example.json` — named points, weights summing to one, and a stated basis | `read_sampling_geography` | No gridded feature is built |

All three readers **refuse the committed example by name**: an example whose identifier is
`example-not-a-declaration`, or whose reference still carries `REPLACE BEFORE USE.`, stops the
run. This is gate G3 of the design made executable, and it is why
`tests/test_config_examples.py` keeps the examples both parseable and recognisable.

The effective cutoff for delivery day `D` is

```
cutoff_utc(D) = closure_utc(D) - decision_lead_minutes
available_for(D) := published_at_utc < cutoff_utc(D)          (strict; a tie is late)
```

A closure that falls in a daylight-saving gap or repetition is refused rather than guessed, and a
delivery day earlier than the first declared regime is refused rather than judged against a rule
that was not in force.

---

## 2. The table: one row per value, carrying how it was available

`greek_bess.data.point_in_time` defines the closed column set, the closed source set, the closed
variable registry with its units, and the four evidence grades. The columns are Section 5.1 of
the design. Four rules govern what may be in them.

**A missing value is an absent row, never `NaN`.** Coverage is counted, never filled. Nothing is
forward-filled, interpolated or imputed, and a coarser feature is not broadcast into a finer
column at storage time.

**Every revision is stored and none is selected.** The table holds each publication of a datum,
including revisions published after any cutoff, so that "this revision was superseded" stays
visible evidence. Selecting the decision-time revision is the join's job at v0.9.2.

**A unit that is not the registry's unit is refused.** There is no silent conversion. The
variable registry is closed for the same reason: a realized target-day quantity cannot enter
under a new name, because a name that is not registered is not a feature.

**Two rows that share the uniqueness key and disagree are refused, naming both.** Identical
duplicates are one observation. The uniqueness key is
(`source`, `dataset`, `variable`, `area`, `delivery_start_utc`, `source_document_id`,
`source_revision`).

*Settled in implementation:* `source_revision` is normalized to a nullable **string**. A revision
is an identity, not a quantity; storing it as a number would make an absent revision read back
from CSV as `NaN` rather than as absent. Ordering by it is therefore lexicographic, which only
ever acts as a tie-break — the decision-time revision is selected by publication instant first.

---

## 3. Evidence grades, and the one direction they may move

| Grade | What it means | Admitted? |
|---|---|---|
| `witnessed` | this project retrieved the datum before the cutoff, and it was published before the cutoff | yes |
| `provider_declared` | a provider instant attached to the datum places it before the cutoff; the retrieval came later | yes, reported separately and never merged with `witnessed` |
| `assumed` | availability inferred from a rule not attached to the datum — a regulatory deadline, a model cycle plus a nominal latency | **no.** Quarantined; usable only in a labelled exploratory run |
| `unavailable` | published at or after the cutoff, or no publication instant | no; the feature is absent for that day |

*Settled in implementation:* the **stored** grade records what the retrieval established about the
publication instant; the **effective** grade is derived per delivery day by
`effective_evidence_grade`, because `witnessed` is defined by the row's own two instants against
a cutoff, and the retrieval does not know the cutoff. The derivation may lower a grade and may
raise `provider_declared` to `witnessed` when the row's own retrieval instant earns it — but a
row stored as `assumed` stays `assumed` whatever its timestamps say. What is weak about an
assumed row is that the instant was inferred, not that the arithmetic came out badly.

The source spike supplies the concrete case that justifies the quarantine: on 14 June 2021 the
00 UTC cycle's step-48 object appeared 1 h 39 m after the illustrative cutoff. A nominal-latency
assumption of "about four hours" would have admitted that day and been wrong.

---

## 4. Availability is established per delivery interval, never per day

`greek_bess.data.availability_audit` checks every delivery interval of every audited day on its
own evidence. This is not caution; it is a measured property of the chosen source. On 1 August
2026 the 06 UTC cycle's `f024` object appeared at 09:53:54 UTC and its `f048` object at
09:46:04 UTC — the later step first. Upload order is not monotone in forecast step, so one
step's availability says nothing about another's.

Day statuses, and what each one means:

| Status | Meaning | Acceptable? |
|---|---|---|
| `witnessed_before_cutoff` | every interval covered, every covering value witnessed | yes |
| `provider_declared_before_cutoff` | every interval covered, at least one on a provider instant alone | yes |
| `incomplete_before_cutoff` | some intervals covered in time, some not | no |
| `all_publications_after_cutoff` | rows exist, none published before the cutoff | no |
| `grade_not_admitted` | rows published in time, none of an admitted grade | no |
| `no_publication` | no rows at all for that variable and day | no |
| `assumed_grade_admitted_exploratory` | covered only because the exploratory flag admitted the quarantined grade | no, by construction |

The expected interval count comes from the market day's own length, so a 23-hour and a 25-hour
day answer for themselves. A resolution that does not tile the day exactly is refused rather
than rounded.

`audit-feature-availability` exits **2** when any audited day is not accepted, and writes its
evidence anyway. Exit 2 is a recorded finding, not a crash.

---

## 5. What the chosen source contributes, and what it cannot

The one admitted source is NOAA GFS 0.25° forecast vintages, 00 UTC cycle of D-1
(`docs/fundamentals_source_assessment_2026-09-02.md`, decision entry 2026-09-02). Three feature
variables: `dswrf_surface` (W/m2), `temperature_2m` (K) and `wind_speed_10m` (m/s), the last
derived from the two 10 m components because the component signs are a coordinate convention and
the speed is the physical quantity.

Five source facts are enforced rather than documented:

1. **The cycle is 00 UTC of D-1 and nothing else.** The 06 UTC cycle was observed publishing
   after a midday cutoff. A missing 00 UTC object makes the day incomplete and it is excluded by
   name; an earlier cycle is not substituted, because a fallback-cycle rule would be a decision
   with its own evidence and there is none.
2. **Both archive key layouts are tried.** The product moved under an `atmos/` segment on
   23 March 2021. A client that hard-codes the current layout returns *nothing* for the earliest
   usable days — silently, as an empty result rather than an error.
3. **The hourly record starts at delivery day 27 February 2021.** Before 26 February 2021 the
   product is 3-hourly. Earlier days carry no feature and are excluded by named cause; a 3-hour
   mean is not broadcast into an hourly column, because that would make one column mean different
   things on different dates.
4. **Radiation is de-averaged from two adjacent steps.** For a step `f` whose bucket began at
   `b = 6·⌊(f-1)/6⌋`, the message holds the mean over `[b, f]`, and the hourly mean over
   `(f-1, f]` is `A_f·(f-b) − A_(f-1)·(f-1-b)`, reducing to `A_f` at the first step of a bucket.
   A missing predecessor is named, never assumed zero.
5. **A declared sampling point must land on a grid node.** A point between nodes would have to be
   interpolated, and no interpolation rule is declared, so the refusal names the nearest node and
   the operator adjusts the declaration deliberately. The points are resolved to flat grid
   indices once, from the first decoded message's own grid header, and every later message is
   checked against that grid: a step published on a different grid would otherwise be sampled at
   the right index of the wrong array, which is the one failure mode here that produces
   plausible-looking numbers.

*Corrected in implementation:* the source assessment computed the required forecast steps as
**21–46** from the *Athens* delivery day. This project's delivery day is the **CET/CEST market
day** (`MARKET_TZ`, the same day the canonical price schema uses), which begins an hour later, so
the range actually needed is **22–47**. The client derives the step set from each market day
rather than carrying a constant, so a 23- or 25-hour day produces its own set and no written-down
number can drift from the calendar. A test asserts the derived range across the whole usable
record.

**A derived value's provenance is the union of its inputs.** Wind speed comes from two messages
and a de-averaged radiation hour from two step objects, so for such a value:
`published_at_utc` is the **latest** contributing object's publication instant — the value became
available when its last input did; `source_document_id` names every contributing object and
message; and `raw_sha256` is taken over the contributing message digests in a stated order, with
each contributing message listed separately in the retrieval manifest.

---

## 6. What passing this contract does not establish

- that any audited value is correct, or that its unit is as declared;
- that any audited variable carries forecasting skill;
- that a delivery day absent from the audited table was never published for;
- that the declared cutoff matches the market rule the operator cited.

The audit summary carries these four statements in its own output, alongside
`establishes_only_availability: true` and `quarantine_lifted: false`, so the limits travel with
the evidence rather than living only here.


## 7. Decision-time revision selection and join audit

`join_point_in_time_features` validates canonical complete price days and this feature schema, resolves the supplied schedule and lead for each day, and selects the latest revision published strictly before the effective cutoff. Revision and document identifiers break publication-time ties deterministically; rows at or after the cutoff are counted and excluded. Each price interval maps by containment of its UTC start in the selected feature interval. Coarser broadcasts are labelled, finer features require a separately declared aggregation rule, and incomplete coverage excludes the whole day with a named cause.

Every emitted value has exactly one audit row carrying its source document, revision, raw-byte digest, publication/retrieval/issue instants, effective grade, cutoff margin and resolution relation. No price appears in that audit. No missing value is filled. Passing this join establishes only point-in-time selection and traceability, not feature acceptance or forecasting skill.
