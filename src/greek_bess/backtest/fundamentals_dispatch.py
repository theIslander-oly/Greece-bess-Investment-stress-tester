"""Settled dispatch comparison for the v0.9 fundamentals ablation.

The forecast ablation of v0.9.3 answers a question about price error. This module answers the
one the project actually asks: on the same delivery days, under the same battery and the same
realized prices, did the fundamentals-augmented model *settle* more value than the identical
model on price history alone? The two questions have already been shown to disagree in this
repository — ``rolling_mean`` has a worse RMSE than ``ridge`` and captures more value — so
neither substitutes for the other, and the primary figure here is euro settled, not euro of
error.

The module is deliberately thin. It plans and settles through
:func:`~greek_bess.backtest.ml_dispatch._backtest_precomputed_forecast`, which is the accepted
path the ML dispatch benchmark already uses, so an arm run through here is the accepted
computation with a different forecast column and nothing else. What this module adds is the
comparison discipline around that path:

- **The days are the ablation's own.** The evaluation set is the held-out subset of the days
  the forecast benchmark recorded as common to every baseline and both arms. This module never
  widens that set and never re-derives it; a method column carrying a gap on one of those days
  contradicts the record and is refused rather than excluded, because an exclusion here would
  silently give two arms different calendars.
- **The comparison basis is recorded, not assumed.** One battery configuration plans every
  arm, one price series settles every arm, and the perfect-foresight ceiling is asserted
  identical across methods to a tolerance. The equivalence is written into the summary as
  ``equivalent_basis`` so a reader does not have to take it on trust.
- **The incremental figure is recorded here, never derived downstream.** A renderer must not
  subtract one recorded margin from another; the difference is a result, and results are
  computed by the module that owns the basis. Paired daily differences and their sign counts
  are recorded too, which is what this project reports instead of an interval it would have to
  call a probability.

Nothing here selects anything: the arms, the models and the days were fixed before any test
price was settled, and a challenger that settles less than its control is recorded exactly as
one that settles more.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..dispatch import BatteryDispatchConfig
from ..forecast.fundamentals import EXPLORATORY_LABEL_SUFFIX, FUNDAMENTALS_ARM_SUFFIX
from .forecast_dispatch import ForecastDispatchBacktestResult, ForecastDispatchInputError
from .ml_dispatch import _backtest_precomputed_forecast

FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL = (
    "Held-out like-for-like Greek DAM fundamentals forecast-dispatch comparison settled at "
    "realized prices on common days; historical research result, not expected investment "
    "revenue."
)

#: Tolerance on the assertion that every method faced the same perfect-foresight ceiling. It is
#: the tolerance ``ml_dispatch`` already applies to the same assertion, and it is absolute: the
#: ceiling is a sum of euro amounts from identical inputs, so anything above solver noise is a
#: defect rather than a rounding difference.
CEILING_TOLERANCE_EUR = 1e-6

#: The battery fields that describe the terminal-energy convention rather than the asset. They
#: are separated for the same reason ``stress/ensemble.py`` separates them: a comparison that
#: shared the asset but not the terminal-energy constraint would not be like for like, and a
#: reader needs to see the two groups distinguished rather than merged into one blob.
TERMINAL_ENERGY_FIELDS = (
    "energy_capacity_mwh",
    "soc_min_fraction",
    "soc_max_fraction",
    "initial_soc_fraction",
    "terminal_soc_fraction",
)

#: Summary keys the forecast benchmark must have recorded before its forecasts may be settled.
#: A dispatch result names the ablation it came from; it may not describe one.
REQUIRED_BENCHMARK_KEYS = (
    "result_label",
    "ablation_arms",
    "feature_set_sha256",
    "decision_cutoff_schedule_id",
    "decision_lead_minutes",
    "evidence_grades_admitted",
    "common_test_day_count",
    "is_exploratory",
)


class FundamentalsDispatchInputError(ForecastDispatchInputError):
    """Raised when a fundamentals dispatch comparison would not be like for like."""


@dataclass(frozen=True)
class FundamentalsDispatchBenchmarkResult:
    """Every settled interval, the daily results, the paired differences and the summary."""

    interval_schedules: pd.DataFrame
    daily_results: pd.DataFrame
    paired_differences: pd.DataFrame
    method_summaries: dict[str, dict[str, Any]]
    summary: dict[str, Any]


def backtest_fundamentals_dispatch(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    forecasts: pd.DataFrame,
    benchmark_summary: Mapping[str, Any],
    *,
    methods: Sequence[str],
) -> FundamentalsDispatchBenchmarkResult:
    """Settle every named arm over the ablation's held-out common days and pair the results."""

    arms = _arms(benchmark_summary)
    comparison_methods = _validated_methods(methods, arms)
    held_out = _held_out_common_rows(forecasts, comparison_methods, benchmark_summary)
    common_days = sorted(held_out["market_day"].unique())

    method_results: dict[str, ForecastDispatchBacktestResult] = {}
    daily_outputs: list[pd.DataFrame] = []
    for method in comparison_methods:
        result = _backtest_precomputed_forecast(prices, config, held_out, method=method)
        if result.summary["excluded_incomplete_forecast_days"]:
            raise FundamentalsDispatchInputError(
                f"Method {method} lost a held-out common day during settlement; the forecast "
                "table and its recorded common-day set disagree"
            )
        method_results[method] = result
        daily = result.daily_results.copy()
        daily.insert(0, "comparison_method", method)
        daily_outputs.append(daily)

    method_summaries = {
        method: result.summary for method, result in method_results.items()
    }
    ceiling, ceiling_spread = _shared_ceiling(method_summaries)
    daily_results = pd.concat(daily_outputs, ignore_index=True)
    pairs = _comparison_pairs(comparison_methods, arms)
    paired_differences = _paired_differences(daily_results, pairs)
    incremental = _incremental_rows(paired_differences, method_summaries, role="control")
    incremental_vs_baseline = _incremental_rows(
        paired_differences, method_summaries, role="baseline"
    )
    if not incremental:
        raise FundamentalsDispatchInputError(
            "No challenger arm was named beside its own control arm, so nothing here is an "
            "ablation. Name at least one "
            f"'<model>{FUNDAMENTALS_ARM_SUFFIX}' method together with '<model>'"
        )

    exploratory_causes = [
        str(cause) for cause in benchmark_summary.get("exploratory_causes", []) or []
    ]
    is_exploratory = bool(benchmark_summary["is_exploratory"])
    summary: dict[str, Any] = {
        "result_label": FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL
        + (EXPLORATORY_LABEL_SUFFIX if is_exploratory else ""),
        "comparison_methods": list(comparison_methods),
        "comparison_policy": (
            "Every arm is planned from its own forecast and settled at the same realized "
            "prices over the identical held-out delivery days the forecast ablation recorded "
            "as common to every baseline and both arms"
        ),
        "arm_membership": {
            "baselines": [m for m in comparison_methods if m in arms["baselines"]],
            "control": [m for m in comparison_methods if m in arms["control"]],
            "challenger": [m for m in comparison_methods if m in arms["challenger"]],
        },
        "common_backtest_day_count": len(common_days),
        "common_backtest_interval_count": int(len(held_out)),
        "first_common_backtest_day": str(min(common_days)),
        "last_common_backtest_day": str(max(common_days)),
        "perfect_foresight_margin_eur": ceiling,
        "maximum_ceiling_spread_eur": ceiling_spread,
        "equivalent_basis": _equivalent_basis(
            config, held_out, common_days, benchmark_summary, ceiling, ceiling_spread
        ),
        "dispatch_ranking": _dispatch_ranking(comparison_methods, method_summaries),
        "incremental_realized_margin_eur": incremental,
        "incremental_realized_margin_versus_baseline_eur": incremental_vs_baseline,
        "paired_difference_policy": (
            "One paired daily difference per common delivery day, recorded with its sign "
            "counts and its total. No interval, dispersion or significance statistic is "
            "derived from them: the differences are a series of historical outcomes on one "
            "period, not a sample from a distribution this project claims to know"
        ),
        "method_summaries": method_summaries,
        "feature_set_sha256": str(benchmark_summary["feature_set_sha256"]),
        "decision_cutoff_schedule_id": str(benchmark_summary["decision_cutoff_schedule_id"]),
        "decision_lead_minutes": int(benchmark_summary["decision_lead_minutes"]),
        "evidence_grades_admitted": [
            str(grade) for grade in benchmark_summary["evidence_grades_admitted"]
        ],
        "forecast_benchmark_result_label": str(benchmark_summary["result_label"]),
        "is_exploratory": is_exploratory,
        "exploratory_causes": exploratory_causes,
        "exploratory_causes_source": (
            "Carried verbatim from the forecast ablation. This comparison settles exactly the "
            "days that ablation recorded, so it can neither add nor retire a cause"
        ),
        "market_acceptance_assumption": (
            "Price-taking planned quantities are fully accepted; bid acceptance and imbalance "
            "exposure are excluded"
        ),
        "terminal_soc_policy": "Initial SOC restored at the end of every market day",
        "establishes_only_historical_settled_value": True,
        "is_probabilistic": False,
        "is_forecast": False,
        "is_investment_evidence": False,
    }
    return FundamentalsDispatchBenchmarkResult(
        interval_schedules=pd.concat(
            [method_results[method].interval_schedule for method in comparison_methods],
            ignore_index=True,
        ),
        daily_results=daily_results,
        paired_differences=paired_differences,
        method_summaries=method_summaries,
        summary=summary,
    )


