from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.services.digital_twin import LearnedDigitalTwin


class PlanEvaluator:
    def __init__(self, digital_twin: LearnedDigitalTwin | None = None) -> None:
        self.digital_twin = digital_twin or LearnedDigitalTwin()

    def evaluate_plan(self, current_state: Dict[str, int], goal_state: GoalState, plan: Dict) -> Dict:
        simulation = self.digital_twin.simulate_plan(current_state, plan["actions"])
        progress_values: List[float] = []

        for skill, target_goal in goal_state.target_skills.items():
            current_target = current_state.get(skill, 0)
            projected_target = simulation["predicted_future_state"].get(skill, current_target)
            target_gap = max(1, target_goal - current_target)
            achieved_gap = max(0, projected_target - current_target)
            progress_values.append(achieved_gap / target_gap)

        goal_progress = round((sum(progress_values) / len(progress_values)) * 100, 2) if progress_values else 0.0
        expected_growth = round(sum(
            max(0, simulation["predicted_future_state"].get(skill, 0) - current_state.get(skill, 0))
            for skill in current_state
        ), 2)

        return {
            "plan_name": plan["name"],
            "expected_growth": expected_growth,
            "success_probability": round(simulation["success_probability"], 2),
            "goal_progress": goal_progress,
            "confidence": round(simulation["confidence"], 2),
            "simulation": simulation,
        }

    def evaluate_plans(self, current_state: Dict[str, int], goal_state: GoalState, plans: List[Dict]) -> List[Dict]:
        return [self.evaluate_plan(current_state, goal_state, plan) for plan in plans]

    def compare_plans(self, current_state: Dict[str, int], goal_state: GoalState, plans: List[Dict]) -> List[Dict]:
        evaluations = self.evaluate_plans(current_state, goal_state, plans)
        return [{"plan": item["plan_name"], "goal_progress": item["goal_progress"]} for item in evaluations]


plan_evaluator = PlanEvaluator()
