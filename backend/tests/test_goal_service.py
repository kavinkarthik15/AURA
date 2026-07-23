import unittest

from backend.models.goal_state import GoalState
from backend.services.goal_service import estimate_goal_progress


class GoalServiceTests(unittest.TestCase):
    def test_estimate_goal_progress(self) -> None:
        target_state = GoalState(goal="AI Engineer", target_skills={"python": 80, "statistics": 70})
        current_state = {"python": 50, "statistics": 40}
        progress = estimate_goal_progress(current_state, target_state)
        self.assertAlmostEqual(progress, 0.62)


if __name__ == "__main__":
    unittest.main()
