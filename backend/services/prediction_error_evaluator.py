from __future__ import annotations

from copy import deepcopy
from typing import Dict, Optional

from backend.models.decision_outcome import DecisionOutcome
from backend.models.prediction_error_result import PredictionErrorResult


class PredictionErrorEvaluator:
    def evaluate(
        self,
        decision_outcome: DecisionOutcome,
    ) -> PredictionErrorResult:
        predicted_state = deepcopy(decision_outcome.predicted_state or {})
        actual_state = deepcopy(decision_outcome.actual_state or {})

        state_errors: Dict[str, float] = {}
        signed_state_errors: Dict[str, float] = {}
        actual_available = bool(actual_state)
        prediction_error: Optional[float] = None
        mean_absolute_error: Optional[float] = None
        max_absolute_error: Optional[float] = None

        if actual_available:
            all_keys = sorted(set(predicted_state.keys()) | set(actual_state.keys()))
            for key in all_keys:
                predicted_value = float(predicted_state.get(key, 0.0) or 0.0)
                actual_value = float(actual_state.get(key, 0.0) or 0.0)
                abs_error = abs(predicted_value - actual_value)
                signed_error = actual_value - predicted_value
                state_errors[key] = abs_error
                signed_state_errors[key] = signed_error

            if state_errors:
                values = list(state_errors.values())
                prediction_error = round(sum(values) / len(values), 2)
                mean_absolute_error = round(sum(values) / len(values), 2)
                max_absolute_error = round(max(values), 2)

        return PredictionErrorResult(
            decision_id=decision_outcome.decision_id,
            prediction_error=prediction_error,
            state_errors=state_errors,
            signed_state_errors=signed_state_errors,
            mean_absolute_error=mean_absolute_error,
            max_absolute_error=max_absolute_error,
            state_dimensions=len(state_errors),
            actual_available=actual_available,
        )
