# Changelog

All notable project changes are documented here.

## [Unreleased]

### Added

- **The point-in-time feature table is accepted, and the primary text the declarations rest on is
  retained.** `docs/fundamentals_acceptance_2026-09-10.md` records the verdict `accepted` for the
  table combined by run `34503398871`, naming the accepted feature set
  `a718f462…99aefc`, every declared input by digest, 2,002 complete delivery days and 122 excluded
  by name out of 2,124 joined, 6,006 accepted variable-days with none witnessed and none
  quarantined, the custody outcome and seven recorded limitations. The verdict is data
  suitability: no benchmark had been run when it was written, and no forecast, margin or cash flow
  had been computed from this feature set.

  Both operator declarations require their primary publications to be retained with the acceptance
  evidence. `Retain primary sources` is a manual, declaration-driven workflow that downloads the
  documents named in `config/primary_sources.json`, records byte size and SHA-256, prints the
  passages that bear on a declaration for review, and attaches the files to a private release —
  **never overwriting a retained copy**, since a differing digest is a finding. Nine documents are
  retained on release `primary-sources-2026-09-10` and cited with digests and quoted passages in
  `docs/primary_sources/README.md`. The guard fired in earnest: one retrieval of the HWEA
  statistics returned a 12 KB non-PDF response, nothing was overwritten, and the next retrieval
  matched the retained digest.

### Fixed

- **The declared pre-coupling gate closure was an hour early, and the retained primary text is
  what showed it.** The 3 September 2026 declaration set the Greek day-ahead closure at 12:00
  `Europe/Athens` on D-1 for delivery days before 2020-12-16, called that its weakest element, and
  required correction before any test run if the primary text disagreed. HEnEx Decision 10 of
  20 October 2020 — the timeline in force at the 1 November 2020 launch, and the only version
  before September 2021 in the HEnEx library — tabulates the Day-Ahead Market Gate Closure Time at
  12:00 (CET) / 13:00 (EET) on D-1, as do its 2021 and 2026 successors. The schedule now declares
  one regime from 2020-11-01 at 12:00 `Europe/Brussels` under the id
  `greek-dam-gate-closure-2026-09-10`; the coupling and 15-minute-MTU dates are recorded in its
  reference as events that did not move the gate. Preflight run `34519415488` confirmed rather
  than assumed that no accepted observation changes: the accepted feature-set digest and every
  count are identical to the run before the correction, because no admitted feature predates
  2021-02-27. No benchmark had been run, so this corrects a declaration and revises no result.

- **Retrieved fundamentals slices can be recombined without being re-retrieved.**
  `Fetch point-in-time fundamentals` gains an optional `shards_from_run_id`: retrieval is skipped
  and the combine job reads the named earlier run's slice artifacts under the same slice-count
  guard and official reconciliation. A failed or cancelled retrieval still stops the combination.
  Run `34503398871` combined the 23 slices run `34476720910` retrieved into the private
  `point-in-time-fundamentals` artifact; the run summary states that nothing was retrieved.

- **Custody of the combined fundamentals feature table is recorded and verified.**
  `docs/custody/accepted-fundamentals-feature-table.json` fingerprints the seven files of that
  artifact as the tooling emitted the record (run `34504032804`); the push-triggered verification
  (run `34504409514`) reports zero differences for both the price history and the feature table.
  The custody workflow prints each generated record in its log so a record can be reviewed where
  the artifact cannot be fetched, and its feature-table defaults follow the committed record.
  Custody accepts no feature value.

- **A design of record for the integrated study runner.** The repository can already plan a day on
  a causal forecast and settle it at realized prices, evolve a cohort degradation state across
  days, and turn a daily operating path into dated cash flows — but not together. Answering
  whether a better forecast pays for itself once the battery ages under the throughput that
  forecast causes currently means running three commands and joining their outputs by hand, and no
  contract governs that join. `docs/integrated_study_design.md` specifies one study configuration
  and the contracts between the modules it drives: what each strategy may read at its declared
  decision time; that each strategy owns a private degradation state advanced only by its own
  settled throughput; that a declared window's gaps are refused rather than bridged and finance
  uses exactly that horizon; that physical fade and the monetary dispatch adder stay distinct and
  are not double-counted; and that no single perfect-foresight ceiling is asserted across
  strategies once their states diverge. It records the result kind and basis the study will use,
  the artifacts it will write, and what would make the design wrong. Tests keep its [Verified]
  claims checkable against the code. The design adds no source code, accepts no dataset, produces
  no figure and authorizes no official-data run; the implementation unit follows adoption.

- **A matched-training control for the fundamentals ablation.** The declared ablation compared a
  price-only control trained on every day against a weather challenger trained only on days whose
  weather features are complete, so the two arms differed in the feature columns *and* the
  training rows and any difference confounded weather value with lost training coverage. A third
  arm now trains on exactly the challenger's eligible rows with the baseline's columns, and the
  original full-history arm is retained under its own name. `challenger − matched_control` is
  attributable to the weather columns; `matched_control − full_history_baseline` to training
  coverage; the challenger-minus-baseline difference confounds the two and is not reported as a
  weather effect. The prospective amendment fixing this structure was recorded before the
  implementation and before any comparison outcome exists
  (`docs/fundamentals_matched_control_amendment_2026-09-10.md`).

  The match is enforced rather than asserted: every refit records a digest of its training row
  identities and of its training targets, computed independently of the feature columns read, and
  the benchmark refuses a run unless each matched pair agrees on both at every refit. The dispatch
  comparison now pairs a challenger with its matched control rather than the full-history
  baseline, so the confound cannot be carried into euro. No retrieval, acceptance or benchmark
  workflow was launched and no outcome was produced.

### Fixed

- **The feature-table custody record named the wrong producer, and the custody workflow's
  reconciliation default named an expired artifact.** The record, publish and benchmark
  workflows labelled the feature table's source workflow as the benchmark that consumes it; every
  feature-table custody step now names `Fetch point-in-time fundamentals`. The reconciliation
  artifact of run `33073631530` expired on 3 September 2026 and cannot be regenerated while
  `ENTSOE_SECURITY_TOKEN` is unset, so a default pointing at it made every push that touched a
  custody record fail on a download rather than a verification; the default is empty, the input
  says why, and the committed reconciliation record remains verifiable against the decrypted
  release copy by the documented drill.

- **Official feature-table reconciliation now accepts equal intervals across pandas duration
  storage units and discovers only numbered shard tables.** The first corrected full-window
  retrieval exposed two representation defects before acceptance: the workflow glob counted each
  `features_N.coverage.csv` sidecar as another shard, and interval validation used dtype-sensitive
  `Series.equals`, rejecting equal 60-minute durations stored at different pandas resolutions.
  Shard discovery now selects only `features_<integer>.csv`, and interval validation compares
  duration values. Unequal and non-positive intervals remain refused.

- **The degraded dispatch aggregate was labelled an upper bound and is not one.** Each market
  day is solved optimally under the limits it begins with, so every day is a perfect-foresight
  ceiling for that day — but those limits depend on what earlier days discharged, so the total
  is the outcome of one myopic policy rather than a ceiling over all policies. With one warranted
  equivalent full cycle and two days whose spreads are EUR 1 and EUR 100 per MWh, the daily
  policy spends the cycle on the first day and earns EUR 1; a feasible policy that waits earns
  EUR 100. The result now reports on a new `historical_replay_simulation` basis, its label states
  that it is not a lifetime optimum or an upper bound, and it carries a `result_basis_note`
  saying why. Finance gains a `daily_policy_degraded_simulation` operating-margin case so a
  degraded path fed into it cannot inherit the upper-bound wording. Perfect-foresight dispatch
  over a fixed battery is unchanged and keeps its genuine upper-bound basis. The daily policy is
  retained and no lifetime optimizer is introduced.

  A manifest stored under the superseded basis is refused with a message naming what changed and
  telling the operator to re-run, never silently relabelled: the same number means something
  different under the two bases. No accepted record, custody document or committed report carries
  this kind, so nothing in the acceptance record changes. `docs/sample_report.html` is
  regenerated because the report now lists the new basis among those it does not represent.

- **NPV and IRR described different cash-flow timings.** NPV discounted the daily table, in which
  each delivery day's cash flow carries its own date; IRR solved on the annual table, which sums
  a project year's flows and dates the total at that year's final day. The two metrics therefore
  answered about different projects. For EUR 1,000 paid initially and EUR 1,200 received evenly
  across 365 daily periods, the dated series gives 45.586% and the annual relocation 20.015%: the
  annual figure understates the return by treating money received in January as if it arrived in
  December. The summary already declared the intended convention, so IRR was the metric not
  honouring it. Both metrics now read one dated series built from the same
  `years_from_project_start` NPV discounts by. The annual table is unchanged and remains a
  summary; no monetary metric is derived from it.

  Moving the ambiguity checks onto that series needed more than moving the existing test, since
  counting sign changes over daily flows refuses a project that merely pays for a mid-life
  augmentation. Uniqueness is now settled by the sign rule, then Norstrom's cumulative-balance
  criterion, then a scan of the search range that answers from the root structure actually
  present. The repository's existing ambiguity fixture was confirmed to have two roots and is
  still refused; the synthetic demonstration, which never recovers its capex, has exactly one and
  is still reported. `not_evaluable_multiple_sign_changes` is renamed
  `not_evaluable_multiple_rates` to describe what is actually checked.

  **Every previously reported IRR is superseded.** The committed synthetic demonstration moves
  from `-0.9798843527086536` to `-0.9800653165183428` and `docs/sample_report.html` is
  regenerated. No accepted official result carries an IRR, so the acceptance record is unchanged.
  NPV, payback, break-even outputs, cash-flow totals, fees and augmentation costs are unchanged.

- **Shard combination checked declarations, not contents.** `combine_feature_shards` verified
  that shards shared one retrieval identity and that their *declared* windows tiled without
  overlap or gap, then concatenated. Nothing checked those declarations against what the shards
  held, so a shard whose table lost a delivery day still declared its original window, still
  listed the day among those it built, and still reported zero exclusions — and the combined
  summary repeated all three claims, counting a day the table did not contain. Downstream that
  is indistinguishable from a delivery day the provider never published, the one distinction
  this project records by name and never infers. Every shard is now reconciled before
  concatenation: days claimed but not held, days held but not claimed, rows outside the declared
  window, a day recorded as both built and excluded, and a day short of one row per variable per
  delivery interval are each refused, with the interval count taken from the market day itself
  rather than assumed to be 24. The built-day count is now the reconciled one. The declared
  window's partition is checked by count arithmetic rather than as a set, because the exclusion
  list is capped and a shard that hit its cap lists fewer days than it excluded. A new
  `--official` mode on `combine-feature-tables`, set in the retrieval workflow, additionally
  requires every shard to carry a retrieval manifest, refuses two records naming one document
  with different digests, and refuses a manifest shorter than the document count its shard
  reports. No official-data workflow was launched by this change.

