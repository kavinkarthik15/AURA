from typing import Dict, List

from backend.models.goal_state import GoalState


class RecommendationEngine:
    def __init__(self, plan_evaluator=None) -> None:
        self.plan_evaluator = plan_evaluator

    def _build_reasoning_payload(self, best: Dict, current_state: Dict[str, int], goal_state: GoalState) -> Dict:
        goal_gap_reduction = 0
        for skill, target_goal in goal_state.target_skills.items():
            current_value = current_state.get(skill, 0)
            projected_value = best["simulation"]["predicted_future_state"].get(skill, current_value)
            goal_gap_reduction += max(0, min(target_goal - current_value, projected_value - current_value))

        return {
            "python_growth": round(best["simulation"]["predicted_future_state"].get("python", 0) - current_state.get("python", 0), 2),
            "project_growth": round(best["simulation"]["predicted_future_state"].get("projects", 0) - current_state.get("projects", 0), 2),
            "goal_gap_reduction": round(goal_gap_reduction, 2),
            "history_bonus": round(best["confidence"] * 10, 2),
            "action_contributions": [
                {
                    "action": action,
                    "predicted_python_gain": round(max(0, best["simulation"]["predicted_future_state"].get("python", 0) - current_state.get("python", 0)) / max(1, len(best["simulation"]["steps"])), 2),
                }
                for action in [step.get("action") for step in best["simulation"].get("steps", [])]
                if action
            ],
        }

    def recommend_plan(self, current_state: Dict[str, int], goal_state: GoalState, plans: List[Dict]) -> Dict:
        if not plans:
            return {"recommended_plan": None, "reason": "No candidate plans were generated.", "expected_outcome": "Negative"}

        evaluations = self.plan_evaluator.evaluate_plans(current_state, goal_state, plans)
        best = max(
            evaluations,
            key=lambda item: (
                item["goal_progress"],
                item["confidence"],
                item["expected_growth"],
            ),
        )
        expected_outcome = "Positive" if best["goal_progress"] >= 100 else "Neutral" if best["goal_progress"] >= 60 else "Negative"
        reasoning = self._build_reasoning_payload(best, current_state, goal_state)
        reason_lines = [
            f"Selected {best['plan_name']} because:",
            f"- Highest projected goal progress: {best['goal_progress']}%",
            f"- Predicted confidence: {best['confidence']}",
            f"- Expected future state: {best['simulation']['predicted_future_state']}",
        ]
        return {
            "recommended_plan": best["plan_name"],
            "goal_progress": best["goal_progress"],
            "expected_future_state": best["simulation"]["predicted_future_state"],
            "confidence": best["confidence"],
            "reason": "\n".join(reason_lines),
            "reasoning": reasoning,
            "expected_outcome": expected_outcome,
            "evaluation": best,
            "plan_comparison": self.plan_evaluator.compare_plans(current_state, goal_state, plans),
        }


recommendation_engine = RecommendationEngine()
