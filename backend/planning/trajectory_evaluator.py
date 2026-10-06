from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.planning.adaptive_weight_provider import AdaptiveWeightProvider
from backend.planning.expected_state_evaluator import ExpectedEvaluation, ExpectedStateEvaluator
from backend.planning.planning_context import PlanningContext
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.risk_evaluator import RiskEvaluator
from backend.planning.uncertainty_evaluator import UncertaintyEvaluator


@dataclass
class TrajectoryStepEvaluation:
    step_index: int
    transition: ProbabilisticTransition
    expected_value: float
    discounted_value: float
    cumulative_utility: float
    cumulative_risk: float
    cumulative_cost: float
    goal_progress: float
    confidence: float
    risk: float = 0.0
    uncertainty: float = 0.0
    explanation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryEvaluation:
    trajectory_score: float
    expected_value: float
    cumulative_utility: float
    cumulative_risk: float
    cumulative_cost: float
    goal_progress: float
    confidence: float
    horizon: int
    discount_factor: float
    risk_sensitivity: float = 0.0
    uncertainty_sensitivity: float = 0.0
    cumulative_uncertainty: float = 0.0
    step_evaluations: List[TrajectoryStepEvaluation] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)


class TrajectoryEvaluator:
    def __init__(
        self,
        discount_factor: float = 0.9,
        expected_state_evaluator: Optional[ExpectedStateEvaluator] = None,
        risk_sensitivity: float = 0.0,
        uncertainty_sensitivity: float = 0.0,
        risk_evaluator: Optional[RiskEvaluator] = None,
        uncertainty_evaluator: Optional[UncertaintyEvaluator] = None,
        adaptive_weight_provider: Optional[AdaptiveWeightProvider] = None,
    ) -> None:
        self.discount_factor = max(0.0, min(1.0, float(discount_factor)))
        self.expected_state_evaluator = expected_state_evaluator or ExpectedStateEvaluator()
        self.risk_sensitivity = max(0.0, float(risk_sensitivity))
        self.uncertainty_sensitivity = max(0.0, float(uncertainty_sensitivity))
        self.risk_evaluator = risk_evaluator or RiskEvaluator(self.expected_state_evaluator)
        self.uncertainty_evaluator = uncertainty_evaluator or UncertaintyEvaluator(self.expected_state_evaluator)
        self.adaptive_weight_provider = adaptive_weight_provider

    def evaluate(
        self,
        transitions: List[ProbabilisticTransition],
        goal_state: GoalState,
        context: Optional[PlanningContext] = None,
    ) -> TrajectoryEvaluation:
        if not transitions:
            return TrajectoryEvaluation(
                trajectory_score=0.0,
                expected_value=0.0,
                cumulative_utility=0.0,
                cumulative_risk=0.0,
                cumulative_cost=0.0,
                goal_progress=0.0,
                confidence=0.0,
                horizon=0,
                discount_factor=self.discount_factor,
                risk_sensitivity=self.risk_sensitivity,
                uncertainty_sensitivity=self.uncertainty_sensitivity,
                cumulative_uncertainty=0.0,
                step_evaluations=[],
                explanation={"trajectory_score": 0.0, "reason": "No transitions supplied."},
            )

        cumulative_utility = 0.0
        cumulative_risk = 0.0
        cumulative_cost = 0.0
        cumulative_goal_progress = 0.0
        cumulative_confidence = 0.0
        cumulative_uncertainty = 0.0
        cumulative_risk_penalty = 0.0
        cumulative_uncertainty_penalty = 0.0
        step_evaluations: List[TrajectoryStepEvaluation] = []

        adaptive_weights = None
        expected_state_evaluator = self.expected_state_evaluator
        risk_evaluator = self.risk_evaluator
        uncertainty_evaluator = self.uncertainty_evaluator
        effective_risk_sensitivity = self.risk_sensitivity
        effective_uncertainty_sensitivity = self.uncertainty_sensitivity

        if self.adaptive_weight_provider is not None and context is not None:
            adaptive_weights = self.adaptive_weight_provider.provide_weights(context)
            expected_state_evaluator = ExpectedStateEvaluator(weights=adaptive_weights)
            uncertainty_evaluator = UncertaintyEvaluator(expected_state_evaluator)
            risk_evaluator = RiskEvaluator(expected_state_evaluator, uncertainty_evaluator)

        if context is not None:
            risk_tolerance = max(0.0, min(1.0, float(getattr(context, "risk_tolerance", 0.5))))
            uncertainty_tolerance = max(0.0, min(1.0, float(getattr(context, "uncertainty_tolerance", 0.5))))
            base_risk_sensitivity = effective_risk_sensitivity if effective_risk_sensitivity > 0.0 else 1.0
            base_uncertainty_sensitivity = effective_uncertainty_sensitivity if effective_uncertainty_sensitivity > 0.0 else 1.0
            effective_risk_sensitivity = base_risk_sensitivity * max(0.1, 2.0 * (1.0 - risk_tolerance))
            effective_uncertainty_sensitivity = base_uncertainty_sensitivity * max(0.1, 2.0 * (1.0 - uncertainty_tolerance))

        for index, transition in enumerate(transitions):
            expected_eval: ExpectedEvaluation = expected_state_evaluator.evaluate(transition, goal_state)
            risk_eval = risk_evaluator.evaluate(transition, goal_state)
            uncertainty_eval = uncertainty_evaluator.evaluate(transition, goal_state)
            step_discount = self.discount_factor ** index
            discounted_value = expected_eval.expected_score * step_discount
            cumulative_utility += expected_eval.expected_utility * step_discount
            cumulative_risk += expected_eval.expected_risk * step_discount
            cumulative_cost += expected_eval.expected_cost * step_discount
            cumulative_goal_progress += expected_eval.expected_goal_alignment * step_discount
            cumulative_confidence += expected_eval.expected_confidence * step_discount
            cumulative_uncertainty += uncertainty_eval.uncertainty * step_discount
            cumulative_risk_penalty += risk_eval.risk_score * step_discount
            cumulative_uncertainty_penalty += uncertainty_eval.uncertainty * step_discount

            step_evaluations.append(
                TrajectoryStepEvaluation(
                    step_index=index,
                    transition=transition,
                    expected_value=expected_eval.expected_score,
                    discounted_value=round(discounted_value, 4),
                    cumulative_utility=round(cumulative_utility, 4),
                    cumulative_risk=round(cumulative_risk, 4),
                    cumulative_cost=round(cumulative_cost, 4),
                    goal_progress=round(cumulative_goal_progress, 4),
                    confidence=round(cumulative_confidence, 4),
                    risk=round(risk_eval.risk_score, 4),
                    uncertainty=round(uncertainty_eval.uncertainty, 4),
                    explanation={
                        "discounted_value": round(discounted_value, 4),
                        "step_expected_score": round(expected_eval.expected_score, 4),
                        "discount_factor": round(self.discount_factor, 4),
                        "risk": round(risk_eval.risk_score, 4),
                        "uncertainty": round(uncertainty_eval.uncertainty, 4),
                    },
                )
            )

        trajectory_base_score = sum(step.discounted_value for step in step_evaluations)
        expected_value = sum(step.expected_value for step in step_evaluations)
        goal_progress = cumulative_goal_progress / max(1, len(step_evaluations))
        confidence = cumulative_confidence / max(1, len(step_evaluations))
        trajectory_score = (
            trajectory_base_score
            - effective_risk_sensitivity * cumulative_risk_penalty
            - effective_uncertainty_sensitivity * cumulative_uncertainty_penalty
        )

        result = TrajectoryEvaluation(
            trajectory_score=round(trajectory_score, 4),
            expected_value=round(expected_value, 4),
            cumulative_utility=round(cumulative_utility, 4),
            cumulative_risk=round(cumulative_risk, 4),
            cumulative_cost=round(cumulative_cost, 4),
            goal_progress=round(goal_progress, 4),
            confidence=round(confidence, 4),
            horizon=len(transitions),
            discount_factor=self.discount_factor,
            risk_sensitivity=round(effective_risk_sensitivity, 4),
            uncertainty_sensitivity=round(effective_uncertainty_sensitivity, 4),
            cumulative_uncertainty=round(cumulative_uncertainty, 4),
            step_evaluations=step_evaluations,
            explanation={
                "trajectory_score": round(trajectory_score, 4),
                "expected_value": round(expected_value, 4),
                "cumulative_utility": round(cumulative_utility, 4),
                "cumulative_risk": round(cumulative_risk, 4),
                "cumulative_cost": round(cumulative_cost, 4),
                "goal_progress": round(goal_progress, 4),
                "confidence": round(confidence, 4),
                "discount_factor": round(self.discount_factor, 4),
                "horizon": len(transitions),
                "risk_sensitivity": round(effective_risk_sensitivity, 4),
                "uncertainty_sensitivity": round(effective_uncertainty_sensitivity, 4),
                "cumulative_risk_penalty": round(cumulative_risk_penalty, 4),
                "cumulative_uncertainty_penalty": round(cumulative_uncertainty_penalty, 4),
                "weights": {k: round(v, 4) for k, v in ((adaptive_weights or self.expected_state_evaluator.weights).items())},
            },
        )
        return result