- **Point-in-time feature observation times were run-start times.** A feature row's
  `retrieved_at_utc` recorded the instant its retrieval *run* began, stamped identically onto
  every row the run produced. The availability audit grades a row `witnessed` when that instant
  falls strictly before the delivery day's declared decision cutoff, so a run that started
  before a cutoff and kept receiving messages after it recorded every late value as observed in
  time. `witnessed` is the one grade that cannot be reconstructed afterwards, so nothing
  downstream could have detected this. The receipt instant is now read per message, immediately
  after that message's transfer succeeds and never before its request, and a derived feature row
  inherits the latest receipt among its contributing messages — a wind speed is not observed
  until both components have arrived. Provider publication time remains a separate field and is
  unchanged. Run start is still recorded, as a property of the run: summaries now carry
  `run_started_at_utc`, `first_message_received_at_utc` and `last_message_received_at_utc` as
  three distinct instants. `GFS_OBSERVATION_SEMANTICS_VERSION` is 2 and joins the shard identity
  fields, so tables carrying run-start stamps are refused rather than combined with corrected
  ones. Shard recombination now requires and carries those receipt fields instead of the removed
  `retrieved_at_utc`, and its own combination instant is named `combined_at_utc`. The seven
  existing successful witness runs were reviewed against the declared cutoff and needed no
  reclassification: each completed by 06:24 UTC against a 10:00 UTC cutoff. No official-data
  workflow was launched by this change.

- **GFS decoded-message and feature-value semantics.** Every selected GRIB2 message must now
  agree with its sidecar and request on parameter identity, units, level, source cycle, valid
  time, forecast window, step units and instant/average semantics. Wind speed is calculated at
  each declared grid point before the declared geographic weights are applied; this prevents
  opposite signed components at different locations from cancelling before magnitude is taken.
  Radiation is de-averaged at each point before weighting. Retrieval summaries now carry the
  complete geography, decoded-message contract and feature-semantics version. Any GFS feature
  table produced by the earlier implementation must be rebuilt and receive a new acceptance
  identity before use. No official-data workflow was launched by this change.

- **Cross-platform deterministic demo manifests.** Run-manifest JSON now forces LF newlines
  instead of accepting the host platform's text translation, and the committed byte-checked
  sample report is pinned to LF through `.gitattributes`. Windows therefore records the same
  manifest digests and regenerates the same synthetic demonstration report as other supported
  platforms. No analytical value, result label or project assumption changes.

- **v0.9.7: absence, transport failure and a source condition were one event.** The first
  dispatch of the declared window (run `33843070945`, 23 slices of 90 delivery days) failed:
  six slices died on the first attempt and four on the second, so `combine` never ran and the
  window produced nothing. Every one of those deaths was one of three defects, and they compound
  in a specific order.

  *Absence and transport failure were indistinguishable.* `head_https_headers` and
  `fetch_https_bytes` collapsed HTTP 404, HTTP 5xx and connection or TLS failures into one
  untyped `OfficialDataDownloadError` with no status preserved, and `_locate_object` in the NOAA
  GFS client caught every one of them and tried the next archive key layout. When both layouts
  had been tried it raised "No 0.25° object … both archive key layouts were tried" — a statement
  that the provider published nothing, reached from evidence that could equally have been a
  transient 503. Slice 20 died with exactly that message for delivery day 2026-04-18, and
  nothing in the retrieval says which it was. Every failure now carries a **kind** — `absent`,
  `client_error`, `server_error`, `transport`, `unsafe_request`, `unusable_response` — and the
  HTTP status when the server answered one. `head_step_object` treats only `absent` as "not at
  this key"; anything else stops the retrieval by name, because an unanswered request is not
  evidence about what the provider published. `IncompleteRead` is classified rather than escaping
  as a raw `http.client` traceback, which is how slice 11 died.

  *There were no retries.* The declared window is roughly 200,000 HTTPS requests issued with no
  retry at all, so one reset discarded a 90-day slice — slice 4 died on a single
  `Connection reset by peer`. Transport faults and 5xx answers are now retried up to five
  attempts with 1, 2, 4 and 8 second backoff. A 404 is never retried, because absence is an
  answer and re-asking cannot change it, and neither is the `.idx` sidecar mismatch or any other
  deterministic refusal. The retrieval stays sequential: making it concurrent would change how an
  accepted evidence path talks to the provider, which is a change to the evidence.

  *A source condition aborted the window instead of excluding one day.* The refusals for a
  genuinely missing object and for an `.idx` sidecar that indexes a different publication both
  promised the delivery day "is excluded by name", but the exception propagated out of
  `run_fetch_fundamentals` and killed the whole slice; only `day < FIRST_HOURLY_DELIVERY_DAY` was
  ever recorded as an exclusion. `fetch-fundamentals` now catches the two named source conditions
  — `missing_object` and `sidecar_object_mismatch`, carried as a typed `cause` on `NoaaGfsError`
  — records the day in the retrieval summary's `excluded_days_by_cause`, and continues. Every
  other refusal still stops the retrieval: a grid change, an undecodable message, a non-finite
  sample or an unanswered request is a statement about how a value would be built, and recording
  one as a provider non-publication would put a false finding into a pre-registered benchmark
  window that nothing downstream could detect. **This third fix does not ship without the first**:
  without typed absence, a network blip would permanently exclude a real delivery day and record
  it as a non-publication.

  The retrieval and combined summaries now also carry `excluded_day_count_by_cause`, and the
  combined count is summed from each slice's own total rather than recounted from its capped
  day-by-day list, so an exclusion can never be invisible in the aggregate.

- **A persistent source inconsistency, recorded rather than worked around.** Slice 7
  (`2022-11-19..2023-02-16`) reproduced the `.idx` sidecar mismatch identically on both attempts.
  That is a property of the archive, not a race, and it is now excluded by name for the delivery
  day it affects rather than treated as a retrieval failure.

### Added

- **v0.9.6: the declared window becomes retrievable.** The first dispatch of
  `Fetch point-in-time fundamentals` (run `33760441164`) measured what the surface costs:
  **72.1 seconds per delivery day**, and 83 MB per delivery day of GRIB2 messages when
  `--raw-dir` retains them. Against the pre-registered 2,006-day window that is **40.2 hours**
  of retrieval against a six-hour per-job ceiling, and **163 GB** against roughly 14 GB of
  runner disk — two hard failures that only a dispatched run could reveal, because the surface
  had only ever been exercised on synthetic fixtures. The window is pre-registered and is not
  shortened to fit a runner. Instead the workflow stops retaining raw messages, which the
  retrieval manifest already identifies by digest and byte count, and tiles the window into
  slices retrieved in parallel and recombined — 23 slices of about 1 h 50 m at 90 days each.
  The retrieval client is untouched: making it concurrent would change how an evidence path
  talks to the provider. Add `combine-feature-tables` and `data/feature_shards.py`, which hold
  the invariant that makes the recombination checkable rather than assumed — the slices must
  **tile** the window, covering every delivery day exactly once. An overlap is refused rather
  than deduplicated, because two retrievals of one day are two revisions of one observation and
  choosing between them is the point-in-time join's decision under a declared cutoff; a gap is
  refused by name; and slices disagreeing on source, variable set or declared geography are
  refused by naming the fields that differ. The combined summary records every slice and its own
  retrieval instant and the combined manifest carries every document from every slice, so any
  one slice can be re-retrieved alone.

### Fixed

- **A digest that depended on how many times a table had been copied.** The point-in-time
  feature table is written exactly but was read back with pandas' default float parser, which is
  accurate only to within one unit in the last place. The observed relative difference was 2e-16
  — far below anything meteorological or monetary this project reports — but the feature set is
  identified downstream by a SHA-256 over its own values, and a digest has no tolerance, so a
  table written, read and written again digested differently from the one the retrieval
  produced. Both readers that feed a digested frame now parse with round-trip precision. No
  analytical result changes; one digest computation becomes stable that was not.

- **v0.9.5 record corrections.** No source, test, workflow or configuration behaviour changed.
  The v0.9.5 merge had appended its documentation below the closing sections of `STATUS.md`,
  `CHANGELOG.md`, `README.md` and `PLAN.md` rather than into the structures those files already
  had, so each is put back in order: the status section returns to reverse-chronological position,
  this changelog entry returns to the `[Unreleased]` bullet style every version above 0.7.2 uses,
  the README section is folded into the v0.9 narrative, and `PLAN.md` stops tracking v0.9.5 in two
  contradictory places. Four statements are corrected against the repository: `STATUS.md` still
  declared version `0.9.4`; the README still said the three v0.9 declarations do not exist and
  that nothing can be retrieved until they do; `PLAN.md` still listed those declarations under
  "waiting on an operator declaration"; and the README's "full list" of project records stopped at
  v0.8.2, omitting eighteen committed records including both design documents and every v0.9
  implementation report. Two facts no document carried are now recorded: `Fetch point-in-time
  fundamentals` has never been dispatched, so the v0.9 chain is complete in code and empty of
  evidence for a reason that is no longer the missing declarations; and the first scheduled
  `witness-fundamentals` run stopped at its guard two hours before those declarations merged,
  losing delivery day 4 September 2026 from the witnessed subset permanently
  (`docs/history/implementation_report_record_corrections_2026-09-03.md`)

- **v0.9.5: the official-run machinery, and the declarations that unblock it.** Add the manually
  dispatched `Benchmark point-in-time fundamentals` workflow, which runs the fixed order the v0.9
  design requires and refuses anything out of it: it guards every pre-registered declaration by
  value, verifies custody of both accepted inputs, audits availability and builds the
  point-in-time join before any benchmark, checks the accepted feature-set digest, applies the
  declared hourly-to-quarter-hour split and the complete-season exploratory rule, runs the
  forecast ablation and the settled dispatch comparison, records, verifies and renders their
  manifests, and uploads the evidence privately; its step summary carries an artifact index and
  interpretation labels and no figure. `reporting/contract.py` refuses both fundamentals
  benchmark kinds, on record and on read, unless the declared inputs name the same 64-character
  accepted feature-set digest as the producer summary, so a benchmark cannot be presented whose
  feature table no acceptance document identified. `record-artifact-custody` and
  `publish-encrypted-custody` take an optional accepted-feature-table run ID through the
  established record, verify and encryption paths rather than a second mechanism; no
  second-copy-under-separate-control rule was added, because that placement remains outside this
  repository's knowledge. `docs/templates/` adds reusable acceptance and benchmark document
  structures that enumerate the required aggregate findings without interval-level official data.
  A clearly synthetic fundamentals dispatch manifest is rendered through the existing generic
  path, so no bespoke ablation layout is introduced and the renderer still computes nothing.
  Validated on synthetic fixtures only: this milestone creates no official feature table, price
  interval, workflow run ID, acceptance finding, benchmark value or custody outcome. The three
  operator declarations were then committed on 3 September 2026 — the two-regime cutoff, the
  zero-minute lead and the wind-capacity sampling geography — which lifts the refusal that had
  blocked v0.9.1 through v0.9.4 and makes every v0.9 surface runnable for the first time. Nothing
  has yet been run through them, so the v0.9 chain is complete in code and empty of evidence

- **v0.9.4: the settled fundamentals dispatch comparison.** Add
  `benchmark-fundamentals-dispatch` and `backtest/fundamentals_dispatch.py`: every named ablation
  arm is planned from its own forecast and settled at the same realized prices, and the
  incremental realized margin of each challenger over its own control — and, separately, over
  each named baseline — is recorded by the producing module. Planning and settlement go through
  `_backtest_precomputed_forecast`, the accepted path the ML dispatch benchmark already uses, so
  an arm run through the new surface is the accepted computation with a different forecast column
  and nothing else; a regression asserts the control arm and the naive baselines reproduce
  `backtest_ml_dispatch_benchmark` figure for figure. The settled days are exactly the held-out
  days the forecast ablation recorded as common to every baseline and both arms: a gap on one of
  those days contradicts that record and is refused rather than excluded, because an exclusion
  here would give two arms different calendars, and a table whose held-out common day count
  disagrees with its own summary is refused as well. Equivalence is asserted and recorded rather
  than assumed — one battery configuration whose terminal SOC must equal its initial SOC, one
  realized price series, and one perfect-foresight ceiling checked identical across arms to 1e-6
  EUR with a wider spread named rather than reconciled — and the shared basis is written into the
  summary as `equivalent_basis`. `--methods` is required with no default and every challenger
  must be named beside its own control. Four artifacts are written: the settled interval schedule
  per method, the daily results, the paired daily differences per comparison and delivery day,
  and the summary, which records the differences' sign counts, total and largest daily gain and
  shortfall and derives no dispersion, interval or significance statistic from them.
  `reporting/contract.py` gains the `fundamentals_dispatch_benchmark` kind on the
  `historical_forecast_backtest` basis, guaranteeing the comparison methods, the common day
  count, the shared ceiling, the equivalent basis, the ranking, the incremental margin and the
  exploratory flag; the exploratory label is carried verbatim from the ablation, which this
  comparison can neither strengthen nor retire. Validated entirely on synthetic fixtures: the
  three operator declarations are still absent, so no accepted feature table, no settled figure,
  no manifest and no acceptance document was produced, and no accepted figure or analytical
  behaviour changed

