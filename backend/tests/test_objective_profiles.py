import unittest

from backend.models.goal_state import GoalState
from backend.models.objective_profile import ObjectiveProfile
from backend.services.goal_plan_service import GoalPlanService
from backend.services.objective_profiles import build_default_profiles


class ObjectiveProfileTests(unittest.TestCase):
    def test_profiles_are_available(self) -> None:
        profiles = build_default_profiles()
        self.assertIn("career_focused", profiles)
        self.assertIn("balanced_learning", profiles)
        self.assertIn("placement", profiles)

    def test_service_uses_selected_profile(self) -> None:
        service = GoalPlanService()
        current_state = {"python": 60, "dsa": 45, "projects": 40}
        goal_state = GoalState(goal="Become AI Engineer", target_skills={"python": 80, "dsa": 60})
        profile = build_default_profiles()["career_focused"]

        result = service.recommend_goal_plan(current_state, goal_state, profile=profile)

        self.assertEqual(result["selected_profile"], "CareerFocusedProfile")
        self.assertIn("profile_score", result)


if __name__ == "__main__":
    unittest.main()
