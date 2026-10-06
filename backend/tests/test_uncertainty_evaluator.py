import unittest

from backend.models.goal_state import GoalState
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.uncertainty_evaluator import UncertaintyEvaluator


class UncertaintyEvaluatorTests(unittest.TestCase):
    def test_deterministic_outcome_has_near_zero_uncertainty(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        transition = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[{"python": 80, "confidence": 0.9}],
            probabilities=[1.0],
            confidence=0.95,
            evidence=["stable"],
        )

        result = UncertaintyEvaluator().evaluate(transition, goal)

        self.assertLess(result.uncertainty, 0.05)
        self.assertAlmostEqual(result.entropy, 0.0, places=4)

    def test_concentrated_distribution_has_lower_uncertainty_than_even_distribution(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        concentrated = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 72, "confidence": 0.8},
                {"python": 70, "confidence": 0.7},
                {"python": 68, "confidence": 0.6},
            ],
            probabilities=[0.7, 0.2, 0.1],
            confidence=0.8,
            evidence=["biased"],
        )
        uneven = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 90, "confidence": 0.9},
                {"python": 55, "confidence": 0.5},
                {"python": 35, "confidence": 0.2},
            ],
            probabilities=[0.34, 0.33, 0.33],
            confidence=0.8,
            evidence=["balanced"],
        )

        c_result = UncertaintyEvaluator().evaluate(concentrated, goal)
        u_result = UncertaintyEvaluator().evaluate(uneven, goal)

        self.assertLess(c_result.uncertainty, u_result.uncertainty)

    def test_same_expected_value_but_different_distributions_have_different_uncertainty(self):
        goal = GoalState(goal="Improve Python", target_skills={})
        spread_out = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 40, "confidence": 0.1},
                {"python": 80, "confidence": 0.1},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.7,
            evidence=["wide"],
        )
        narrow = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 55, "confidence": 0.1},
                {"python": 65, "confidence": 0.1},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.7,
            evidence=["narrow"],
        )

        spread_result = UncertaintyEvaluator().evaluate(spread_out, goal)
        narrow_result = UncertaintyEvaluator().evaluate(narrow, goal)

        self.assertEqual(round(spread_result.expected_value, 2), round(narrow_result.expected_value, 2))
        self.assertGreater(spread_result.uncertainty, narrow_result.uncertainty)

    def test_confidence_remains_separate_from_distributional_uncertainty(self):
        goal = GoalState(goal="Improve Python", target_skills={})
        low_conf = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 90, "confidence": 0.2},
                {"python": 30, "confidence": 0.1},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.2,
            evidence=["low confidence"],
        )
        high_conf = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 90, "confidence": 0.2},
                {"python": 30, "confidence": 0.1},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.95,
            evidence=["high confidence"],
        )

        low_result = UncertaintyEvaluator().evaluate(low_conf, goal)
        high_result = UncertaintyEvaluator().evaluate(high_conf, goal)

        self.assertAlmostEqual(low_result.uncertainty, high_result.uncertainty, places=6)
        self.assertNotEqual(low_result.confidence, high_result.confidence)


if __name__ == "__main__":
    unittest.main()
