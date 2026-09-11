"""Perfect-foresight Greek DAM battery arbitrage optimization.

The result is a deterministic gross-margin upper bound under the supplied
prices and assumptions. It is not a forecast of achievable project revenue.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from ..data.quality import assess_quality
from ..data.schema import ensure_canonical

UPPER_BOUND_LABEL = (
    "Perfect-foresight Greek DAM gross-margin upper bound; not expected or "
    "forecast investment revenue."
)
DAILY_SOLVE_LABEL = (
    "Perfect-foresight Greek DAM gross-margin upper bound composed from independent "
    "daily solves; not expected or forecast investment revenue."
)
NUMERICAL_THROUGHPUT_TIEBREAK_EUR_PER_MWH = 1e-7

RELAXATION_FIRST = "relaxation_first"
MIXED_INTEGER = "mixed_integer"
SOLVE_STRATEGIES = (RELAXATION_FIRST, MIXED_INTEGER)

# Charge and discharge powers below this many MW are reported as zero, so a pair of
# values that both survive it is a genuine simultaneous charge and discharge rather
# than solver noise. `_clean` applies the same threshold to the reported schedule.
SIMULTANEITY_TOLERANCE_MW = 1e-8


class DispatchInputError(ValueError):
    """Raised when prices or battery assumptions are unsuitable for dispatch."""


class DispatchSolveError(RuntimeError):
    """Raised when the mathematical optimizer does not return a solution."""


@dataclass(frozen=True)
class BatteryDispatchConfig:
    """Editable battery and commercial assumptions.

    Charge/discharge power is measured at the grid meter. Stored energy is
    measured inside the battery after charge efficiency and before discharge
    efficiency. Defaults are illustrative and must be replaced for a project.
    """

    charge_power_mw: float
    discharge_power_mw: float
    energy_capacity_mwh: float
    soc_min_fraction: float = 0.05
    soc_max_fraction: float = 0.95
    initial_soc_fraction: float = 0.50
    terminal_soc_fraction: float | None = None
    charge_efficiency: float = 0.94
    discharge_efficiency: float = 0.94
    self_discharge_per_hour: float = 0.0
    grid_import_limit_mw: float | None = None
    grid_export_limit_mw: float | None = None
    max_daily_equivalent_cycles: float | None = None
    buy_fee_eur_per_mwh: float = 0.0
    sell_fee_eur_per_mwh: float = 0.0
    degradation_cost_eur_per_mwh_discharged: float = 0.0
    require_complete_market_days: bool = True
    mip_relative_gap: float = 1e-7
    solver_time_limit_seconds: float | None = None
    solve_strategy: str = RELAXATION_FIRST

    def __post_init__(self) -> None:
        for name in ("charge_power_mw", "discharge_power_mw", "energy_capacity_mwh"):
            _require_finite_positive(name, getattr(self, name))
        for name in ("soc_min_fraction", "soc_max_fraction", "initial_soc_fraction"):
            _require_fraction(name, getattr(self, name))
        if self.soc_min_fraction >= self.soc_max_fraction:
            raise DispatchInputError("soc_min_fraction must be below soc_max_fraction")
        if not self.soc_min_fraction <= self.initial_soc_fraction <= self.soc_max_fraction:
            raise DispatchInputError("initial_soc_fraction must lie within SOC limits")
        terminal = self.effective_terminal_soc_fraction
        _require_fraction("terminal_soc_fraction", terminal)
        if not self.soc_min_fraction <= terminal <= self.soc_max_fraction:
            raise DispatchInputError("terminal_soc_fraction must lie within SOC limits")
        for name in ("charge_efficiency", "discharge_efficiency"):
            value = getattr(self, name)
            if not np.isfinite(value) or not 0 < value <= 1:
                raise DispatchInputError(f"{name} must be greater than 0 and at most 1")
        if not np.isfinite(self.self_discharge_per_hour) or not (
            0 <= self.self_discharge_per_hour < 1
        ):
            raise DispatchInputError("self_discharge_per_hour must be at least 0 and below 1")
        for name in ("grid_import_limit_mw", "grid_export_limit_mw"):
            value = getattr(self, name)
            if value is not None:
                _require_finite_nonnegative(name, value)
        if self.max_daily_equivalent_cycles is not None:
            _require_finite_nonnegative(
                "max_daily_equivalent_cycles", self.max_daily_equivalent_cycles
            )
        for name in (
            "buy_fee_eur_per_mwh",
            "sell_fee_eur_per_mwh",
            "degradation_cost_eur_per_mwh_discharged",
        ):
            _require_finite_nonnegative(name, getattr(self, name))
        if not np.isfinite(self.mip_relative_gap) or self.mip_relative_gap < 0:
            raise DispatchInputError("mip_relative_gap must be finite and nonnegative")
        if self.solver_time_limit_seconds is not None:
            _require_finite_positive(
                "solver_time_limit_seconds", self.solver_time_limit_seconds
            )
        if self.solve_strategy not in SOLVE_STRATEGIES:
            raise DispatchInputError(
                "solve_strategy must be one of " + ", ".join(SOLVE_STRATEGIES)
            )

    @property
    def effective_terminal_soc_fraction(self) -> float:
        return (
            self.initial_soc_fraction
            if self.terminal_soc_fraction is None
            else self.terminal_soc_fraction
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DispatchResult:
    schedule: pd.DataFrame
    summary: dict[str, Any]
    config: BatteryDispatchConfig


def optimize_perfect_foresight(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    *,
    availability: float | Sequence[float] | pd.Series = 1.0,
) -> DispatchResult:
    """Maximize settled DAM margin across the full supplied price horizon."""

    input_availability = _availability_array(availability, len(prices))
    original_starts = pd.to_datetime(
        prices["delivery_start_utc"], utc=True, errors="coerce"
    )
    data = ensure_canonical(prices, allow_empty=False)
    quality = assess_quality(
        data, require_complete_days=config.require_complete_market_days
    )
    if not quality.is_valid:
        errors = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        raise DispatchInputError(f"Price data failed dispatch quality checks: {errors}")

    interval_count = len(data)
    sort_order = np.argsort(original_starts.astype("int64").to_numpy(), kind="stable")
    availability_values = input_availability[sort_order]
    durations = data["duration_hours"].to_numpy(dtype=float)
    prices_eur = data["price_eur_per_mwh"].to_numpy(dtype=float)

    charge_caps = config.charge_power_mw * availability_values
    discharge_caps = config.discharge_power_mw * availability_values
    if config.grid_import_limit_mw is not None:
        charge_caps = np.minimum(charge_caps, config.grid_import_limit_mw)
    if config.grid_export_limit_mw is not None:
        discharge_caps = np.minimum(discharge_caps, config.grid_export_limit_mw)

    charge_index = np.arange(interval_count)
    discharge_index = np.arange(interval_count, 2 * interval_count)
    energy_index = np.arange(2 * interval_count, 3 * interval_count + 1)
    mode_index = np.arange(3 * interval_count + 1, 4 * interval_count + 1)
    variable_count = 4 * interval_count + 1

    objective = np.zeros(variable_count)
    objective[charge_index] = (
        prices_eur
        + config.buy_fee_eur_per_mwh
        + NUMERICAL_THROUGHPUT_TIEBREAK_EUR_PER_MWH
    ) * durations
    objective[discharge_index] = (
        -prices_eur
        + config.sell_fee_eur_per_mwh
        + config.degradation_cost_eur_per_mwh_discharged
        + NUMERICAL_THROUGHPUT_TIEBREAK_EUR_PER_MWH
    ) * durations

    lower = np.zeros(variable_count)
    upper = np.full(variable_count, np.inf)
    upper[charge_index] = charge_caps
    upper[discharge_index] = discharge_caps
    lower[energy_index] = config.soc_min_fraction * config.energy_capacity_mwh
    upper[energy_index] = config.soc_max_fraction * config.energy_capacity_mwh
    initial_energy = config.initial_soc_fraction * config.energy_capacity_mwh
    terminal_energy = (
        config.effective_terminal_soc_fraction * config.energy_capacity_mwh
    )
    lower[energy_index[0]] = upper[energy_index[0]] = initial_energy
    lower[energy_index[-1]] = upper[energy_index[-1]] = terminal_energy
    upper[mode_index] = 1

    daily_cycle_limit = config.max_daily_equivalent_cycles
    daily_groups: list[np.ndarray] = []
    if daily_cycle_limit is not None:
        market_days = data["delivery_start_market"].dt.date.to_numpy()
        daily_groups = [np.flatnonzero(market_days == day) for day in pd.unique(market_days)]

    row_count = 3 * interval_count + len(daily_groups)
    matrix = lil_matrix((row_count, variable_count), dtype=float)
    constraint_lower = np.full(row_count, -np.inf)
    constraint_upper = np.full(row_count, np.inf)
    row = 0

    for interval in range(interval_count):
        duration = durations[interval]
        retention = (1 - config.self_discharge_per_hour) ** duration
        matrix[row, charge_index[interval]] = -config.charge_efficiency * duration
        matrix[row, discharge_index[interval]] = duration / config.discharge_efficiency
        matrix[row, energy_index[interval]] = -retention
        matrix[row, energy_index[interval + 1]] = 1
        constraint_lower[row] = constraint_upper[row] = 0
        row += 1

    for interval in range(interval_count):
        matrix[row, charge_index[interval]] = 1
        matrix[row, mode_index[interval]] = -charge_caps[interval]
        constraint_upper[row] = 0
        row += 1

        matrix[row, discharge_index[interval]] = 1
        matrix[row, mode_index[interval]] = discharge_caps[interval]
        constraint_upper[row] = discharge_caps[interval]
        row += 1

    for group in daily_groups:
        assert daily_cycle_limit is not None
        for interval in group:
            matrix[row, discharge_index[interval]] = durations[interval]
        constraint_upper[row] = daily_cycle_limit * config.energy_capacity_mwh
        row += 1

    integrality = np.zeros(variable_count, dtype=np.uint8)
    integrality[mode_index] = 1
    options: dict[str, Any] = {
        "disp": False,
        "mip_rel_gap": config.mip_relative_gap,
    }
    if config.solver_time_limit_seconds is not None:
        options["time_limit"] = config.solver_time_limit_seconds

    result, solve_record = _solve_dispatch_program(
        objective=objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(
            matrix.tocsr(), constraint_lower, constraint_upper
        ),
        options=options,
        charge_index=charge_index,
        discharge_index=discharge_index,
        strategy=config.solve_strategy,
    )
    if not result.success or result.x is None:
        raise DispatchSolveError(
            f"Dispatch solve failed with status {result.status}: {result.message}"
        )

    charge_mw = _clean(result.x[charge_index])
    discharge_mw = _clean(result.x[discharge_index])
    energy_mwh = _clean(result.x[energy_index])
    schedule = _build_schedule(
        data,
        config,
        availability_values,
        charge_mw,
        discharge_mw,
        energy_mwh,
    )
    summary = _build_summary(schedule, config, result, solve_record)
    return DispatchResult(schedule=schedule, summary=summary, config=config)


def _solve_dispatch_program(
    *,
    objective: np.ndarray,
    integrality: np.ndarray,
    bounds: Bounds,
    constraints: LinearConstraint,
    options: dict[str, Any],
    charge_index: np.ndarray,
    discharge_index: np.ndarray,
    strategy: str,
) -> tuple[Any, dict[str, Any]]:
    """Return the mixed-integer optimum, reaching it through the relaxation when it can.

    The binary mode variable exists for exactly one purpose: to forbid charging and
    discharging in the same interval. Without it an optimizer will happily do both at
    once whenever a price is negative, because the round-trip efficiency losses of a
    pointless circulating flow are a way to get paid for consuming energy. Dropping
    that variable therefore enlarges the feasible set, which makes the relaxed optimum
    an upper bound on the mixed-integer optimum.

    That bound is what makes the shortcut exact rather than approximate. Every binary
    constraint in this program has the form `charge <= cap * mode` and
    `discharge <= cap * (1 - mode)`, and both bounds already cap charge and discharge
    at `cap`. So an interval that charges but does not discharge admits `mode = 1`, an
    interval that discharges but does not charge admits `mode = 0`, and an idle
    interval admits either: a relaxed solution that never does both in one interval can
    be extended to a full mixed-integer feasible point. A feasible point that attains
    an upper bound on the optimum *is* an optimum, so it is returned unchanged.

    Only when the relaxation actually violates the exclusivity it dropped does the
    mixed-integer program have to be solved, and the answer this function returns is
    the mixed-integer optimum on either path. Empirically the relaxation succeeds on
    every market day with no negative prices, which on Greek DAM history is most of
    them, and the daily solve convention means one negative-price day costs only its
    own re-solve.
    """

    relaxed_simultaneous: int | None = None
    if strategy == RELAXATION_FIRST:
        relaxed = milp(
            c=objective,
            integrality=np.zeros_like(integrality),
            bounds=bounds,
            constraints=constraints,
            options=options,
        )
        if relaxed.success and relaxed.x is not None:
            relaxed_simultaneous = _simultaneous_interval_count(
                relaxed.x[charge_index], relaxed.x[discharge_index]
            )
            if relaxed_simultaneous == 0:
                return relaxed, {
                    "solve_strategy": strategy,
                    "solve_path": "relaxation_accepted",
                    "relaxation_simultaneous_interval_count": 0,
                    "mixed_integer_solve_required": False,
                }

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options=options,
    )
    return result, {
        "solve_strategy": strategy,
        "solve_path": "mixed_integer",
        "relaxation_simultaneous_interval_count": relaxed_simultaneous,
        "mixed_integer_solve_required": True,
    }


def _simultaneous_interval_count(
    charge_mw: np.ndarray, discharge_mw: np.ndarray
) -> int:
    """Count intervals that both charge and discharge by more than reporting noise."""

    charging = np.abs(np.asarray(charge_mw, dtype=float)) >= SIMULTANEITY_TOLERANCE_MW
    discharging = (
        np.abs(np.asarray(discharge_mw, dtype=float)) >= SIMULTANEITY_TOLERANCE_MW
    )
    return int(np.count_nonzero(charging & discharging))


def _build_schedule(
    data: pd.DataFrame,
    config: BatteryDispatchConfig,
    availability: np.ndarray,
    charge_mw: np.ndarray,
    discharge_mw: np.ndarray,
    energy_mwh: np.ndarray,
) -> pd.DataFrame:
    schedule = data.copy()
    duration = schedule["duration_hours"].to_numpy(dtype=float)
    price = schedule["price_eur_per_mwh"].to_numpy(dtype=float)
    charge_grid_mwh = charge_mw * duration
    discharge_grid_mwh = discharge_mw * duration
    charge_cost = price * charge_grid_mwh
    discharge_revenue = price * discharge_grid_mwh
    buy_fee = config.buy_fee_eur_per_mwh * charge_grid_mwh
    sell_fee = config.sell_fee_eur_per_mwh * discharge_grid_mwh
    degradation = (
        config.degradation_cost_eur_per_mwh_discharged * discharge_grid_mwh
    )

    schedule["availability_fraction"] = availability
    schedule["charge_mw"] = charge_mw
    schedule["discharge_mw"] = discharge_mw
    schedule["net_export_mw"] = discharge_mw - charge_mw
    schedule["energy_start_mwh"] = energy_mwh[:-1]
    schedule["energy_end_mwh"] = energy_mwh[1:]
    schedule["soc_start_fraction"] = energy_mwh[:-1] / config.energy_capacity_mwh
    schedule["soc_end_fraction"] = energy_mwh[1:] / config.energy_capacity_mwh
    schedule["charge_grid_mwh"] = charge_grid_mwh
    schedule["discharge_grid_mwh"] = discharge_grid_mwh
    schedule["charging_energy_cost_eur"] = charge_cost
    schedule["discharge_energy_revenue_eur"] = discharge_revenue
    schedule["buy_fee_eur"] = buy_fee
    schedule["sell_fee_eur"] = sell_fee
    schedule["degradation_cost_eur"] = degradation
    schedule["market_cash_margin_eur"] = (
        discharge_revenue - charge_cost - buy_fee - sell_fee
    )
    schedule["net_market_margin_eur"] = (
        discharge_revenue - charge_cost - buy_fee - sell_fee - degradation
    )
    schedule["operating_mode"] = np.select(
        [charge_mw > 1e-7, discharge_mw > 1e-7],
        ["charge", "discharge"],
        default="idle",
    )
    return schedule


def _build_summary(
    schedule: pd.DataFrame,
    config: BatteryDispatchConfig,
    solver_result: Any,
    solve_record: dict[str, Any],
) -> dict[str, Any]:
    charge_mwh = float(schedule["charge_grid_mwh"].sum())
    discharge_mwh = float(schedule["discharge_grid_mwh"].sum())
    charge_cost = float(schedule["charging_energy_cost_eur"].sum())
    discharge_revenue = float(schedule["discharge_energy_revenue_eur"].sum())
    buy_fees = float(schedule["buy_fee_eur"].sum())
    sell_fees = float(schedule["sell_fee_eur"].sum())
    degradation = float(schedule["degradation_cost_eur"].sum())
    net_margin = float(schedule["net_market_margin_eur"].sum())
    return {
        "result_label": UPPER_BOUND_LABEL,
        **solve_record,
        "interval_count": int(len(schedule)),
        "horizon_start_utc": str(schedule["delivery_start_utc"].min()),
        "horizon_end_utc_exclusive": str(schedule["delivery_end_utc"].max()),
        "gross_discharge_revenue_eur": discharge_revenue,
        "charging_energy_cost_eur": charge_cost,
        "buy_fees_eur": buy_fees,
        "sell_fees_eur": sell_fees,
        "degradation_cost_eur": degradation,
        "market_cash_margin_eur": float(schedule["market_cash_margin_eur"].sum()),
        "wear_penalty_policy": "degradation_cost_eur is a non-cash dispatch wear penalty",
        "net_market_margin_eur": net_margin,
        "grid_charge_mwh": charge_mwh,
        "grid_discharge_mwh": discharge_mwh,
        "equivalent_full_cycles": discharge_mwh / config.energy_capacity_mwh,
        "average_charge_price_eur_per_mwh": (
            charge_cost / charge_mwh if charge_mwh > 1e-9 else None
        ),
        "average_discharge_price_eur_per_mwh": (
            discharge_revenue / discharge_mwh if discharge_mwh > 1e-9 else None
        ),
        "initial_energy_mwh": float(schedule["energy_start_mwh"].iloc[0]),
        "terminal_energy_mwh": float(schedule["energy_end_mwh"].iloc[-1]),
        "one_way_charge_efficiency": config.charge_efficiency,
        "one_way_discharge_efficiency": config.discharge_efficiency,
        "nominal_round_trip_efficiency": (
            config.charge_efficiency * config.discharge_efficiency
        ),
        "solver_status": int(solver_result.status),
        "solver_message": str(solver_result.message),
        "solver_objective_eur": float(solver_result.fun),
        "economic_objective_eur": -net_margin,
        "numerical_throughput_tiebreak_eur": (
            NUMERICAL_THROUGHPUT_TIEBREAK_EUR_PER_MWH
            * (charge_mwh + discharge_mwh)
        ),
    }


def optimize_daily_perfect_foresight(
    prices: pd.DataFrame,
    config: BatteryDispatchConfig,
    *,
    availability: float | Sequence[float] | pd.Series = 1.0,
) -> DispatchResult:
    """Solve every market day independently and compose the schedules.

    This is the repository's established comparative convention and the ceiling the
    forecast backtests are measured against: each market day starts and ends at the
    configured SOC, so no energy is arbitraged across a day boundary. Because no day
    borrows energy from another, every interval's margin belongs unambiguously to its
    own market day, and therefore to its own delivery year.

    The composed margin is necessarily at or below the single full-horizon solve,
    which may move energy between days. Both remain labelled upper bounds.
    """

    if not np.isclose(config.initial_soc_fraction, config.effective_terminal_soc_fraction):
        raise DispatchInputError(
            "Daily composed dispatch requires terminal_soc_fraction to equal "
            "initial_soc_fraction, so that independent days can be composed"
        )

    input_availability = _availability_array(availability, len(prices))
    original_starts = pd.to_datetime(
        prices["delivery_start_utc"], utc=True, errors="coerce"
    )
    sort_order = np.argsort(original_starts.astype("int64").to_numpy(), kind="stable")
    availability_values = input_availability[sort_order]

    data = ensure_canonical(prices, allow_empty=False).reset_index(drop=True)
    market_days = data["delivery_start_market"].dt.date

    schedules: list[pd.DataFrame] = []
    solver_statuses: list[int] = []
    solve_paths: list[str] = []
    terminal_errors: list[float] = []
    target_energy = config.energy_capacity_mwh * config.effective_terminal_soc_fraction

    for market_day in sorted(market_days.unique()):
        selector = market_days.eq(market_day).to_numpy()
        day = data.loc[selector].reset_index(drop=True)
        result = optimize_perfect_foresight(
            day, config, availability=availability_values[selector]
        )
        schedule = result.schedule.copy()
        schedule.insert(0, "market_day", market_day)
        schedules.append(schedule)
        solver_statuses.append(int(result.summary["solver_status"]))
        solve_paths.append(str(result.summary["solve_path"]))
        terminal_errors.append(
            abs(float(result.summary["terminal_energy_mwh"]) - target_energy)
        )

    composed = pd.concat(schedules, ignore_index=True)
    summary = _daily_summary(
        composed, config, solver_statuses, solve_paths, terminal_errors
    )
    return DispatchResult(schedule=composed, summary=summary, config=config)


def _daily_summary(
    schedule: pd.DataFrame,
    config: BatteryDispatchConfig,
    solver_statuses: list[int],
    solve_paths: list[str],
    terminal_errors: list[float],
) -> dict[str, Any]:
    charge_mwh = float(schedule["charge_grid_mwh"].sum())
    discharge_mwh = float(schedule["discharge_grid_mwh"].sum())
    charge_cost = float(schedule["charging_energy_cost_eur"].sum())
    discharge_revenue = float(schedule["discharge_energy_revenue_eur"].sum())
    status_counts: dict[str, int] = {}
    for status in solver_statuses:
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    path_counts: dict[str, int] = {}
    for path in solve_paths:
        path_counts[path] = path_counts.get(path, 0) + 1
    return {
        "result_label": DAILY_SOLVE_LABEL,
        "solve_mode": "daily_independent_solves",
        "solve_strategy": config.solve_strategy,
        "solve_path_counts": path_counts,
        "mixed_integer_solve_count": path_counts.get("mixed_integer", 0),
        "interval_count": int(len(schedule)),
        "market_day_count": len(solver_statuses),
        "horizon_start_utc": str(schedule["delivery_start_utc"].min()),
        "horizon_end_utc_exclusive": str(schedule["delivery_end_utc"].max()),
        "gross_discharge_revenue_eur": discharge_revenue,
        "charging_energy_cost_eur": charge_cost,
        "buy_fees_eur": float(schedule["buy_fee_eur"].sum()),
        "sell_fees_eur": float(schedule["sell_fee_eur"].sum()),
        "degradation_cost_eur": float(schedule["degradation_cost_eur"].sum()),
        "market_cash_margin_eur": float(schedule["market_cash_margin_eur"].sum()),
        "wear_penalty_policy": "degradation_cost_eur is a non-cash dispatch wear penalty",
        "net_market_margin_eur": float(schedule["net_market_margin_eur"].sum()),
        "grid_charge_mwh": charge_mwh,
        "grid_discharge_mwh": discharge_mwh,
        "equivalent_full_cycles": discharge_mwh / config.energy_capacity_mwh,
        "average_charge_price_eur_per_mwh": (
            charge_cost / charge_mwh if charge_mwh > 1e-9 else None
        ),
        "average_discharge_price_eur_per_mwh": (
            discharge_revenue / discharge_mwh if discharge_mwh > 1e-9 else None
        ),
        "one_way_charge_efficiency": config.charge_efficiency,
        "one_way_discharge_efficiency": config.discharge_efficiency,
        "nominal_round_trip_efficiency": (
            config.charge_efficiency * config.discharge_efficiency
        ),
        "solver_status_counts": status_counts,
        "maximum_terminal_energy_error_mwh": (
            max(terminal_errors) if terminal_errors else 0.0
        ),
        "terminal_soc_policy": "Initial SOC restored at the end of every market day",
    }


def _availability_array(
    availability: float | Sequence[float] | pd.Series, interval_count: int
) -> np.ndarray:
    if np.isscalar(availability):
        values = np.full(interval_count, float(cast(Any, availability)))
    else:
        values = np.asarray(availability, dtype=float)
        if values.ndim != 1 or len(values) != interval_count:
            raise DispatchInputError(
                f"availability must contain exactly {interval_count} values"
            )
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise DispatchInputError("availability values must be finite and between 0 and 1")
    return values


def _clean(values: np.ndarray, tolerance: float = 1e-8) -> np.ndarray:
    cleaned = np.asarray(values, dtype=float).copy()
    cleaned[np.abs(cleaned) < tolerance] = 0
    return cleaned


def _require_fraction(name: str, value: float) -> None:
    if not np.isfinite(value) or not 0 <= value <= 1:
        raise DispatchInputError(f"{name} must be finite and between 0 and 1")


def _require_finite_positive(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0:
        raise DispatchInputError(f"{name} must be finite and greater than 0")


def _require_finite_nonnegative(name: str, value: float) -> None:
    if not np.isfinite(value) or value < 0:
        raise DispatchInputError(f"{name} must be finite and nonnegative")
