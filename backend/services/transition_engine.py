from typing import Dict, List

from backend.models.experience import Experience
from backend.services.experience_service import experience_service
from backend.services.state_similarity import find_similar_transitions


class TransitionEngine:
    def __init__(self, experiences: List[Experience] | None = None) -> None:
        self.experiences = experiences or experience_service.get_all_experiences()

    def get_similar_experiences(self, current_state: Dict, action: str) -> List[Experience]:
        scored_matches = find_similar_transitions(self.experiences, current_state, action)
        return [experience for experience, _ in scored_matches]

    def predict_skill_growth(self, current_state: Dict, action: str) -> Dict:
        matches = self.get_similar_experiences(current_state, action)
        if not matches:
            return {skill: 0 for skill in current_state}

        predictions: Dict = {}
        for skill in current_state:
            deltas = []
            weights = []
            for experience in matches:
                if skill not in experience.state_delta:
                    continue
                deltas.append(experience.state_delta.get(skill, 0))
                weights.append(getattr(experience, "experience_weight", 1.0) * getattr(experience, "experience_confidence", 0.5))
            if deltas and weights:
                total_weight = sum(weights)
                predictions[skill] = round(sum(delta * weight for delta, weight in zip(deltas, weights)) / total_weight, 2)
            else:
                predictions[skill] = 0
        return predictions

    def predict_success_probability(self, current_state: Dict, action: str) -> float:
        matches = self.get_similar_experiences(current_state, action)
        if not matches:
            return 0.0

        weighted_outcomes = [
            experience.outcome_value
            * getattr(experience, "experience_weight", 1.0)
            * getattr(experience, "experience_confidence", 0.5)
            for experience in matches
        ]
        total_weight = sum(getattr(experience, "experience_weight", 1.0) * getattr(experience, "experience_confidence", 0.5) for experience in matches)
        avg_outcome = sum(weighted_outcomes) / total_weight if total_weight else 0.0
        probability = max(0.0, min(1.0, avg_outcome))
        return round(probability, 2)

    def predict_future_state(self, current_state: Dict, action: str) -> Dict:
        predicted_growth = self.predict_skill_growth(current_state, action)
        future_state = dict(current_state)
        for skill, gain in predicted_growth.items():
            future_state[skill] = int(current_state.get(skill, 0) + gain)
        return future_state


transition_engine = TransitionEngine()
