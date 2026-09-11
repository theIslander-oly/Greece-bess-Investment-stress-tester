# Limitations and required cautions

## Interpretation

- This is research and pre-feasibility software, not financial advice or an investment-grade
  study.
- Perfect foresight is a gross-margin ceiling, not expected or achievable revenue.
- Historical replay and forecast backtests do not establish future profitability.
- Synthetic demonstrations test software behavior; they are not market evidence.

## Market coverage

- Only Greek Day-Ahead Market energy arbitrage is modeled.
- The replayed 2020-2026 history predates operating battery competition: storage units were
  only integrated into the Greek Day-Ahead and Intraday Markets in April 2026. As the
  tendered, availability-supported fleet (about 1 GW awarded in the 2023-2024 auctions) and
  merchant projects enter operation, price spreads are widely expected to compress, so
  historical replay tends to overstate what a future merchant DAM-only battery could earn.
- Balancing-market participation and state availability-support payments — major revenue
  components for real Greek battery projects — are excluded and would require their own
  data-acceptance track before inclusion.
- Price taking and full acceptance of planned quantities are assumed.
- Intraday, balancing, reserves, imbalance exposure, route-to-market constraints, taxes,
  subsidies, permitting, licensing and grid feasibility are excluded.
- The legality and practical feasibility of a specific project require current Greek legal,
  market-access, licensing, grid-connection and contractual review.

## Data

- The accepted private HEnEx history from 1 November 2020 through 25 August 2026 passes
  continuity, duplicate, DST and price-preservation checks; it is not committed to Git.
- In 980 historical intervals, one or two cross-border asset rows differ from the dominant
  Greek-zone MCP by EUR 0.01/MWh. The bounded consensus is retained and explicitly flagged;
  larger or ambiguous disagreements remain errors.
- HEnEx incremental daily discovery depends on a website asset-catalog layout rather than a
  documented data API and may need maintenance when the site changes.
- **ADMIE load and RES forecasts are out of scope** (decision entry 2026-09-01). No exogenous
  ADMIE variable may enter any forecast, feature set, dispatch plan or reported result.
  Forecasting uses causal price-history features only. No ADMIE data was ever parsed, so this
  removes a candidate input and changes no accepted figure.
- What the ADMIE work did establish, and no more: the live catalog and a 26-28 August 2026
  retrieval confirm `ISP1DayAheadLoadForecast`, `ISP1DayAheadRESForecast`,
  `ISP2DayAheadLoadForecast` and `ISP2DayAheadRESForecast` as retrievable day-ahead forecast
  filetypes. That is names and non-empty discovery. Publication before auction closure was never
  established, no file format was ever accepted, and no timing audit was ever run over the
  confirmed filetypes against a verified closure.
- The retrieval client and the publication-timing audit are retained and unused. They are the
  executable form of the refusal rather than a capability in service: `audit-admie-publication-timing`
  still checks only a *declared* gate closure, cannot check that declaration against the market
  rules, and the repository still refuses to declare it on the operator's behalf. Its ordinary
  evidence would be the provider's own publication timestamp read after the fact, which a restated
  or backdated timestamp would defeat; only a retrieval performed before the closure witnesses
  availability independently, and such witnesses accumulate one delivery day at a time. Reversing
  the exclusion needs that declaration, a contemporaneous audited window, format acceptance and a
  new dated decision.
- The ENTSO-E series is reconciled against HEnEx for 1 November 2020 through 25 August 2026, with
  one 29 October 2023 interval differing by EUR 0.01/MWh. ENTSO-E A44 `A03` documents state a
  price once and imply its repeats; those implied intervals are materialized and flagged, not
  interpolated.
- Official publication revisions, terms and formats may change. Accepted artifacts are to be held
  outside Git as encrypted release assets, and are fingerprinted by custody records committed
  under `docs/custody/`. The two are distinct: a committed record is a fingerprint, not a durable
  copy. The operator upload is not verified complete in the repository record, and this repository
  does not track live GitHub release state, so custody is not recorded as complete. Once a stored
  copy can be verified against its record, a revision is detected rather than silently adopted;
  the encryption key is consequently part of the custody chain, and a lost key forces a
  re-retrieval that may not reproduce the accepted baseline.
