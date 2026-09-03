# Methodology

## 1. Analytical chain

The project is intentionally modular:

1. acquire official price publications privately;
2. normalize them to a canonical interval schema;
3. audit completeness, timestamps, revisions and cross-source consistency;
4. calculate a constrained perfect-foresight dispatch ceiling;
5. generate causal price forecasts using information available before delivery;
6. plan dispatch on forecasts and settle the plan on realized prices;
7. evolve usable energy and power through degradation and augmentation cohorts;
8. transform a continuous operating path into explicit unlevered cash flows;
9. generate reproducible synthetic price paths for later stress scenarios (v0.7 foundation);
10. apply declared availability and outage schedules to those paths;
11. report non-probabilistic ranges of margin outcomes across explicitly named scenarios.

Each stage emits auditable interval, daily and summary outputs rather than only a headline
return.

## 2. Data and time

The canonical price observation contains UTC interval start/end, market-clock and
Europe/Athens timestamps, resolution, price, currency/unit, source, publication version,
retrieval metadata and quality flags. UTC is the unique key. Daylight-saving days are
validated against their expected 23/25 hourly or 92/100 quarter-hour intervals.

HEnEx workbook ingestion selects a single published market-clearing price per interval and
records the raw file SHA-256. The greatest published workbook revision is selected per delivery
day before parsing. Repeated asset rows must agree, except for a unique strict majority with at
most two one-cent cross-border rounding outliers; accepted cases remain interval-level quality
flags. Annual retrieval records outer and approved nested DAM ZIP hashes, member revisions and
coverage. Incremental daily discovery is used only for years not yet in the annual archive and
must pass the same parser and quality gates. ENTSO-E ingestion uses the A44 day-ahead document
type for the Greek bidding zone, honoring the declared curve type: an `A03` document states a
price once and implies it until the next declared position, so those intervals are materialized
and flagged rather than treated as missing. Overlapping normalized series can be compared interval
by interval, and a reconciliation derives its window from the accepted history so that both
sources cover identical market days.

ADMIE load and RES forecasts are **out of scope** (decision entry 2026-09-01), so no exogenous
ADMIE variable enters any forecast, feature set, dispatch plan or reported result. Forecasting
uses causal price-history features only. The retrieval client below preserves publication time
independently from delivery coverage and is retained as unused; the quarantine it served is
closed as never accepted rather than discharged. That
proof is executable rather than asserted, and is described in section 16.

Official raw files and normalized datasets are not committed. Reproduction depends on the
source register, commands, retrieval manifests, hashes and quality reports described in
`docs/data_sources.md` and `docs/official_data_retrieval.md`.

## 3. Dispatch

The perfect-foresight problem maximizes settled DAM energy value less configured fees and
degradation cost subject to:

- charge/discharge power and grid limits;
- usable energy and state-of-charge bounds;
- separate one-way charge and discharge efficiency;
- availability;
- a binary operating mode preventing simultaneous charge and discharge;
- optional daily equivalent-cycle limits; and
- explicit initial and terminal state of charge.

Grid import for charging and grid export for discharge are settled at the interval price.
Negative prices are preserved. Because all future prices are known, this result is labelled a
gross-margin upper bound.

### How the exclusivity constraint is solved

The binary operating mode is the only integer variable in the program, and it is load-bearing
for exactly one situation: a negative price with no headroom to charge into. There, being paid
to import is reachable only by exporting at the same time to make room, and since the round
trip returns less energy than it takes, the pair nets a profit that the optimizer will take
unless something forbids it.

Every other interval never wants to do both, so the program is solved relaxation-first by
default (`"solve_strategy": "relaxation_first"`). The continuous relaxation drops the binary,
which enlarges the feasible set and therefore returns an upper bound on the mixed-integer
optimum. If that relaxed solution happens to charge or discharge but never both in one
interval, a mode value satisfying every dropped constraint exists for every interval, so the
relaxed solution is itself mixed-integer feasible — and a feasible point attaining an upper
bound on the optimum is an optimum. It is returned unchanged. Only when the relaxation actually
violates the exclusivity it dropped is the mixed-integer program solved.

