"""One declared integrated study: a window, its strategies and the three configurations.

The study is the composition the repository could not previously express. Each module it
drives already refuses its own bad inputs; what had no owner was the join between them, and
this module is where that join is declared rather than assembled by hand.

Every judgmental value here is declared, never defaulted: the window, the price source, the
strategies and the battery, degradation and finance assumptions all arrive from one file.
The design of record is ``docs/integrated_study_design.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ..degradation import DegradationConfig
from ..dispatch import BatteryDispatchConfig
from ..finance import FinanceConfig
from ..forecast import FORECAST_METHODS

#: The planner that reads the delivery day's realized prices. It is a strategy like any other
#: here, with its own ageing state, and never a ceiling over the other strategies once those
#: states have diverged (design §5.2).
PERFECT_FORESIGHT_PLANNER = "perfect_foresight"

FROZEN_SELECTION_PLANNERS = ("frozen_validation_rmse", "frozen_validation_margin")

#: Every planner a strategy may declare.
STUDY_PLANNERS: tuple[str, ...] = (
    *FORECAST_METHODS, PERFECT_FORESIGHT_PLANNER, *FROZEN_SELECTION_PLANNERS,
)

#: Which information set each planner reads, as the declaration a strategy must make about
#: itself. A strategy states what it may read; this mapping is what makes that statement
#: checkable rather than decorative.
DECISION_INFORMATION_SETS: dict[str, tuple[str, ...]] = {
    "price_history_before_delivery_day": FORECAST_METHODS,
    "realized_delivery_day_prices": (PERFECT_FORESIGHT_PLANNER,),
    "accepted_frozen_causal_forecasts": FROZEN_SELECTION_PLANNERS,
}

#: Recorded, never inferred. A study on synthetic prices is a demonstration and says so.
PRICE_SOURCES = ("official", "synthetic")

#: How a strategy's settled operating path is described to the finance model. The case is a
#: property of the path, not of the cost and discounting basis, so it cannot be read off the
#: one `FinanceConfig` a study declares; see `operating_margin_case_for`.
OPERATING_MARGIN_CASE_BY_PLANNER: dict[str, str] = {
    PERFECT_FORESIGHT_PLANNER: "daily_policy_degraded_simulation",
    **{method: "historical_forecast_backtest" for method in FORECAST_METHODS},
    **{method: "historical_forecast_backtest" for method in FROZEN_SELECTION_PLANNERS},
}

STUDY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class IntegratedStudyInputError(ValueError):
    """Raised when a declared study cannot be run exactly as it was declared."""


@dataclass(frozen=True)
class SyntheticPriceGenerationConfig:
    """Every input needed to reproduce a synthetic study price history."""

    history_start_day: date
    resolution_minutes: int
    seed: int
    negative_price_share: float
    retrieved_at_utc: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "history_start_day", _as_date(self.history_start_day, "history_start_day")
        )
        if self.resolution_minutes not in (15, 60):
            raise IntegratedStudyInputError("synthetic resolution_minutes must be 15 or 60")
        if not isinstance(self.seed, int):
            raise IntegratedStudyInputError("synthetic seed must be an integer")
        if not 0.0 <= self.negative_price_share <= 0.25:
            raise IntegratedStudyInputError(
                "synthetic negative_price_share must be between 0 and 0.25"
            )
        try:
            parsed = datetime.fromisoformat(
                self.retrieved_at_utc.replace("Z", "+00:00")
            )
        except (AttributeError, ValueError) as exc:
            raise IntegratedStudyInputError(
                "synthetic retrieved_at_utc must be an ISO timestamp"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise IntegratedStudyInputError(
                "synthetic retrieved_at_utc must include a UTC offset"
            )
        if parsed.utcoffset() != timedelta(0):
            raise IntegratedStudyInputError(
                "synthetic retrieved_at_utc must use the UTC offset +00:00"
            )

    @classmethod
    def from_dict(cls, payload: Any) -> SyntheticPriceGenerationConfig:
        if not isinstance(payload, dict):
            raise IntegratedStudyInputError(
                "synthetic_price_generation must be one JSON object"
            )
        required = {
            "history_start_day",
            "resolution_minutes",
            "seed",
            "negative_price_share",
            "retrieved_at_utc",
        }
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise IntegratedStudyInputError(
                "Unknown synthetic price generation fields: " + ", ".join(unknown)
            )
        if missing:
            raise IntegratedStudyInputError(
                "Missing synthetic price generation fields: " + ", ".join(missing)
            )
        return cls(
            history_start_day=_as_date(payload["history_start_day"], "history_start_day"),
            resolution_minutes=int(payload["resolution_minutes"]),
            seed=int(payload["seed"]),
            negative_price_share=float(payload["negative_price_share"]),
            retrieved_at_utc=str(payload["retrieved_at_utc"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_start_day": self.history_start_day.isoformat(),
            "resolution_minutes": self.resolution_minutes,
            "seed": self.seed,
            "negative_price_share": self.negative_price_share,
            "retrieved_at_utc": self.retrieved_at_utc,
        }


def operating_margin_case_for(planner: str) -> str:
    """Name the finance operating-margin case a planner's settled path belongs to."""

    case = OPERATING_MARGIN_CASE_BY_PLANNER.get(planner)
    if case is None:
        raise IntegratedStudyInputError(f"Unknown planner: {planner}")
    return case


