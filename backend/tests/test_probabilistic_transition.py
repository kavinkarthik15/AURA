import unittest

from backend.planning.probabilistic_transition import ProbabilisticTransitionModel


class ProbabilisticTransitionTests(unittest.TestCase):
    def test_probabilistic_transition_builds_distribution(self):
        model = ProbabilisticTransitionModel()
        transition = model.predict({"python": 60}, "Practice Python", context={"confidence": 0.8, "supporting_evidence": ["memory-1"]})
        self.assertEqual(len(transition.possible_states), 3)
        self.assertEqual(len(transition.probabilities), 3)
        self.assertAlmostEqual(sum(transition.probabilities), 1.0)
        self.assertIn("memory-1", transition.evidence)
        self.assertAlmostEqual(transition.confidence, 0.8)

    def test_expected_state_is_weighted_average(self):
        model = ProbabilisticTransitionModel()
        transition = model.predict({"python": 60}, "Practice Python")
        self.assertIn("python", transition.expected_state)
        self.assertGreater(transition.expected_state["python"], 60)

    def test_transition_keeps_current_state_and_action(self):
        model = ProbabilisticTransitionModel()
        transition = model.predict({"python": 60}, "Practice Python", context={"supporting_evidence": ["src"]})
        self.assertEqual(transition.current_state, {"python": 60})
        self.assertEqual(transition.action, "Practice Python")


if __name__ == "__main__":
    unittest.main()
