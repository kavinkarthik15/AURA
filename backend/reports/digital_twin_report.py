from __future__ import annotations

from typing import Any, Dict, List

from backend.services.plan_evaluator import PlanEvaluator


class DigitalTwinReport:
    def __init__(self, evaluator: PlanEvaluator | None = None) -> None:
        self.evaluator = evaluator or PlanEvaluator()

    def build_report(self, initial_state: Dict[str, int], actions: List[str], goal_state: Any) -> Dict[str, Any]:
        simulation = self.evaluator.digital_twin.simulate_plan(initial_state, actions)
        goal_progress = self.evaluator.evaluate_plan(initial_state, goal_state, {"name": "report-plan", "actions": actions})

        return {
            "initial_state": dict(initial_state),
            "actions": list(actions),
            "predicted_state": simulation["predicted_future_state"],
            "goal_progress": goal_progress["goal_progress"],
            "confidence": simulation["confidence"],
        }


report = DigitalTwinReport()
