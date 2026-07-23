import unittest

from backend.models.goal_state import GoalState
from backend.services.beam_search_planner import BeamSearchPlanner


class BeamSearchPlannerTests(unittest.TestCase):
    def test_beam_search_returns_a_plan(self) -> None:
        planner = BeamSearchPlanner()
        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = planner.search(current_state, goal_state, beam_width=3, max_depth=3)

        self.assertTrue(result["best_plan"])
        self.assertGreaterEqual(len(result["best_plan"]), 1)
        self.assertGreaterEqual(result["plans_evaluated"], result["beam_width"])
        self.assertIn("score", result)
        self.assertIn("search_trace", result)
        self.assertIsNotNone(result["score"])


if __name__ == "__main__":
    unittest.main()
