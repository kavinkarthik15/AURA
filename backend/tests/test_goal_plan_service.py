import unittest

from backend.models.goal_state import GoalState
from backend.services.goal_plan_service import GoalPlanService


class GoalPlanServiceTests(unittest.TestCase):
    def test_recommend_goal_plan_returns_best_plan_and_candidates(self) -> None:
        service = GoalPlanService()
        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = service.recommend_goal_plan(current_state, goal_state)

        self.assertIn("recommended_plan", result)
        self.assertIn("goal_progress", result)
        self.assertIn("confidence", result)
        self.assertIn("reasoning", result)
        self.assertIn("candidate_plans", result)
        self.assertIn("candidate_evaluations", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(len(result["candidate_plans"]), 1)
        self.assertGreaterEqual(len(result["candidate_evaluations"]), 1)
        self.assertIn("plans_generated", result["metrics"])
        self.assertIn("plans_evaluated", result["metrics"])
        self.assertIn("search_time_ms", result["metrics"])


if __name__ == "__main__":
    unittest.main()
