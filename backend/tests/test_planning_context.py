import unittest

from backend.models.goal_state import GoalState
from backend.planning.planning_context import PlanningContext


class PlanningContextTests(unittest.TestCase):
    def test_basic_construction_preserves_values(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        context = PlanningContext(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.3,
            uncertainty_tolerance=0.4,
            constraints=["no overtime"],
            confidence=0.9,
            metadata={"session_id": "abc123"},
        )

        self.assertEqual(context.current_state, {"python": 50})
        self.assertEqual(context.goal_state, goal)
        self.assertEqual(context.risk_tolerance, 0.3)
        self.assertEqual(context.uncertainty_tolerance, 0.4)
        self.assertEqual(context.constraints, ["no overtime"])
        self.assertEqual(context.confidence, 0.9)
        self.assertEqual(context.metadata, {"session_id": "abc123"})

    def test_default_values_are_set(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        context = PlanningContext(current_state={"python": 50}, goal_state=goal)

        self.assertEqual(context.risk_tolerance, 0.5)
        self.assertEqual(context.uncertainty_tolerance, 0.5)
        self.assertEqual(context.constraints, [])
        self.assertEqual(context.confidence, 1.0)
        self.assertEqual(context.metadata, {})

    def test_validation_rejects_invalid_risk_tolerance(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, risk_tolerance=-0.1)

        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, risk_tolerance=1.1)

    def test_validation_rejects_invalid_uncertainty_tolerance(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, uncertainty_tolerance=-0.1)

        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, uncertainty_tolerance=1.1)

    def test_validation_rejects_invalid_confidence(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, confidence=-0.1)

        with self.assertRaises(ValueError):
            PlanningContext(current_state={"python": 50}, goal_state=goal, confidence=1.1)

    def test_to_dict_serializes_complete_context(self):
        goal = GoalState(goal="Python Growth", target_skills={"python": 80})
        context = PlanningContext(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.3,
            uncertainty_tolerance=0.4,
            constraints=["no overtime"],
            confidence=0.9,
            metadata={"session_id": "abc123"},
        )

        result = context.to_dict()

        self.assertEqual(result["current_state"], {"python": 50})
        self.assertEqual(result["goal_state"], {"goal": "Python Growth", "target_skills": {"python": 80}})
        self.assertEqual(result["risk_tolerance"], 0.3)
        self.assertEqual(result["uncertainty_tolerance"], 0.4)
        self.assertEqual(result["constraints"], ["no overtime"])
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["metadata"], {"session_id": "abc123"})


if __name__ == "__main__":
    unittest.main()
