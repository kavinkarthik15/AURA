from __future__ import annotations

from typing import Any, Dict, List


class SelfCritiqueEngine:
    def critique(self, confidence: float, consistency: bool, evidence_count: int, counterfactuals: List[Dict[str, Any]]) -> Dict[str, Any]:
        retrieval_quality = min(1.0, 0.2 + 0.2 * evidence_count + 0.2 * confidence)
        reasoning_quality = min(1.0, 0.3 * confidence + 0.3 * (1.0 if consistency else 0.5))
        counterfactual_quality = 0.9 if counterfactuals else 0.6
        policy_support = min(1.0, confidence + 0.1)
        overall = round(
            min(1.0, 0.25 * retrieval_quality + 0.25 * reasoning_quality + 0.2 * counterfactual_quality + 0.15 * policy_support + 0.15 * (0.8 if evidence_count >= 2 else 0.6)),
            4,
        )
        issues = []
        if retrieval_quality < 0.7:
            issues.append("retrieval quality below target")
        if reasoning_quality < 0.7:
            issues.append("reasoning quality below target")
        if counterfactual_quality < 0.7:
            issues.append("counterfactual quality below target")
        status = "needs_replanning" if issues else "acceptable"
        recommendation = "replan" if status == "needs_replanning" else "accept"
        return {
            "retrieval_quality": round(retrieval_quality, 4),
            "reasoning_quality": round(reasoning_quality, 4),
            "counterfactual_quality": round(counterfactual_quality, 4),
            "policy_support": round(policy_support, 4),
            "overall": overall,
            "status": status,
            "issues": issues,
            "recommendation": recommendation,
            "confidence": round(confidence, 4),
        }
