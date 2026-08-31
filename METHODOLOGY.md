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

ADMIE retrieval preserves publication time independently from delivery coverage. Candidate load,
RES, availability and interconnector variables are quarantined from forecast features until their
historical publication time is proven to precede the bid decision for the target market day. That
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

## 4. Forecast evaluation

Naive daily, weekly and rolling-seasonal baselines and the ML benchmarks are causal. For a
target day, no realized target-day price enters its features or model fit. Model selection uses
the validation period only; the held-out test period is reported separately. Forecast-planned
quantities are settled against realized prices and compared with a perfect-foresight solve under
the same physical and terminal-energy constraints.

MAE, RMSE, bias, median absolute error, WAPE, correlation and negative-price detection are
reported. MAPE is excluded because zero and negative prices make it misleading.

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

## 16. ADMIE pre-auction publication timing

The quarantine above is discharged, if at all, by an audit that reads ADMIE retrieval manifests
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

Acceptance here establishes publication timing only. It accepts no file format, schema or value,
demonstrates no forecasting skill, and does not lift the quarantine on its own; the audit summary
carries that exclusion in its own output. The policy is in
`docs/admie_publication_timing_policy.md`.

## 17. Validation

Code changes must pass Ruff, mypy, pytest and a clean wheel build. Tests use deterministic
synthetic inputs or small purpose-built fixtures. Official-data acceptance is recorded as
aggregate evidence and hashes without committing the source files. Detailed milestone methods
and test evidence are retained in `docs/implementation_report_v*.md`.
