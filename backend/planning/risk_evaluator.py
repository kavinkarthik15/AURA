from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.planning.expected_state_evaluator import ExpectedEvaluation, ExpectedStateEvaluator
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.uncertainty_evaluator import UncertaintyEvaluator


@dataclass
class RiskEvaluation:
    expected_value: float
    downside_risk: float
    variance: float
    uncertainty: float
    confidence: float
    worst_case_score: float
    best_case_score: float
    risk_score: float
    explanation: Dict[str, Any] = field(default_factory=dict)


class RiskEvaluator:
    def __init__(
        self,
        expected_state_evaluator: Optional[ExpectedStateEvaluator] = None,
        uncertainty_evaluator: Optional[UncertaintyEvaluator] = None,
    ) -> None:
        self.expected_state_evaluator = expected_state_evaluator or ExpectedStateEvaluator()
        self.uncertainty_evaluator = uncertainty_evaluator or UncertaintyEvaluator(self.expected_state_evaluator)

    def evaluate(self, probabilistic_transition: ProbabilisticTransition, goal_state: GoalState) -> RiskEvaluation:
        if probabilistic_transition is None or not probabilistic_transition.possible_states:
            return RiskEvaluation(
                expected_value=0.0,
                downside_risk=0.0,
                variance=0.0,
                uncertainty=0.0,
                confidence=0.0,
                worst_case_score=0.0,
                best_case_score=0.0,
                risk_score=0.0,
                explanation={"reason": "No possible states to evaluate."},
            )

        expected_eval: ExpectedEvaluation = self.expected_state_evaluator.evaluate(probabilistic_transition, goal_state)
        scores = [outcome.score for outcome in expected_eval.outcome_evaluations]
        probabilities = [outcome.probability for outcome in expected_eval.outcome_evaluations]
        expected_value = expected_eval.expected_score

        if not scores:
            return RiskEvaluation(
                expected_value=expected_value,
                downside_risk=0.0,
                variance=0.0,
                uncertainty=0.0,
                confidence=expected_eval.expected_confidence,
                worst_case_score=0.0,
                best_case_score=0.0,
                risk_score=0.0,
                explanation={"reason": "No outcome scores available."},
            )

        mean = expected_value
        variance = sum(p * (score - mean) ** 2 for p, score in zip(probabilities, scores))
        threshold = max(0.0, mean * 0.75)
        downside_risk = sum(p * max(0.0, threshold - score) for p, score in zip(probabilities, scores))
        uncertainty_eval = self.uncertainty_evaluator.evaluate(probabilistic_transition, goal_state)
        uncertainty = max(0.0, uncertainty_eval.uncertainty)
        worst_case_score = min(scores)
        best_case_score = max(scores)

        risk_score = (
            downside_risk * 1.0
            + variance * 0.8
            + uncertainty * 0.5
            - expected_eval.expected_confidence * 0.4
        )

        explanation = {
            "expected_value": round(expected_value, 4),
            "downside_risk": round(downside_risk, 4),
            "variance": round(variance, 4),
            "uncertainty": round(uncertainty, 4),
            "confidence": round(expected_eval.expected_confidence, 4),
            "worst_case_score": round(worst_case_score, 4),
            "best_case_score": round(best_case_score, 4),
            "risk_score": round(max(0.0, risk_score), 4),
            "distribution_size": len(scores),
            "entropy": round(uncertainty_eval.entropy, 4),
            "spread": round(uncertainty_eval.spread, 4),
        }

        return RiskEvaluation(
            expected_value=round(expected_value, 4),
            downside_risk=round(downside_risk, 4),
            variance=round(variance, 4),
            uncertainty=round(uncertainty, 4),
            confidence=round(expected_eval.expected_confidence, 4),
            worst_case_score=round(worst_case_score, 4),
            best_case_score=round(best_case_score, 4),
            risk_score=round(max(0.0, risk_score), 4),
            explanation=explanation,
        )