- **v0.9.3: the fundamentals forecast ablation.** Add `benchmark-fundamentals-forecast` and
  `forecast/fundamentals.py`: a control arm of the two existing model families on calendar and
  price-history features, and a challenger arm of the same two families with the accepted
  point-in-time columns appended, sharing the walk-forward loop, the fixed hyperparameters, the
  seed, the refit cadence and the delivery days, so only the information differs. `ml.py` gains
  the one parameter that makes this possible — `_walk_forward_predict(..., feature_columns=...)`,
  with `require_non_null` naming the columns that must be complete wherever the model reads them
  — and a regression asserts the control arm reproduces `generate_ml_forecasts` bit for bit,
  refit logs included. Both arms are measured on the intersection of days complete for every
  baseline and both arms, the control is re-measured on that reduced calendar with its unreduced
  metrics recorded alongside, and a day missing any accepted feature leaves every arm by the
  join's own named cause, its rows dropped from the challenger's fit and counted, never imputed.
  Accuracy is sliced by delivery year, market-clock interval of day, declared price regime and
  resolution era; `--price-regime-bands` is required and has no default, and the renderer's
  landing checklist names it. The benchmark identifies rather than describes its inputs: the join
  summary now records a `feature_set_sha256` over the joined frame, and the run refuses unless
  the digest, the cutoff schedule, the decision lead and the admitted evidence grades all equal
  what the join recorded. `reporting/contract.py` gains the `fundamentals_forecast_benchmark`
  kind on the `historical_forecast_backtest` basis, plus a check — applied on record and on read,
  so a hand-edited manifest cannot pass — refusing any summary that admits the quarantined
  `assumed` availability grade while declaring itself not exploratory. A run whose common
  held-out days do not cover a complete meteorological season of quarter-hour deliveries is
  labelled exploratory and carries the suffix saying so. Validated entirely on synthetic
  fixtures: the three operator declarations are still absent, so no accepted feature table, no
  benchmark figure, no manifest and no acceptance document was produced, and no accepted figure
  or analytical behaviour changed

- **v0.9.2: revision-aware point-in-time join.** Add `build-point-in-time-features` and its reusable join: every emitted interval value is the latest revision published strictly before the declared effective cutoff, every selected value has a source-document/revision/byte-digest audit row, later revisions are counted and excluded, coarser broadcasts are explicit, and an incomplete variable excludes the whole delivery day without fill or imputation. Synthetic tests cover cutoff ties, revision selection, provenance, permutation invariance, incomplete days, hourly-to-quarter-hour broadcast, quarantined grades and finer-resolution refusal. Real-data acceptance remains outstanding solely because the three operator declarations are absent; no real join, model, manifest or acceptance document was produced.

- Document measured engineering scale with direct provenance and the opt-in deterministic synthetic dispatch benchmark; no analytical result changes.


- **v0.9.1: point-in-time fundamentals ingestion and the availability audit.** The first v0.9
  code. `data/decision_cutoff.py` gives the declared gate-closure schedule a neutral home —
  moved verbatim out of the retained-but-unused ADMIE timing module, which re-exports it, so a
  live feature path no longer reaches its decision rule through a module documented as unused —
  and adds the readers that refuse the committed example by name, a required decision lead where
  `0` is a declaration and absence is not, and the effective cutoff that is closure minus lead.
  `data/point_in_time.py` is the typed feature schema: a closed column set, a closed source set,
  a closed variable registry with its units, four evidence grades, and refusals for a missing
  value that is not an absent row, a unit that is not the registry's, a naive instant, a
  retrieval that precedes its publication, and two rows that share the uniqueness key and
  disagree. `data/gfs.py` reads NOAA GFS 0.25° forecast vintages from the 00 UTC cycle of D-1:
  both archive key layouts, `.idx` sidecar parsing into inclusive byte ranges, single-message
  byte-range retrieval, ecCodes decoding, sampling at declared grid nodes, and the stated
  two-step de-averaging rule for bucketed radiation. `data/availability_audit.py` judges every
  delivery interval on its own evidence against the declared cutoff, because upload order is not
  monotone in forecast step. `cli/fundamentals.py` adds `fetch-fundamentals` and
  `audit-feature-availability`, the latter exiting `2` on any unaccepted day with its evidence
  still written. `.github/workflows/fetch-fundamentals.yml` and `witness-fundamentals.yml`
  dispatch and schedule them; the witness workflow starts now because a witnessed day exists only
  if a retrieval happened before that day's cutoff and can never be backfilled.
  `reporting/contract.py` gains the `point_in_time_availability_audit` kind on the
  `data_acceptance_evidence` basis, and `reporting/render.py` gains checklist entries for the
  decision cutoff, the decision lead and the sampling geography. `eccodes` is declared as the one
  new dependency — not `cfgrib` or `xarray` — and its first CI run closes the source spike's one
  open residual by proving the decoder on the `actions/setup-python` images. The policy the code
  enforces is `docs/point_in_time_feature_contract.md`. Nothing is accepted: no value, no unit and
  no source enters forecasting, and no accepted figure or analytical behaviour changed
  (`docs/history/implementation_report_v0.9.1.md`).

- **The v0.9 fundamentals source is chosen: NOAA GFS 0.25° forecast vintages.** The v0.9.0
  source-selection spike ran against the live public archive and is recorded in
  `docs/fundamentals_source_assessment_2026-09-02.md`, which converts every external fact the
  design labelled an inference into a verified fact or a recorded unknown with a named closing
  step. All three checks passed — archive coverage across 2021-2026, `.idx` byte-range retrieval
  at a 157x reduction (3.27 MiB rather than 514 MiB per forecast step, 85 MiB per delivery day,
  167 GiB across the usable history), and a pip-installable ecCodes binding that installs with no
  system package and leaves Ruff, mypy, 403 tests and the wheel build green on 3.12 and 3.13 — so
  G0 is not triggered, the EEX EU ETS fallback is not selected and stays unassessed, and the
  provider licence is captured verbatim with its three obligations named. The spike corrected the
  design in four places: the usable hourly record begins at delivery day 27 February 2021 rather
  than at the archive start, leaving 118 of the accepted history's 2,131 delivery days without a
  feature; the decision-time cycle is fixed at 00 UTC of D-1, because the 06 UTC cycle was
  observed publishing after a midday cutoff; both archive key layouts must be tried for days
  before April 2021; and availability must be checked per forecast step, because upload order is
  not monotone in step. Three findings are recorded rather than resolved: a restated-timestamp
  window covering 1 January to 25 February 2021, where the recorded instant can only under-claim
  availability and never over-claim it; one genuinely late run on 14 June 2021; and one whole
  missing cycle on 2 February 2021. Documentation only: no source code, no dependency — the
  decoder was tested in a throwaway virtual environment and `pyproject.toml` is unchanged — no
  workflow, no committed provider content, and no accepted figure or analytical behaviour
  changed. The decision cutoff, decision lead and sampling geography remain operator declarations
  with no defaults, and the 2026-09-01 removal of ADMIE load and RES forecasts from scope is
  untouched.

- **v0.9 is open: a point-in-time fundamentals forecast benchmark.** `docs/v0.9_design.md` is the
  design of record for the one open analytic question in the forecasting layer — whether an
  independently validated exogenous input improves realized settled dispatch value over
  price-history models alone. It specifies a typed point-in-time feature schema carrying a
  publication instant, a retrieval instant, a source document, a revision and a byte digest per
  value; a declared decision cutoff and decision lead with no defaults, where a publication at the
  cutoff is late; graded availability evidence in which witnessed and provider-declared are
  admissible and never merged, and assumed is quarantined; a revision-aware as-of join whose audit
  table names the revision behind every feature value and whose days are complete or excluded by
  named cause; an ablation of the two existing model families with and without the accepted
  features under identical hyperparameters, refit cadence and splits; a settled dispatch
  comparison on common days under an identical battery and a common perfect-foresight ceiling; and
  three new manifest kinds to carry the result. `config/decision_cutoff.example.json` and
  `config/fundamentals_geography.example.json` ship the two declaration formats with placeholder
  references, and a test keeps both parseable by the reader that will read the real declaration
  and refused as declarations while the placeholders remain. Documentation and configuration only:
  no source code, dependency, workflow or data source, and no accepted figure or analytical
  behaviour changed. The choice of data source is not made: the design's external facts are
  labelled as inferences until the v0.9.0 spike verifies them. The 2026-09-01 removal of ADMIE
  load and RES forecasts from scope is not reopened; ENTSO-E's Greek forecasts originate from
  ADMIE and are isolated as a separate track that no part of v0.9 depends on.

### Changed

- **v0.9.2 review correction:** revision selection now occurs before evidence-grade admission,
  so an inadmissible latest pre-cutoff revision excludes the day instead of allowing an older
  revision to be cherry-picked. Per-value audit rows now count only post-cutoff revisions of
  that native feature interval; the summary remains de-duplicated when a coarser value is
  broadcast across price intervals.

- Merge the deferred v0.8.x narrative for renderer-contract version 3: scenario-ensemble reports include deterministic, dependency-free inline SVGs of already-recorded path ranges, with labels, basis and exclusions retained and no new analytical quantity.


- **Two corrections to the v0.9 source assessment, both verified in v0.9.1.** The assessment
  computed the required forecast-step range as 21-46 from the *Athens* delivery day; this
  project's delivery day is the CET/CEST market day, the same day the canonical price schema
  uses, which begins an hour later, so the range a market day needs is **22-47**. Rather than
  replace one constant with another, the client derives the step set from each market day, so a
  23-hour or 25-hour day produces its own, and a test walks every market day of the usable record
  to assert the widest range. Separately, the schema's assumption that one value comes from one
  message does not hold for two of the three variables: wind speed combines the two 10 m
  components and a de-averaged radiation hour combines two adjacent step objects. For a derived
  value the publication instant is therefore the **latest** contributing object's — the value
  became available when its last input did — the document identity names every contributing
  object, and the byte digest is taken over the contributing digests in a stated order, with each
  contributing message listed separately in the retrieval manifest.

- **`fetch_https_bytes` accepts a byte range, and `head_https_headers` reads response headers.**
  A gridded forecast object is hundreds of megabytes of which a few are wanted, and the provider
  publishes a sidecar giving the exact offsets. A server that answers `200` to a range request is
  refused rather than accepted as the requested slice. `HEAD` exists because an object store's
  publication instant is a response header, not a value inside the object.

- **The README now leads with the accepted official-history findings.** A compact, fully
  labelled annual table presents the recorded official market-day coverage, historical
  daily-composed perfect-foresight gross-margin ceilings, causal-method capture ranges,
  negative-price intervals and mean within-day ranges, with partial years explicit and the
  unchanged limitations immediately following. Detailed scenario and end-to-end command
  workflows moved to `docs/command_reference.md`; no analytical result or behavior changed.
