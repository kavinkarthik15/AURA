import unittest

from backend.models.goal_state import GoalState
from backend.services.goal_planner import GoalPlanner
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.plan_generator import PlanGenerator
from backend.services.recommendation_engine import RecommendationEngine


class EndToEndPipelineTests(unittest.TestCase):
    def test_goal_planner_to_recommendation_pipeline(self) -> None:
        current_state = {
            "python": 50,
            "dsa": 20,
        }
        goal_state = GoalState(goal="Improve Python", target_skills={"python": 80})

        goal_planner = GoalPlanner()
        plan = goal_planner.create_plan(current_state, goal_state)
        self.assertIn("recommended_actions", plan)

        generator = PlanGenerator(goal_planner=goal_planner)
        plans = generator.generate_candidate_plans(current_state, goal_state)
        self.assertGreaterEqual(len(plans), 3)

        evaluator = PlanEvaluator()
        evaluations = evaluator.evaluate_plans(current_state, goal_state, plans)
        self.assertGreaterEqual(len(evaluations), 3)

        recommendation = RecommendationEngine(plan_evaluator=evaluator).recommend_plan(current_state, goal_state, plans)
        self.assertIsNotNone(recommendation)
        self.assertGreater(recommendation["goal_progress"], 0)
        self.assertIn("recommended_plan", recommendation)
        self.assertIn("reason", recommendation)


if __name__ == "__main__":
    unittest.main()
