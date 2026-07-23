from typing import Dict, List

from backend.models.experience import Experience


class EvaluationService:
    def __init__(self, experiences: List[Experience] | None = None) -> None:
        self.experiences = experiences or []

    def prediction_error(self, predicted_gain: float, actual_gain: float) -> float:
        return round(abs(predicted_gain - actual_gain), 2)

    def success_prediction_accuracy(self, predicted_probability: float, actual_outcome: float) -> float:
        actual_label = 1.0 if actual_outcome >= 0.5 else 0.0
        predicted_label = 1.0 if predicted_probability >= 0.5 else 0.0
        return round(1.0 if actual_label == predicted_label else 0.0, 2)

    def state_prediction_accuracy(self, predicted_state: Dict, actual_state: Dict) -> float:
        if not predicted_state and not actual_state:
            return 1.0
        if not predicted_state or not actual_state:
            return 0.0

        shared_keys = set(predicted_state.keys()) & set(actual_state.keys())
        if not shared_keys:
            return 0.0

        correct = sum(1 for key in shared_keys if predicted_state.get(key) == actual_state.get(key))
        return round(correct / len(shared_keys), 2)
