from __future__ import annotations

from dataclasses import dataclass, field
from math import log, sqrt
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.planning.expected_state_evaluator import ExpectedEvaluation, ExpectedStateEvaluator
from backend.planning.probabilistic_transition import ProbabilisticTransition


@dataclass
class UncertaintyEvaluation:
    expected_value: float
    variance: float
    entropy: float
    uncertainty: float
    confidence: float
    spread: float
    explanation: Dict[str, Any] = field(default_factory=dict)


class UncertaintyEvaluator:
    def __init__(self, expected_state_evaluator: Optional[ExpectedStateEvaluator] = None) -> None:
        self.expected_state_evaluator = expected_state_evaluator or ExpectedStateEvaluator()

    def evaluate(self, probabilistic_transition: ProbabilisticTransition, goal_state: GoalState) -> UncertaintyEvaluation:
        if probabilistic_transition is None or not probabilistic_transition.possible_states:
            return UncertaintyEvaluation(
                expected_value=0.0,
                variance=0.0,
                entropy=0.0,
                uncertainty=0.0,
                confidence=0.0,
                spread=0.0,
                explanation={"reason": "No possible states to evaluate."},
            )

        expected_eval: ExpectedEvaluation = self.expected_state_evaluator.evaluate(probabilistic_transition, goal_state)
        scores = [outcome.score for outcome in expected_eval.outcome_evaluations]
        probabilities = [outcome.probability for outcome in expected_eval.outcome_evaluations]
        expected_value = expected_eval.expected_score

        if not scores:
            return UncertaintyEvaluation(
                expected_value=expected_value,
                variance=0.0,
                entropy=0.0,
                uncertainty=0.0,
                confidence=float(probabilistic_transition.confidence or 0.0),
                spread=0.0,
                explanation={"reason": "No outcome scores available."},
            )

        variance = sum(p * (score - expected_value) ** 2 for p, score in zip(probabilities, scores))
        spread = max(scores) - min(scores)

        if len(probabilities) > 1:
            entropy = -sum(p * log(p) for p in probabilities if p > 0) / log(len(probabilities))
        else:
            entropy = 0.0

        normalized_variance = min(1.0, variance / (1.0 + abs(expected_value)))
        normalized_spread = min(1.0, spread / (1.0 + abs(expected_value)))
        uncertainty = 0.5 * min(1.0, entropy) + 0.5 * max(normalized_variance, normalized_spread)

        explanation = {
            "expected_value": round(expected_value, 4),
            "variance": round(variance, 4),
            "entropy": round(entropy, 4),
            "uncertainty": round(uncertainty, 4),
            "confidence": round(float(probabilistic_transition.confidence or 0.0), 4),
            "spread": round(spread, 4),
            "distribution_size": len(scores),
        }

        return UncertaintyEvaluation(
            expected_value=round(expected_value, 4),
            variance=round(variance, 4),
            entropy=round(entropy, 4),
            uncertainty=round(uncertainty, 4),
            confidence=round(float(probabilistic_transition.confidence or 0.0), 4),
            spread=round(spread, 4),
            explanation=explanation,
        )