- A custody record proves that a stored copy is the accepted artifact. It says nothing about
  whether that artifact supports any analytical or investment conclusion.
- Missing official prices are not silently interpolated; this can make a run incomplete.
- The run-manifest contract enforces that a recorded result carries its label, its declared
  kind and the standing exclusions. It does not check that the label is the right one for the
  arithmetic performed, and it cannot stop a consumer that reads the carried summary directly
  from presenting a figure without its projection.

## Forecasting and backtests

- Seasonal bootstrap paths reuse historical price blocks and are synthetic scenarios, not
  forecasts, probability-calibrated samples or evidence of future market behavior.
- Meteorological-season matching is a coarse dependence assumption. Sparse histories or unusual
  DST block positions can leave no compatible source block, which fails explicitly.
- The bootstrap foundation does not model structural change, outages, cannibalisation, spreads,
  or negative-price shocks, and does not produce percentiles or loss probabilities.
- The bootstrap samples one declared source era and cannot mix delivery regimes. Neither era of
  the accepted history is a good basis on its own: the quarter-hour era (1 October 2025 to
  25 August 2026) is the operating regime but contains exactly one occurrence of each
  meteorological season, so resampling it expresses no inter-annual variation at all, and its
  autumn is only 61 days; the hourly era (1 November 2020 to 30 September 2025) spans five or
  six occurrences of every season but is a superseded delivery regime whose blocks can only be
  mapped onto hourly target days. The era is a declared judgment about relevance and carries no
  probability.
- Block-candidate scarcity is reported, not corrected. A minimum candidate count of 1 means
  every path repeats the same source block at that position, which is a property of the chosen
  era rather than of the random seed.
- Bootstrap dispatch knows every price within each synthetic path and is therefore only a
  gross-margin upper bound. Paths are solved independently with shared assumptions; no path
  probability, percentile, ranking, degradation, finance or investment conclusion is produced.

- Current ML models use calendar and historical prices only; validated weather, demand, fuel,
  renewable and interconnector forecasts are not yet included.
- The Greek DAM moved from hourly to quarter-hour delivery on 1 October 2025. Persistence lags have
  no matching wall-clock slot on that day, and models trained on hourly history forecast
  quarter-hour delivery later in the held-out test period. This is disclosed rather than corrected.
- Accepted historical dispatch assumes constant full availability, and no auxiliary-load path
  exists, so the accepted official margins do not reflect unavailability. Declared availability
  schedules apply to synthetic bootstrap-path dispatch only; the accepted replay has not been
  re-run under one.
- The daily-composed perfect-foresight mode restores the configured SOC at every day end, so
  it is at or below the single full-horizon bound by construction. Neither is achievable
  revenue; the composed mode exists because it is the ceiling the forecast backtests are
  measured against and the only basis on which a trade cannot span a year boundary.
- Daily backtests restore initial SOC at day end and do not optimize energy across days.
- Daylight-saving slot differences can make persistence forecasts incomplete; exclusions are
  disclosed.
- Forecast accuracy does not guarantee dispatch value, and backtested value does not guarantee
  executable bids or settlement outcomes.

## Battery model

- Fade rates, warranty thresholds and costs are illustrative until replaced by OEM and EPC
  evidence.
- Linear additive degradation omits temperature, C-rate, depth-of-discharge bins, SOC dwell,
  nonlinear knees and cell dispersion.
- Cohort throughput allocation is proportional, not a rack-level controller simulation.
- Availability and efficiency are assumptions rather than a full auxiliary-load and outage
  model.

- Stored-energy allocation and energy made unavailable by fade are proportional approximations.
  Empty additions may require grid charging; replacement below minimum SOC requires explicit
  commissioning energy or an admissible SOC range.

## Finance