**The reported answer is the mixed-integer optimum on either path.** This is an exactness
guarantee, not a tolerance: the shortcut is taken only in the case where it is provably the
same answer. Setting `"solve_strategy": "mixed_integer"` skips the relaxation and always solves
the integer program, which is useful for verifying that claim rather than for using the tool.

The summary records which path was taken (`solve_path`), how many intervals of the relaxation
were simultaneous (`relaxation_simultaneous_interval_count`), and, for daily composed solves,
how many market days needed the integer program (`mixed_integer_solve_count`).

On one year of quarter-hourly synthetic prices (35,136 intervals, 50 MWh / 25 MW), measured on
the CI image:

| Prices | Solve | `mixed_integer` | `relaxation_first` | Change |
| --- | --- | --- | --- | --- |
| No negative | Full horizon | 39.0 s | 4.3 s | 9.1× faster |
| No negative | Daily composed | 21.2 s | 12.3 s | 1.7× faster |
| 5% negative | Full horizon | 60.6 s | 63.7 s | 5% slower |
| 5% negative | Daily composed | 21.7 s | 13.8 s | 1.6× faster |

Margins agreed to within one floating-point unit in the last place in all four cases — a
relative difference of 2e-16, nine orders of magnitude inside the solver's own
`mip_relative_gap` of 1e-7, and arising from summation order over equally-valued optima rather
than from any difference in the optimum found.

The single adverse case is the one where the relaxation is rejected and its cost is wasted: one
full-horizon solve over a whole year containing negative prices, where 34 simultaneous
intervals out of 35,136 were enough to force the integer program. The daily composed
convention, which is what the forecast backtests are measured against, does not have this
problem: with 5% negative prices only 26 of 366 market days needed the integer program, and the
other 340 took the relaxation.

## 4. Forecast evaluation

Naive daily, weekly and rolling-seasonal baselines and the ML benchmarks are causal. For a
target day, no realized target-day price enters its features or model fit. Model selection uses
the validation period only; the held-out test period is reported separately. Forecast-planned
quantities are settled against realized prices and compared with a perfect-foresight solve under
the same physical and terminal-energy constraints.

MAE, RMSE, bias, median absolute error, WAPE, correlation and negative-price detection are
reported. MAPE is excluded because zero and negative prices make it misleading.

### 4.1 Fundamentals ablation

The v0.9.3 ablation answers one question — whether an independently validated exogenous input
improves a forecast — by holding everything else fixed. The control arm is the accepted ML
benchmark unchanged: the same two model families on the same calendar and price-history feature
set. The challenger arm is the same two families, the same fixed hyperparameters, the same seed
and the same refit cadence, with the accepted point-in-time feature columns appended. Both arms
walk forward through the same loop and refit on the same days, so a difference between them can
come only from the information the fit sees.

Both arms are measured on one calendar. The evaluation set is the intersection of delivery days
complete for every naive baseline, for the control arm and for the challenger, and the control is
re-measured on that reduced calendar rather than credited with days the challenger could not be
run on. The control's metrics on its own unreduced calendar are recorded alongside, so the cost
of the reduction is visible rather than implied. A day missing any accepted feature is excluded
from every arm by the join's own named cause; its rows are dropped from the challenger's fit and
the dropped-interval count is recorded. No exogenous value is ever imputed: the pipeline's
imputer exists for the price-lag warm-up gaps, and the walk-forward loop refuses to fit or
predict when a column declared complete is not.

Within each arm the reported model is chosen on validation RMSE alone. Test metrics never select,
and the feature set, the split and the cutoff are never revised after a test run — any such
revision is a new benchmark under a new decision entry. Accuracy is additionally reported on
declared slices of the held-out days: by delivery year, by market-clock interval of day, by
declared price regime and by resolution era. The price-regime bands are declared, because which
price levels are worth separating is a judgment.

