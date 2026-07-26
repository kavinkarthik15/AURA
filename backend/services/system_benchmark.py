from __future__ import annotations

from typing import Any, Dict


class SystemBenchmark:
    def evaluate(
        self,
        goal_success: float,
        planning_accuracy: float,
        recommendation_accuracy: float,
        policy_accuracy: float,
        retrieval_accuracy: float,
        reasoning_consistency: float,
        counterfactual_quality: float,
        execution_success: float,
        learning_improvement: float,
        reflection_score: float | None = None,
        self_critique_score: float | None = None,
    ) -> Dict[str, Any]:
        reflection_value = reflection_score if reflection_score is not None else 0.8
        self_critique_value = self_critique_score if self_critique_score is not None else 0.8
        overall = (
            0.18 * goal_success
            + 0.13 * planning_accuracy
            + 0.13 * recommendation_accuracy
            + 0.1 * policy_accuracy
            + 0.1 * retrieval_accuracy
            + 0.1 * reasoning_consistency
            + 0.08 * counterfactual_quality
            + 0.08 * execution_success
            + 0.05 * learning_improvement
            + 0.07 * reflection_value
            + 0.06 * self_critique_value
        )
        return {
            "goal_success": goal_success,
            "planning_accuracy": planning_accuracy,
            "recommendation_accuracy": recommendation_accuracy,
            "policy_accuracy": policy_accuracy,
            "retrieval_accuracy": retrieval_accuracy,
            "reasoning_consistency": reasoning_consistency,
            "counterfactual_quality": counterfactual_quality,
            "execution_success": execution_success,
            "learning_improvement": learning_improvement,
            "reflection_score": reflection_value,
            "self_critique_score": self_critique_value,
            "overall_intelligence_score": round(overall, 4),
            "overall_intelligence_score_v2": round(overall, 4),
        }