def _arms(benchmark_summary: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Read the three arms out of the forecast benchmark rather than inferring them."""

    if not isinstance(benchmark_summary, Mapping):
        raise FundamentalsDispatchInputError("The forecast benchmark summary must be an object")
    missing = [key for key in REQUIRED_BENCHMARK_KEYS if key not in benchmark_summary]
    if missing:
        raise FundamentalsDispatchInputError(
            "The forecast benchmark summary is missing keys this comparison must carry "
            f"forward: {', '.join(missing)}. A dispatch result names the ablation it settled"
        )
    recorded = benchmark_summary["ablation_arms"]
    if not isinstance(recorded, Mapping):
        raise FundamentalsDispatchInputError("ablation_arms must be an object")
    arms: dict[str, tuple[str, ...]] = {}
    for name in ("baselines", "control", "challenger"):
        entry = recorded.get(name)
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("methods"), (list, tuple)
        ):
            raise FundamentalsDispatchInputError(
                f"ablation_arms.{name} must record the methods that arm produced"
            )
        arms[name] = tuple(str(method) for method in entry["methods"])
    if not arms["challenger"]:
        raise FundamentalsDispatchInputError(
            "The forecast benchmark recorded no challenger arm, so there is no ablation to "
            "settle"
        )
    # The pairing between a challenger and its control is carried by the naming convention the
    # ablation applies, and every later step relies on it. Checking it here rather than trusting
    # it means a hand-edited summary is refused at the doorway instead of silently pairing a
    # challenger with a method that is not the identical model on price history alone.
    unpairable = [
        method
        for method in arms["challenger"]
        if not method.endswith(FUNDAMENTALS_ARM_SUFFIX)
        or _control_of(method) not in arms["control"]
    ]
    if unpairable:
        raise FundamentalsDispatchInputError(
            "The forecast benchmark records challenger arms with no control counterpart: "
            f"{', '.join(unpairable)}. A challenger must be named "
            f"'<control>{FUNDAMENTALS_ARM_SUFFIX}' for a control arm the same run recorded"
        )
    return arms


def _validated_methods(
    methods: Sequence[str], arms: Mapping[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Refuse a method list that would produce an unpaired or unrecognised comparison."""

    named = tuple(str(method) for method in methods)
    if not named:
        raise FundamentalsDispatchInputError(
            "The comparison method list is empty and has no default; a dispatch comparison "
            "states which arms it settled"
        )
    duplicates = sorted({method for method in named if named.count(method) > 1})
    if duplicates:
        raise FundamentalsDispatchInputError(
            f"Comparison methods are repeated: {', '.join(duplicates)}"
        )
    known = {method for group in arms.values() for method in group}
    unknown = [method for method in named if method not in known]
    if unknown:
        raise FundamentalsDispatchInputError(
            f"The forecast benchmark recorded no arm producing {', '.join(unknown)}. "
            f"Recorded methods: {', '.join(sorted(known))}"
        )
    unpaired = [
        method
        for method in named
        if method in arms["challenger"] and _control_of(method) not in named
    ]
    if unpaired:
        raise FundamentalsDispatchInputError(
            "Every challenger must be settled beside its own control arm, and these were named "
            f"without it: {', '.join(unpaired)}. Comparing a challenger against anything but "
            "the identical model on price history alone is not the ablation"
        )
    return named


def _control_of(challenger: str) -> str:
    return challenger[: -len(FUNDAMENTALS_ARM_SUFFIX)]


def _held_out_common_rows(
    forecasts: pd.DataFrame,
    methods: Sequence[str],
    benchmark_summary: Mapping[str, Any],
) -> pd.DataFrame:
    """Take exactly the held-out days the ablation recorded as common, and refuse any gap."""

    required = {"delivery_start_utc", "market_day", "split", "is_common_day", *methods}
    absent = sorted(required - set(forecasts.columns))
    if absent:
        raise FundamentalsDispatchInputError(
            f"Forecast table is missing required columns: {', '.join(absent)}"
        )
    table = forecasts.copy()
    # The forecast table reaches this module either in memory or through the CSV the ablation
    # wrote, and only the in-memory form still carries `market_day` as a date. Normalising here
    # rather than at the call site keeps the two routes on one code path: a string day would
    # match no realized interval and the settlement would fail with an empty day rather than a
    # readable refusal.
    market_days = pd.to_datetime(table["market_day"], errors="coerce")
    if market_days.isna().any():
        raise FundamentalsDispatchInputError(
            "Forecast table carries a market_day that is not a delivery date"
        )
    table["market_day"] = market_days.dt.date
    common_flag = table["is_common_day"]
    if common_flag.dtype == object:
        common_flag = common_flag.astype(str).str.strip().str.lower().isin({"true", "1"})
    held_out = table.loc[table["split"].astype(str).eq("test") & common_flag.astype(bool)]
    if held_out.empty:
        raise FundamentalsDispatchInputError(
            "The forecast table carries no held-out day marked common to every arm, so there "
            "is no like-for-like day to settle"
        )
    gaps = {
        method: int(held_out[method].isna().sum())
        for method in methods
        if held_out[method].isna().any()
    }
    if gaps:
        named = ", ".join(f"{method} ({count})" for method, count in sorted(gaps.items()))
        raise FundamentalsDispatchInputError(
            "A held-out day recorded as common to every arm carries a missing forecast: "
            f"{named}. This contradicts the forecast benchmark's own record, and excluding "
            "the day here would give the arms different calendars"
        )
    recorded_days = int(benchmark_summary["common_test_day_count"])
    found_days = int(held_out["market_day"].nunique())
    if found_days != recorded_days:
        raise FundamentalsDispatchInputError(
            f"The forecast table carries {found_days} held-out common days but its summary "
            f"records {recorded_days}. The table and the summary must describe one run"
        )
    return held_out.reset_index(drop=True)


def _shared_ceiling(method_summaries: Mapping[str, Mapping[str, Any]]) -> tuple[float, float]:
    """Assert one perfect-foresight ceiling across arms and record the spread that proved it."""

    ceilings = {
        method: float(summary["perfect_foresight_margin_eur"])
        for method, summary in method_summaries.items()
    }
    values = list(ceilings.values())
    spread = float(max(values) - min(values))
    if spread > CEILING_TOLERANCE_EUR:
        highest = max(ceilings, key=lambda method: ceilings[method])
        lowest = min(ceilings, key=lambda method: ceilings[method])
        raise FundamentalsDispatchInputError(
            "The arms did not face the same perfect-foresight ceiling: "
            f"{highest} saw EUR {ceilings[highest]:.6f} and {lowest} saw "
            f"EUR {ceilings[lowest]:.6f}. Identical realized prices, days and battery "
            "constraints must produce one ceiling, so an incremental margin measured against "
            "two of them would not be like for like"
        )
    return float(values[0]), spread


def _comparison_pairs(
    methods: Sequence[str], arms: Mapping[str, tuple[str, ...]]
) -> list[dict[str, str]]:
    """Every challenger against its own control, then against each named baseline."""

    baselines = [method for method in methods if method in arms["baselines"]]
    pairs: list[dict[str, str]] = []
    for challenger in [method for method in methods if method in arms["challenger"]]:
        pairs.append(
            {
                "comparison_id": f"{challenger}_vs_{_control_of(challenger)}",
                "challenger_method": challenger,
                "reference_method": _control_of(challenger),
                "reference_role": "control",
            }
        )
        for baseline in baselines:
            pairs.append(
                {
                    "comparison_id": f"{challenger}_vs_{baseline}",
                    "challenger_method": challenger,
                    "reference_method": baseline,
                    "reference_role": "baseline",
                }
            )
    return pairs


def _paired_differences(
    daily_results: pd.DataFrame, pairs: Sequence[Mapping[str, str]]
) -> pd.DataFrame:
    """One row per comparison and delivery day: both settled margins and their difference."""

    by_method = {
        method: frame.set_index("market_day")
        for method, frame in daily_results.groupby("comparison_method", sort=False)
    }
    records: list[dict[str, Any]] = []
    for pair in pairs:
        challenger = by_method[pair["challenger_method"]]
        reference = by_method[pair["reference_method"]]
        for market_day in challenger.index:
            challenger_margin = float(challenger.at[market_day, "realized_margin_eur"])
            reference_margin = float(reference.at[market_day, "realized_margin_eur"])
            records.append(
                {
                    "comparison_id": pair["comparison_id"],
                    "challenger_method": pair["challenger_method"],
                    "reference_method": pair["reference_method"],
                    "reference_role": pair["reference_role"],
                    "market_day": market_day,
                    "interval_count": int(challenger.at[market_day, "interval_count"]),
                    "challenger_realized_margin_eur": challenger_margin,
                    "reference_realized_margin_eur": reference_margin,
                    "realized_margin_difference_eur": challenger_margin - reference_margin,
                    "perfect_foresight_margin_eur": float(
                        challenger.at[market_day, "perfect_foresight_margin_eur"]
                    ),
                }
            )
    return pd.DataFrame.from_records(records)


def _incremental_rows(
    paired_differences: pd.DataFrame,
    method_summaries: Mapping[str, Mapping[str, Any]],
    *,
    role: str,
) -> list[dict[str, Any]]:
    """Record the incremental figure here, so no consumer has to subtract two recorded ones."""

    rows: list[dict[str, Any]] = []
    if paired_differences.empty:
        return rows
    selected = paired_differences.loc[paired_differences["reference_role"].eq(role)]
    for comparison_id, frame in selected.groupby("comparison_id", sort=False):
        differences = frame["realized_margin_difference_eur"].to_numpy(dtype=float)
        challenger = str(frame["challenger_method"].iloc[0])
        reference = str(frame["reference_method"].iloc[0])
        rows.append(
            {
                "comparison_id": str(comparison_id),
                "challenger_method": challenger,
                "reference_method": reference,
                "reference_role": role,
                "challenger_realized_margin_eur": float(
                    method_summaries[challenger]["realized_margin_eur"]
                ),
                "reference_realized_margin_eur": float(
                    method_summaries[reference]["realized_margin_eur"]
                ),
                "incremental_realized_margin_eur": float(differences.sum()),
                "challenger_capture_ratio": method_summaries[challenger][
                    "perfect_foresight_capture_ratio"
                ],
                "reference_capture_ratio": method_summaries[reference][
                    "perfect_foresight_capture_ratio"
                ],
                "common_day_count": int(len(differences)),
                "days_challenger_settled_higher": int((differences > 0).sum()),
                "days_reference_settled_higher": int((differences < 0).sum()),
                "days_settled_equal": int((differences == 0).sum()),
                "largest_daily_gain_eur": float(differences.max()),
                "largest_daily_shortfall_eur": float(differences.min()),
            }
        )
    return rows


def _dispatch_ranking(
    methods: Sequence[str], method_summaries: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    ordered = sorted(
        methods,
        key=lambda method: float(method_summaries[method]["realized_margin_eur"]),
        reverse=True,
    )
    return [
        {
            "rank": position,
            "method": method,
            "realized_margin_eur": method_summaries[method]["realized_margin_eur"],
            "perfect_foresight_margin_eur": method_summaries[method][
                "perfect_foresight_margin_eur"
            ],
            "perfect_foresight_regret_eur": method_summaries[method][
                "perfect_foresight_regret_eur"
            ],
            "perfect_foresight_capture_ratio": method_summaries[method][
                "perfect_foresight_capture_ratio"
            ],
            "forecast_rmse_eur_per_mwh": method_summaries[method][
                "backtested_forecast_metrics"
            ]["rmse_eur_per_mwh"],
        }
        for position, method in enumerate(ordered, start=1)
    ]


def _equivalent_basis(
    config: BatteryDispatchConfig,
    held_out: pd.DataFrame,
    common_days: Sequence[Any],
    benchmark_summary: Mapping[str, Any],
    ceiling: float,
    ceiling_spread: float,
) -> dict[str, Any]:
    """Write down what every arm shared, in the groups a reader has to check separately."""

    configuration = config.to_dict()
    starts = pd.to_datetime(held_out["delivery_start_utc"], utc=True).sort_values()
    return {
        "battery_configuration": {
            key: value
            for key, value in configuration.items()
            if key not in TERMINAL_ENERGY_FIELDS
        },
        "terminal_energy_basis": {
            **{name: configuration[name] for name in TERMINAL_ENERGY_FIELDS},
            "effective_terminal_soc_fraction": config.effective_terminal_soc_fraction,
            "convention": "Initial SOC restored at the end of every market day",
        },
        "realized_price_identity": {
            "interval_count": int(len(held_out)),
            "first_delivery_start_utc": starts.iloc[0].isoformat(),
            "last_delivery_start_utc": starts.iloc[-1].isoformat(),
            "settled_at": "the realized price of every settled interval, for every arm",
        },
        "common_day_identity": {
            "common_backtest_day_count": len(common_days),
            "first_common_backtest_day": str(min(common_days)),
            "last_common_backtest_day": str(max(common_days)),
            "common_day_sha256": _day_digest(common_days),
        },
        "perfect_foresight_ceiling": {
            "perfect_foresight_margin_eur": ceiling,
            "maximum_ceiling_spread_eur": ceiling_spread,
            "tolerance_eur": CEILING_TOLERANCE_EUR,
        },
        "feature_set_identity": {
            "feature_set_sha256": str(benchmark_summary["feature_set_sha256"]),
            "decision_cutoff_schedule_id": str(
                benchmark_summary["decision_cutoff_schedule_id"]
            ),
            "decision_lead_minutes": int(benchmark_summary["decision_lead_minutes"]),
            "evidence_grades_admitted": [
                str(grade) for grade in benchmark_summary["evidence_grades_admitted"]
            ],
        },
    }


def _day_digest(common_days: Sequence[Any]) -> str:
    """Identify the settled calendar, so two runs can be compared without opening the CSVs."""

    digest = hashlib.sha256()
    for day in common_days:
        digest.update(str(day).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