A benchmark identifies its inputs rather than describing them. It declares the digest of the
joined feature frame it fits on, the cutoff schedule, the decision lead and the admitted evidence
grades, and refuses to run unless every one equals what the join recorded and the frame hashes to
the digest its summary states. A run that admits the quarantined `assumed` grade, or whose common
held-out days do not cover a complete meteorological season of quarter-hour deliveries, is
labelled exploratory and carries the suffix saying so; the manifest contract refuses a summary
that admits the quarantined grade while declaring itself otherwise.

Price error is the secondary measure here and is reported because it explains a mechanism. The
primary measure is realized settled dispatch value, computed by the settled comparison of section
4.2 rather than by the ablation itself.

### 4.2 Settled fundamentals dispatch comparison

The v0.9.4 comparison answers the question the project actually asks: on the same delivery days,
under the same battery and the same realized prices, did the fundamentals-augmented model settle
more value than the identical model on price history alone? Price error and settled value are
reported together and neither substitutes for the other; the accepted evidence shows they can
disagree, since `rolling_mean` has a worse RMSE than `ridge` and captures more value.

Each named arm is planned from its own forecast through the same daily solve the accepted ML
dispatch benchmark uses, and settled at the realized prices of the same intervals. The evaluation
set is the held-out subset of the days the ablation recorded as common to every baseline and both
arms; the comparison never widens that set and never re-derives it. A method column carrying a
gap on one of those days contradicts the record and is refused rather than excluded, because an
exclusion at this stage would give two arms different calendars.

Equivalence is asserted and recorded, not assumed. One battery configuration plans every arm, its
terminal SOC must equal its initial SOC so that every day starts and ends in the same energy
state, one realized price series settles every arm, and the perfect-foresight ceiling is checked
identical across arms to an absolute tolerance of `1e-6` EUR. A spread above that is refused by
naming the two arms and their ceilings. What every arm shared — the battery parameters, the
terminal-energy convention, the settled interval range, the common-day identity and its digest,
the shared ceiling, and the feature-set identity carried from the ablation — is written into the
summary as `equivalent_basis`.

The incremental figure is recorded by the producing module, never derived downstream: for each
challenger the difference against its own control on the common days, and separately against each
named baseline. The paired daily differences are written per comparison and per delivery day, and
the summary records their sign counts, their total and the largest daily gain and shortfall. No
interval, dispersion or significance statistic is computed from them. A dependence-preserving
option exists — a moving-block bootstrap of the paired differences, or a Diebold-Mariano-type
comparison — and either would be a statement about the sampling variability of a statistic rather
than a market probability; adopting one is a separate decision with its own wording, not a side
effect of this milestone. A challenger that settles less than its control is recorded under the
same labels as one that settles more, and the exploratory label is carried verbatim from the
ablation, which this comparison can neither strengthen nor retire.

## 5. Degradation

Each battery cohort ages separately through additive calendar and equivalent-cycle fade.
Beginning-of-day usable energy and power constrain that day's dispatch. Cell throughput is
allocated proportionally across active cohorts. Capacity additions, replacements, retirement,
retained-capacity thresholds and optional EFC warranty limits are explicit. The model is a
transparent approximation and not an electrochemical lifetime model.

## 6. Finance

The finance engine requires a continuous daily operating path and preserves its provenance
label. It itemizes initial CAPEX, fixed and variable OPEX, augmentation, decommissioning and
residual value. OPEX can escalate nominally. Cash flows use exact dates for discounting and
report unlevered NPV, IRR (with sign-change ambiguity handling), simple/discounted payback,
maximum initial CAPEX and market-margin break-even values.

No revenue is extrapolated across missing operating days. Tax, debt, subsidy and working
capital layers are not included.

## 7. Seasonal block-bootstrap foundation

