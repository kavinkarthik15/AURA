import unittest

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.goal_state import GoalState
from backend.planning.candidate_selector import CandidateSelector
from backend.services.beam_search_planner import BeamSearchPlanner
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

    def test_recommend_goal_plan_passes_digital_twin_flag_to_planner(self) -> None:
        selector = CandidateSelector(enabled=True, fallback_action="fallback")
        planner = BeamSearchPlanner(candidate_selector=selector)
        service = GoalPlanService(beam_search_planner=planner)
        current_state = {"python": 10, "dsa": 5, "projects": 1}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = service.recommend_goal_plan(current_state, goal_state, use_digital_twin=True)

        self.assertTrue(result["use_digital_twin"])
        self.assertTrue(result["digital_twin_enabled"])
        self.assertIsNotNone(result["digital_twin_selection"])
        self.assertIn("digital_twin_advisory", result)
        self.assertIn("first_action", result["digital_twin_advisory"])
        self.assertEqual(result["recommended_action"], result["digital_twin_advisory"]["first_action"])
        self.assertEqual(result["recommended_plan_actions"], [result["recommended_action"]])

    def test_recommend_goal_plan_exposes_first_action_and_plan_actions(self) -> None:
        selector = CandidateSelector(enabled=True, fallback_action="fallback")
        planner = BeamSearchPlanner(candidate_selector=selector)
        service = GoalPlanService(beam_search_planner=planner)
        current_state = {"python": 10, "dsa": 5, "projects": 1}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = service.recommend_goal_plan(current_state, goal_state, use_digital_twin=True)

        self.assertIn("recommended_action", result)
        self.assertIn("recommended_plan_actions", result)
        self.assertEqual(result["recommended_plan_actions"], [result["recommended_action"]])

    def test_recommend_goal_plan_uses_calibrated_digital_twin_for_recommendations(self) -> None:
        service = GoalPlanService()
        current_state = {"python": 10, "dsa": 5, "projects": 1}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})
        calibration_parameters = CalibrationParameters(expected_state_bias={"python": 5}, confidence=0.9, uncertainty=0.2)

        baseline_result = service.recommend_goal_plan(current_state, goal_state, use_digital_twin=True)
        calibrated_result = service.recommend_goal_plan(
            current_state,
            goal_state,
            use_digital_twin=True,
            calibration_parameters=calibration_parameters,
        )

        self.assertGreater(
            calibrated_result["expected_future_state"]["python"],
            baseline_result["expected_future_state"]["python"],
        )
        self.assertGreater(
            calibrated_result["confidence"],
            baseline_result["confidence"],
        )
        self.assertEqual(
            calibrated_result["evaluation"]["confidence"],
            calibrated_result["candidate_evaluations"][0]["confidence"],
        )


if __name__ == "__main__":
    unittest.main()