- **The dispatch program is solved relaxation-first.** The binary operating mode is the only
  integer variable and earns its place in one situation: a negative price with no headroom to
  charge into. The continuous relaxation is solved first, and returned unchanged when it never
  charges and discharges in the same interval, which makes it mixed-integer feasible and, because
  the relaxation bounds the integer optimum from above, optimal. The integer program is solved
  whenever the relaxation violates the exclusivity it dropped. The reported answer is the
  mixed-integer optimum on either path; no result changes. A year of quarter-hourly prices solves
  9.1x faster over the full horizon with no negative prices, and 1.6-1.7x faster under the daily
  composed convention. `solve_strategy` in the battery configuration selects the strategy and
  defaults to the shortcut; the summary records which path produced the figure.
- **Canonical timestamps are normalized to one resolution.** `ensure_canonical` was normalizing
  everything about a timestamp except its resolution, so a generated history carried microseconds
  and the same history read back from CSV carried nanoseconds, and the two compared unequal
  despite describing identical instants. All five timestamp columns are now nanoseconds. No
  figure or interval changes.
- **Each subcommand has its own module and a registry entry.** `cli.py` declared thirty
  subcommands in one 460-line function and handled them in one 30-branch chain with nothing
  connecting the two. A `Command` record now pairs each name with its help, its argument
  configuration and its handler, so the parser and the dispatch table are built from one list.
  All thirty subcommands' help output and argument sets are byte-identical; only the order the
  top-level help lists them in changed, now grouped by workflow stage. `greek_bess.cli.AdmieClient`
  is now `greek_bess.cli.admie.AdmieClient` for callers that patch it.
- **The README opens with a quickstart** and the per-release implementation reports and release
  notes moved to `docs/history/`, indexed there, with every link updated.

### Added

- **One-command synthetic demonstration.** `greek-bess demo` runs synthetic generation,
  daily-composed perfect-foresight dispatch, declared daily-mean spread compression, stressed
  dispatch, illustrative one-year finance screening, manifest recording for every result and
  indexed report rendering. The committed synthetic-only sample report is linked from the
  README and a regression test requires byte-for-byte regeneration, so the exception for this
  generated public demonstration cannot become stale.

- **Property-based tests over the market calendar.** Delivery days across 2015-2035 at both
  resolutions are generated rather than enumerated, asserting that a market day is contiguous in
  UTC, spans exactly one local midnight-to-midnight, has one of only three legal lengths and
  agrees with the real elapsed duration; that canonicalization is idempotent and independent of
  row order; and that a complete generated day passes the quality gate. The round-trip property
  is what found the timestamp-resolution defect above.
- **Closed-form dispatch tests** checking the optimizer against arithmetic rather than against
  itself: asymmetric one-way efficiencies, fees and degradation cost, and self-discharge
  compounding once per interval at both resolutions.
- **Registry coherence tests** asserting every declared subcommand is reachable from the parser,
  no two claim the same name, and every command module still contributes.
- **Coverage measurement and a 3.12/3.13 CI matrix.** Coverage is reported without a threshold:
  a percentage measures which lines ran, not whether what they computed was correct, and this
  repository does not treat it as an acceptance gate.
- **`Render a report from the accepted replay` workflow.** The v0.8 reporting layer was validated
  against synthetic manifests and real module summaries, but no report had ever been rendered from
  the accepted official history: `render-report` appeared nowhere outside the design documents,
  the implementation reports and the tests. This workflow closes that gap and does nothing else.
- It renders an accepted analysis rather than re-running one. Given the run ID of a completed
  `Decompose the accepted replay by delivery year` run, it records that run's summaries — the
  daily-composed perfect-foresight ceiling, the per-delivery-year decomposition and every forecast
  backtest — under the run-manifest contract, verifies each manifest, and renders them into one
  indexed report. Re-solving would take hours and could produce figures differing from the ones
  the acceptance document records.
- It refuses a decomposition run whose custody verification did not pass, and one that carries no
  custody verification at all: only a run that verified the official history against its committed
  custody record produces evidence a report may present. Neither case is re-run, because a
  difference is a finding to record.
- The job's step summary carries the report's index — manifest identity, kind, basis, producing
  command and digest — and no figure, for the same reason the report's own index carries none. The
  figures stay in the uploaded report beside the labels that say what they are and are not. The
  report and its index are generated research outputs and are never committed.
- Two regression tests assert that a real forecast-backtest summary and a real annual-decomposition
  summary satisfy the result kinds the workflow declares for them, so a renamed summary key fails
  the suite rather than a dispatched workflow.
- No source behaviour, dependency, command, contract or report format changed, and the declared
  project version is unchanged: the workflow runs the existing CLI against existing evidence.

### Fixed

- **v0.8.3 — completed-v0.8 review corrections.** The formal review of the completed v0.8 scope
  found four defects in the reporting layer. None changes an analytical result: no dispatch,
  forecast, stress, degradation, finance or data behaviour is touched, and no recorded figure
  changes value.
- A verified manifest missing one of its result kind's guaranteed summary keys crashed
  `render-report` with an unhandled `KeyError` instead of producing a report. The guaranteed-key
  check runs when a manifest is built rather than when one is read — deliberately, so that a
  manifest recorded before its kind guaranteed a key still verifies — so the renderer must be
  able to meet one. It now states such a key as not recorded, by the same route every other
  absent value takes, and records no figure for it.
- `read_run_manifest` now applies the standing-claim cross-check and the scoped
  distributional-term refusal, not only `build_run_manifest`. A manifest whose summary declared
  `is_probabilistic`, `is_forecast` or `is_investment_evidence` as anything but false was refused
  when recorded, yet read and rendered — placing that claim in a report directly above the
  standing exclusion "not a probability-calibrated estimate". Both checks are properties of the
  recorded content, and a manifest travels; neither can refuse a manifest this project recorded,
  because building one already applied both.
- A manifest whose `declared_inputs` is not an object is refused with a contract error naming the
  field. It previously raised an unhandled `TypeError`, or a `ValueError` whose message described
  a dictionary update sequence rather than the manifest.
- Two distinct manifest IDs reducing to one readable anchor were disambiguated with a single
  unchecked positional suffix, which could itself already be taken: IDs `A`, `A-2` and `a` are
  three manifests but produced two anchors, so the index link for one led to another's block.
  The suffixed anchor is now advanced until unused.
- The `greek_bess.reporting.render` module docstring claimed the manifest doorway inherits the
  guaranteed-key check. It does not, by design; the docstring now states which checks reading
  applies, and why that one is a record-time check.
- Project version raised to 0.8.3 in `pyproject.toml`, `greek_bess.__version__` and the README
  release line. The manifest `schema_version` stays at 1 and the renderer version stays at 2: no
  envelope, report format or index field changed.

### Changed

- **v0.8.2 — interactive viewer decision.** The viewer is deliberately declined and v0.8 closes
  with the deterministic static renderer. The indexed, self-contained report already satisfies
  the approved read-only and exportable-report scope; a viewer would add a runtime dependency,
  a server lifecycle and a second rendering surface without adding evidence.
- A future interactive proposal must identify a user need the static report cannot meet, define
  any scope change, and preserve the verified-manifest-only doorway and every rendering refusal
  under a separately approved milestone. Interactivity is not retained as implicit unfinished
  v0.8 scope.
- Project version raised to 0.8.2 in `pyproject.toml`, `greek_bess.__version__` and the README
  release line. No runtime dependency or rendering behaviour changed.

### Added

- **v0.8.1 — multi-run composition.** A report now composes many verified manifests, and
  composition is layout only: nothing is computed across manifests, and figures of different
  bases are never merged into one row, total or derived value.
- An index across every manifest the report carries, grouped by basis in the contract's declared
  order. It names each manifest by ID, result kind, recorded label, producing command, recorded
  time and SHA-256 digest, links to the block that holds its figures, and names the bases the
  report does *not* cover, because a reader cannot otherwise tell an absent basis from an absent
  question.
- **The index carries no figure at all**, deliberately. A summary table spanning the whole report
  is the one place a perfect-foresight ceiling would sit in a column beside a settled backtest,
  and combining them is a short second step producing a number whose basis is none of the five
  the contract defines. A test asserts every cell of the index is one of the manifest's identity,
  label or provenance fields.
- A scenario ensemble is laid out side by side: one column per named scenario with the
  provenance each figure has to carry, the equivalent-basis evidence the ensemble recorded — the
  battery parameters, terminal-energy basis, source era and path identity every scenario was
  required to share — and one row per bootstrap path giving the lowest and highest margin any
  named scenario produced for that path, which scenario attained each end, and the spread. The
  scenario name joins the two tables; nothing is totalled or reordered across paths, and a test
  asserts no total of the recorded spreads appears anywhere in the document.
- Every composition cell is still a `RenderedFigure` naming the manifest and, now, the exact
  place in that manifest's summary it was read from (`summary_path`). "Nothing was computed while
  rendering" stays checkable rather than asserted, now that layout reaches inside a summary.
- The machine-readable index gains `bases_absent`, `manifests_by_basis`, and per manifest the
  `composition_sections` rendered and the `rendered_summary_keys` it contributed. The renderer
  version is 2; the manifest schema version is unchanged at 1.
- What a manifest does not record is stated, not filled in. An ensemble manifest recorded before
  its module carried a key renders an explicit "records no ..." note, and the renderer still
  opens no file a run wrote beside it. Recorded per-path range rows that declare different
  columns are refused rather than padded, because a blank cell in a range table reads as a value.

### Changed

- **`report_scenario_ensemble` records its per-path ranges in the run summary** (`path_ranges`),
  and `scenario_ensemble_range` now guarantees `scenarios`, `equivalent_basis`, `path_count` and
  `path_ranges` alongside `result_label`, `scenario_count` and `scenario_names`. The ranges lived
  only in the CSV, and a report reads a verified manifest and nothing else — so a range absent
  from the summary was a range no report could show. Recording is not computing: the rows are a
  projection of the same frame the CSV is written from, in the same order, with nothing rounded,
  converted or re-reduced, and a test asserts each recorded cell equals the frame's cell. The
  CSV is unchanged, and per-scenario provenance is recorded once under `scenarios` rather than
  repeated per path. See the 2026-09-01 decision entry and the amendment in
  `docs/v0.8_design.md`.
- The contract's distributional-term check now reaches nested key names for the kinds that
  declare it. A report renders a nested key as a visible column heading, and a top-level scan
  would clear a per-path table whose headings claimed a percentile. The scoping to those kinds
  is unchanged and still load-bearing.
- Because the guaranteed-key check runs when a manifest is built rather than when one is read,
  an ensemble manifest recorded before this milestone still verifies and still renders. The
  manifest schema version stays at 1: the envelope did not change.
- Project version raised to 0.8.1 in `pyproject.toml`, `greek_bess.__version__` and the README
  release line, which is what stamps the `User-Agent` on official retrievals.

### Added

- **v0.8.0 — the report rendering foundation.** `greek_bess.reporting.render` and a
  `render-report` command turn verified run manifests, and only verified run manifests, into one
  self-contained static HTML report plus a machine-readable index. `read_run_manifest` is the
  sole doorway, so the schema-version check, the closed kind registry, the basis cross-check, the
  guaranteed-key check and the scoped distributional-term refusal are inherited by the
  presentation layer rather than restated in it. No new runtime dependency, no server, no
  computation and no environment or network read.