The v0.7 foundation samples contiguous historical market-day blocks with replacement. An
explicit seed drives NumPy's deterministic generator. Candidate blocks must begin in the same
meteorological season as the target block, be calendar-contiguous, and match the target block's
exact vector of daily interval counts. The last block may be shorter. Each sampled block records
its target/source day boundaries, season, interval count, candidate count and selected candidate
index.

Target UTC and local timestamps are reconstructed from the target market days; sampled prices
are copied by physical interval order without scaling, smoothing or interpolation. Complete-day
and continuous-horizon validation occurs before sampling, and a target block fails when no
seasonal source block has a compatible 23/25-hour or 92/100-quarter-hour structure. Outputs are
labelled synthetic scenarios and are not forecasts or probability-calibrated market evidence.

### 7.1 Source era and resolution

Mapping a sampled block onto target days requires one delivery resolution, and the accepted
history holds two because the Greek DAM moved from hourly to quarter-hour delivery on
1 October 2025. A source era is a maximal contiguous run of market days at one resolution; a
resolution change or a gap in market days ends one. The bootstrap samples from exactly one era.

A history with one era needs no declaration. A history with several requires an explicit
declaration, with no default and no "most recent" rule, because a default would make the
sampled regime an accident of the input. The refusal lists the available eras and their
windows. The selected era is recorded in the run summary and on every provenance row, and days
outside it are absent from the candidate search, so no block can straddle a regime boundary.

The choice is a judgment about relevance and carries a cost either way: the quarter-hour era is
the operating regime but contains one occurrence of each meteorological season and therefore
expresses no inter-annual variation, while the hourly era spans five or six occurrences of every
season but is a superseded delivery regime. Minimum and median block-candidate counts are
reported so scarcity is visible. Resampling one resolution into another, blending eras and
attaching any likelihood to an era are all excluded. The full policy is in
`docs/bootstrap_source_era_policy.md`.

## 8. Additive bootstrap price-level transformation

