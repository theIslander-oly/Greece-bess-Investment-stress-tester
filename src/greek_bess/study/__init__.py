"""The integrated study: forecasting, ageing, settlement and cash flows in one run."""

from .config import (
    DECISION_INFORMATION_SETS,
    PERFECT_FORESIGHT_PLANNER,
    PRICE_SOURCES,
    STUDY_PLANNERS,
    IntegratedStudyConfig,
    IntegratedStudyInputError,
    StrategySpec,
    operating_margin_case_for,
    read_integrated_study_config,
)
from .results import (
    INTEGRATED_STUDY_BASIS_NOTE,
    INTEGRATED_STUDY_LABEL,
    IntegratedStudyResult,
    assemble_integrated_study,
)
from .runner import IntegratedStudyRun, StrategyRun, run_integrated_study

__all__ = [
    "DECISION_INFORMATION_SETS",
    "INTEGRATED_STUDY_BASIS_NOTE",
    "INTEGRATED_STUDY_LABEL",
    "PERFECT_FORESIGHT_PLANNER",
    "PRICE_SOURCES",
    "STUDY_PLANNERS",
    "IntegratedStudyConfig",
    "IntegratedStudyInputError",
    "IntegratedStudyResult",
    "IntegratedStudyRun",
    "StrategyRun",
    "StrategySpec",
    "assemble_integrated_study",
    "operating_margin_case_for",
    "read_integrated_study_config",
    "run_integrated_study",
]