- The landing state is the declaration checklist. Rendered with no manifests, the report shows no
  figure and no example number at all; it lists each judgmental input that has no default — the
  bootstrap source era, the spread-compression factor and reference basis, the availability
  baseline, the negative-price event list and the scenario set of an ensemble — with the dated
  decision that made it default-free and the command that records a result once it is declared.
  A regression test asserts the page contains no digit outside those decision dates.
- Every figure renders inside a block carrying its manifest's `result_label`, its basis in
  reader-facing words and the three standing exclusions, adjacent to the figure and never in a
  global footer. The label is read from the manifest and never re-declared, so it cannot drift
  from the sentence the producing module wrote. A regression test renders a manifest for every
  kind in the registry and asserts all three appear inside that kind's own block.
- The export refusals are executable. A manifest that fails verification refuses the whole report
  rather than being skipped, and the CLI writes no file in that case. Two inputs declaring one
  manifest ID are refused. Renderer vocabulary that would read as a claim about a distribution is
  refused for kinds that forbid the terms — scoped to the headings and captions the renderer
  itself emits, because the standing exclusions say "not a probability-calibrated estimate" and a
  blanket scan would refuse the disclaimer the design requires beside every figure. A test pins
  that scoping.
- Reports are deterministic: manifests are ordered by basis, then kind, then manifest ID rather
  than by input order, and the only timestamp the renderer adds is `rendered_at_utc` in the
  index, so the document itself is byte-identical for identical inputs. A test renders the full
  registry in both directions and compares.
- No figure can be computed while rendering. Every rendered value is recorded as a
  `RenderedFigure` naming the manifest and summary key it came from, and a test asserts each one
  equals the value that manifest recorded, so "nothing was computed" is checkable rather than
  asserted. Values are formatted as the JSON they were recorded as, with no rounding or unit
  conversion between the manifest and the page.
- Interval-level official prices cannot enter an export. The renderer's only input is the
  manifest list; a path a manifest names in `declared_inputs` is displayed, never opened, and a
  test writes a price CSV, names it in a manifest and asserts its price does not reach the
  document.
- A manifest is identified in the index by its ID and the digest of the exact bytes rendered,
  never by its path on the machine that rendered it: an export travels, and the operator's
  directory layout is not part of the evidence.
- The rendered document is self-contained by test: no script, no iframe, no external stylesheet,
  font or image, and no URL of any kind.

### Changed

- Project version raised to 0.8.0 in `pyproject.toml`, `greek_bess.__version__` and the README
  release line, which is what stamps the `User-Agent` on official retrievals.
- `.gitignore` ignores `*.html`. A rendered report is a generated research output produced from
  verified run manifests, and generated research outputs stay outside Git.

### Added

- **v0.8 opened by explicit user approval on 1 September 2026**, lifting the gate the
  completed-v0.7 review set. `PROMPT.md` gains the amended scope bullet: a read-only research
  interface and exportable reports that render verified run manifests, and only verified run
  manifests. `docs/v0.8_design.md` is the design of record and a dated decision entry records
  the opening. No implementation lands with the plan; the package version stays at 0.7.11 until
  v0.8.0 merges.
- The design answers the three questions the gate required. The landing state with no
  judgmental input declared is the declaration checklist itself — each default-free input, the
  dated decision behind it, and the command that records a result once declared — never a
  result or a demo with implied defaults. Every rendered figure carries its manifest's
  `result_label`, its basis in reader-facing words and the standing exclusions adjacent to the
  figure, read from the manifest and never re-declared. An export refuses any figure not
  reachable from a verified manifest, interval-level official price series, distributional
  vocabulary where the kind forbids it, unlabeled figures, and any value computed across
  manifests or across bases.
- The core renderer is a deterministic `render-report` CLI producing self-contained static
  HTML plus a machine-readable index of every rendered manifest's kind, basis, label and
  digest, with no new runtime dependency, no server and no computation. Milestones: v0.8.0
  report rendering foundation, v0.8.1 multi-run composition, and v0.8.2's dated decision to
  decline an interactive viewer and complete v0.8. The suggested branch sequence's
  `streamlit-dashboard` label is
  superseded by `research-reports`; AI-generated explanations remain outside v0.8.
- The complete v0.7 scope was re-verified on 1 September 2026 on the unchanged v0.7.11
  implementation before opening v0.8: Ruff clean, mypy clean over 42 source files, all 301
  tests passing and a clean wheel build.

### Removed

- **ADMIE load and RES forecasts are out of scope** (decision entry 2026-09-01). The 2026-08-26
  quarantine is closed as **never accepted** rather than discharged: no ADMIE field ever entered
  forecasting and none may. This removes a candidate input and changes no accepted figure, because
  no ADMIE data was ever parsed; every recorded ceiling, backtest, capture ratio and scenario is
  unaffected, and forecasting continues on causal price-history features only.
- The quarantine had two exits and had been open since 26 August. One required an operator
  declaration of the gate closure that the repository is built to refuse to supply, then a
  contemporaneous audited window, then format acceptance, then a further decision. `PROMPT.md`
  mentions ADMIE nowhere, so this narrows the project back to its approved brief rather than
  amending it.
- Nothing carrying evidence is deleted. `list-admie-filetypes`, `fetch-admie-files`,
  `audit-admie-publication-timing`, the gate-closure format, their tests and the
  `Audit ADMIE publication timing` workflow are **retained and documented as unused** — the
  executable form of the refusal, kept so a future declaration could be tested without rebuilding
  them, and marked as such in their own module docstrings so a reader meets the status with the
  code. The 2026-08-31 filetype acceptance keeps its evidentiary value as a record of what was
  established, which was names and non-empty discovery only.

### Added

- Encrypted custody copies published as release `custody-2026-09-01` (run `33497084006`), after
  verifying both artifacts against their committed records. The reconciliation copy is the only
  surviving form of that evidence once its source artifact expires 3 September 2026. Ciphertext
  digests are recorded in `docs/official_artifact_custody.md`.
- A decryption drill covering both artifacts, recorded as the step that proves the private key
  opens the copies and that the recovered plaintext is the accepted artifact, because an
  encrypted copy whose key has never been exercised is an assumption rather than a backup and
  fails silently. **Run on 1 September 2026**, while the source artifacts still existed and a key
  failure would have been recoverable; the private key opens the published copies. The document
  now states which of the pre-encryption verification, age's authenticated encryption and the
  successful decryption establishes which part of the custody claim.
- A Windows note that age's output must be redirected with its own `-o` flag rather than a
  PowerShell `>`, which re-encodes binary as text and presents a tooling error as a key failure.
- Replacement retrieval of the accepted official history before the original artifact's expiry.
  Run `33483975614` re-ran `Fetch official Greek market history` with the inputs that produced
  the accepted baseline, yielding an artifact that expires 30 November 2026 under the 90-day
  retention instead of 2 September 2026 under the original seven-day window.
- Verification of that replacement against the committed custody record (run `33484823956`):
  four differences, all per-file byte digests, with **no content fingerprint differing**. Both
  price-series digests match, so the accepted history is unchanged interval for interval.
- A fourth case in the custody failure taxonomy, the faithful re-retrieval, and the rule that
  per-file digests are not diagnostic for one because `retrieved_at_utc` is a canonical column.
  Only the content fingerprints separate unchanged data from a revised publication.
- `docs/official_history_replacement_2026-09-01.md` and a dated decision entry recording the
  finding. The committed custody record was deliberately not replaced in that step.
- The history custody record re-recorded against run `33483975614` as a separate decision, since
  after 2 September 2026 no obtainable copy could match the superseded per-file digests and a
  record that verifies against nothing preserves no evidence. Generated by the tooling in
  `record` mode and committed as emitted; every content fingerprint is unchanged and the
  superseded record remains in Git history.
- A `record_mode` input on the `Record official artifact custody` workflow, so a deliberate
  re-record is an explicit request rather than something provoked by deleting the committed
  record. Neither mode writes to `docs/custody/`. The workflow's history defaults now point at
  the replacement run.

- A `Publish encrypted custody copies` workflow, which verifies each accepted artifact against
  its committed custody record, encrypts it to an operator-supplied age recipient, and attaches
  the ciphertext to a private release. An age recipient is a public key, so the automation can
  encrypt and cannot decrypt; the private key stays with the operator. This reverses the recorded
  exclusion that the procedure does not automate the upload, and reduces the operator's part to
  generating one key pair. An artifact that does not verify is never encrypted.

- Live ADMIE filetype acceptance against the 74-entry catalog and delivery days 26-28 August
  2026. The ISP1 day-ahead load/RES pair returned six files per type and the ISP2 pair returned
  three per type; the catalog-valid DAM pair returned none. Leakage-relevant declarations,
  official-source metadata, workflow defaults, examples and tests now use the confirmed ISP1
  and ISP2 pairs. This settles discovery only, not gate closure, publication timing or format
  acceptance, and the forecast-feature quarantine remains in force.
- `docs/admie_filetype_acceptance_2026-08-31.md` and a dated decision recording that evidence.
- `fetch-admie-files` refuses an empty discovery instead of writing an empty manifest and
  exiting zero, matching the existing HEnEx daily behaviour. The live catalog is consulted so the
  message distinguishes a filetype the provider does not publish (naming the catalog's actual
  filetypes) from a valid filetype over a window it published nothing for.
- Found by the first live audit run on 2026-08-31, which discovered zero files for
  `DayAheadLoadForecast` and `DayAheadRESForecast` and reported `no_record` for all six audited
  filetype-days. That verdict reads as "the publisher published nothing", which is one of the
  four things the timing audit explicitly does not establish, so a wrong or renamed filetype must
  not be able to impersonate it.
- `greek_bess.reporting` and the `record-run-manifest` / `verify-run-manifest` commands: the
  versioned run manifest and report contract the completed-v0.7 review named as the prerequisite
  for any future presentation layer. A manifest carries the producing module's summary verbatim
  and adds a stable projection: declared `result_kind` from a closed registry, the `basis` that
  kind reports on, the required non-empty `result_label`, `produced_by`, `project_version`,
  declared inputs and the project's standing exclusions.
- Label retention is now executable rather than conventional. `PROMPT.md` requires that model
  outputs retain their source and limitation labels through downstream analysis; a result whose
  summary lacks a non-empty `result_label`, or a kind's other guaranteed keys, is refused.
- `schema_version` is checked on read: a manifest from a newer contract is refused rather than
  read on the assumption its fields still mean the same thing, as is a declared basis that
  disagrees with its result kind, and an unknown kind names the closed registry.
- The distributional-term check is scoped to the result kinds that declare it — today
  `scenario_ensemble_range` alone, exactly matching the ensemble's existing behaviour. A blanket
  ban would refuse the optimizer's own `average_charge_price_eur_per_mwh`, a forecast benchmark's
  mean absolute error and the ADMIE audit's median lead time, none of which claim a distribution
  over outcomes. A regression test pins a real summary carrying such a term so the reason stays
  visible.
- Where a summary declares the standing claims itself, the contract cross-checks rather than
  ignores them: `is_probabilistic`, `is_forecast` or `is_investment_evidence` set to anything but
  false is refused as a scope change requiring a recorded decision.
- `docs/run_manifest_contract.md`, `docs/history/implementation_report_v0.7.11.md`, and a dated decision.

- `audit-admie-publication-timing` and `greek_bess.data.admie_timing`, turning the
  `requires_pre_auction_timing_validation` quarantine label into an executable acceptance step.
  The audit reads ADMIE retrieval manifests and answers, per filetype and delivery day, whether a
  file was published strictly before that day's day-ahead gate closure. No forecast file is
  parsed and no feature is built.
