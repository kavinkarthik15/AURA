from typing import Dict, List


class ActionRanker:
    def rank_actions(self, actions: List[Dict], current_state: Dict[str, int] | None = None, transition_engine=None) -> List[Dict]:
        ranked = []
        for action in actions:
            action_name = action.get("name", "")
            expected_growth = action.get("expected_growth", 0)
            success_probability = action.get("success_probability", 0.0)
            confidence = action.get("confidence", 0.0)

            if transition_engine is not None and current_state is not None:
                predicted_growth = transition_engine.predict_skill_growth(current_state, action_name)
                predicted_success = transition_engine.predict_success_probability(current_state, action_name)
                expected_growth = max(expected_growth, predicted_growth.get(next(iter(current_state.keys()), "skill"), 0))
                success_probability = max(success_probability, predicted_success)

            score = (expected_growth * 0.5) + (success_probability * 0.3) + (confidence * 0.2)
            ranked.append({**action, "score": score})
        return sorted(ranked, key=lambda item: item["score"], reverse=True)