- Inputs remain illustrative until supported by project-specific EPC, grid, O&M, insurance,
  land, market-access and decommissioning evidence.
- Results are unlevered and pre-tax; debt, tax, subsidy, inflation-basis consistency and working
  capital require separate treatment.
- Finance does not repair or extrapolate incomplete operating paths.
- IRR is withheld when uniqueness cannot be established; sampling alone cannot exclude close
  or tangent roots. The numerical solution range is finite even for certified unique roots.
- Legacy net-only inputs cannot reveal an unknown wear-cost basis and are treated as cash margin.
- The integrated study inherits the proportional fade approximation: energy a strategy carries
  across a day boundary shrinks with that strategy's own usable capacity, and the difference is
  recorded as an unavailability loss rather than modelled electrochemically.
  Rerun affected results under the corrected cash, energy and break-even conventions; existing
  recorded results are not retroactively recomputed.
- Scenario probability estimates are excluded unless an independently validated calibration
  methodology is approved; v0.7 reports only non-probabilistic ranges across named scenarios.

## Software

- Solvers and third-party package behavior can vary by platform and version.
- The test suite fails on warnings attributed to `greek_bess` or to the project's own tests, and
  reports warnings attributed to a dependency without failing. A warning a dependency raises
  entirely within its own frames is therefore visible but not gated, and dependencies are
  installed from ranges rather than pinned, so a passing suite is evidence about the resolved
  versions of the day and not about every version in range.
- The command-line interface is research-oriented; no user interface exists yet.
- The first GitHub snapshot imports already completed v0.1-v0.6 work, so earlier development
  history is represented by implementation reports rather than fabricated Git commits.

## Per-delivery-year decomposition limitations

- A delivery year is a regrouping of an already-accepted replay, not new evidence. Splitting a
  historical upper bound by year does not make any year's figure a forecast, an expectation or
  a probable outcome for a comparable future year.
- Years of unequal coverage are not comparable on totals alone. Partial years are flagged and
  carry their market-day count; per-market-day figures are within-period averages and are
  deliberately not annualized.
- A year's figures are conditioned on that year's market regime, on the illustrative battery
  and fee assumptions, and on the fixed availability of 1.0. A high-spread year says what the
  replayed battery would have captured in that regime under those assumptions, not what a
  battery operating in that year would have earned.
- The 2020-2026 accepted history mixes hourly and quarter-hour delivery, with the change on
  1 October 2025. Years on either side of that change differ in interval structure as well as
  in price regime, and the per-year interval counts by resolution disclose this rather than
  correcting for it.
- Annual capture ratios compare a method against the ceiling on the days that method
  backtested. Methods exclude different days for structural reasons, so cross-method
  comparison uses the common-day table, whose recorded ceiling spread is the like-for-like
  evidence.
- No probability, percentile, loss metric or ranking of delivery years is produced, and a year
  ordering by margin is not a ranking of anything about the future.

## Spread-compression limitations

- The compression factor is a declared judgmental scenario, not an estimate, a calibration or a
  probability-weighted view. Nothing in the replayed history estimates it: the 2020-2026 record
  predates operating battery competition in the Greek DAM almost entirely, so it contains no
  episode from which a competitive spread response could be inferred. A factor of 0.7 is a
  statement of what to examine, not a claim that spreads will compress by 30 %.
- The transformation represents cannibalisation pressure only in the loose sense that
  cannibalisation compresses spreads. It is not a causal model of entry, bidding behaviour,
  fleet size or market clearing, and it says nothing about when or whether compression occurs.
- Compression scales every within-day range by the same factor. Real spread compression would
  not be uniform across days, seasons, hours or price regimes, and it would interact with the
  negative-price and duck-curve structure the accepted history shows growing since 2023.
- The daily reference level is a declared choice with no default. A daily mean preserves each
  day's mean exactly; a daily median does not, and the summary reports the resulting daily-mean
  shift. Neither is a claim about which level a compressing market would converge on.