- The gate closure is declared with **no default and no built-in constant**: a schedule is one or
  more dated regimes, each naming the clock its time is stated on and carrying a required
  reference to the market rule it comes from, because the rule can change across a history
  starting in November 2020. A day earlier than the first regime is refused rather than audited
  against a rule that was not declared for it, and a closure falling in a daylight-saving gap or
  repetition is refused rather than guessed.
- Contemporaneously witnessed evidence is separated from publisher-asserted evidence and never
  promoted to it. A retrieval performed before the closure observed the file in the catalog and
  is recorded as `witnessed_pre_gate`; a publication timestamp read afterwards only asserts
  availability and is recorded as `asserted_pre_gate`. A publication exactly at the closure
  instant counts as late.
- Each accepted day names its **decision-time revision** — the latest revision published strictly
  before closure, the only one a backtest may read — with the count of revisions that superseded
  it after closure, because reading a provider's latest revision for a past day leaks
  post-decision information even on a day that passes on timing.
- A delivery day no supplied record covers is reported as `no_record` rather than assumed
  compliant; one ADMIE URL carrying two different digests across manifests is refused as an
  in-place replacement, and one carrying two different publication timestamps as a restated
  publication time.
- `config/admie_gate_closure.example.json`, the `Audit ADMIE publication timing` workflow, which
  retrieves every revision covering a declared window and uploads the manifest, per-day verdicts,
  per-observation evidence and summary for 90 days, and
  `docs/admie_publication_timing_policy.md`.
- The summary states its own limits in its own output: `establishes_only_publication_timing`,
  `does_not_establish` and `quarantine_lifted`. Timing acceptance is not format acceptance and
  does not lift the forecast-feature quarantine on its own.
- `docs/history/implementation_report_v0.7.10.md`, and a dated decision recording the audit contract.

- `apply-negative-price-events` and `greek_bess.stress.apply_negative_price_events`, completing
  the approved v0.7 modeling scope. Each event declares an identifier, inclusive UTC start,
  exclusive UTC end and strictly negative absolute replacement price in EUR/MWh; every
  consequential field has no default and `events: []` is the exact identity.
- Event occurrence is declared, never sampled, inferred, fitted, ranked or searched. Frequency,
  rate, likelihood, probability, percentile and expected-count fields are refused as unknown.
  Windows must align to whole delivery intervals, cover at least one interval and not overlap.
- One-to-one provenance covers every path interval, including untouched rows. The summary records
  the policy, method, full configuration, applied interval counts and negative/zero counts before
  and after. Existing signed prices outside named windows are unchanged and no price is clipped.
- `docs/history/implementation_report_v0.7.9.md`, and a dated decision defining the event unit and the
  refusal to sample occurrence.

- `greek_bess.stress.build_availability_profile` and `dispatch-bootstrap-paths
  --availability-schedule`, completing the last approved v0.7 modeling item. An availability
  schedule is a declared baseline available fraction with **no default** plus zero or more
  declared outage windows, each with its own available fraction in [0, 1]. Timing, duration and
  depth are judgmental scenario inputs and are never sampled: a forced-outage rate would be an
  uncalibrated probability, and a configuration carrying one is refused by name.
- A window is applied whole to every interval it covers. A boundary falling strictly inside a
  delivery interval is refused, naming the interval, rather than prorated or rounded — prorating
  would apply a schedule finer than the one declared. Overlapping windows, a window covering no
  dispatched interval, reversed or empty windows, naive timestamps, duplicate outage identifiers
  and out-of-range fractions are all refused. A schedule with an empty window list is the
  declared full-availability scenario.
- The profile is built from the paths' own canonical UTC keys, so 23/25-hour market days and the
  quarter-hour regime are handled by construction, and paths that do not share one interval
  identity are refused. Per-interval provenance records the schedule, the baseline, the outage
  covering each interval and the applied fraction, and `dispatch-bootstrap-paths` writes it as an
  `.availability.csv` sidecar.
- The dispatch summary records a declared schedule by identity — `schedule_id`, baseline,
  window count, derated intervals and hours, minimum fraction and each window with its applied
  interval count — so a margin traces back to the outage assumption rather than to an anonymous
  array of fractions.

### Known blocker

- `ENTSOE_SECURITY_TOKEN` is no longer configured as a repository secret, so
  `Reconcile HEnEx and ENTSO-E prices` cannot run (run `33489364087` was refused at its guard
  step). The `henex-entsoe-reconciliation` artifact from run `33073631530` therefore has no
  replacement before it expires 3 September 2026.

### Changed

- `audit-admie-publication-timing` summaries now carry a `result_label`, closing the one gap in
  the project's otherwise universal labelling convention and letting the audit be recorded under
  the contract. No verdict, refusal or provenance behaviour changed.

- Completed the formal v0.7 consistency review across public APIs, CLI surfaces, provenance,
  summaries, tests, methodology, limitations, decisions and implementation reports. The review
  found no correctness or data-integrity defect and confirmed the missing-price, signed-price,
  time-ordering, realized-settlement, equivalent-basis and non-probabilistic invariants.
- Reconciled one roadmap wording contradiction: differing declared availability schedules are
  scenario judgments carried as provenance, not part of the equivalent asset-and-sample basis.
  Battery parameters, terminal-energy constraints, source-era selection and path identity must
  still match, and an unrecorded availability assumption is still refused.

- The scenario-ensemble equivalent-basis check no longer covers the availability assumption.
  The basis is now the asset and the sample — battery parameters, terminal-energy constraint,
  source-era selection and path identity — while the price transformation and the availability
  schedule are the judgments under examination and are expected to differ. Without this an
  ensemble could never place a declared outage against a baseline, which is the comparison an
  outage scenario exists to make. Availability is carried as provenance instead: every margin
  row gains `availability_type`, `availability_schedule_id` and `availability_declaration`, each
  range row names the availability at both ends, and the summary records each scenario's
  declaration. An unrecorded availability assumption is still refused. See the dated
  `DECISIONS.md` entries of 2026-08-31.

- `report-scenario-ensemble` command and `greek_bess.stress.report_scenario_ensemble`, which
  compose bootstrap-path dispatch results already produced under two or more named scenarios and
  report the minimum, maximum and spread of their margin outcomes. Ranges are taken per bootstrap
  path — nothing is aggregated across paths, because a total or an average over sampled paths
  would read as an expectation the uniform block resampling cannot support. The milestone
  composes accepted outputs and adds no price transformation, dispatch mode, forecast method or
  finance treatment.
- Every scenario is named by the caller through an explicit manifest. There is no default
  scenario set and no implicit baseline: `transformation_summary_json` is a required key, so a
  scenario with no transformation declares that as `null`, and an ensemble of fewer than two
  scenarios is refused.
- The non-probabilistic framing is enforced rather than described.
  `greek_bess.stress.FORBIDDEN_REPORT_TERMS` lists the excluded vocabulary — probability,
  percentile, likelihood, expected value, mean, median, quantile, loss, rank, central and others —
  and every emitted column name and summary key, including nested provenance keys, is checked
  against it before the result is returned. A field such as `p95_margin_eur` raises rather than
  being written.
- Scenarios are combined only on an equivalent basis. Differing battery parameters,
  terminal-energy constraint, selected source era or path identity are refused with the
  mismatching basis named and both values shown; the terminal-energy constraint is checked
  separately from the rest of the battery configuration so a day-end energy difference is
  refused by that name. Differing declared availability schedules remain scenario provenance.
- Provenance on every reported figure: `scenario_margins` carries the scenario name,
  transformation method, transformation ID, recorded transformation parameters, source-era
  resolution and day span, input run identity and bootstrap seed for each scenario and path, and
  `scenario_ranges` repeats scenario name, transformation and run identity for the scenarios at
  both ends of each path's range.
- `docs/history/implementation_report_v0.7.7.md`, and dated `DECISIONS.md` entries covering the
  non-probabilistic framing and the equivalent-basis refusal rule.

### Fixed

- Replaced generic-unit `pd.Timedelta` construction with explicit units in synthetic, HEnEx and
  ENTSO-E ingestion and in the two affected tests, removing the NumPy generic-unit deprecation
  the suite had been emitting.
- Scoped the pytest warning gate instead of promoting every warning to an error. `filterwarnings`
  now fails on warnings attributed to `greek_bess` or to the project's own test modules and
  reports the rest: dependencies are installed from ranges, so a blanket policy would let an
  upstream release rather than a reviewed change decide when validation breaks. The narrowed gate
  still catches the deprecation above, because pandas attributes it to the constructing line.
  `tests/test_warning_policy.py` covers the deprecation at each call site and the policy's scope.
- Repaired the declared project version, which had drifted between `pyproject.toml` (`0.7.6`) and
  `greek_bess.__version__` (`0.7.2`). The package version is sent as the `User-Agent` on official
  HEnEx and ENTSO-E retrievals, so the stale value mislabelled the client that fetched an accepted
  artifact. `tests/test_project_metadata.py` locks `pyproject.toml`, `greek_bess.__version__`, the
  README release line and that header together. The version stays at `0.7.6`, because this is a
  maintenance correction and not a milestone; the changelog's released sections still stop at
  `[0.7.2]`, with `0.7.3`-`0.7.6` content under `[Unreleased]`.
- Corrected custody wording that read as a claim about stored copies. The records committed under
  `docs/custody/` are fingerprints, not durable encrypted copies; the operator upload is not
  verified complete in the repository record, and nothing here reads live GitHub release state.
- Aligned the limitations with the decision to exclude scenario probability estimates unless an
  independently validated calibration methodology is approved.

### Added

- `compress-spread` command and `greek_bess.stress.apply_spread_compression`, a deterministic
  compression of within-day spread about a declared daily reference level:
  `compressed = reference + factor * (price - reference)` over each path's CET/CEST market day.
  Every within-day range is scaled by exactly the factor; a factor of 1.0 is the identity and 0.0
  flattens each day onto its reference. `reference_basis` is declared with no default
  (`daily_mean` preserves each daily mean exactly, `daily_median` does not and the summary
  reports the resulting shift), the factor is bounded to [0, 1], and spread widening is out of
  scope. Zero and negative results are preserved and never clipped, so intervals can cross zero;
  the count is reported as `sign_change_interval_count`. The summary also reports mean and
  maximum daily range and negative and zero interval counts, before and after. Interval
  provenance records the market day, reference level, factor, basis, original and compressed
  prices and input source metadata. Missing prices are refused explicitly, because one would
  propagate through its market day's reference level.

- `scripts/bootstrap-dev-env.sh`, a tracked, editor-neutral development environment bootstrap.
  It creates or updates `.venv` on Python 3.12, installs the project with its development
  extras, and optionally appends `VIRTUAL_ENV`/`PATH` exports to a file for callers that source
  an environment file. Local session tooling should call it rather than reimplement the steps.

- A decision entry scoping custody to retrieved official artifacts. Derived evidence such as
  the `annual-replay-decomposition` artifact gets no custody record: it carries no
  interval-level price and no provider that could revise it, and its inputs — the custodied
  history, the pinned commit and the recorded configuration — are already fingerprinted, so
  reproducibility is the guarantee that fits it.

- `docs/official_annual_decomposition_2026-08-28.md`, recording the accepted per-delivery-year
  decomposition of the official replay from workflow run `33147448666`. Custody verification of
  the source artifact passed, and every per-year figure reconciles with previously accepted
  aggregates to the euro, including the EUR 0.00 common-day ceiling spread within each year.

