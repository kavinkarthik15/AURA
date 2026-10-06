import unittest

from backend.models.goal_state import GoalState
from backend.planning.state_evaluator import StateEvaluator
from backend.planning.state_transition import StateTransition


class StateTransitionTests(unittest.TestCase):
    def test_transition_computes_state_change_and_predicted_state(self):
        transition = StateTransition(
            current_state={"python": 40, "dsa": 20},
            action="Practice Python",
            predicted_state={"python": 55, "dsa": 22},
            confidence=0.82,
            supporting_evidence=["memory-1", "knowledge-2"],
            transition_explanation="Python practice increases coding depth and reinforces DSA consistency.",
        )

        self.assertEqual(transition.state_change, {"python": 15.0, "dsa": 2.0})
        self.assertEqual(transition.predicted_state["python"], 55)
        self.assertAlmostEqual(transition.confidence, 0.82)
        self.assertIn("Python practice", transition.transition_explanation)

    def test_state_evaluator_accepts_transition_object(self):
        transition = StateTransition(
            current_state={"python": 40},
            action="Practice Python",
            predicted_state={"python": 60},
            state_change={"python": 20.0},
            confidence=0.9,
            supporting_evidence=["memory-a"],
            transition_explanation="Practice raises Python skill.",
        )
        evaluator = StateEvaluator()
        result = evaluator.evaluate_state(
            current_state=transition.current_state,
            predicted_state=transition.predicted_state,
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.8,
            risk=0.1,
            cost=0.2,
            confidence=transition.confidence,
        )
        self.assertIn("score", result.explanation)
        self.assertGreater(result.score, 0.0)


if __name__ == "__main__":
    unittest.main()
