import unittest

from backend.planning.transition_model import DeterministicTransitionModel
from backend.planning.state_evaluator import StateEvaluator
from backend.models.goal_state import GoalState


class TransitionModelTests(unittest.TestCase):
    def test_deterministic_transition_creates_state_transition(self):
        model = DeterministicTransitionModel(default_confidence=0.85)
        transition = model.predict(
            {"python": 40, "dsa": 20},
            {"expected_state_change": {"python": 10, "dsa": 2}, "action": "Practice Python"},
            context={"supporting_evidence": ["memory-1", "knowledge-2"], "confidence": 0.82},
        )
        self.assertEqual(transition.current_state, {"python": 40, "dsa": 20})
        self.assertEqual(transition.state_change, {"python": 10.0, "dsa": 2.0})
        self.assertEqual(transition.predicted_state, {"python": 50.0, "dsa": 22.0})
        self.assertAlmostEqual(transition.confidence, 0.82)
        self.assertIn("memory-1", transition.supporting_evidence)

    def test_transition_available_for_state_evaluator(self):
        model = DeterministicTransitionModel(default_confidence=0.9)
        transition = model.predict(
            {"python": 35},
            "Practice Python",
            context={"confidence": 0.9},
        )
        evaluator = StateEvaluator()
        result = evaluator.evaluate_state(
            current_state=transition.current_state,
            predicted_state=transition.predicted_state,
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.75,
            risk=0.2,
            cost=0.1,
            confidence=transition.confidence,
        )
        self.assertGreater(result.score, 0.0)

    def test_transition_uses_inferred_state_change_if_missing(self):
        model = DeterministicTransitionModel(default_confidence=0.7)
        transition = model.predict({"python": 30, "dsa": 10}, "Practice Python")
        self.assertIn("python", transition.state_change)
        self.assertIn("python", transition.predicted_state)


if __name__ == "__main__":
    unittest.main()