@dataclass(frozen=True)
class StrategySpec:
    """One compared strategy: what it is called, what it plans with, what it may read."""

    strategy_id: str
    planner: str
    decision_information: str

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_id, str) or not self.strategy_id.strip():
            raise IntegratedStudyInputError("strategy_id must be a non-empty string")
        if self.strategy_id != self.strategy_id.strip():
            raise IntegratedStudyInputError(
                "strategy_id must not have surrounding whitespace"
            )
        if self.planner not in STUDY_PLANNERS:
            raise IntegratedStudyInputError(
                f"Strategy {self.strategy_id} declares unknown planner {self.planner!r}; "
                f"known planners: {', '.join(STUDY_PLANNERS)}"
            )
        permitted = DECISION_INFORMATION_SETS.get(self.decision_information)
        if permitted is None:
            raise IntegratedStudyInputError(
                f"Strategy {self.strategy_id} declares unknown decision_information "
                f"{self.decision_information!r}; known sets: "
                + ", ".join(sorted(DECISION_INFORMATION_SETS))
            )
        if self.planner not in permitted:
            raise IntegratedStudyInputError(
                f"Strategy {self.strategy_id} declares planner {self.planner!r} under "
                f"information set {self.decision_information!r}, which that planner does not "
                "read. A strategy that misdescribes what it knows is the one error this "
                "comparison cannot survive"
            )

    @property
    def reads_realized_delivery_day_prices(self) -> bool:
        return self.planner == PERFECT_FORESIGHT_PLANNER

    @property
    def operating_margin_case(self) -> str:
        return operating_margin_case_for(self.planner)

    @classmethod
    def from_dict(cls, payload: Any) -> StrategySpec:
        if not isinstance(payload, dict):
            raise IntegratedStudyInputError("Every strategy must be one JSON object")
        required = {"strategy_id", "planner", "decision_information"}
        unknown = sorted(set(payload) - required)
        missing = sorted(required - set(payload))
        if unknown:
            raise IntegratedStudyInputError(
                f"Unknown strategy fields: {', '.join(unknown)}"
            )
        if missing:
            raise IntegratedStudyInputError(
                f"Missing strategy fields: {', '.join(missing)}"
            )
        return cls(
            strategy_id=str(payload["strategy_id"]),
            planner=str(payload["planner"]),
            decision_information=str(payload["decision_information"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "planner": self.planner,
            "decision_information": self.decision_information,
            "operating_margin_case": self.operating_margin_case,
        }


@dataclass(frozen=True)
class IntegratedStudyConfig:
    """One study configuration, read from one file and driving one command."""

    study_id: str
    window_start_day: date
    window_end_day: date
    price_source: str
    strategies: tuple[StrategySpec, ...]
    battery: BatteryDispatchConfig
    degradation: DegradationConfig
    finance: FinanceConfig
    result_label: str
    rolling_window_days: int = 28
    synthetic_price_generation: SyntheticPriceGenerationConfig | None = None
    selection_evidence_index_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.study_id, str) or not STUDY_ID_PATTERN.match(self.study_id):
            raise IntegratedStudyInputError(
                "study_id must start with a letter or digit and contain only letters, "
                "digits, dot, dash or underscore; it names every artifact the study writes"
            )
        object.__setattr__(
            self, "window_start_day", _as_date(self.window_start_day, "window_start_day")
        )
        object.__setattr__(
            self, "window_end_day", _as_date(self.window_end_day, "window_end_day")
        )
        if self.window_end_day < self.window_start_day:
            raise IntegratedStudyInputError(
                "window_end_day cannot precede window_start_day"
            )
        if self.price_source not in PRICE_SOURCES:
            raise IntegratedStudyInputError(
                "price_source must be one of: " + ", ".join(PRICE_SOURCES)
            )
        if self.price_source == "official" and self.synthetic_price_generation is not None:
            raise IntegratedStudyInputError(
                "An official study cannot declare synthetic_price_generation"
            )
        if (
            self.synthetic_price_generation is not None
            and self.synthetic_price_generation.history_start_day >= self.window_start_day
        ):
            raise IntegratedStudyInputError(
                "synthetic history_start_day must precede the study window so forecast "
                "strategies have declared prior information"
            )
        strategies = tuple(self.strategies)
        if not strategies:
            raise IntegratedStudyInputError("A study must declare at least one strategy")
        identifiers = [strategy.strategy_id for strategy in strategies]
        if len(identifiers) != len(set(identifiers)):
            raise IntegratedStudyInputError("strategy_id values must be unique")
        object.__setattr__(self, "strategies", strategies)

        frozen = set(self.planners) & set(FROZEN_SELECTION_PLANNERS)
        pin = self.selection_evidence_index_sha256
        if frozen:
            if frozen != set(FROZEN_SELECTION_PLANNERS) or any(
                sum(strategy.planner == planner for strategy in strategies) != 1
                for planner in FROZEN_SELECTION_PLANNERS
            ):
                raise IntegratedStudyInputError(
                    "Both frozen selection planners must be declared exactly once"
                )
            if not isinstance(pin, str) or re.fullmatch(r"[0-9a-f]{64}", pin) is None:
                raise IntegratedStudyInputError(
                    "Frozen selection requires a declared selection_evidence_index_sha256"
                )
        elif pin is not None:
            raise IntegratedStudyInputError("Selection evidence requires frozen selection planners")

        if not isinstance(self.result_label, str) or not self.result_label.strip():
            raise IntegratedStudyInputError(
                "result_label must state what this study is and is not"
            )
        if not isinstance(self.rolling_window_days, int) or self.rolling_window_days < 1:
            raise IntegratedStudyInputError(
                "rolling_window_days must be a positive integer"
            )

        # §5.4: every strategy restores the configured initial SOC at day end, so daily values
        # stay comparable and no strategy borrows energy across days.
        if not _close(
            self.battery.initial_soc_fraction,
            self.battery.effective_terminal_soc_fraction,
        ):
            raise IntegratedStudyInputError(
                "An integrated study requires terminal_soc_fraction to equal "
                "initial_soc_fraction; independent daily solves are otherwise not comparable "
                "and a strategy can borrow energy across days"
            )
        if self.degradation.project_start_day > self.window_start_day:
            raise IntegratedStudyInputError(
                "The study window cannot begin before the degradation project_start_day "
                f"({self.degradation.project_start_day.isoformat()})"
            )
        # §2: finance uses exactly the declared horizon. A shorter replay must not become a
        # longer project, and a longer finance horizon must not be filled from a shorter one.
        if (
            self.finance.project_start_day != self.window_start_day
            or self.finance.project_end_day != self.window_end_day
        ):
            raise IntegratedStudyInputError(
                "Finance must cover exactly the declared study window "
                f"{self.window_start_day.isoformat()}..{self.window_end_day.isoformat()}; "
                f"the finance configuration declares "
                f"{self.finance.project_start_day.isoformat()}.."
                f"{self.finance.project_end_day.isoformat()}. The study does not annualise, "
                "extrapolate or repeat a year"
            )
        derivable = sorted(set(OPERATING_MARGIN_CASE_BY_PLANNER.values()))
        if self.finance.operating_margin_case not in derivable:
            raise IntegratedStudyInputError(
                "The finance operating_margin_case must be one an integrated study can "
                f"produce ({', '.join(derivable)}); the case describes the operating path, "
                "and each strategy's path is described by its own planner"
            )

    @property
    def planners(self) -> tuple[str, ...]:
        """Declared planners, in declaration order, without repeats."""

        seen: list[str] = []
        for strategy in self.strategies:
            if strategy.planner not in seen:
                seen.append(strategy.planner)
        return tuple(seen)

    @property
    def forecast_methods(self) -> tuple[str, ...]:
        """The naive forecast methods this study must be able to produce for every day."""

        return tuple(
            planner for planner in self.planners if planner in FORECAST_METHODS
        )

    @property
    def window_days(self) -> tuple[date, ...]:
        span = (self.window_end_day - self.window_start_day).days
        return tuple(
            self.window_start_day + timedelta(days=offset) for offset in range(span + 1)
        )

    @classmethod
    def from_dict(cls, payload: Any) -> IntegratedStudyConfig:
        if not isinstance(payload, dict):
            raise IntegratedStudyInputError("A study configuration must be one JSON object")
        required = {
            "study_id",
            "window_start_day",
            "window_end_day",
            "price_source",
            "strategies",
            "battery",
            "degradation",
            "finance",
            "result_label",
        }
        optional = {
            "rolling_window_days", "synthetic_price_generation", "selection_evidence_index_sha256",
        }
        unknown = sorted(set(payload) - required - optional)
        missing = sorted(required - set(payload))
        if unknown:
            raise IntegratedStudyInputError(
                f"Unknown study configuration fields: {', '.join(unknown)}"
            )
        if missing:
            raise IntegratedStudyInputError(
                f"Missing study configuration fields: {', '.join(missing)}"
            )
        declared = payload["strategies"]
        if not isinstance(declared, list):
            raise IntegratedStudyInputError("strategies must be a list")
        battery = payload["battery"]
        if not isinstance(battery, dict):
            raise IntegratedStudyInputError("battery must be one JSON object")
        return cls(
            study_id=str(payload["study_id"]),
            window_start_day=_as_date(payload["window_start_day"], "window_start_day"),
            window_end_day=_as_date(payload["window_end_day"], "window_end_day"),
            price_source=str(payload["price_source"]),
            strategies=tuple(StrategySpec.from_dict(item) for item in declared),
            battery=BatteryDispatchConfig(**battery),
            degradation=DegradationConfig.from_dict(payload["degradation"]),
            finance=FinanceConfig.from_dict(payload["finance"]),
            result_label=str(payload["result_label"]),
            rolling_window_days=int(payload.get("rolling_window_days", 28)),
            selection_evidence_index_sha256=payload.get("selection_evidence_index_sha256"),
            synthetic_price_generation=(
                SyntheticPriceGenerationConfig.from_dict(payload["synthetic_price_generation"])
                if payload.get("synthetic_price_generation") is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "study_id": self.study_id,
            "window_start_day": self.window_start_day.isoformat(),
            "window_end_day": self.window_end_day.isoformat(),
            "window_day_count": len(self.window_days),
            "price_source": self.price_source,
            "rolling_window_days": self.rolling_window_days,
            "strategies": [strategy.to_dict() for strategy in self.strategies],
            "battery": self.battery.to_dict(),
            "degradation": self.degradation.to_dict(),
            "finance": self.finance.to_dict(),
            "result_label": self.result_label,
        }
        if self.synthetic_price_generation is not None:
            payload["synthetic_price_generation"] = self.synthetic_price_generation.to_dict()
        if self.selection_evidence_index_sha256 is not None:
            payload["selection_evidence_index_sha256"] = self.selection_evidence_index_sha256
        return payload


def read_integrated_study_config(path: Path) -> IntegratedStudyConfig:
    """Read one declared study configuration from one JSON file."""

    return IntegratedStudyConfig.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise IntegratedStudyInputError(f"{name} must be an ISO date: {exc}") from exc
    raise IntegratedStudyInputError(f"{name} must be an ISO date string")


def _close(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) <= 1e-12
