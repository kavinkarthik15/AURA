import unittest

from backend.models.goal_state import GoalState
from backend.services.plan_search import PlanSearch


class PlanSearchTests(unittest.TestCase):
    def test_recommend_goal_plan_generates_candidate_plans(self) -> None:
        search = PlanSearch()
        current_state = {"python": 50, "dsa": 20}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        plans = search.recommend_goal_plan(current_state, goal_state)
        self.assertGreaterEqual(len(plans), 5)
        for plan in plans:
            self.assertIn("name", plan)
            self.assertIn("actions", plan)
            self.assertGreaterEqual(len(plan["actions"]), 2)


if __name__ == "__main__":
    unittest.main()