- Zero and negative prices are preserved and never clipped. Because compression pulls prices
  toward the daily reference, intervals can cross zero and change sign; the count is reported.
  A scenario that materially changes the number of negative intervals is changing the market's
  character, not only its spread, and should be read accordingly.
- Spread widening is out of scope, so the accepted factor range is closed at 1. This is a
  deliberate scope limit, not a judgment that widening is unlikely — the per-delivery-year
  decomposition found mean daily range rising every year since 2023.
- Compressed paths are synthetic scenarios. No likelihood, percentile, loss metric or ranking
  is attached to a factor, and no dispatch, finance or investment conclusion follows from one.

## Availability and outage-path limitations

- An availability schedule is a declared judgment, not an outage rate, an availability
  guarantee, a maintenance plan or a reliability model. No likelihood, frequency or expected
  unavailability attaches to it, and none can be inferred from a reported margin.
- Outages are never sampled, because nothing calibrates a rate: there is no operating history
  for a Greek merchant battery, no fleet maintenance record and no warranty claim series in
  scope. A borrowed rate from another asset class would be a number dressed as evidence.
- Timing is the whole content of the scenario, and the model gives no help choosing it. The same
  outage costs almost nothing in a low-spread week and a great deal in a high-spread one, so a
  schedule describes one placement and nothing more. Comparing two placements is comparing two
  judgments.
- Availability scales grid-side charge and discharge power only. Auxiliary load, state-of-charge
  drift while unavailable, partial-string derating, restart behaviour, degradation effects of an
  outage and any cost of the outage itself are not modelled.
- A perfect-foresight dispatch knows the declared outage in advance and positions the battery
  for it. A real unplanned outage arrives without notice, so a margin reported under a declared
  outage remains an upper bound, and it is a weaker bound for unplanned outages than for planned
  maintenance.
- A window is applied whole to every interval it covers, and a boundary inside an interval is
  refused rather than prorated. Schedules are therefore expressed at the market's own interval
  resolution and cannot represent sub-interval events.
- Declared schedules are integrated into bootstrap-path dispatch only. The degradation-aware and
  forecast-dispatch backtests do not yet accept one.

## Scenario-ensemble limitations

- A range across named scenarios is a range across judgments, not a distribution. The scenarios
  carry no weights and no likelihoods, so no probability, percentile, expected value, loss metric,
  ranking or central case is produced, and none can be inferred from the reported minimum and
  maximum. A midpoint of the range is not a central case.
- The range is bounded by the scenarios the caller chose. It says nothing about outcomes outside
  that set, and adding or removing a scenario moves the range without any new evidence. A wide
  range describes disagreement between named judgments; a narrow one is not confirmation.
- Each end of a range is a perfect-foresight gross-margin upper bound on synthetic bootstrap
  paths and inherits every limitation of the bootstrap, the transformation and the dispatch that
  produced it. A range of upper bounds is still a range of upper bounds.
- Ranges are reported per bootstrap path and never aggregated across paths, because a total or an
  average over sampled paths would read as an expectation the uniform block resampling cannot
  support. A per-path range is not a statement about any particular future.
- Scenarios solved under different battery parameters, terminal-energy constraints, source eras
  or path identities are refused rather than reconciled. This is a refusal to approximate, not
  evidence that such a comparison would otherwise be meaningful.
- The price transformation and the availability schedule are expected to differ between
  scenarios: they are the judgments under examination. A range across them therefore mixes two
  kinds of judgment, and reading a spread without reading the provenance on both ends can
  attribute an outage cost to a price scenario or the reverse.
- The report composes recorded summaries. It cannot detect that two scenarios were produced from
  different price histories if their recorded bases agree, so the summaries supplied must be the
  ones the runs actually emitted.

## Declared negative-price-event limitations

- Event timing, duration and depth are user declarations, not estimates. The transformation
  gives no evidence about how often negative prices occur, how long they last, how deep they are
  or which future intervals they affect.
