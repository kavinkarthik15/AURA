from __future__ import annotations

from typing import Any, Dict, List


class ReasoningAnalytics:
    def __init__(self) -> None:
        self.version = "reasoning_analytics_v1"
        self.records: List[Dict[str, Any]] = []

    def record(self, reasoning_time_ms: float, evidence_count: int, counterfactuals_generated: int, contradictions_detected: int, explanation_length: int, coverage: float) -> Dict[str, Any]:
        entry = {
            "reasoning_time_ms": reasoning_time_ms,
            "evidence_count": evidence_count,
            "counterfactuals_generated": counterfactuals_generated,
            "contradictions_detected": contradictions_detected,
            "explanation_length": explanation_length,
            "coverage": coverage,
        }
        self.records.append(entry)
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        if not self.records:
            return {
                "average_reasoning_time_ms": 0.0,
                "average_evidence_count": 0.0,
                "counterfactuals_generated": 0,
                "contradictions_detected": 0,
                "average_explanation_length": 0.0,
                "coverage": 0.0,
            }
        count = len(self.records)
        return {
            "average_reasoning_time_ms": round(sum(item["reasoning_time_ms"] for item in self.records) / count, 2),
            "average_evidence_count": round(sum(item["evidence_count"] for item in self.records) / count, 2),
            "counterfactuals_generated": sum(item["counterfactuals_generated"] for item in self.records),
            "contradictions_detected": sum(item["contradictions_detected"] for item in self.records),
            "average_explanation_length": round(sum(item["explanation_length"] for item in self.records) / count, 2),
            "coverage": round(sum(item["coverage"] for item in self.records) / count, 2),
        }
