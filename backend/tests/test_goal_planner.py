import unittest

from backend.models.goal_state import GoalState
from backend.services.action_ranker import ActionRanker
from backend.services.goal_planner import GoalPlanner


class GoalPlannerTests(unittest.TestCase):
    def test_plan_contains_project_action_for_python_gap(self) -> None:
        planner = GoalPlanner()
        plan = planner.create_plan({"python": 55}, GoalState(goal="Python 80", target_skills={"python": 80}))
        self.assertIn("Complete Python Project", plan["recommended_actions"])

    def test_estimated_steps_are_small_when_goal_is_almost_reached(self) -> None:
        planner = GoalPlanner()
        plan = planner.create_plan({"python": 75}, GoalState(goal="Python 80", target_skills={"python": 80}))
        self.assertLessEqual(plan["estimated_steps"], 1)

    def test_no_actions_required_when_goal_is_already_reached(self) -> None:
        planner = GoalPlanner()
        plan = planner.create_plan({"python": 80}, GoalState(goal="Python 80", target_skills={"python": 80}))
        self.assertEqual(plan["recommended_actions"], [])

    def test_rank_actions_uses_transition_engine_predictions(self) -> None:
        class StubTransitionEngine:
            def predict_skill_growth(self, current_state, action):
                return {"python": 15 if action == "Complete Python Project" else 3}

            def predict_success_probability(self, current_state, action):
                return 0.95 if action == "Complete Python Project" else 0.4

        ranker = ActionRanker()
        ranked = ranker.rank_actions(
            [
                {"name": "Complete Python Project", "expected_growth": 8, "success_probability": 0.6, "confidence": 0.6},
                {"name": "Read Research Paper", "expected_growth": 2, "success_probability": 0.3, "confidence": 0.6},
            ],
            current_state={"python": 50},
            transition_engine=StubTransitionEngine(),
        )
        self.assertEqual(ranked[0]["name"], "Complete Python Project")


if __name__ == "__main__":
    unittest.main()
