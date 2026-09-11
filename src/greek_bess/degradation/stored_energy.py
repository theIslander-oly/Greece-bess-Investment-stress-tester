"""The stored-energy ledger that carries charge across market days.

Two units simulate a battery day by day under degradation: the degradation backtest in
`backtest/degradation_dispatch.py` and the integrated study in `study/runner.py`. Both face
the same question at every day boundary — how much energy is actually in the cells when the
day opens — and the answer is not "the configured state of charge". Capacity fades, cohorts
retire and augmentation adds capacity that is empty until somebody pays to fill it.

The accounting lives here once because the two units must agree. A second implementation
would be a second thing to keep in step, and the failure it would produce is silent: a
battery that begins a day with energy nobody charged still dispatches, still settles and
still reports a plausible margin.

**Conventions.**

- Stored energy is held per cohort and allocated proportionally to usable cohort capacity.
- Fade makes the same proportion of that cohort's stored energy unavailable. This is an
  explicit approximation, recorded as a loss rather than silently reset or sold.
- Retirement removes its cohort's stored energy.
- Added capacity starts empty. Energy in it exists only if the augmentation event declares
  `commissioning_energy_mwh`, whose cost the event declares separately and finance pays once.
- Every day closes with an energy balance that must reconcile, or the day is refused.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from .model import AugmentationEvent, DegradationInputError, DegradationSnapshot

if TYPE_CHECKING:  # pragma: no cover - import cycle only matters to the type checker
    from ..dispatch import BatteryDispatchConfig

#: The cohort id the initial system holds. `AugmentationEvent` refuses it, so no event can
#: overwrite the initial cohort's stored energy by colliding with its key.
INITIAL_COHORT_ID = "initial"

_ENERGY_TOLERANCE_MWH = 1e-8
_SOC_TOLERANCE = 1e-9


@dataclass(frozen=True)
class DayOpening:
    """What the battery holds when a market day opens, and where the difference went."""

    opening_energy_mwh: float
    retired_energy_mwh: float
    commissioning_energy_mwh: float
    commissioning_energy_cost_eur: float
    calendar_fade_energy_loss_mwh: float
    initial_energy_mwh: float
    initial_soc_fraction: float


@dataclass(frozen=True)
class DayClosing:
    """What the battery holds when the day ends, and every loss that got it there."""

    terminal_energy_mwh: float
    closing_energy_mwh: float
    cycle_fade_energy_loss_mwh: float
    conversion_loss_mwh: float
    self_discharge_loss_mwh: float
    balance_residual_mwh: float


class StoredEnergyLedger:
    """Carry stored energy across market days, one cohort at a time.

    The ledger is mutable and single-threaded on purpose: it follows one battery through one
    continuous sequence of days. A study comparing strategies holds one ledger per strategy,
    for the same reason it holds one degradation state per strategy.
    """

    def __init__(self, battery: BatteryDispatchConfig) -> None:
        self._stored = {
            INITIAL_COHORT_ID: battery.initial_soc_fraction * battery.energy_capacity_mwh
        }
        self._capacities = {INITIAL_COHORT_ID: battery.energy_capacity_mwh}

    @property
    def stored_energy_mwh(self) -> float:
        return float(sum(self._stored.values()))

    def open_day(
        self,
        start: DegradationSnapshot,
        events: Iterable[AugmentationEvent],
        battery: BatteryDispatchConfig,
    ) -> DayOpening:
        """Apply the day's augmentation events, then fade what is carried into it."""

        opening_energy = self.stored_energy_mwh
        retired_energy = 0.0
        commissioning_energy = 0.0
        commissioning_cost = 0.0
        for event in events:
            for cohort_id in event.retired_cohort_ids:
                retired_energy += self._stored.pop(cohort_id)
                self._capacities.pop(cohort_id)
            self._stored[event.event_id] = event.commissioning_energy_mwh
            self._capacities[event.event_id] = event.added_energy_mwh
            commissioning_energy += event.commissioning_energy_mwh
            commissioning_cost += event.commissioning_energy_cost_eur

        calendar_loss = 0.0
        initial_energy = 0.0
        for cohort in start.cohorts:
            capacity = self._capacities[cohort.cohort_id]
            retained = (
                self._stored[cohort.cohort_id] * cohort.usable_energy_mwh / capacity
                if capacity > 0
                else 0.0
            )
            if retained > cohort.usable_energy_mwh + _ENERGY_TOLERANCE_MWH:
                raise DegradationInputError(
                    "Commissioning energy exceeds usable capacity"
                )
            calendar_loss += self._stored[cohort.cohort_id] - retained
            initial_energy += retained

        initial_soc = initial_energy / start.usable_energy_mwh
        if not (
            battery.soc_min_fraction - _SOC_TOLERANCE
            <= initial_soc
            <= battery.soc_max_fraction + _SOC_TOLERANCE
        ):
            raise DegradationInputError(
                f"{start.day} carried and commissioned energy is outside SOC limits; "
                "declare commissioning energy or an admissible SOC range"
            )
        return DayOpening(
            opening_energy_mwh=opening_energy,
            retired_energy_mwh=retired_energy,
            commissioning_energy_mwh=commissioning_energy,
            commissioning_energy_cost_eur=commissioning_cost,
            calendar_fade_energy_loss_mwh=calendar_loss,
            initial_energy_mwh=initial_energy,
            initial_soc_fraction=float(
                np.clip(initial_soc, battery.soc_min_fraction, battery.soc_max_fraction)
            ),
        )

    def close_day(
        self,
        *,
        opening: DayOpening,
        start: DegradationSnapshot,
        end: DegradationSnapshot,
        schedule: pd.DataFrame,
        summary: dict[str, object],
        cell_discharge_mwh: float,
        battery: BatteryDispatchConfig,
    ) -> DayClosing:
        """Store the day's terminal energy by cohort and reconcile the day's balance."""

        terminal_energy = float(summary["terminal_energy_mwh"])  # type: ignore[arg-type]
        grid_charge = float(summary["grid_charge_mwh"])  # type: ignore[arg-type]
        grid_discharge = float(summary["grid_discharge_mwh"])  # type: ignore[arg-type]
        self._stored = {
            cohort.cohort_id: terminal_energy
            * cohort.usable_energy_mwh
            / start.usable_energy_mwh
            for cohort in end.cohorts
        }
        self._capacities = {
            cohort.cohort_id: cohort.usable_energy_mwh for cohort in end.cohorts
        }
        closing_energy = self.stored_energy_mwh
        cycle_loss = terminal_energy - closing_energy
        conversion_loss = (
            grid_charge * (1 - battery.charge_efficiency)
            + cell_discharge_mwh
            - grid_discharge
        )
        self_discharge_loss = float(
            (
                schedule["energy_start_mwh"]
                * (
                    1
                    - (1 - battery.self_discharge_per_hour)
                    ** schedule["duration_hours"]
                )
            ).sum()
        )
        residual = (
            opening.opening_energy_mwh
            + opening.commissioning_energy_mwh
            + grid_charge
            - grid_discharge
            - opening.retired_energy_mwh
            - opening.calendar_fade_energy_loss_mwh
            - cycle_loss
            - conversion_loss
            - self_discharge_loss
            - closing_energy
        )
        if abs(residual) > 1e-6 * max(1.0, start.usable_energy_mwh):
            raise DegradationInputError(
                f"{start.day} stored-energy ledger does not reconcile"
            )
        return DayClosing(
            terminal_energy_mwh=terminal_energy,
            closing_energy_mwh=closing_energy,
            cycle_fade_energy_loss_mwh=cycle_loss,
            conversion_loss_mwh=conversion_loss,
            self_discharge_loss_mwh=self_discharge_loss,
            balance_residual_mwh=residual,
        )


def refuse_augmentation_before(
    first_day: object, events: Iterable[AugmentationEvent]
) -> None:
    """Refuse an augmentation dated before the first simulated day.

    Its cost and its commissioned energy would both fall outside the ledger, so the run would
    begin with capacity nobody paid for.
    """

    if any(event.day < first_day for event in events):  # type: ignore[operator]
        raise DegradationInputError(
            "Augmentation before the simulated horizon requires a prior energy and cost history"
        )
