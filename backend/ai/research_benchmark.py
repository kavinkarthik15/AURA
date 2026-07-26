from __future__ import annotations

from typing import Any, Dict


class ResearchBenchmark:
    def evaluate(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        goal_success = float(metrics.get("goal_success", 0.0))
        planning_accuracy = float(metrics.get("planning_accuracy", 0.0))
        policy_accuracy = float(metrics.get("policy_accuracy", 0.0))
        retrieval_accuracy = float(metrics.get("retrieval_accuracy", 0.0))
        reasoning_score = float(metrics.get("reasoning_score", 0.0))
        execution_success = float(metrics.get("execution_success", 0.0))
        learning_improvement = float(metrics.get("learning_improvement", 0.0))

        overall = (
            0.25 * goal_success
            + 0.15 * planning_accuracy
            + 0.15 * policy_accuracy
            + 0.15 * retrieval_accuracy
            + 0.15 * reasoning_score
            + 0.10 * execution_success
            + 0.05 * learning_improvement
        )

        return {
            "goal_success": goal_success,
            "planning_accuracy": planning_accuracy,
            "policy_accuracy": policy_accuracy,
            "retrieval_accuracy": retrieval_accuracy,
            "reasoning_score": reasoning_score,
            "execution_success": execution_success,
            "learning_improvement": learning_improvement,
            "overall_intelligence_score": round(overall, 4),
        }
