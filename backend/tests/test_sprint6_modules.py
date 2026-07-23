import unittest

from backend.models.goal_state import GoalState
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.plan_generator import PlanGenerator
from backend.services.recommendation_engine import RecommendationEngine


class Sprint6ModulesTests(unittest.TestCase):
    def test_plan_generation_and_recommendation(self) -> None:
        current_state = {"python": 50}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        generator = PlanGenerator()
        plans = generator.generate_candidate_plans(current_state, goal_state)
        self.assertGreaterEqual(len(plans), 3)

        evaluator = PlanEvaluator()
        evaluations = evaluator.evaluate_plans(current_state, goal_state, plans)
        self.assertGreaterEqual(len(evaluations), 3)

        comparison = evaluator.compare_plans(current_state, goal_state, plans)
        self.assertGreaterEqual(len(comparison), 3)

        sequence = evaluator.digital_twin.simulate_action_sequence(current_state, ["Complete Python Project", "Practice DSA", "Participate in Hackathon"])
        self.assertIn("final_state", sequence)
        self.assertIn("state_history", sequence)
        self.assertGreaterEqual(len(sequence["state_history"]), 2)

        engine = RecommendationEngine(plan_evaluator=evaluator)
        recommendation = engine.recommend_plan(current_state, goal_state, plans)
        self.assertIn("recommended_plan", recommendation)
        self.assertIn("expected_outcome", recommendation)
        self.assertIn("plan_comparison", recommendation)


if __name__ == "__main__":
    unittest.main()