- An explicit bootstrap source-era and resolution policy. A source era is a maximal contiguous
  run of market days at one delivery resolution; a resolution change or a market-day gap ends
  one. `BootstrapConfig` gains `source_resolution_minutes`, `source_start_day` and
  `source_end_day`; `detect_source_eras` and `select_source_era` are public. A single-era
  history needs no declaration, a multi-era history must declare one, and there is no default,
  because the accepted 2020-2026 history holds an hourly and a quarter-hour era and a default
  would settle that trade-off silently. The refusal lists the available eras and their windows,
  the selection is recorded in the run summary and on every provenance row, sampling is confined
  to the selected era so no block straddles a regime boundary, and minimum and median
  block-candidate counts are reported so scarcity is visible.
- `docs/bootstrap_source_era_policy.md`, recording the policy, the two eras of the accepted
  history with their season coverage, what each choice costs, and the deliberate exclusions:
  no resampling between resolutions, no blending of eras and no likelihood attached to either.

- `decompose-annual-replay` command and a `greek_bess.analysis` package, which regroup an
  already-accepted replay into delivery years without adding a model, market or
  transformation. A delivery year is the calendar year of the interval's CET/CEST market-day
  start, matching the committed custody records. The per-year overview carries market-day
  coverage, an explicit partial-year flag, interval counts by resolution, preserved negative,
  zero and missing price counts, price context including the mean daily price range, and the
  perfect-foresight ceiling; a second table reports forecast capture per method on that
  method's own backtested days; a third restricts every method to the days all methods
  backtested and records the ceiling spread that proves the comparison is like-for-like.
  Per-market-day figures are within-period averages and nothing is annualized. No probability,
  percentile, loss metric or ranking of years is produced. A duplicated accepted history, a
  schedule settled on prices the history does not publish and a daily-results table describing
  another history are each refused explicitly.
- `optimize-perfect-foresight --daily-solves` and `optimize_daily_perfect_foresight`, which
  solve every market day independently and compose the schedules. This publishes the
  daily-composed mode the 2026-08-27 acceptance ran through a temporary runner, requires the
  terminal SOC to equal the initial SOC, and is the basis on which no trade can span a
  delivery-year boundary. The composed schedule carries a `market_day` column and its summary
  records per-day solver statuses and the largest terminal-energy error.
- `Decompose the accepted replay by delivery year` GitHub Actions workflow, which verifies an
  accepted `greek-dam-official-history` artifact against its committed custody record before
  consuming it, then runs the daily-composed ceiling, the requested causal naïve backtests and
  the decomposition inside Actions, publishing only per-year aggregates to the job summary.

- `record-custody` and `verify-custody` commands and a `greek_bess.data.custody` module, which
  fingerprint an accepted official artifact without recording any price. A custody record holds
  per-file digests plus content-level invariants of the normalized series — interval count,
  window, market-day count, negative/zero/missing price counts, counts by delivery year,
  resolution and source, quality-flag counts by name — and a digest of the interval and price
  series computed over sorted `(delivery_start_utc, delivery_end_utc, price)` triples at six
  fixed decimals, so it is independent of CSV column order, file formatting and float repr.
  `verify-custody` returns exit code 2 on any difference.
- `Record official artifact custody` GitHub Actions workflow, which downloads an accepted
  artifact inside Actions and either records a custody record when none is committed or
  verifies the artifact against the committed one and fails on any difference.
- `docs/official_artifact_custody.md`, recording the durable storage procedure for accepted
  official artifacts: encrypted assets on a private repository release, fingerprinted by
  committed custody records, with operator steps, a verification drill and a taxonomy
  separating a corrupted copy, a revised official publication and a change in this project's
  own normalization.
- `read_canonical_csv` in `greek_bess.data.schema`, which restores a written canonical history
  with its timezone-aware views and decoded quality flags. The CLI's private reader now
  delegates to it.
- `merge-canonical` command and `concat_canonical` helper, which join normalized CSV files
  from one official source into a single quality-assessed history and refuse to mix sources or
  to drop a repeated interval.
- `Reconcile HEnEx and ENTSO-E prices` GitHub Actions workflow, which reads the accepted
  `greek-dam-official-history` artifact from an earlier run, derives the reconciliation window
  from that history, retrieves ENTSO-E A44 prices for the same window with the encrypted
  repository secret, classifies every interval with `compare-sources` and uploads the interval
  detail as an artifact while keeping official prices out of the job log.
- `docs/official_source_reconciliation_2026-08-27.md`, recording the passed live reconciliation
  of the accepted HEnEx history against ENTSO-E A44 prices over market days 1 November 2020
  through 25 August 2026: 74,662 of 74,663 intervals match within EUR 0.000001/MWh, neither
  source omits an interval the other publishes, and one 29 October 2023 interval differs by
  EUR 0.01/MWh.
- Bounded retry with backoff for ENTSO-E timeouts, connection failures and 429/5xx responses,
  with the socket timeout, attempt budget and backoff exposed on `fetch-entsoe`.
- The request period and the acknowledgement reason in a rejected ENTSO-E request's error.
- Reader-facing "What this tool cannot tell you" README section covering the April 2026 entry
  of batteries into the Greek DAM/IDM, expected spread compression from the arriving storage
  fleet, and the exclusion of balancing-market and availability-support revenues.
- `CLAUDE.md` and a `.claude/` SessionStart hook that prepares a Python 3.12 virtual
  environment so Claude Code on the web sessions can run Ruff, mypy and the test suite.
- Explicit documentation that the dispatch summary's equivalent full cycles are grid-side while
  the degradation model uses cell-side cycles.
- `docs/official_multiyear_operational_acceptance_2026-08-27.md`, recording live acceptance of the
  existing perfect-foresight dispatch and forecast-dispatch backtests over all 74,663 official
  HEnEx intervals from 1 November 2020 through 25 August 2026.
- Aggregate input, constraint, leakage, settlement, coverage, exclusion and determinism evidence,
  including the accepted artifact SHA-256, solver identity and software versions.

### Changed

- The price-level and spread-compression transformations now share one bootstrap-path validation
  contract (`greek_bess.stress._paths.validate_bootstrap_paths`), so two transformations cannot
  drift apart on what counts as an acceptable path. Behaviour is unchanged.
- Repository content is contributor-neutral: no tool or assistant attribution in commit
  messages, pull requests, comments, documentation or tracked configuration (decision entry
  2026-08-28). Editor- and service-specific session configuration is untracked and ignored.
- `CONTRIBUTING.md` now states the real Python 3.12 requirement and the four validation gates;
  it previously described a `python -m unittest` invocation the project does not use.

- The bootstrap no longer refuses a mixed-resolution history with a bare "must use one
  interval resolution" message. It reports the eras the history contains and requires one
  to be chosen.
- Artifact retention on `Fetch official Greek market history`, `Fetch ENTSO-E prices` and
  `Reconcile HEnEx and ENTSO-E prices` is raised from 7 to 90 days, so a passed acceptance no
  longer has a one-week shelf life.

- ENTSO-E A44 parsing now honors the document's declared curve type. Under `A03` a point's price
  holds until the next declared position, so those intervals are materialized and labelled
  `entsoe_variable_block_repeat` instead of being reported as missing; `A01` documents are
  unchanged and an unknown curve type is rejected. The previous behavior understated ENTSO-E
  coverage of the accepted window by 4,874 intervals (decision entry 2026-08-27).
- `PLAN.md` records private-token validation and overlapping-source reconciliation as accepted;
  `STATUS.md` and `LIMITATIONS.md` record the reconciliation result and drop the pending items it
  resolves.
- Repositioned the project documentation as a Greek DAM battery replay and research benchmark;
  repository, package and CLI names are unchanged (decision entry 2026-08-27).
- Corrected the v0.7 scope from "probabilistic stress testing" to deterministic named
  scenarios: source-era/resolution policy, availability/outage paths, spread-compression
  transformations and non-probabilistic scenario ranges. P5/P50/P95 and loss-probability
  outputs were removed pending a defensible calibration methodology (decision entry
  2026-08-27).
- Documented that a constant price-level shift leaves within-path spreads unchanged and is
  therefore a weak stress for arbitrage value (`METHODOLOGY.md` §8, `LIMITATIONS.md`).
- Added parallel-track items for durable private storage of the accepted history before
  artifact expiry (2 September 2026) and a per-calendar-year replay decomposition.
- `PLAN.md` records the incremental 2026 daily retrieval as accepted; workflow run `32971677163`
  and the hash-verified artifact prove the previous pending state was stale.
- `STATUS.md` records the operational acceptance and removes the completed multi-year optimizer and
  forecast-backtest validation item.

### Interpretation limits

- No model, market, stress transformation, degradation, finance or interface behaviour changed;
  no production code was modified.
- Perfect-foresight results are historical gross-margin upper bounds and forecast results are
  historical benchmark evidence, not expected revenue, forecasts, probabilities, rankings of future
  performance or investment conclusions.

## [0.7.2] — 2026-08-27

### Added

- Strict multi-path bootstrap validation and independent deterministic dispatch using identical
  battery and availability assumptions.
- Interval schedules retaining path/canonical identity and path-level operational/revenue
  summaries.
- `dispatch-bootstrap-paths` CLI plus deterministic synthetic API, failure and CLI regressions.

### Interpretation limits

- Results remain synthetic perfect-foresight gross-margin upper bounds, not forecasts,
  probabilities, expected revenues, finance outputs or investment evidence.
- Degradation, percentiles, probability metrics, rankings and negative-price-event
  transformations are not included.

## [0.7.1] — 2026-08-27

### Added

- Strict additive price-level shock configuration with a finite EUR/MWh shift and required
  transformation identifier.
- Deterministic public Python API and `apply-price-level-shock` CLI workflow.
- Interval provenance containing path identity, UTC key, original and shocked prices, method,
  configured shift and input source metadata.
- Synthetic tests for exact arithmetic, reproducibility, signed prices, CLI artifacts and
  rejection of missing, duplicate or incomplete paths.

### Interpretation limits

- Shocked paths are synthetic sensitivities, not forecasts, probabilities, revenues or
  investment evidence.
- No spread, negative-price-event, outage or cannibalisation shocks are included.

## [0.7.0] — 2026-08-26

### Added

- Deterministic meteorological-season block bootstrap with explicit target dates, path count,
  block length and random seed.
- Block-level provenance recording target/source dates, season, interval count, candidate count
  and sampled candidate index.
- Public Python API and `generate-bootstrap-paths` CLI with path, provenance and summary outputs.
- Synthetic tests for reproducibility, timezone-aware timestamps, zero/negative prices, spring
  and autumn DST market days, strict configuration and missing-observation rejection.

### Interpretation limits

- Bootstrap paths are labelled synthetic scenarios, not forecasts, probability-calibrated
  outcomes, expected revenues or investment evidence.
- Dispatch, degradation, finance, percentile/loss outputs and additional shocks are excluded
  from this foundation.

## [0.6.3] — 2026-08-26

### Fixed

- Parse live HEnEx daily result labels that omit the `.xlsx` suffix.
- Use the current `/web/guest/` Liferay pagination route and redirect parameter.
- Continue through catalogue pages newer than the requested range.
- Reject repeated catalogue pages and missing requested delivery days.

### Validation

- The preceding 2020-2025 workflow run passed and its private artifact was integrity-checked.
- Failed incremental workflow run 32969157951 is retained as evidence of the live-layout defect.
- Six focused catalogue regression tests cover the corrected behavior.

## [0.6.2] — 2026-08-26

### Fixed

- Select the latest HEnEx daily workbook revision before parsing superseded files.
- Safely extract the official nested 2021 DAM archive and retain its parent/child hashes.
- Accept only a tightly bounded one-cent MCP rounding consensus when one or two cross-border
  asset rows differ from the dominant Greek-zone value; flag every affected interval.
