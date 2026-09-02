"""The declared day-ahead decision cutoff: dated gate-closure regimes with no default.

This module holds the gate-closure schedule itself, separated from the ADMIE publication-timing
audit that first needed it. The separation is not tidiness. ``admie_timing`` is documented as
**retained but unused** — ADMIE load and RES forecasts left scope on 2026-09-01 — and a live
point-in-time feature path must not import its decision rule from a module whose own docstring
says nothing it does is currently used. The classes below are the same ones, moved without a
behaviour change; ``admie_timing`` re-exports them so nothing ADMIE-facing moves.

What the schedule is, and what it deliberately is not:

**It is declared, never defaulted.** A closure time is a market rule that changes across a
multi-year history, so a schedule is one or more dated regimes, each naming the clock it is
stated on and carrying a required reference to the rule it came from. There is no constant, no
environment fallback and no "SDAC default" in this repository. A delivery day earlier than the
first declared regime is refused rather than judged against a rule that was not in force.

**The comparison is strict.** A datum is available for delivery day D only when its publication
instant is strictly before ``closure_utc(D) - decision_lead_minutes``. A publication at the
cutoff is late. The decision lead is the second declared quantity: a bidder must build a
forecast, plan and submit before the gate, and how long that takes is a judgment this repository
also refuses to supply. It may be declared as zero; it may not be omitted.

**The tooling cannot check the declaration.** It reports whatever closure is declared. That is
why :func:`read_decision_cutoff_schedule` refuses the committed example outright: an example
copied into a run unchanged would make a placeholder into evidence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

DECLARABLE_CLOSURE_TIMEZONES = frozenset({"Europe/Athens", "Europe/Brussels", "UTC"})

#: Text that marks a committed configuration example as an example. An operator declaration
#: replaces both: the identifier names the operator's own schedule, and the reference cites the
#: rulebook section and its effective dates.
EXAMPLE_PLACEHOLDER_MARKER = "REPLACE BEFORE USE."
EXAMPLE_PLACEHOLDER_IDENTIFIER = "example-not-a-declaration"


class DecisionCutoffError(ValueError):
    """Raised when a decision cutoff cannot be resolved exactly as declared."""


@dataclass(frozen=True)
class GateClosureRegime:
    """One dated day-ahead gate-closure rule.

    ``closure_day_offset`` is counted in days from the delivery day and must not be positive:
    a closure on the delivery day itself or later would make the whole question moot. The
    ``reference`` is required so the rule behind an accepted day is on the record.
    """

    effective_from_delivery_day: date
    closure_day_offset: int
    closure_local_time: time
    closure_timezone: str
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.effective_from_delivery_day, date) or isinstance(
            self.effective_from_delivery_day, datetime
        ):
            raise DecisionCutoffError(
                "effective_from_delivery_day must be a calendar date, not a timestamp"
            )
        if isinstance(self.closure_day_offset, bool) or not isinstance(
            self.closure_day_offset, int
        ):
            raise DecisionCutoffError("closure_day_offset must be an integer")
        if self.closure_day_offset > 0:
            raise DecisionCutoffError(
                "closure_day_offset must not be positive; a gate closing after the delivery "
                "day starts cannot bound a day-ahead decision"
            )
        if not isinstance(self.closure_local_time, time):
            raise DecisionCutoffError("closure_local_time must be a time of day")
        if self.closure_local_time.tzinfo is not None:
            raise DecisionCutoffError(
                "closure_local_time must be a naive time of day; declare its clock in "
                "closure_timezone"
            )
        if self.closure_timezone not in DECLARABLE_CLOSURE_TIMEZONES:
            allowed = ", ".join(sorted(DECLARABLE_CLOSURE_TIMEZONES))
            raise DecisionCutoffError(
                f"closure_timezone must be one of: {allowed}"
            )
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise DecisionCutoffError(
                "reference must name the market rule or publication the closure comes from"
            )

    def closure_utc(self, delivery_day: date) -> pd.Timestamp:
        """Return the closure instant in UTC for one delivery day."""

        naive = datetime.combine(
            delivery_day + timedelta(days=self.closure_day_offset), self.closure_local_time
        )
        try:
            localized = pd.Timestamp(naive).tz_localize(
                ZoneInfo(self.closure_timezone), nonexistent="raise", ambiguous="raise"
            )
        # pandas raises a pytz NonExistentTimeError/AmbiguousTimeError here, and pytz is a
        # transitive dependency this project does not import; the refusal is the same for
        # either, so the localization call is guarded rather than the exception class named.
        except Exception as exc:
            raise DecisionCutoffError(
                f"Gate closure {self.closure_local_time.isoformat()} "
                f"{self.closure_timezone} does not exist exactly once on "
                f"{(delivery_day + timedelta(days=self.closure_day_offset)).isoformat()}; a "
                "daylight-saving transition makes the declared closure ambiguous and it is "
                "refused rather than guessed"
            ) from exc
        return localized.tz_convert("UTC")

    def to_dict(self) -> dict[str, Any]:
        return {
            "effective_from_delivery_day": self.effective_from_delivery_day.isoformat(),
            "closure_day_offset": int(self.closure_day_offset),
            "closure_local_time": self.closure_local_time.isoformat(),
            "closure_timezone": self.closure_timezone,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class GateClosureSchedule:
    """An ordered, dated sequence of declared gate-closure regimes."""

    schedule_id: str
    regimes: tuple[GateClosureRegime, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.schedule_id, str) or not self.schedule_id.strip():
            raise DecisionCutoffError("schedule_id must be a non-empty string")
        if self.schedule_id != self.schedule_id.strip():
            raise DecisionCutoffError("schedule_id must not have surrounding whitespace")
        if not isinstance(self.regimes, tuple) or not self.regimes:
            raise DecisionCutoffError(
                "A gate-closure schedule must declare at least one regime; there is no default "
                "closure time"
            )
        for regime in self.regimes:
            if not isinstance(regime, GateClosureRegime):
                raise DecisionCutoffError("Every regime must be a GateClosureRegime")
        days = [regime.effective_from_delivery_day for regime in self.regimes]
        if days != sorted(days):
            raise DecisionCutoffError(
                "Gate-closure regimes must be declared in ascending effective_from_delivery_day "
                "order"
            )
        if len(set(days)) != len(days):
            raise DecisionCutoffError(
                "Two gate-closure regimes share an effective_from_delivery_day; a delivery day "
                "would have two declared closures"
            )

    @classmethod
    def from_dict(cls, payload: object) -> GateClosureSchedule:
        if not isinstance(payload, Mapping):
            raise DecisionCutoffError("Gate-closure schedule config must be one object")
        required = {"schedule_id", "regimes"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise DecisionCutoffError(
                f"Unknown gate-closure schedule fields: {', '.join(unknown)}"
            )
        if missing:
            raise DecisionCutoffError(
                f"Missing gate-closure schedule fields: {', '.join(missing)}"
            )
        declared = payload["regimes"]
        if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
            raise DecisionCutoffError("regimes must be a non-empty list")
        return cls(
            schedule_id=str(payload["schedule_id"]),
            regimes=tuple(_regime_from_dict(entry) for entry in declared),
        )

    def regime_for(self, delivery_day: date) -> GateClosureRegime:
        selected: GateClosureRegime | None = None
        for regime in self.regimes:
            if regime.effective_from_delivery_day <= delivery_day:
                selected = regime
        if selected is None:
            raise DecisionCutoffError(
                f"Delivery day {delivery_day.isoformat()} precedes the first declared "
                f"gate-closure regime ({self.regimes[0].effective_from_delivery_day.isoformat()}); "
                "a day is not audited against a rule that was not declared for it"
            )
        return selected

    def closure_utc(self, delivery_day: date) -> pd.Timestamp:
        return self.regime_for(delivery_day).closure_utc(delivery_day)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "regimes": [regime.to_dict() for regime in self.regimes],
        }

def _regime_from_dict(payload: object) -> GateClosureRegime:
    if not isinstance(payload, Mapping):
        raise DecisionCutoffError("Every gate-closure regime must be an object")
    required = {
        "effective_from_delivery_day",
        "closure_day_offset",
        "closure_local_time",
        "closure_timezone",
        "reference",
    }
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown:
        raise DecisionCutoffError(
            f"Unknown gate-closure regime fields: {', '.join(unknown)}"
        )
    if missing:
        raise DecisionCutoffError(
            f"Missing gate-closure regime fields: {', '.join(missing)}"
        )
    try:
        effective_from = date.fromisoformat(str(payload["effective_from_delivery_day"]))
        closure_time = time.fromisoformat(str(payload["closure_local_time"]))
    except ValueError as exc:
        raise DecisionCutoffError(
            "effective_from_delivery_day must be an ISO date and closure_local_time an ISO time"
        ) from exc
    offset = payload["closure_day_offset"]
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise DecisionCutoffError("closure_day_offset must be an integer")
    return GateClosureRegime(
        effective_from_delivery_day=effective_from,
        closure_day_offset=offset,
        closure_local_time=closure_time,
        closure_timezone=str(payload["closure_timezone"]),
        reference=str(payload["reference"]),    )


def read_decision_cutoff_schedule(path: Path) -> GateClosureSchedule:
    """Read a declared decision-cutoff schedule, refusing the committed example.

    :meth:`GateClosureSchedule.from_dict` stays permissive on purpose: it is the parser the
    committed example must keep passing, so that the example cannot drift away from the reader
    that will read the real declaration. This function is the gate in front of it. Gate G3 of
    the v0.9 design says nothing runs while the placeholder reference remains, and a refusal at
    the door is the only place that rule can be enforced without also refusing the example test.
    """

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    schedule = GateClosureSchedule.from_dict(payload)
    if schedule.schedule_id == EXAMPLE_PLACEHOLDER_IDENTIFIER:
        raise DecisionCutoffError(
            f"{path}: schedule_id is still {EXAMPLE_PLACEHOLDER_IDENTIFIER!r}. This is the "
            "committed format example, not a declaration. Copy it, name your own schedule and "
            "cite the day-ahead trading rule that was in force; there is no default cutoff."
        )
    placeholders = [
        regime.effective_from_delivery_day.isoformat()
        for regime in schedule.regimes
        if EXAMPLE_PLACEHOLDER_MARKER in regime.reference
    ]
    if placeholders:
        raise DecisionCutoffError(
            f"{path}: the regime effective from {', '.join(placeholders)} still carries the "
            f"{EXAMPLE_PLACEHOLDER_MARKER!r} placeholder reference. Cite the rulebook section "
            "and its effective dates; the tooling reports whatever closure is declared and "
            "cannot check the declaration against the market rules."
        )
    return schedule


def validate_decision_lead_minutes(value: object) -> int:
    """Return a declared decision lead in minutes, refusing anything that was not declared.

    Zero is a declaration and is accepted: an operator may state that no lead is taken. ``None``
    is not, and neither is a negative lead, which would place the effective cutoff *after* the
    gate and admit information a bidder could not have had.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        raise DecisionCutoffError(
            "decision_lead_minutes must be declared as an integer number of minutes; it has no "
            "default and may be 0, but it may not be omitted"
        )
    if value < 0:
        raise DecisionCutoffError(
            "decision_lead_minutes must not be negative; a negative lead would place the "
            "effective cutoff after the declared gate closure"
        )
    return int(value)


def effective_cutoff_utc(
    schedule: GateClosureSchedule, delivery_day: date, decision_lead_minutes: int
) -> pd.Timestamp:
    """Return the instant a feature must be published strictly before, for one delivery day."""

    lead = validate_decision_lead_minutes(decision_lead_minutes)
    return schedule.closure_utc(delivery_day) - pd.Timedelta(lead, unit="min")