- Applying the same named windows to every bootstrap path is a controlled sensitivity, not a
  calibrated joint price process. The bootstrap seed reproduces the input paths; it does not
  make the event declaration probable.
- An absolute replacement price deliberately overwrites the sampled price inside a named window.
  Results therefore depend directly on the selected timing and depth and cannot support a
  forecast, expected count, likelihood, percentile, ranking or investment conclusion.
- Windows operate only at the path's delivery-interval resolution. Sub-interval events are
  refused, not prorated, and interactions with separate transformations are neither composed nor
  silently resolved by this command.

## Price-level shock limitations

- The additive constant is a user-configured sensitivity, not an estimated price process or a
  probability-calibrated market view.
- Applying one shift to every interval does not change within-path spreads or temporal shape and
  does not represent negative-price events, outages, cannibalisation or structural market change.
- Because spreads are unchanged, a constant level shift alters battery arbitrage economics only
  through round-trip efficiency losses and per-MWh fees; it is therefore a weak stress for
  storage value, and spread transformations are the economically first-order sensitivity.
- Shocked paths are not forecasts, expected prices, investment evidence or dispatch/finance
  results. No likelihood, percentile, loss metric or ranking is attached to them.


## Point-in-time join limitations

Passing the v0.9.2 join establishes only that the selected synthetic-test value obeyed the declared as-of rule and is traceable to identified bytes. It does not establish that a real feature is correct, representative of Greece, available under a defensible market cutoff, accepted for forecasting or useful for settled battery value. The three real operator declarations are absent, so no real join result, model, manifest or acceptance document exists. Coarser containment is an explicit broadcast rather than interpolation; finer-to-coarser aggregation remains refused. ADMIE-originated forecasts remain excluded by every route.

Evidence-grade admission cannot be used to select an older revision: the latest pre-cutoff
revision is selected first, and an inadmissible selected grade excludes the day. This prevents
stale cherry-picking but does not validate the provider's revision policy or publication record.

## Fundamentals ablation limitations

The v0.9.3 ablation is validated entirely on synthetic fixtures. It has produced no benchmark
figure, because the three operator declarations do not exist and therefore no accepted feature
table exists; nothing here is evidence about weather, about Greek prices or about battery value.

What the ablation could establish, once run on an accepted feature table, is narrow. It measures
price error on one held-out period, under one declared cutoff, one feature set and one battery-
independent forecast comparison. Price error is not dispatch value, and the accepted evidence
already shows the two can disagree: a naive `rolling_mean` has worse RMSE than `ridge` and
captures more value. A better RMSE in the challenger arm would therefore not, on its own, be a
result about revenue.

The comparison is also one draw. One split of a non-stationary history is not a distribution, and
nothing in the summary is a probability, a confidence interval or a rate. The paired daily
differences are reported so a reader can inspect them; no sampling-variability statistic is
computed, because adding one would be a separate deliberate decision about vocabulary rather than
a side effect of this milestone.

Reducing the evaluation to the days both arms can be run on protects the comparison but shrinks
it, and the reduction is not random: days are excluded because a feature was unavailable, which
may correlate with the weather the feature describes. The control's metrics on its unreduced
calendar are recorded alongside so the size of that reduction is visible, but the possible
selection effect is not corrected and cannot be from within the run.

The exploratory rule is deliberately strict: a meteorological season counts only when every one
of its days is a common held-out quarter-hour day. A run that falls short is labelled exploratory
and supports no general conclusion, whatever its numbers say.

## Settled fundamentals dispatch limitations

The v0.9.4 comparison is validated entirely on synthetic fixtures and has produced no figure, for
the same single reason as v0.9.1 through v0.9.3: the decision cutoff, the decision lead and the
sampling geography are undeclared, so no accepted feature table exists to benchmark against.
Nothing here is evidence about weather, about Greek prices or about battery value.

What the comparison could establish once run on an accepted table is narrower than it may look.
It measures euro settled on one held-out period, under one battery, one declared cutoff and one
feature set, against a market history that almost entirely predates operating battery
competition. Storage units entered the Greek Day-Ahead and Intraday Markets only in April 2026,
so an incremental margin measured here describes what the information would have been worth in a
market without batteries, not what it will be worth in one with them.

