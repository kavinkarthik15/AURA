import unittest

from backend.models.goal_state import GoalState
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.risk_evaluator import RiskEvaluator


class RiskEvaluatorTests(unittest.TestCase):
    def test_risk_evaluator_distinguishes_high_variance_from_low_variance(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        evaluator = RiskEvaluator()

        high_variance = ProbabilisticTransition(
            current_state={"python": 60},
            action="High risk practice",
            possible_states=[
                {"python": 90, "confidence": 0.9, "risk": 0.2},
                {"python": 20, "confidence": 0.3, "risk": 0.8},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.7,
            evidence=["unstable"],
        )

        low_variance = ProbabilisticTransition(
            current_state={"python": 60},
            action="Stable practice",
            possible_states=[
                {"python": 75, "confidence": 0.8, "risk": 0.1},
                {"python": 70, "confidence": 0.7, "risk": 0.1},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.8,
            evidence=["stable"],
        )

        high = evaluator.evaluate(high_variance, goal)
        low = evaluator.evaluate(low_variance, goal)

        self.assertGreater(high.risk_score, low.risk_score)
        self.assertGreater(high.variance, low.variance)
        self.assertGreater(high.downside_risk, low.downside_risk)

    def test_risk_evaluation_returns_structured_explanation(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        transition = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 80, "confidence": 0.9, "risk": 0.1},
                {"python": 75, "confidence": 0.8, "risk": 0.1},
            ],
            probabilities=[0.6, 0.4],
            confidence=0.8,
            evidence=["step"],
        )

        result = RiskEvaluator().evaluate(transition, goal)

        self.assertIn("expected_value", result.explanation)
        self.assertIn("risk_score", result.explanation)
        self.assertGreaterEqual(result.confidence, 0.0)

    def test_empty_distribution_is_handled_safely(self):
        result = RiskEvaluator().evaluate(ProbabilisticTransition(), GoalState(goal="Learn", target_skills={"python": 10}))
        self.assertEqual(result.expected_value, 0.0)
        self.assertEqual(result.risk_score, 0.0)


if __name__ == "__main__":
    unittest.main()
