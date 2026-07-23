from typing import Dict, List

from backend.ai.model_errors import ModelNotFoundError
from backend.ai.sequence_transition_model import SequenceTransitionModel
from backend.services.simulation_engine import SimulationEngine


class DigitalTwin:
    def __init__(self, simulation_engine: SimulationEngine | None = None) -> None:
        self.simulation_engine = simulation_engine or SimulationEngine()

    def simulate_action(self, current_state: Dict[str, int], action: str) -> Dict:
        return self.simulation_engine.simulate_action(current_state, action)

    def simulate_plan(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        state = dict(current_state)
        state_history = [dict(state)]
        step_results = []

        for action in actions:
            result = self.simulation_engine.simulate_action(state, action)
            state = result["predicted_future_state"]
            state_history.append(dict(state))
            step_results.append(
                {
                    "action": action,
                    "state": dict(state),
                    "confidence": result["confidence"],
                    "expected_outcome": result["expected_outcome"],
                }
            )

        final_confidence = round(sum(item["confidence"] for item in step_results) / len(step_results), 2) if step_results else 0.0
        return {
            "final_state": dict(state),
            "state_history": state_history,
            "steps": step_results,
            "confidence": final_confidence,
            "success_probability": round(max(0.0, min(1.0, 0.5 + (len(step_results) * 0.08))), 2),
            "predicted_future_state": dict(state),
        }

    def simulate_action_sequence(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        return self.simulate_plan(current_state, actions)


class LearnedDigitalTwin:
    def __init__(self, sequence_model: SequenceTransitionModel | None = None) -> None:
        self.sequence_model = sequence_model
        self.fallback_engine = DigitalTwin()

        if self.sequence_model is None:
            try:
                self.sequence_model = SequenceTransitionModel.load_model()
            except ModelNotFoundError:
                self.sequence_model = None

    def _predict_future_state(self, current_state: Dict[str, int], action: str, history: List[str]) -> Dict:
        prediction = self.sequence_model.predict(current_state, history, action)
        future_state = dict(current_state)
        growth_map = {
            "python_growth": "python",
            "machine_learning_growth": "machine_learning",
            "dsa_growth": "dsa",
            "project_growth": "projects",
        }

        for growth_key, skill in growth_map.items():
            delta = prediction.get(growth_key, 0.0)
            future_state[skill] = int(current_state.get(skill, 0) + delta)

        confidence = round(min(0.99, max(0.0, 0.55 + (sum(abs(value) for value in prediction.values()) / 100.0))), 2)
        return {
            "predicted_future_state": future_state,
            "confidence": confidence,
            "expected_outcome": prediction,
        }

    def simulate_action(self, current_state: Dict[str, int], action: str, history: List[str] | None = None) -> Dict:
        history = list(history or [])
        result = self._predict_future_state(current_state, action, history)
        return {
            "action": action,
            "history": list(history),
            "predicted_future_state": dict(result["predicted_future_state"]),
            "confidence": result["confidence"],
            "expected_outcome": result["expected_outcome"],
        }

    def simulate_action_sequence(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        if self.sequence_model is None:
            return self.fallback_engine.simulate_action_sequence(current_state, actions)

        state = dict(current_state)
        history: List[str] = []
        state_history = [dict(state)]
        step_results = []

        for action in actions:
            historical_context = list(history)
            result = self._predict_future_state(state, action, historical_context)
            state = result["predicted_future_state"]
            state_history.append(dict(state))
            history.append(action)
            step_results.append(
                {
                    "action": action,
                    "history": list(historical_context),
                    "state": dict(state),
                    "confidence": result["confidence"],
                    "expected_outcome": result["expected_outcome"],
                }
            )

        final_confidence = round(sum(item["confidence"] for item in step_results) / len(step_results), 2) if step_results else 0.0
        return {
            "final_state": dict(state),
            "state_history": state_history,
            "steps": step_results,
            "confidence": final_confidence,
            "success_probability": round(max(0.0, min(1.0, 0.5 + (len(step_results) * 0.08))), 2),
            "predicted_future_state": dict(state),
        }

    def simulate_plan(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        return self.simulate_action_sequence(current_state, actions)


digital_twin = LearnedDigitalTwin()
