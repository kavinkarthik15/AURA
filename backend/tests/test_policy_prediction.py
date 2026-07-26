import unittest

from backend.ai.planning_policy import PlanningPolicy, PolicySample
from backend.models.goal_state import GoalState
from backend.services.beam_search_planner import BeamSearchPlanner


class PolicyPredictionTests(unittest.TestCase):
    def test_predicts_successful_action_with_higher_probability(self) -> None:
        policy = PlanningPolicy().fit([
            PolicySample(state={"python": 50}, goal="Placement", action="Project", success=True),
            PolicySample(state={"python": 50}, goal="Placement", action="Course", success=False),
        ])
        predictions = policy.predict({"python": 50}, "Placement", ["Project", "Course"])
        self.assertEqual(predictions[0].action, "Project")
        self.assertGreater(predictions[0].probability, predictions[1].probability)
        self.assertEqual(predictions[0].support_count, 1)
        self.assertGreater(predictions[0].confidence, predictions[1].confidence)

    def test_beam_search_can_consume_policy(self) -> None:
        policy = PlanningPolicy().fit([
            PolicySample(state={"python": 50, "dsa": 20, "projects": 10}, goal="Python Growth", action="Python Project", success=True),
        ])
        result = BeamSearchPlanner(policy=policy).search(
            {"python": 50, "dsa": 20, "projects": 10},
            GoalState(goal="Python Growth", target_skills={"python": 80}),
            beam_width=3,
            max_depth=2,
            use_policy=True,
        )
        self.assertTrue(result["policy_enabled"])
        self.assertIn("policy_score", result["search_trace"]["depth_1"][0])
        self.assertIn("planner_confidence", result)
        self.assertIn("policy_entropy", result)
        self.assertIn("action_explanations", result)


if __name__ == "__main__":
    unittest.main()