The first shock layer accepts only complete canonical bootstrap paths. For configured shift
\(s\) in EUR/MWh, each interval price is transformed as \(p'_{i,k}=p_{i,k}+s\), where \(i\) is
the interval and \(k\) is the unchanged path ID. There is no random draw, clipping, flooring,
interpolation or calendar remapping. Consequently identical ordered inputs and configuration
produce identical results, and zero or negative shocked prices remain valid.

Because the shift is constant, within-path spreads are unchanged; dispatch schedules and gross
margins therefore respond only through round-trip efficiency losses and per-MWh fees. The
transformation is a level sensitivity, not a stress on the arbitrage opportunity itself.

Validation is performed independently for every path: canonical timezone-aware columns, unique
path/UTC keys, complete DST-aware market days, continuous intervals, one supported resolution and
non-missing prices are required. An interval audit table records the UTC key, path ID,
transformation ID, additive shift, original and shocked values, and input source/version. Outputs
are synthetic sensitivities and not forecasts or investment evidence.

## 9. Independent bootstrap-path dispatch

Every input path is validated independently for complete DST-aware market days, continuous
canonical UTC intervals, unique path/UTC keys, and retained synthetic/non-forecast provenance.
All paths must have exactly the same ordered canonical interval keys. One battery configuration
and one scalar or interval-aligned availability profile are then reused unchanged for every
independent full-horizon mixed-integer solve.

Power, energy, efficiency, exclusivity, grid, SOC, optional daily cycle, and terminal-energy
constraints therefore apply separately to every path; state never crosses path boundaries.
Outputs retain `path_id`, canonical interval identity, source labels, interval operations and
revenue decomposition. A separate table reports the existing optimizer summary for each path.
These are perfect-foresight upper bounds on synthetic paths, not expected revenues or forecasts.

## 10. Official operational acceptance

Before a stage is treated as exercised on real data, it is run over the complete accepted official
history and evidenced in aggregate only. Acceptance verifies the input artifact hash and provenance,
canonical timezone-aware identity, DST-aware market-day completeness across both resolution regimes,
duplicate/gap/overlap absence and signed-price preservation; then, for dispatch, solver identity and
status, constraint compliance restated independently from the published schedule columns, and
aggregate energy and margin components; then, for forecasting, a mutation audit proving no future
observation reaches an earlier target day, refit cutoffs preceding their forecast targets, exact
settlement against realized official prices, like-for-like ceilings on shared days, and coverage
with every excluded day attributed to a structural cause. Both paths must reproduce identical
results on an immediate second run. Interval prices and schedules are never recorded in the report.

## 11. Per-delivery-year replay decomposition

An accepted replay is decomposed into delivery years so that regime dependence is visible
rather than averaged away. The decomposition adds no model, market or transformation: it
regroups results the dispatch and backtest stages already produced.

A delivery year is the calendar year of the interval's CET/CEST market-day start. This is the
sense in which the Greek DAM has delivery years and the convention the committed custody
records use; grouping by UTC year instead places the interval beginning 31 December 23:00Z in
the earlier year, which is a different grouping of identical intervals rather than an error.

The perfect-foresight ceiling is decomposed from a schedule composed of independent daily
solves, so that no trade spans a year boundary and every interval's margin belongs
unambiguously to its own delivery year. A single full-horizon solve may charge in one
delivery year and discharge in the next, and is therefore not the basis for annual
attribution. The schedule must settle every interval at the price the supplied history
publishes; a difference means the schedule was solved on other data and the decomposition is
refused rather than reported.

Forecast capture is decomposed per method against that method's own backtested days, because
each method excludes different days for structural reasons, and separately over the days every
supplied method backtested, where the ceiling must be identical. The recorded spread across
methods on that common set is the like-for-like evidence. Annual error metrics are recomposed
from the daily tables by interval weighting: mean absolute error is interval-weighted and root
mean squared error is recomposed from interval-weighted squared daily values.

Every year carries its market-day count, its coverage against the calendar year and an explicit
partial-year flag. Per-market-day figures are within-period averages over the days present; no
annual figure is annualized, extrapolated or scaled to a full year, because doing so would
manufacture revenue the replay does not contain. Zero, negative and missing prices are counted
per year and never filled. No probability, percentile, loss metric or ranking of delivery years
is produced.

## 12. Bootstrap spread-compression transformation

The second shock layer transforms within-day spread rather than level. For a compression factor
\(f\in[0,1]\) and a declared daily reference level \(r_{k,d}\) for path \(k\) on CET/CEST market
day \(d\), each interval price is transformed as

\[p'_{i,k}=r_{k,d(i)}+f\,\bigl(p_{i,k}-r_{k,d(i)}\bigr).\]

A factor of 1 is the identity and a factor of 0 flattens each market day onto its reference
level. Every within-day range is scaled by exactly \(f\), which is the property the tests assert.

This is the economically first-order storage stress, and it is the transformation that
represents cannibalisation pressure. A causal cannibalisation model is not buildable from price
history alone: the replayed 2020-2026 history predates operating battery competition almost
entirely, so it contains no episode from which a competitive response could be estimated. The
compression factor is therefore a declared judgmental scenario, not an estimate, and carries no
probability, percentile or likelihood.

The reference basis is **declared with no default**, following the source-era precedent: a daily
mean preserves each day's mean exactly, so the transformation is a pure spread change; a daily
median does not, and the summary reports the resulting maximum absolute daily-mean shift so the
difference is visible rather than assumed away. Choosing the basis silently would hide the most
consequential assumption in the transformation.

Zero and negative results are preserved and never clipped or floored. Because compression pulls
prices toward the reference level, an interval on the far side of that level can cross zero and
change sign; this is a real consequence of compressing spread, not a defect, and the count of
such intervals is reported in the summary rather than suppressed. Spread widening — a factor
above 1 — is out of scope, so the accepted range is closed at 1.

Validation is performed independently for every path, sharing one contract with the price-level
transformation: canonical timezone-aware columns, unique path/UTC keys, complete DST-aware market
days, continuous intervals, one supported resolution and non-missing prices. Missing prices are
refused explicitly here rather than merely by the shared quality gate, because a missing price
would propagate through its market day's reference level and silently corrupt every interval of
that day. An interval audit table records the UTC key, path ID, market day, transformation ID,
compression factor, reference basis, the reference level applied, original and compressed values,
and input source/version. Outputs are synthetic scenarios and not forecasts or investment
evidence.

## 13. Declared availability and outage paths

Availability enters dispatch as a per-interval fraction scaling grid-side charge and discharge
power. A schedule is a declared baseline fraction \(a_0\) together with declared windows
\(W_1,\dots,W_m\), each carrying its own fraction \(a_j\); interval \(i\) receives

\[a(i)=\begin{cases}a_j & \text{if interval } i \text{ is covered by } W_j,\\ a_0 &
\text{otherwise.}\end{cases}\]

Windows may not overlap, so every interval has exactly one declared fraction.

Outage timing, duration and depth are judgmental scenario inputs and are never sampled. A
forced-outage rate would be a probability statement, and nothing calibrates one: no Greek
merchant battery has operated, and no fleet maintenance record or warranty series is in scope. A
schedule is a statement of what to examine, in the same sense as a compression factor. The
baseline fraction has no default, because `AGENTS.md` requires availability to be explicit and a
silent 1.0 would make full availability an accident of the input.

A window applies whole to every interval it covers, and a boundary falling strictly inside a
delivery interval is refused rather than prorated. Prorating would apply a schedule finer than
the one declared and rounding would apply a different one, so the only truthful options are to
refuse or to require an aligned boundary. Because the profile is built from the paths' own
canonical UTC keys, 23- and 25-hour market days and the quarter-hour regime are handled by
construction.

One schedule maps onto every path of a run, and paths that do not share one canonical interval
identity are refused. What differs between paths is the sampled price; the physical condition is
common, which is what keeps the paths comparable to each other.

The declared schedule is recorded by identity in the dispatch summary and travels with the
result, so a margin traces back to the outage assumption behind it rather than to an anonymous
array of fractions. Dispatch retains perfect foresight, so it positions the battery for a
declared outage and the resulting margin remains an upper bound.

## 14. Scenario-ensemble range reporting

The final v0.7 layer composes accepted outputs rather than computing new ones. Given two or more
scenarios, each of which is a bootstrap-path dispatch that has already been solved and recorded,
the report gives, for every bootstrap path \(k\) the scenarios share,

\[\min_{s\in S} m_{s,k},\qquad \max_{s\in S} m_{s,k},\qquad
\max_{s\in S} m_{s,k}-\min_{s\in S} m_{s,k},\]

where \(m_{s,k}\) is the settled net market margin of path \(k\) under named scenario \(s\).
Nothing is aggregated across paths: a total or an average over sampled paths would read as an
expectation, and uniform block resampling of a non-stationary history supports no such reading.

The scenario set \(S\) is supplied by the caller and every member is named. There is no default
scenario set and no implicit baseline; an untransformed replay is declared as a member like any
other, because a scenario the report supplies itself would be a judgment the reader never made.

A range across named scenarios is a range across judgments, not a distribution. No probability,
percentile, likelihood, expected value, loss metric, ranking or central case is produced. The
rule is executable rather than documentary: every emitted column and summary key is checked
against a list of excluded terms, and a match raises instead of being written.

Scenarios are combined only on an equivalent basis, and the basis is the asset and the sample:
battery parameters, the terminal-energy constraint, the selected source era and the path
identities must match across the ensemble, and a difference is refused with the mismatching basis
named. This is the standing invariant that strategies are compared only under equivalent physical
and terminal-energy constraints: a range taken across two different batteries or two different
source eras would report a modelling difference as if it were a scenario difference.

The price transformation and the availability schedule are on the other side of that line. They
describe the judgment under examination and are expected to differ, so they are carried as
provenance on every reported figure rather than checked as basis. An ensemble that refused a
differing availability schedule could never place a declared outage against a baseline, which is
the comparison an outage scenario exists to make.

Each reported figure carries its scenario name, the transformation method and parameters that
produced it, the source-era selection and the input run identity, so a range traces back to the
runs behind it.

The run summary records the per-path ranges themselves, not only the lowest, highest, widest and
narrowest figures across them (amended 1 September 2026). The recorded rows are a projection of
the same reduced frame the range CSV is written from, in the same path order, with nothing
rounded, converted or re-reduced; per-scenario provenance is recorded once under `scenarios` and
joined by scenario name rather than repeated on every path row. Recording them is what allows a
report to render a range without opening any file beside the run: a report reads a verified run
manifest and nothing else, so a range absent from the summary is a range no report can show.

## 15. Declared negative-price-event transformation

A negative-price event is defined at the resolution of the validated price path: one or more
whole market intervals. Each event declares an inclusive UTC start (a_j), exclusive UTC end
(b_j), and a strictly negative replacement price (q_j) in EUR/MWh. For path (k),

\[p'_{i,k}=\begin{cases}q_j & a_j\leq t_i<b_j,\\ p_{i,k} & \text{otherwise.}\end{cases}\]

The transformation applies the same declared windows to every path. Event identifiers, timing,
depth and transformation identifier have no defaults; `events: []` is the exact identity.
Windows must align with interval boundaries, cover at least one interval and not overlap. This
uses the smallest price unit the input supports and refuses rather than inventing sub-interval
settlement arithmetic.

Occurrence is never sampled or inferred. No frequency, fitted rate, probability, likelihood,
percentile, expected count, ranking, threshold search or calibration is accepted or reported.
The uniform bootstrap has no calibrated probability interpretation, so using it to decide when
an event occurs would add a probability statement the evidence cannot support.

Only explicitly named windows receive absolute negative replacement prices. This is distinct
from a constant level shift over the full horizon and from scaling every within-day deviation
around a reference. Existing zero and negative prices outside those windows remain numerically
unchanged, and no result is clipped or floored. Provenance has one row per path interval,
including untouched rows, while the summary records the full declaration, applied interval
counts, and negative and zero interval counts before and after. Outputs remain synthetic
deterministic scenarios, not forecasts, probabilities or investment evidence.

## 16. ADMIE pre-auction publication timing (retained, unused)

ADMIE load and RES forecasts were removed from scope on 2026-09-01 and the quarantine was closed
as never accepted, so this section describes tooling the project retains rather than a method it
applies. No audit was ever run over the confirmed filetypes against a verified gate closure, and a
passing audit would no longer admit any ADMIE field into forecasting.

The quarantine would have been discharged, if at all, by an audit that reads ADMIE retrieval manifests
and compares each file's publication time against a declared day-ahead gate closure, per filetype
and per delivery day. No forecast file is parsed by the audit; the question is availability in
time, not content.

The gate closure has no default and no built-in constant. It is declared as one or more dated
regimes, each stating a day offset, a local time, the clock that time is on and a required
reference to the market rule it comes from. A rule that changed during the audited history is
represented as a further regime; a delivery day earlier than the first declared regime is refused
rather than audited against a rule that was not in force for it, and a closure falling in a
daylight-saving gap or repetition is refused rather than resolved by a convention.

Evidence is graded, and the grades do not merge. A retrieval performed before the closure of the
day in question observed the file in the provider's catalog and witnesses its availability
contemporaneously. A publication timestamp read after the closure is the provider's assertion
about the past and is recorded as such. Publication exactly at the closure instant is treated as
late, since a tie is not evidence of availability before the decision.

For each accepted day the audit names the decision-time revision — the latest revision published
strictly before closure — and counts the revisions that superseded it afterwards. This is the
operative caution: reading "the published file" for a past delivery day ordinarily returns the
provider's latest revision, which is post-decision information even on a day that passes on
timing. A feature built from these files must read the decision-time revision by URL.

Acceptance here would establish publication timing only. It accepts no file format, schema or
value and demonstrates no forecasting skill, and the audit summary carries that exclusion in its
own output. It would also no longer admit any ADMIE field into forecasting: those forecasts are
out of scope, so the quarantine is closed rather than pending. The policy is in
`docs/admie_publication_timing_policy.md`.

## 17. Run manifest and report contract

Every result-producing module emits a summary. A recorded run wraps one of those summaries in a
versioned manifest that carries it verbatim and adds a stable projection: a declared result kind
from a closed registry, the basis that kind reports on, the required non-empty result label, the
producing command, the project version, the caller's declared inputs and the project's standing
exclusions.

The projection exists so that a consumer can read a result without knowing which module produced
it, and so that the requirement in `PROMPT.md` that outputs retain their source and limitation
labels through downstream analysis is enforced rather than remembered. A summary without a
non-empty label, or without the keys its kind guarantees, is refused.

The basis distinguishes what a figure describes: a historical replay upper bound, a historical
forecast backtest, a synthetic scenario, screening arithmetic, or data-acceptance evidence. The
same euro amount means something different under each.

The check on distributional terms is scoped to the result kinds that declare it, because the term
list bans claims about the distribution of outcomes rather than the words themselves; a settled
average input price, a model's mean absolute error and a publisher's median lead time are none of
them distributional claims. Where a summary declares the standing claims itself, the contract
verifies them rather than ignoring them.

A manifest is refused on read when its schema version, result kind or declared basis is not one
this build understands. Policy in `docs/run_manifest_contract.md`.

## 18. Validation

Code changes must pass Ruff, mypy, pytest and a clean wheel build. Tests use deterministic
synthetic inputs or small purpose-built fixtures. Official-data acceptance is recorded as
aggregate evidence and hashes without committing the source files. Detailed milestone methods
and test evidence are retained in `docs/history/implementation_report_v*.md`.


## 19. Point-in-time feature join

The v0.9.2 join validates complete canonical price days and the closed point-in-time feature schema before selecting anything. For each delivery day it resolves the declared gate closure minus the declared decision lead, admits only explicitly listed evidence grades, and selects per native feature interval the greatest `(published_at_utc, source_revision, source_document_id)` strictly before that cutoff. A publication at the cutoff is late. Later revisions remain in the input, are counted, and never supply a value.

Price intervals receive a selected feature only by containment of their UTC start in the feature's half-open delivery interval. Revision selection precedes evidence-grade admission: an older admissible revision cannot replace a newer, inadmissible pre-cutoff revision. Equal resolutions are marked `equal`; an hourly feature used for four quarter-hours is marked `broadcast_coarser_feature`; a finer feature is refused without a separately declared aggregation rule. If any declared variable-area pair does not cover every price interval, every feature value for the day remains absent and the day is excluded by named cause. Nothing is forward-filled, interpolated or imputed. The audit row behind every emitted value carries the source document, revision, raw-byte SHA-256, publication/retrieval/issue instants, effective grade, cutoff margin, resolution relation and the number of later revisions for that native feature interval.

## Fundamentals official-run order

The v0.9.5 workflow enforces: declaration validation; official-history and feature-table custody verification; strict publication-time availability audit; revision-aware point-in-time join without filling; DJF 2025–26 completeness preflight; forecast ablation from the accepted digest; and forecast-planned dispatch settled on realized prices using the unchanged 50 MW / 100 MWh battery. Hourly training and validation precede an entirely quarter-hour test, where each hourly GFS value is explicitly broadcast over four intervals. Missing, late, conflicting, interpolated, or inadmissibly graded observations cannot enter an accepted run.
