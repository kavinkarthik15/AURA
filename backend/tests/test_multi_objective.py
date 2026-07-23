import unittest

from backend.models.goal_state import GoalState
from backend.models.planning_objectives import PlanningObjectives
from backend.services.goal_plan_service import GoalPlanService
from backend.services.multi_objective_evaluator import MultiObjectiveEvaluator
from backend.services.pareto_optimizer import ParetoOptimizer


class MultiObjectivePlanningTests(unittest.TestCase):
    def test_objective_calculation(self) -> None:
        evaluator = MultiObjectiveEvaluator()
        plan = {"name": "Plan A", "actions": ["Complete Python Project", "Practice DSA"]}
        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Become AI Engineer", target_skills={"python": 80, "dsa": 50})

        objectives = evaluator.evaluate_plan(current_state, goal_state, plan)

        self.assertIsInstance(objectives, PlanningObjectives)
        self.assertGreaterEqual(objectives.goal_progress, 0.0)
        self.assertGreaterEqual(objectives.python_growth, 0.0)
        self.assertGreaterEqual(objectives.dsa_growth, 0.0)
        self.assertIn("confidence", objectives.to_dict())

    def test_pareto_front_generation(self) -> None:
        optimizer = ParetoOptimizer()
        plans = [
            {"name": "Plan A", "objectives": {"goal_progress": 0.9, "python_growth": 20, "project_growth": 3, "difficulty": 0.2, "confidence": 0.8, "time_cost": 4, "energy_cost": 2}},
            {"name": "Plan B", "objectives": {"goal_progress": 0.7, "python_growth": 12, "project_growth": 10, "difficulty": 0.35, "confidence": 0.9, "time_cost": 5, "energy_cost": 3}},
            {"name": "Plan C", "objectives": {"goal_progress": 0.65, "python_growth": 8, "project_growth": 8, "difficulty": 0.3, "confidence": 0.7, "time_cost": 6, "energy_cost": 2}},
        ]

        front = optimizer.find_pareto_front(plans)
        self.assertGreaterEqual(len(front), 2)

    def test_dominated_plan_removal(self) -> None:
        optimizer = ParetoOptimizer()
        plans = [
            {"name": "Dominated", "objectives": {"goal_progress": 0.4, "python_growth": 5, "project_growth": 2, "difficulty": 0.5, "confidence": 0.5, "time_cost": 7, "energy_cost": 4}},
            {"name": "Leader", "objectives": {"goal_progress": 0.8, "python_growth": 10, "project_growth": 4, "difficulty": 0.3, "confidence": 0.9, "time_cost": 4, "energy_cost": 2}},
        ]

        front = optimizer.find_pareto_front(plans)
        self.assertEqual(len(front), 1)
        self.assertEqual(front[0]["name"], "Leader")

    def test_recommendation_output_contains_tradeoffs(self) -> None:
        service = GoalPlanService()
        current_state = {"python": 60, "dsa": 45, "projects": 40}
        goal_state = GoalState(goal="Become AI Engineer", target_skills={"python": 80, "dsa": 60})

        result = service.recommend_goal_plan(current_state, goal_state)

        self.assertIn("best_plan", result)
        self.assertIn("pareto_front", result)
        self.assertIn("why_selected", result)
        self.assertIn("tradeoffs", result)
        self.assertIn("alternative_plan", result)

    def test_tradeoff_explanation(self) -> None:
        service = GoalPlanService()
        current_state = {"python": 60, "dsa": 45, "projects": 40}
        goal_state = GoalState(goal="Become AI Engineer", target_skills={"python": 80, "dsa": 60})

        result = service.recommend_goal_plan(current_state, goal_state)
        self.assertIn("trade", result["why_selected"].lower())


if __name__ == "__main__":
    unittest.main()
