"""Auditable cohort-based battery degradation and augmentation state evolution.

The model is deliberately first-order. Calendar and cycle fade are additive, every
augmentation is represented as a separately aged cohort, and daily cell discharge is
allocated in proportion to beginning-of-day usable energy. Assumptions are inputs, not
OEM evidence or a warranty interpretation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

DEGRADATION_MODEL_LABEL = (
    "Illustrative cohort-based calendar and cycle degradation state model; "
    "assumptions require project-specific OEM validation and are not warranty advice."
)
YEAR_DAYS = 365.25
TOLERANCE = 1e-9


class DegradationInputError(ValueError):
    """Raised when degradation assumptions or daily throughput are invalid."""


@dataclass(frozen=True)
class AugmentationEvent:
    """A dated capacity addition, optionally replacing named existing cohorts."""

    event_id: str
    day: date
    added_energy_mwh: float
    added_charge_power_mw: float
    added_discharge_power_mw: float
    cost_eur: float = 0.0
    retired_cohort_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized_day = _as_date(self.day, "augmentation day")
        object.__setattr__(self, "day", normalized_day)
        if not self.event_id or not self.event_id.strip():
            raise DegradationInputError("augmentation event_id cannot be empty")
        object.__setattr__(self, "event_id", self.event_id.strip())
        for name in (
            "added_energy_mwh",
            "added_charge_power_mw",
            "added_discharge_power_mw",
        ):
            _require_positive(name, getattr(self, name))
        _require_nonnegative("augmentation cost_eur", self.cost_eur)
        retired = tuple(str(value).strip() for value in self.retired_cohort_ids)
        if any(not value for value in retired):
            raise DegradationInputError("retired_cohort_ids cannot contain empty values")
        if len(retired) != len(set(retired)):
            raise DegradationInputError("retired_cohort_ids must be unique per event")
        if self.event_id in retired:
            raise DegradationInputError("An event cannot retire its own new cohort")
        object.__setattr__(self, "retired_cohort_ids", retired)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AugmentationEvent:
        if not isinstance(payload, dict):
            raise DegradationInputError("Each augmentation event must be an object")
        values = dict(payload)
        raw_retired = values.pop("retired_cohort_ids", [])
        if not isinstance(raw_retired, list):
            raise DegradationInputError("retired_cohort_ids must be a list")
        values["retired_cohort_ids"] = tuple(raw_retired)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["day"] = self.day.isoformat()
        payload["retired_cohort_ids"] = list(self.retired_cohort_ids)
        return payload


@dataclass(frozen=True)
class DegradationConfig:
    """Editable degradation, warranty-screening and augmentation assumptions."""

    project_start_day: date
    calendar_fade_fraction_per_year: float
    cycle_fade_fraction_per_equivalent_cycle: float
    power_fade_exponent: float = 1.0
    warranty_years: float | None = None
    warranty_retained_capacity_fraction: float | None = None
    warranty_max_equivalent_full_cycles: float | None = None
    enforce_warranty_throughput_limit: bool = False
    retirement_capacity_fraction: float | None = None
    augmentation_events: tuple[AugmentationEvent, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_start_day", _as_date(self.project_start_day, "project_start_day")
        )
        _require_fraction(
            "calendar_fade_fraction_per_year",
            self.calendar_fade_fraction_per_year,
        )
        _require_fraction(
            "cycle_fade_fraction_per_equivalent_cycle",
            self.cycle_fade_fraction_per_equivalent_cycle,
        )
        _require_positive("power_fade_exponent", self.power_fade_exponent)
        if (self.warranty_years is None) != (
            self.warranty_retained_capacity_fraction is None
        ):
            raise DegradationInputError(
                "warranty_years and warranty_retained_capacity_fraction must be set together"
            )
        if self.warranty_years is not None:
            _require_positive("warranty_years", self.warranty_years)
            _require_fraction(
                "warranty_retained_capacity_fraction",
                self.warranty_retained_capacity_fraction,
            )
        if self.warranty_max_equivalent_full_cycles is not None:
            _require_nonnegative(
                "warranty_max_equivalent_full_cycles",
                self.warranty_max_equivalent_full_cycles,
            )
        if not isinstance(self.enforce_warranty_throughput_limit, bool):
            raise DegradationInputError(
                "enforce_warranty_throughput_limit must be true or false"
            )
        if (
            self.enforce_warranty_throughput_limit
            and self.warranty_max_equivalent_full_cycles is None
        ):
            raise DegradationInputError(
                "enforce_warranty_throughput_limit requires "
                "warranty_max_equivalent_full_cycles"
            )
        if self.retirement_capacity_fraction is not None:
            _require_fraction(
                "retirement_capacity_fraction", self.retirement_capacity_fraction
            )

        events = tuple(self.augmentation_events)
        if any(not isinstance(event, AugmentationEvent) for event in events):
            raise DegradationInputError(
                "augmentation_events must contain AugmentationEvent objects"
            )
        ids = [event.event_id for event in events]
        if len(ids) != len(set(ids)):
            raise DegradationInputError("augmentation event_id values must be unique")
        if any(event.day < self.project_start_day for event in events):
            raise DegradationInputError(
                "augmentation events cannot precede project_start_day"
            )
        object.__setattr__(
            self,
            "augmentation_events",
            tuple(sorted(events, key=lambda event: (event.day, event.event_id))),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DegradationConfig:
        if not isinstance(payload, dict):
            raise DegradationInputError("Degradation config JSON must contain one object")
        values = dict(payload)
        raw_events = values.pop("augmentation_events", [])
        if not isinstance(raw_events, list):
            raise DegradationInputError("augmentation_events must be a list")
        values["augmentation_events"] = tuple(
            AugmentationEvent.from_dict(item) for item in raw_events
        )
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["project_start_day"] = self.project_start_day.isoformat()
        payload["augmentation_events"] = [
            event.to_dict() for event in self.augmentation_events
        ]
        return payload


@dataclass(frozen=True)
class CohortState:
    cohort_id: str
    commissioned_day: date
    nominal_energy_mwh: float
    nominal_charge_power_mw: float
    nominal_discharge_power_mw: float
    cumulative_cell_discharge_mwh: float = 0.0


@dataclass(frozen=True)
class DegradationState:
    cohorts: tuple[CohortState, ...]
    applied_augmentation_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CohortSnapshot:
    cohort_id: str
    commissioned_day: date
    age_years: float
    nominal_energy_mwh: float
    nominal_charge_power_mw: float
    nominal_discharge_power_mw: float
    cumulative_cell_discharge_mwh: float
    cumulative_equivalent_full_cycles: float
    calendar_fade_fraction: float
    cycle_fade_fraction: float
    retained_capacity_fraction: float
    usable_energy_mwh: float
    usable_charge_power_mw: float
    usable_discharge_power_mw: float
    warranty_active: bool
    warranty_capacity_breach: bool
    warranty_throughput_exceeded: bool


@dataclass(frozen=True)
class DegradationSnapshot:
    day: date
    cohorts: tuple[CohortSnapshot, ...]
    nominal_energy_mwh: float
    usable_energy_mwh: float
    nominal_charge_power_mw: float
    usable_charge_power_mw: float
    nominal_discharge_power_mw: float
    usable_discharge_power_mw: float
    retained_capacity_fraction: float
    cumulative_cell_discharge_mwh: float
    warranty_capacity_breach: bool
    warranty_throughput_exceeded: bool
    warranty_breach: bool
    below_retirement_threshold: bool


@dataclass(frozen=True)
class DegradationSimulationResult:
    daily_states: pd.DataFrame
    cohort_states: pd.DataFrame
    summary: dict[str, Any]
    final_state: DegradationState


def initialize_degradation_state(
    *,
    nominal_energy_mwh: float,
    nominal_charge_power_mw: float,
    nominal_discharge_power_mw: float,
    config: DegradationConfig,
) -> DegradationState:
    """Create the initial project cohort at the configured project start day."""

    for name, value in (
        ("nominal_energy_mwh", nominal_energy_mwh),
        ("nominal_charge_power_mw", nominal_charge_power_mw),
        ("nominal_discharge_power_mw", nominal_discharge_power_mw),
    ):
        _require_positive(name, value)
    initial = CohortState(
        cohort_id="initial",
        commissioned_day=config.project_start_day,
        nominal_energy_mwh=float(nominal_energy_mwh),
        nominal_charge_power_mw=float(nominal_charge_power_mw),
        nominal_discharge_power_mw=float(nominal_discharge_power_mw),
    )
    return DegradationState(cohorts=(initial,))


def prepare_degradation_day(
    state: DegradationState,
    day: date | str,
    config: DegradationConfig,
) -> tuple[DegradationState, DegradationSnapshot, tuple[AugmentationEvent, ...]]:
    """Apply any dated augmentation and return beginning-of-day fleet limits."""

    target_day = _as_date(day, "market_day")
    if target_day < config.project_start_day:
        raise DegradationInputError("market_day cannot precede project_start_day")
    applied = set(state.applied_augmentation_event_ids)
    due = tuple(
        event
        for event in config.augmentation_events
        if event.day <= target_day and event.event_id not in applied
    )
    cohorts = list(state.cohorts)
    for event in due:
        available_ids = {cohort.cohort_id for cohort in cohorts}
        missing_retirements = sorted(set(event.retired_cohort_ids) - available_ids)
        if missing_retirements:
            raise DegradationInputError(
                f"Capacity event {event.event_id} cannot retire unknown cohort(s): "
                + ", ".join(missing_retirements)
            )
        retired = set(event.retired_cohort_ids)
        cohorts = [cohort for cohort in cohorts if cohort.cohort_id not in retired]
        cohorts.append(
            CohortState(
                cohort_id=event.event_id,
                commissioned_day=event.day,
                nominal_energy_mwh=event.added_energy_mwh,
                nominal_charge_power_mw=event.added_charge_power_mw,
                nominal_discharge_power_mw=event.added_discharge_power_mw,
            )
        )
        applied.add(event.event_id)
    prepared = DegradationState(
        cohorts=tuple(cohorts),
        applied_augmentation_event_ids=tuple(sorted(applied)),
    )
    return prepared, _snapshot(prepared, target_day, config), due


def complete_degradation_day(
    state: DegradationState,
    day: date | str,
    cell_discharge_mwh: float,
    config: DegradationConfig,
) -> tuple[DegradationState, DegradationSnapshot, dict[str, float]]:
    """Allocate realized daily cell discharge and return the end-of-day state."""

    target_day = _as_date(day, "market_day")
    _require_nonnegative("cell_discharge_mwh", cell_discharge_mwh)
    start = _snapshot(state, target_day, config)
    if cell_discharge_mwh > TOLERANCE and start.usable_energy_mwh <= TOLERANCE:
        raise DegradationInputError(
            "Positive cell discharge cannot be allocated to zero usable capacity"
        )

    allocations: dict[str, float] = {}
    updated: list[CohortState] = []
    for cohort, snapshot in zip(state.cohorts, start.cohorts, strict=True):
        share = (
            snapshot.usable_energy_mwh / start.usable_energy_mwh
            if start.usable_energy_mwh > TOLERANCE
            else 0.0
        )
        allocation = float(cell_discharge_mwh) * share
        allocations[cohort.cohort_id] = allocation
        updated.append(
            replace(
                cohort,
                cumulative_cell_discharge_mwh=(
                    cohort.cumulative_cell_discharge_mwh + allocation
                ),
            )
        )
    end_state = DegradationState(
        cohorts=tuple(updated),
        applied_augmentation_event_ids=state.applied_augmentation_event_ids,
    )
    return end_state, _snapshot(end_state, target_day, config), allocations


def warranty_discharge_headroom_mwh(
    snapshot: DegradationSnapshot,
    config: DegradationConfig,
) -> float | None:
    """Maximum additional cell discharge under proportional cohort allocation.

    Returns `None` when no EFC warranty assumption is configured. The headroom is a
    model constraint, not an interpretation of enforceable OEM contract language.
    """

    limit = config.warranty_max_equivalent_full_cycles
    if limit is None:
        return None
    if snapshot.usable_energy_mwh <= TOLERANCE:
        return 0.0
    candidates: list[float] = []
    for cohort in snapshot.cohorts:
        share = cohort.usable_energy_mwh / snapshot.usable_energy_mwh
        if share <= TOLERANCE:
            continue
        remaining = max(
            0.0,
            (limit - cohort.cumulative_equivalent_full_cycles)
            * cohort.nominal_energy_mwh,
        )
        candidates.append(remaining / share)
    return max(0.0, min(candidates)) if candidates else 0.0


def simulate_degradation(
    daily_throughput: pd.DataFrame,
    *,
    nominal_energy_mwh: float,
    nominal_charge_power_mw: float,
    nominal_discharge_power_mw: float,
    config: DegradationConfig,
) -> DegradationSimulationResult:
    """Evolve degradation from daily cell-discharge observations."""

    required = {"market_day", "cell_discharge_mwh"}
    missing = sorted(required - set(daily_throughput.columns))
    if missing:
        raise DegradationInputError(
            "Daily throughput is missing required columns: " + ", ".join(missing)
        )
    working = daily_throughput.loc[:, ["market_day", "cell_discharge_mwh"]].copy()
    working["market_day"] = working["market_day"].map(
        lambda value: _as_date(value, "market_day")
    )
    working["cell_discharge_mwh"] = pd.to_numeric(
        working["cell_discharge_mwh"], errors="coerce"
    )
    if working["cell_discharge_mwh"].isna().any():
        raise DegradationInputError("cell_discharge_mwh contains unparseable values")
    if working["market_day"].duplicated().any():
        raise DegradationInputError("Daily throughput contains duplicate market_day rows")
    if not working["market_day"].is_monotonic_increasing:
        raise DegradationInputError("Daily throughput must be sorted by market_day")

    state = initialize_degradation_state(
        nominal_energy_mwh=nominal_energy_mwh,
        nominal_charge_power_mw=nominal_charge_power_mw,
        nominal_discharge_power_mw=nominal_discharge_power_mw,
        config=config,
    )
    records: list[dict[str, Any]] = []
    for record in working.itertuples(index=False):
        prepared, start, events = prepare_degradation_day(
            state, record.market_day, config
        )
        headroom = warranty_discharge_headroom_mwh(start, config)
        if (
            config.enforce_warranty_throughput_limit
            and headroom is not None
            and record.cell_discharge_mwh > headroom + 1e-7
        ):
            raise DegradationInputError(
                f"{record.market_day} cell discharge exceeds modeled warranty "
                f"headroom ({record.cell_discharge_mwh:.6f} > {headroom:.6f} MWh)"
            )
        state, end, allocations = complete_degradation_day(
            prepared,
            record.market_day,
            float(record.cell_discharge_mwh),
            config,
        )
        records.append(
            _daily_record(
                record.market_day,
                start,
                end,
                events,
                float(record.cell_discharge_mwh),
                headroom,
                allocations,
            )
        )

    if records:
        last_day = records[-1]["market_day"]
        final_snapshot = _snapshot(state, last_day, config)
    else:
        last_day = config.project_start_day
        final_snapshot = _snapshot(state, last_day, config)
    daily_states = pd.DataFrame.from_records(records)
    cohort_states = degradation_cohort_table(final_snapshot)
    total_augmentation_cost = sum(
        event.cost_eur
        for event in config.augmentation_events
        if event.event_id in state.applied_augmentation_event_ids
    )
    summary = {
        "result_label": DEGRADATION_MODEL_LABEL,
        "modeled_day_count": int(len(daily_states)),
        "first_market_day": (
            str(daily_states["market_day"].min()) if len(daily_states) else None
        ),
        "last_market_day": (
            str(daily_states["market_day"].max()) if len(daily_states) else None
        ),
        "initial_nominal_energy_mwh": float(nominal_energy_mwh),
        "final_nominal_energy_mwh": final_snapshot.nominal_energy_mwh,
        "final_usable_energy_mwh": final_snapshot.usable_energy_mwh,
        "final_retained_capacity_fraction": final_snapshot.retained_capacity_fraction,
        "final_usable_charge_power_mw": final_snapshot.usable_charge_power_mw,
        "final_usable_discharge_power_mw": final_snapshot.usable_discharge_power_mw,
        "cumulative_cell_discharge_mwh": (
            final_snapshot.cumulative_cell_discharge_mwh
        ),
        "applied_augmentation_event_count": len(
            state.applied_augmentation_event_ids
        ),
        "applied_augmentation_event_ids": list(
            state.applied_augmentation_event_ids
        ),
        "augmentation_cost_eur": float(total_augmentation_cost),
        "warranty_capacity_breach": final_snapshot.warranty_capacity_breach,
        "warranty_throughput_exceeded": (
            final_snapshot.warranty_throughput_exceeded
        ),
        "warranty_breach": final_snapshot.warranty_breach,
        "below_retirement_threshold": (
            final_snapshot.below_retirement_threshold
        ),
        "throughput_allocation_policy": (
            "Daily cell discharge allocated to cohorts in proportion to "
            "beginning-of-day usable energy"
        ),
        "fade_combination_policy": (
            "Linear calendar fade plus linear equivalent-cycle fade, capped at "
            "100% capacity loss per cohort"
        ),
        "config": config.to_dict(),
    }
    return DegradationSimulationResult(
        daily_states=daily_states,
        cohort_states=cohort_states,
        summary=summary,
        final_state=state,
    )


def degradation_cohort_table(snapshot: DegradationSnapshot) -> pd.DataFrame:
    """Convert a fleet snapshot to an auditable cohort table."""

    return pd.DataFrame.from_records(
        [
            {
                **asdict(cohort),
                "commissioned_day": cohort.commissioned_day,
                "snapshot_day": snapshot.day,
            }
            for cohort in snapshot.cohorts
        ]
    )


def _snapshot(
    state: DegradationState,
    day: date,
    config: DegradationConfig,
) -> DegradationSnapshot:
    cohorts: list[CohortSnapshot] = []
    for cohort in state.cohorts:
        if day < cohort.commissioned_day:
            raise DegradationInputError(
                f"Snapshot day {day} precedes cohort {cohort.cohort_id} commissioning"
            )
        age_years = (day - cohort.commissioned_day).days / YEAR_DAYS
        calendar_fade = min(
            1.0, age_years * config.calendar_fade_fraction_per_year
        )
        cumulative_efc = (
            cohort.cumulative_cell_discharge_mwh / cohort.nominal_energy_mwh
        )
        cycle_fade = min(
            1.0,
            cumulative_efc * config.cycle_fade_fraction_per_equivalent_cycle,
        )
        retained = max(0.0, 1.0 - calendar_fade - cycle_fade)
        power_retained = retained**config.power_fade_exponent
        warranty_active = (
            config.warranty_years is not None
            and age_years <= config.warranty_years + TOLERANCE
        )
        capacity_breach = bool(
            warranty_active
            and config.warranty_retained_capacity_fraction is not None
            and retained + TOLERANCE
            < config.warranty_retained_capacity_fraction
        )
        throughput_exceeded = bool(
            config.warranty_max_equivalent_full_cycles is not None
            and cumulative_efc
            > config.warranty_max_equivalent_full_cycles + TOLERANCE
        )
        cohorts.append(
            CohortSnapshot(
                cohort_id=cohort.cohort_id,
                commissioned_day=cohort.commissioned_day,
                age_years=age_years,
                nominal_energy_mwh=cohort.nominal_energy_mwh,
                nominal_charge_power_mw=cohort.nominal_charge_power_mw,
                nominal_discharge_power_mw=cohort.nominal_discharge_power_mw,
                cumulative_cell_discharge_mwh=(
                    cohort.cumulative_cell_discharge_mwh
                ),
                cumulative_equivalent_full_cycles=cumulative_efc,
                calendar_fade_fraction=calendar_fade,
                cycle_fade_fraction=cycle_fade,
                retained_capacity_fraction=retained,
                usable_energy_mwh=cohort.nominal_energy_mwh * retained,
                usable_charge_power_mw=(
                    cohort.nominal_charge_power_mw * power_retained
                ),
                usable_discharge_power_mw=(
                    cohort.nominal_discharge_power_mw * power_retained
                ),
                warranty_active=warranty_active,
                warranty_capacity_breach=capacity_breach,
                warranty_throughput_exceeded=throughput_exceeded,
            )
        )

    nominal_energy = sum(item.nominal_energy_mwh for item in cohorts)
    usable_energy = sum(item.usable_energy_mwh for item in cohorts)
    retained = usable_energy / nominal_energy if nominal_energy > TOLERANCE else 0.0
    capacity_breach = any(item.warranty_capacity_breach for item in cohorts)
    throughput_exceeded = any(item.warranty_throughput_exceeded for item in cohorts)
    below_retirement = bool(
        config.retirement_capacity_fraction is not None
        and retained + TOLERANCE < config.retirement_capacity_fraction
    )
    return DegradationSnapshot(
        day=day,
        cohorts=tuple(cohorts),
        nominal_energy_mwh=nominal_energy,
        usable_energy_mwh=usable_energy,
        nominal_charge_power_mw=sum(
            item.nominal_charge_power_mw for item in cohorts
        ),
        usable_charge_power_mw=sum(item.usable_charge_power_mw for item in cohorts),
        nominal_discharge_power_mw=sum(
            item.nominal_discharge_power_mw for item in cohorts
        ),
        usable_discharge_power_mw=sum(
            item.usable_discharge_power_mw for item in cohorts
        ),
        retained_capacity_fraction=retained,
        cumulative_cell_discharge_mwh=sum(
            item.cumulative_cell_discharge_mwh for item in cohorts
        ),
        warranty_capacity_breach=capacity_breach,
        warranty_throughput_exceeded=throughput_exceeded,
        warranty_breach=capacity_breach or throughput_exceeded,
        below_retirement_threshold=below_retirement,
    )


def _daily_record(
    market_day: date,
    start: DegradationSnapshot,
    end: DegradationSnapshot,
    events: tuple[AugmentationEvent, ...],
    cell_discharge_mwh: float,
    warranty_headroom_start_mwh: float | None,
    allocations: dict[str, float],
) -> dict[str, Any]:
    return {
        "market_day": market_day,
        "augmentation_event_ids": "|".join(event.event_id for event in events),
        "retired_cohort_ids": "|".join(
            cohort_id for event in events for cohort_id in event.retired_cohort_ids
        ),
        "augmentation_energy_mwh": float(
            sum(event.added_energy_mwh for event in events)
        ),
        "augmentation_charge_power_mw": float(
            sum(event.added_charge_power_mw for event in events)
        ),
        "augmentation_discharge_power_mw": float(
            sum(event.added_discharge_power_mw for event in events)
        ),
        "augmentation_cost_eur": float(sum(event.cost_eur for event in events)),
        "nominal_energy_mwh_start": start.nominal_energy_mwh,
        "usable_energy_mwh_start": start.usable_energy_mwh,
        "retained_capacity_fraction_start": start.retained_capacity_fraction,
        "usable_charge_power_mw_start": start.usable_charge_power_mw,
        "usable_discharge_power_mw_start": start.usable_discharge_power_mw,
        "cell_discharge_mwh": cell_discharge_mwh,
        "fleet_equivalent_full_cycles_increment": (
            cell_discharge_mwh / start.nominal_energy_mwh
            if start.nominal_energy_mwh > TOLERANCE
            else 0.0
        ),
        "cohort_allocation_mwh": "|".join(
            f"{cohort_id}:{value:.9f}"
            for cohort_id, value in allocations.items()
        ),
        "warranty_discharge_headroom_start_mwh": warranty_headroom_start_mwh,
        "usable_energy_mwh_end": end.usable_energy_mwh,
        "retained_capacity_fraction_end": end.retained_capacity_fraction,
        "usable_charge_power_mw_end": end.usable_charge_power_mw,
        "usable_discharge_power_mw_end": end.usable_discharge_power_mw,
        "cumulative_cell_discharge_mwh_end": (
            end.cumulative_cell_discharge_mwh
        ),
        "warranty_capacity_breach_end": end.warranty_capacity_breach,
        "warranty_throughput_exceeded_end": end.warranty_throughput_exceeded,
        "warranty_breach_end": end.warranty_breach,
        "below_retirement_threshold_end": end.below_retirement_threshold,
    }


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise DegradationInputError(f"{name} must be an ISO date") from exc
    raise DegradationInputError(f"{name} must be a date or ISO date string")


def _require_positive(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0:
        raise DegradationInputError(f"{name} must be finite and greater than 0")


def _require_nonnegative(name: str, value: float) -> None:
    if not np.isfinite(value) or value < 0:
        raise DegradationInputError(f"{name} must be finite and nonnegative")


def _require_fraction(name: str, value: float | None) -> None:
    if value is None or not np.isfinite(value) or not 0 <= value <= 1:
        raise DegradationInputError(f"{name} must be finite and between 0 and 1")
