import unittest

from backend.models.goal_state import GoalState
from backend.planning.expected_state_evaluator import ExpectedStateEvaluator
from backend.planning.probabilistic_transition import ProbabilisticTransition


class ExpectedStateEvaluatorTests(unittest.TestCase):
    def test_expected_score_is_probability_weighted(self):
        transition = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 63, "confidence": 0.9},
                {"python": 61, "confidence": 0.7},
                {"python": 60, "confidence": 0.5},
            ],
            probabilities=[0.7, 0.2, 0.1],
            expected_state={"python": 62.2},
            confidence=0.8,
            evidence=["memory-1"],
        )
        evaluator = ExpectedStateEvaluator(weights={"utility": 1.0, "goal_alignment": 1.0, "risk": 0.0, "cost": 0.0, "confidence": 0.0})
        result = evaluator.evaluate(transition, GoalState(goal="Improve Python", target_skills={"python": 80}))

        self.assertGreater(len(result.outcome_evaluations), 0)
        self.assertGreater(result.expected_score, 0.0)
        self.assertIn("score", result.explanation)

    def test_best_and_worst_case_scores_are_recorded(self):
        transition = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 70, "confidence": 0.9},
                {"python": 50, "confidence": 0.3},
            ],
            probabilities=[0.5, 0.5],
            confidence=0.8,
            evidence=["memory-2"],
        )
        evaluator = ExpectedStateEvaluator()
        result = evaluator.evaluate(transition, GoalState(goal="Improve Python", target_skills={"python": 80}))
        self.assertGreater(result.best_case_score, result.worst_case_score)

    def test_expected_evaluation_preserves_distribution(self):
        transition = ProbabilisticTransition(
            current_state={"python": 60},
            action="Practice Python",
            possible_states=[
                {"python": 63, "confidence": 0.9},
                {"python": 61, "confidence": 0.7},
            ],
            probabilities=[0.7, 0.3],
            confidence=0.8,
            evidence=["memory-3"],
        )
        evaluator = ExpectedStateEvaluator()
        result = evaluator.evaluate(transition, GoalState(goal="Improve Python", target_skills={"python": 80}))
        self.assertEqual(len(result.outcome_evaluations), 2)
        self.assertAlmostEqual(sum(item.probability for item in result.outcome_evaluations), 1.0)


if __name__ == "__main__":
    unittest.main()