An incremental margin is a difference of two numbers that each carry the standing exclusions, and
the difference carries them too. It is not expected revenue, not a rate per day or per MW, and
not transferable to a different battery, cutoff or period. The paired daily differences are
published so a reader can inspect them directly; their sign counts and total are recorded, and no
sampling-variability, dispersion or significance statistic is derived from them. One split of a
non-stationary history is one draw, and a positive total on it is not evidence that the sign
would recur.

The comparison inherits every limitation of the ablation that produced its forecasts, including
the non-random reduction to days both arms can be run on and the exploratory label, which it
carries verbatim and can neither strengthen nor retire. It settles only what the forecast
benchmark recorded, so a defect upstream is a defect here.

The dispatch itself is the project's standing model and no more: perfect price-taking acceptance
of every planned quantity, no bid acceptance, no imbalance exposure, no intraday or balancing
participation, no revenue stacking, and a terminal state restored at the end of every market day.
The terminal-SOC convention is required for the arms to be comparable at all, and it is a
modelling choice rather than an operating strategy: a real unit is not obliged to end each day
where it started, and a comparison run under a different convention would produce different
increments. No finance or degradation state is coupled to this comparison, by design.

## v0.9.5 transfer and execution limitations

Training and validation are entirely hourly, while the fixed test beginning 1 October 2025 is entirely quarter-hour. Hourly GFS values are broadcast across four test intervals and cannot represent within-hour weather variation. Wind-capacity weights proxy irradiance and temperature imperfectly. An official result remains exploratory unless common held-out quarter-hour days contain every day of a complete meteorological season. Custody and data acceptance establish identity and suitability, not forecast skill, future source stability, expected revenue, or investment value.

## Integrated study limitations

The study runner has been validated on deterministic synthetic prices alone and has produced no
official-history result. Nothing it has computed is evidence about Greek prices or about battery
value.

**What a completed study would and would not be.** A strategy's total is what that strategy's own
policy achieved over one declared historical window under illustrative cost assumptions. It is
not expected revenue, not a forecast, not investment evidence, and not a bound: the limits each
day begins with depend on what that strategy discharged earlier, so the aggregate is a simulation
in exactly the sense `METHODOLOGY.md` §5.1 sets out. A lifetime-optimal policy would be at least
as large.

**No ceiling spans the strategies.** A perfect-foresight ceiling is conditional on a physical
state, and from the second day onward the strategies hold different states. Each strategy's own
per-day ceiling and regret are recorded; no figure anywhere in the output is a ceiling for the
study, and none should be constructed by summing the per-day ones.

**The horizon is the window and nothing more.** Finance covers exactly the declared days. An
18-month study reports 18 months: it does not annualise, extrapolate to a project life, or repeat
a year. A rate of return computed over a short window is dominated by that window's price regime
and by the fixed costs allocated to it, and is not a project IRR.

**A comparison is only as good as the window it ran on.** One continuous window of a
non-stationary history is one draw. A strategy ranking on it is not evidence that the ranking
would recur, and no sampling-variability, dispersion or significance statistic is derived from
the daily differences.

**Scope.** Planners are the naïve forecast methods and perfect foresight; the ML and fundamentals
planners are not wired in. All strategies share one declared battery and one declared degradation
model, instantiated separately — a comparison of differently sized batteries is not expressible.
Multi-year extrapolation, a terminal-value model beyond the configured residual, intraday or
ancillary revenue, revenue stacking and any lifetime-optimal dispatch policy remain excluded, each
a scope change requiring its own decision.

**The standing dispatch assumptions still hold.** Price-taking acceptance of every planned
quantity, no bid acceptance, no imbalance exposure, and a terminal state restored at the end of
every market day. The terminal-SOC convention is required for the strategies to be comparable and
is a modelling choice, not an operating strategy.
