"""Stage 9: does selecting a forecast by battery value beat selecting it by price error?"""

from .candidates import (
    DECLARED_CANDIDATES,
    SelectionCandidate,
    SelectionCandidateError,
    generate_candidate_forecasts,
    validate_candidates,
)
from .experiment import (
    MARGIN_OBJECTIVE,
    RMSE_OBJECTIVE,
    SELECTION_OBJECTIVES,
    VALUE_SELECTION_RESULT_LABEL,
    ValueSelectionInputError,
    ValueSelectionResult,
    compare_selection_objectives,
)

__all__ = [
    "DECLARED_CANDIDATES",
    "MARGIN_OBJECTIVE",
    "RMSE_OBJECTIVE",
    "SELECTION_OBJECTIVES",
    "VALUE_SELECTION_RESULT_LABEL",
    "SelectionCandidate",
    "SelectionCandidateError",
    "ValueSelectionInputError",
    "ValueSelectionResult",
    "compare_selection_objectives",
    "generate_candidate_forecasts",
    "validate_candidates",
]
