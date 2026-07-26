from __future__ import annotations

from typing import Any, Dict, List


class ReasoningConfidenceModel:
    def __init__(self) -> None:
        self.version = "reasoning_confidence_v1"

    def score(self, evidence_count: int, contradictions: int, coverage: float, reasoning_confidence: float) -> Dict[str, Any]:
        return {
            "reasoning_confidence": round(min(0.99, max(0.0, 0.4 * reasoning_confidence + 0.25 * min(1.0, evidence_count / 10.0) + 0.2 * coverage + 0.15 * max(0.0, 1.0 - contradictions / 5.0))), 2),
            "evidence_support": evidence_count,
            "contradictions": contradictions,
            "coverage": round(min(1.0, max(0.0, coverage)), 2),
        }
