from typing import Dict, List


class OutcomeAnalyzer:
    def analyze(self, experience: Dict) -> Dict:
        predicted_state = experience.get("predicted_state", {})
        actual_state = experience.get("actual_state", {})
        completed_actions = experience.get("completed_actions", [])
        actions = experience.get("actions", [])
        total_actions = max(1, len(actions))

        prediction_error = 0.0
        if predicted_state or actual_state:
            keys = set(predicted_state.keys()) | set(actual_state.keys())
            errors = []
            for key in keys:
                errors.append(abs(predicted_state.get(key, 0) - actual_state.get(key, 0)))
            prediction_error = round(sum(errors) / len(errors), 2) if errors else 0.0

        goal_progress = 0.0
        if predicted_state and actual_state:
            goal_progress = round(sum(actual_state.values()) / max(1, sum(predicted_state.values())), 2) * 100

        completion_rate = round(len(completed_actions) / total_actions, 2) if actions else 0.0
        success_rate = round(1.0 if experience.get("success") else 0.0, 2)
        confidence_error = round(max(0.0, 0.5 - (completion_rate * 0.5)), 2)

        return {
            "prediction_error": prediction_error,
            "goal_progress": round(goal_progress, 2),
            "completion_rate": completion_rate,
            "success_rate": success_rate,
            "confidence_error": confidence_error,
        }
