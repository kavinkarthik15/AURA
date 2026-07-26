from __future__ import annotations

from typing import Any, Dict, List


class ExplanationConsistencyChecker:
    def __init__(self) -> None:
        self.version = "consistency_v1"

    def check(self, recommendation: List[str], reasoning: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        recommendation_text = " ".join(recommendation).lower()
        reasoning_text = " ".join(reasoning.get("successful_patterns", []) + reasoning.get("failure_patterns", [])).lower()
        evidence_text = " ".join([str(item.get("experience_id", "")) for item in evidence]).lower()
        recommendation_matches_reasoning = bool(recommendation_text and reasoning_text) and (
            recommendation_text in reasoning_text or reasoning_text in recommendation_text
        )
        evidence_matches_reasoning = bool(evidence_text) and (
            recommendation_matches_reasoning or any(token in reasoning_text for token in evidence_text.split())
        )
        consistent = recommendation_matches_reasoning and evidence_matches_reasoning
        return {
            "consistent": bool(consistent),
            "recommendation_matches_reasoning": bool(recommendation_matches_reasoning),
            "evidence_matches_reasoning": bool(evidence_matches_reasoning),
        }
