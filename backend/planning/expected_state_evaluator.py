from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.planning.probabilistic_transition import ProbabilisticTransition


@dataclass
class OutcomeEvaluation:
    state: Dict[str, Any]
    probability: float
    score: float
    utility: float
    goal_alignment: float
    risk: float
    cost: float
    confidence: float
    explanation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpectedEvaluation:
    expected_score: float
    expected_utility: float
    expected_goal_alignment: float
    expected_risk: float
    expected_cost: float
    expected_confidence: float
    best_case_score: float
    worst_case_score: float
    outcome_evaluations: List[OutcomeEvaluation] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)


class ExpectedStateEvaluator:
    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = {
            "utility": float(weights.get("utility", 1.0)) if weights else 1.0,
            "goal_alignment": float(weights.get("goal_alignment", 1.0)) if weights else 1.0,
            "risk": float(weights.get("risk", 0.5)) if weights else 0.5,
            "cost": float(weights.get("cost", 0.5)) if weights else 0.5,
            "confidence": float(weights.get("confidence", 0.5)) if weights else 0.5,
        }

    def evaluate(self, transition: ProbabilisticTransition, goal_state: GoalState) -> ExpectedEvaluation:
        if not transition or not transition.possible_states:
            return ExpectedEvaluation(
                expected_score=0.0,
                expected_utility=0.0,
                expected_goal_alignment=0.0,
                expected_risk=0.0,
                expected_cost=0.0,
                expected_confidence=0.0,
                best_case_score=0.0,
                worst_case_score=0.0,
                outcome_evaluations=[],
                explanation={"score": 0.0, "reason": "No possible states to evaluate."},
            )

        evaluations: List[OutcomeEvaluation] = []
        for state, probability in zip(transition.possible_states, transition.probabilities):
            utility = self._utility_from_state(state)
            goal_alignment = self._goal_alignment(state, goal_state)
            risk = self._risk_from_state(state)
            cost = self._cost_from_state(state)
            confidence = self._confidence_from_state(state, transition.confidence)
            score = (
                utility * self.weights["utility"]
                + goal_alignment * self.weights["goal_alignment"]
                - risk * self.weights["risk"]
                - cost * self.weights["cost"]
                + confidence * self.weights["confidence"]
            )

            evaluations.append(
                OutcomeEvaluation(
                    state=dict(state),
                    probability=float(probability),
                    score=score,
                    utility=utility,
                    goal_alignment=goal_alignment,
                    risk=risk,
                    cost=cost,
                    confidence=confidence,
                    explanation={
                        "score": round(score, 4),
                        "weights": {k: round(v, 4) for k, v in self.weights.items()},
                    },
                )
            )

        expected_score = sum(item.probability * item.score for item in evaluations)
        expected_utility = sum(item.probability * item.utility for item in evaluations)
        expected_goal_alignment = sum(item.probability * item.goal_alignment for item in evaluations)
        expected_risk = sum(item.probability * item.risk for item in evaluations)
        expected_cost = sum(item.probability * item.cost for item in evaluations)
        expected_confidence = sum(item.probability * item.confidence for item in evaluations)
        best_case_score = max(item.score for item in evaluations) if evaluations else 0.0
        worst_case_score = min(item.score for item in evaluations) if evaluations else 0.0

        explanation = {
            "score": round(expected_score, 4),
            "expected_utility": round(expected_utility, 4),
            "expected_goal_alignment": round(expected_goal_alignment, 4),
            "expected_risk": round(expected_risk, 4),
            "expected_cost": round(expected_cost, 4),
            "expected_confidence": round(expected_confidence, 4),
            "best_case_score": round(best_case_score, 4),
            "worst_case_score": round(worst_case_score, 4),
            "distribution_size": len(evaluations),
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
        }

        return ExpectedEvaluation(
            expected_score=round(expected_score, 4),
            expected_utility=round(expected_utility, 4),
            expected_goal_alignment=round(expected_goal_alignment, 4),
            expected_risk=round(expected_risk, 4),
            expected_cost=round(expected_cost, 4),
            expected_confidence=round(expected_confidence, 4),
            best_case_score=round(best_case_score, 4),
            worst_case_score=round(worst_case_score, 4),
            outcome_evaluations=evaluations,
            explanation=explanation,
        )

    def _utility_from_state(self, state: Dict[str, Any]) -> float:
        skill_values = [float(value) for key, value in state.items() if key != "confidence"]
        if not skill_values:
            return 0.0
        return sum(skill_values) / max(1, len(skill_values)) / 100.0

    def _goal_alignment(self, state: Dict[str, Any], goal_state: GoalState) -> float:
        if not getattr(goal_state, "target_skills", None):
            return 0.0
        scores = []
        for skill, target in goal_state.target_skills.items():
            current = float(state.get(skill, 0) or 0)
            target_value = float(target)
            if target_value <= 0:
                scores.append(1.0 if current >= 0 else 0.0)
            else:
                scores.append(max(0.0, min(1.0, current / target_value)))
        return sum(scores) / max(1, len(scores))

    def _risk_from_state(self, state: Dict[str, Any]) -> float:
        return float(state.get("risk", 0.0) or 0.0)

    def _cost_from_state(self, state: Dict[str, Any]) -> float:
        return float(state.get("cost", 0.0) or 0.0)

    def _confidence_from_state(self, state: Dict[str, Any], base_confidence: float) -> float:
        confidence = float(state.get("confidence", base_confidence) or base_confidence)
        return max(0.0, min(1.0, confidence))
