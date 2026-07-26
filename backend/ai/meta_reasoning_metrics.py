from __future__ import annotations

from typing import Any, Dict


class MetaReasoningMetrics:
    def evaluate(
        self,
        reflection_accuracy: float,
        replanning_rate: float,
        assumption_precision: float,
        self_critique_accuracy: float,
        strategy_selection_accuracy: float,
        evidence_sufficiency_rate: float,
        reflection_agreement_rate: float,
        false_replan_rate: float,
        reflection_improvement_rate: float,
        calibration_error: float,
    ) -> Dict[str, Any]:
        overall = (
            0.18 * reflection_accuracy
            + 0.12 * replanning_rate
            + 0.12 * assumption_precision
            + 0.12 * self_critique_accuracy
            + 0.12 * strategy_selection_accuracy
            + 0.12 * evidence_sufficiency_rate
            + 0.08 * reflection_agreement_rate
            + 0.08 * reflection_improvement_rate
            + 0.06 * (1.0 - calibration_error)
        )
        return {
            "reflection_accuracy": reflection_accuracy,
            "replanning_rate": replanning_rate,
            "assumption_precision": assumption_precision,
            "self_critique_accuracy": self_critique_accuracy,
            "strategy_selection_accuracy": strategy_selection_accuracy,
            "evidence_sufficiency_rate": evidence_sufficiency_rate,
            "reflection_agreement_rate": reflection_agreement_rate,
            "false_replan_rate": false_replan_rate,
            "reflection_improvement_rate": reflection_improvement_rate,
            "calibration_error": calibration_error,
            "overall_meta_reasoning_score": round(overall, 4),
        }