- Continue to reject ties, larger differences and non-majority MCP disagreements.

### Validation

- Live HEnEx archives for 1 November 2020 through 31 December 2025 produced 51,915 contiguous
  intervals with no missing or duplicate UTC keys.
- All six annual archive hashes, row counts, DST validation and provider-row rounding flags are
  recorded in `docs/official_history_acceptance_2026-08-26.md`.
- The failed first workflow run is retained as evidence of the acceptance defects that prompted
  this patch.

## [0.6.1] — 2026-08-26

### Added

- Verified HEnEx annual DAM-results archive register for 2020-2025.
- Safe ZIP extraction restricted to English `EL-DAM_Results` workbooks.
- Multi-workbook latest-revision normalization and conflict rejection.
- Incremental HEnEx daily results discovery for unarchived dates.
- ADMIE filetype and range API client with latest-revision selection.
- File-level retrieval manifests with coverage, publication/retrieval timestamps, hashes and
  leakage classifications.
- Exact HTTPS source-host allowlists and atomic raw-file writes.
- Manual private GitHub Actions retrieval workflow.
- Eight archive, ADMIE, daily-catalog and HTTP-security tests.

### Changed

- Package version increased from 0.6.0 to 0.6.1.
- Official multi-year evidence acquisition now precedes v0.7 stress testing.
- ADMIE forecast candidates are explicitly quarantined pending publication-time acceptance.

### Validation

- All 68 source tests pass.
- Clean GitHub CI passed Ruff, mypy, all 68 tests and a wheel build.
- Live 2020-2026 provider retrieval remains required before evidence acceptance.

## [0.6.0] — 2026-08-25

### Added

- Explicit unlevered, nominal, pre-tax and pre-subsidy project-finance model.
- Continuous daily operating-path validation from configured project start through end.
- Mandatory operating-margin provenance labels for perfect foresight, historical
  forecast backtests and user-supplied scenarios.
- Separately itemized battery, power-conversion, grid, development/construction and other
  initial CAPEX.
- Fixed OPEX, insurance, asset management, discharge-linked variable OPEX and nominal
  OPEX escalation.
- Dated augmentation cost integration from v0.5 daily degradation-dispatch outputs.
- Project-end decommissioning cost and residual value.
- Daily and annual cash-flow artifacts with exact-date discount factors.
- Unlevered NPV and IRR, with explicit suppression when multiple cash-flow sign changes
  make IRR ambiguous.
- Simple and discounted payback dates and years.
- Maximum initial CAPEX, break-even market-margin realization and break-even average
  annual market-margin outputs.
- `evaluate-project-finance` CLI command and illustrative non-project-specific finance
  configuration.
- Seven new finance and CLI tests, including end-to-end degradation-to-finance coverage.

### Changed

- Package version increased from 0.5.0 to 0.6.0.
- v0.5 augmentation costs are now explicitly consumable by the separate finance layer.
- The immediate next milestone is probabilistic stress testing.

### Validation

- All 60 automated tests pass.
- Exact cash-flow components, NPV reconstruction, break-even values, payback behavior and
  IRR status are covered.
- Missing, duplicate and unsorted daily operating paths are rejected.
- Invalid costs, margin labels and realization fractions are rejected.
- Existing ingestion, DST, optimizer, forecast, leakage, ML and degradation tests remain
  green.

### Interpretation limits

- Finance outputs inherit the evidence quality of the supplied operating margins.
- A perfect-foresight operating path remains an upper bound after NPV treatment.
- The included finance values are illustrative round numbers, not Greek project costs.
- Taxes, subsidies, debt, financing fees, working capital, grid feasibility, bid
  acceptance and non-DAM revenues remain excluded.

## [0.5.0] — 2026-08-25

### Added

- Cohort-based battery state with separately aged initial and augmentation capacity.
- Linear calendar fade and cell-discharge equivalent-cycle fade assumptions.
- Usable energy and charge/discharge power evolution with configurable power coupling.
- Proportional daily cell-throughput allocation across usable cohorts.
- Retained-capacity warranty, EFC throughput and retirement-threshold indicators.
- Optional enforceable per-cohort EFC warranty headroom in daily dispatch.
- Dated augmentation/replacement energy, power and cost records with explicit retirement
  of named cohorts.
- `simulate-degradation-dispatch` CLI command.
- Interval, daily, final-cohort and JSON summary degradation artifacts.
- Illustrative degradation and augmentation configuration.
- Eleven new degradation, warranty, augmentation/replacement, DST and CLI tests.

### Changed

- Package version increased from 0.4.0 to 0.5.0.
- The immediate next milestone is now unlevered project finance.
- Documentation distinguishes physical capacity fade from the optional per-MWh monetary
  degradation adder already available in dispatch configuration.

### Validation

- All 53 automated tests pass.
- Exact additive calendar/cycle fade arithmetic is tested.
- Augmentation cohorts retain independent age and throughput histories.
- Beginning-of-day degraded limits constrain the current market-day solve; current-day
  discharge changes only end-of-day and future capacity.
- Enforced EFC headroom prevents later dispatch from exceeding the modeled throughput
  ceiling.
- A 92-quarter-hour spring DST market day remains complete.
- Existing ingestion, optimizer, forecast, leakage and like-for-like tests remain green.

### Interpretation limits

- The generic fade and warranty parameters are illustrative, not OEM evidence.
- The degradation-aware dispatch remains a daily perfect-foresight DAM gross-margin upper
  bound, not expected revenue.
- Augmentation cost is recorded separately; cash-flow timing begins in v0.6.
- Temperature, C-rate, depth-of-discharge, nonlinear knee and controller-specific cohort
  dispatch models remain outside v0.5.

## [0.4.0] — 2026-08-25

### Added

- Causal calendar, prior-price lag and matching-slot rolling feature table.
- Feature-level availability provenance and explicit no-target-price policy.
- Deterministic ridge and histogram-gradient-boosting benchmark models.
- Time-based training, validation and held-out test periods.
- Walk-forward expanding/optional rolling-window refits with exact training-date logs.
- Validation-only model selection and separate validation/test metric rankings.
- Forecast-error comparison against daily, weekly, rolling-mean and ensemble baselines.
- Like-for-like held-out dispatch benchmarking over common complete forecast days.
- Cross-method realized margin, perfect-foresight capture and regret rankings.
- `forecast-ml` and `backtest-ml-dispatch` CLI commands.
- GitHub Actions wheel construction after the complete test suite.
- Leakage, split, refit, DST, common-horizon, settlement and CLI regression tests.

### Changed

- Package version increased from 0.3.1 to 0.4.0.
- Forecast metrics accept any explicitly supplied forecast column, enabling ML and naïve
  methods to use the same signed-price-safe calculations.
- Scikit-learn is now a direct runtime dependency.

### Validation

- All 42 automated tests pass.
- Future-price mutations cannot change earlier ML predictions.
- Hourly and quarter-hour DST behavior remains valid.
- Synthetic fixtures test engineering behavior only and provide no investment evidence.
- The production HEnEx parser accepted the official English v01 result workbooks for
  24 and 25 August 2026: 96 quarter-hour intervals per day, 192 contiguous intervals,
  no missing prices and no quality errors. Raw hashes are recorded in the official-data
  acceptance report; the workbooks are not bundled.

### Still pending

- Private-token ENTSO-E production acceptance, official-source reconciliation and
  multi-year Greek market benchmarking.
- Publication-time validation before any exogenous feature is admitted.
- Degradation state evolution, project finance, Monte Carlo and user interface.

## [0.3.1] — 2026-08-25

### Fixed

- Forecast-dispatch summaries now disclose every market day excluded because the
  selected forecast is incomplete.
- Full requested-period forecast coverage is retained instead of being recalculated as
  100% after incomplete days are removed.
- Spring-DST daily-persistence gaps are reported correctly as one missing hourly
  interval or four missing quarter-hour intervals.

### Added

- Separate full-period and backtested-only forecast metrics.
- Evaluation/backtest day and interval counts, coverage fractions, missing interval
  count, and structured excluded-day details.
- Hourly and quarter-hour spring-DST regression tests plus an ensemble-completeness test.
- NumPy as an explicit direct runtime dependency.

### Changed

- Package version increased from 0.3.0 to 0.3.1.
- ENTSO-E requests now identify the current package version in their user-agent.

### Validation

- All 35 automated tests pass.
- Source and packaged-wheel test suites pass independently.
- Official-data acceptance remains pending.

## [0.3.0] — 2026-08-25

### Added

- Strictly causal daily-persistence, weekly-persistence and rolling-mean price baselines.
- Leakage-safe ensemble forecast using only prior market days.
- Walk-forward forecast metrics compatible with negative and zero prices.
- Negative-price precision and recall alongside MAE, RMSE, bias, WAPE and correlation.
- Day-by-day dispatch planned on forecast prices and settled on realized DAM prices.
- Like-for-like daily perfect-foresight ceiling, value-capture and regret outputs.
- Daily and interval-level forecast-dispatch backtest results.
- `forecast-naive` and `backtest-forecast-dispatch` CLI commands.
- Durable `AGENTS.md`, `PLAN.md` and `STATUS.md` project context.

### Changed

- Package version increased from 0.2.0 to 0.3.0.
- Perfect-foresight optimization now uses a negligible numerical throughput tie-breaker
  to avoid unnecessary zero-value cycling in economically degenerate solutions.
- README expanded with forecast and backtest workflows.

### Validation

- All 32 automated tests pass.
- Tests cover future-data mutation, spring DST, negative-price metrics, exact forecast
  value capture, deliberately wrong forecasts, and end-to-end CLI outputs.

### Still pending

- Official-data acceptance and multi-year official backtesting.
- ML price forecasts benchmarked against the v0.3 naïve baselines.
- Degradation state evolution, project finance, Monte Carlo and user interface.

## [0.2.0] — 2026-08-24

### Added

- Mixed-integer perfect-foresight Greek Day-Ahead Market dispatch optimizer.
- Grid-meter charge and discharge accounting with separate one-way efficiencies.
- Power, energy, SOC, availability, grid-limit and terminal-SOC constraints.
- Binary charge/discharge exclusivity, including correct behavior at negative prices.
- Optional self-discharge and daily equivalent-cycle limits.
- Buy fees, sell fees and degradation-throughput costs.
- Interval schedule and auditable aggregate margin decomposition.
- `optimize-perfect-foresight` command-line workflow.
- Illustrative 50 MW / 100 MWh battery configuration.
- GitHub Actions test workflow for Python 3.12.

### Changed

- Package version increased from 0.1.0 to 0.2.0.
- README expanded with dispatch conventions, usage and limitations.
- Data quality now rejects gaps or overlaps between consecutive UTC intervals.
- Availability arrays remain aligned when input price rows are unsorted.

### Validation

- All 24 automated tests pass.
- A 744-interval synthetic engineering benchmark solved to optimality in the
  development environment. It is not an official-data or investment result.

### Still pending

- Live validation with a user-supplied HEnEx workbook or private ENTSO-E token.
- Real HEnEx-versus-ENTSO-E overlap comparison.
- Forecast-based dispatch, degradation state evolution, financial modeling,
  Monte Carlo stress testing and user interface.

## [0.1.0] — 2026-08-24

### Added

- Canonical Greek Day-Ahead Market interval schema.
- ENTSO-E A44 client and HEnEx workbook parser.
- DST-safe UTC, market-clock and Greece-clock timestamps.
- Data quality and official-source comparison tools.
- Deterministic, clearly labelled synthetic fixtures for tests and demos.
