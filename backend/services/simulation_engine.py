from typing import Dict, List

from backend.services.experience_service import experience_service
from backend.services.transition_engine import TransitionEngine


class SimulationEngine:
    def __init__(self, transition_engine: TransitionEngine | None = None) -> None:
        self.transition_engine = transition_engine or TransitionEngine(experiences=experience_service.get_all_experiences())

    def _classify_outcome(self, probability: float) -> str:
        if probability >= 0.75:
            return "Positive"
        if probability >= 0.45:
            return "Neutral"
        return "Negative"

    def simulate_action(self, current_state: Dict[str, int], action: str) -> Dict:
        predicted_growth = self.transition_engine.predict_skill_growth(current_state, action)
        predicted_success = self.transition_engine.predict_success_probability(current_state, action)

        future_state = dict(current_state)
        for skill, gain in predicted_growth.items():
            future_state[skill] = int(current_state.get(skill, 0) + gain)

        confidence = max(0.0, min(1.0, 0.5 + predicted_success * 0.4))
        expected_outcome = self._classify_outcome(predicted_success)
        return {
            "current_state": dict(current_state),
            "predicted_future_state": future_state,
            "confidence": round(confidence, 2),
            "expected_outcome": expected_outcome,
        }

    def simulate_plan(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        state = dict(current_state)
        steps = []
        for action in actions:
            result = self.simulate_action(state, action)
            state = result["predicted_future_state"]
            steps.append(
                {
                    "action": action,
                    "predicted_future_state": state,
                    "confidence": result["confidence"],
                    "expected_outcome": result["expected_outcome"],
                }
            )

        success_probability = min(1.0, 0.5 + (len(steps) * 0.08))
        expected_outcome = self._classify_outcome(success_probability)
        return {
            "steps": steps,
            "predicted_future_state": state,
            "final_state": state,
            "success_probability": round(success_probability, 2),
            "expected_outcome": expected_outcome,
            "summary": f"Python: {current_state.get('python', 0)} -> {state.get('python', 0)}",
        }


simulation_engine = SimulationEngine()
