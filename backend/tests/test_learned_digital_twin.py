import unittest

from backend.models.goal_state import GoalState
from backend.services.digital_twin import LearnedDigitalTwin
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.recommendation_engine import RecommendationEngine


class LearnedDigitalTwinTests(unittest.TestCase):
    def test_learned_recommendation_flow(self) -> None:
        current_state = {"python": 50, "machine_learning": 30, "dsa": 20, "projects": 40, "communication": 35}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        plans = [
            {"name": "Plan A", "actions": ["Python Project", "DSA Practice", "Hackathon"]},
            {"name": "Plan B", "actions": ["Course", "Research Paper"]},
            {"name": "Plan C", "actions": ["Internship"]},
        ]

        twin = LearnedDigitalTwin()
        plan_result = twin.simulate_plan(current_state, plans[0]["actions"])
        self.assertIn("predicted_future_state", plan_result)
        self.assertIn("confidence", plan_result)

        evaluator = PlanEvaluator(digital_twin=twin)
        evaluation = evaluator.evaluate_plan(current_state, goal_state, plans[0])
        self.assertIn("goal_progress", evaluation)
        self.assertIn("simulation", evaluation)

        engine = RecommendationEngine(plan_evaluator=evaluator)
        recommendation = engine.recommend_plan(current_state, goal_state, plans)
        self.assertIn("recommended_plan", recommendation)
        self.assertIn("goal_progress", recommendation)
        self.assertIn("expected_future_state", recommendation)
        self.assertIn("confidence", recommendation)


if __name__ == "__main__":
    unittest.main()
