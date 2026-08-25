"""Battery capacity degradation and augmentation interfaces."""

from .model import (
    DEGRADATION_MODEL_LABEL,
    AugmentationEvent,
    CohortSnapshot,
    CohortState,
    DegradationConfig,
    DegradationInputError,
    DegradationSimulationResult,
    DegradationSnapshot,
    DegradationState,
    complete_degradation_day,
    degradation_cohort_table,
    initialize_degradation_state,
    prepare_degradation_day,
    simulate_degradation,
    warranty_discharge_headroom_mwh,
)

__all__ = [
    "DEGRADATION_MODEL_LABEL",
    "AugmentationEvent",
    "CohortSnapshot",
    "CohortState",
    "DegradationConfig",
    "DegradationInputError",
    "DegradationSimulationResult",
    "DegradationSnapshot",
    "DegradationState",
    "complete_degradation_day",
    "degradation_cohort_table",
    "initialize_degradation_state",
    "prepare_degradation_day",
    "simulate_degradation",
    "warranty_discharge_headroom_mwh",
]
