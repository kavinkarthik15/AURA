import unittest

from backend.models.goal_state import GoalState
from backend.planning.adaptive_weight_provider import AdaptiveWeightProvider
from backend.planning.expected_state_evaluator import ExpectedStateEvaluator
from backend.planning.planning_context import PlanningContext
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.trajectory_evaluator import TrajectoryEvaluator


class TrajectoryEvaluatorTests(unittest.TestCase):
    def test_trajectory_score_discounts_future_steps(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        evaluator = TrajectoryEvaluator(discount_factor=0.9, expected_state_evaluator=ExpectedStateEvaluator())

        transitions = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[{"python": 70, "confidence": 0.9}, {"python": 65, "confidence": 0.5}],
                probabilities=[0.7, 0.3],
                confidence=0.8,
                evidence=["step-1"],
            ),
            ProbabilisticTransition(
                current_state={"python": 70},
                action="Practice Python",
                possible_states=[{"python": 78, "confidence": 0.85}, {"python": 72, "confidence": 0.6}],
                probabilities=[0.8, 0.2],
                confidence=0.8,
                evidence=["step-2"],
            ),
        ]

        result = evaluator.evaluate(transitions, goal)

        self.assertEqual(result.horizon, 2)
        self.assertGreater(result.trajectory_score, 0.0)
        self.assertGreater(result.expected_value, 0.0)
        self.assertEqual(len(result.step_evaluations), 2)
        self.assertAlmostEqual(result.discount_factor, 0.9)

    def test_contextual_planning_changes_trajectory_score(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        provider = AdaptiveWeightProvider()
        evaluator = TrajectoryEvaluator(adaptive_weight_provider=provider)

        transitions = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 75, "confidence": 0.8, "risk": 0.2, "cost": 0.1},
                    {"python": 65, "confidence": 0.6, "risk": 0.5, "cost": 0.2},
                ],
                probabilities=[0.7, 0.3],
                confidence=0.8,
                evidence=["step-1"],
            )
        ]

        low_risk_context = PlanningContext(
            current_state={"python": 60},
            goal_state=goal,
            risk_tolerance=0.1,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )
        high_risk_context = PlanningContext(
            current_state={"python": 60},
            goal_state=goal,
            risk_tolerance=0.9,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )

        low_risk_result = evaluator.evaluate(transitions, goal, low_risk_context)
        high_risk_result = evaluator.evaluate(transitions, goal, high_risk_context)

        self.assertNotEqual(low_risk_result.trajectory_score, high_risk_result.trajectory_score)
        self.assertLess(low_risk_result.trajectory_score, high_risk_result.trajectory_score)

    def test_trajectory_evaluation_aggregates_cumulative_metrics(self):
        goal = GoalState(goal="Build portfolio", target_skills={"projects": 10})
        evaluator = TrajectoryEvaluator(discount_factor=0.8)

        transitions = [
            ProbabilisticTransition(
                current_state={"projects": 4},
                action="Ship project",
                possible_states=[{"projects": 8, "confidence": 0.7}, {"projects": 6, "confidence": 0.5}],
                probabilities=[0.6, 0.4],
                confidence=0.7,
                evidence=["step-1"],
            ),
            ProbabilisticTransition(
                current_state={"projects": 8},
                action="Ship project",
                possible_states=[{"projects": 10, "confidence": 0.9}, {"projects": 9, "confidence": 0.7}],
                probabilities=[0.75, 0.25],
                confidence=0.8,
                evidence=["step-2"],
            ),
        ]

        result = evaluator.evaluate(transitions, goal)

        self.assertGreater(result.cumulative_utility, 0.0)
        self.assertGreaterEqual(result.goal_progress, 0.0)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertIn("trajectory_score", result.explanation)

    def test_risk_sensitive_trajectory_prefers_safer_path(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})

        safer = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 72, "confidence": 0.8, "risk": 0.05},
                    {"python": 69, "confidence": 0.7, "risk": 0.05},
                ],
                probabilities=[0.8, 0.2],
                confidence=0.8,
                evidence=["safer"],
            ),
            ProbabilisticTransition(
                current_state={"python": 72},
                action="Practice Python",
                possible_states=[
                    {"python": 80, "confidence": 0.8, "risk": 0.05},
                    {"python": 76, "confidence": 0.7, "risk": 0.05},
                ],
                probabilities=[0.8, 0.2],
                confidence=0.8,
                evidence=["safer"],
            ),
        ]

        riskier = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 85, "confidence": 0.9, "risk": 0.5},
                    {"python": 40, "confidence": 0.2, "risk": 0.9},
                ],
                probabilities=[0.7, 0.3],
                confidence=0.7,
                evidence=["riskier"],
            ),
            ProbabilisticTransition(
                current_state={"python": 85},
                action="Practice Python",
                possible_states=[
                    {"python": 95, "confidence": 0.85, "risk": 0.6},
                    {"python": 35, "confidence": 0.1, "risk": 0.9},
                ],
                probabilities=[0.75, 0.25],
                confidence=0.7,
                evidence=["riskier"],
            ),
        ]

        risk_neutral = TrajectoryEvaluator(discount_factor=0.9, risk_sensitivity=0.0, uncertainty_sensitivity=0.0)
        risk_sensitive = TrajectoryEvaluator(discount_factor=0.9, risk_sensitivity=1.5, uncertainty_sensitivity=1.0)

        safe_result = risk_sensitive.evaluate(safer, goal)
        risky_result = risk_sensitive.evaluate(riskier, goal)
        neutral_risky = risk_neutral.evaluate(riskier, goal)
        neutral_safe = risk_neutral.evaluate(safer, goal)

        self.assertGreater(safe_result.trajectory_score, risky_result.trajectory_score)
        self.assertGreater(neutral_safe.expected_value, neutral_risky.expected_value)

    def test_increasing_uncertainty_sensitivity_penalizes_uncertain_trajectory(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        stable = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 74, "confidence": 0.85, "risk": 0.1},
                    {"python": 72, "confidence": 0.8, "risk": 0.1},
                ],
                probabilities=[0.8, 0.2],
                confidence=0.8,
                evidence=["stable"],
            )
        ]
        uncertain = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 90, "confidence": 0.9, "risk": 0.3},
                    {"python": 50, "confidence": 0.2, "risk": 0.7},
                ],
                probabilities=[0.5, 0.5],
                confidence=0.6,
                evidence=["uncertain"],
            )
        ]

        base = TrajectoryEvaluator(discount_factor=0.9, risk_sensitivity=0.0, uncertainty_sensitivity=0.0)
        penalized = TrajectoryEvaluator(discount_factor=0.9, risk_sensitivity=0.0, uncertainty_sensitivity=2.0)

        stable_result = penalized.evaluate(stable, goal)
        uncertain_result = penalized.evaluate(uncertain, goal)
        neutral_uncertain = base.evaluate(uncertain, goal)

        self.assertGreater(stable_result.trajectory_score, uncertain_result.trajectory_score)
        self.assertGreater(neutral_uncertain.expected_value, uncertain_result.trajectory_score)

    def test_trajectory_step_evaluations_include_risk_and_uncertainty(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        evaluator = TrajectoryEvaluator(discount_factor=0.9, risk_sensitivity=1.0, uncertainty_sensitivity=1.0)

        transitions = [
            ProbabilisticTransition(
                current_state={"python": 60},
                action="Practice Python",
                possible_states=[
                    {"python": 75, "confidence": 0.8, "risk": 0.1},
                    {"python": 68, "confidence": 0.7, "risk": 0.15},
                ],
                probabilities=[0.75, 0.25],
                confidence=0.8,
                evidence=["step-1"],
            )
        ]

        result = evaluator.evaluate(transitions, goal)

        self.assertEqual(len(result.step_evaluations), 1)
        self.assertIn("risk", result.step_evaluations[0].explanation)
        self.assertIn("uncertainty", result.step_evaluations[0].explanation)
        self.assertGreaterEqual(result.step_evaluations[0].risk, 0.0)
        self.assertGreaterEqual(result.step_evaluations[0].uncertainty, 0.0)

    def test_empty_trajectory_returns_zeroed_evaluation(self):
        evaluator = TrajectoryEvaluator()
        result = evaluator.evaluate([], GoalState(goal="Learn", target_skills={"python": 10}))

        self.assertEqual(result.horizon, 0)
        self.assertEqual(result.trajectory_score, 0.0)
        self.assertEqual(result.expected_value, 0.0)
        self.assertEqual(result.step_evaluations, [])


if __name__ == "__main__":
    unittest.main()
