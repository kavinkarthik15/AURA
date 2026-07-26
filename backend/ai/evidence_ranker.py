from __future__ import annotations

from typing import Any, Dict, List


class EvidenceRanker:
    def __init__(self) -> None:
        self.version = "evidence_ranker_v1"

    def rank(self, evidence: List[Dict[str, Any]], similarity: float = 0.0, retrieval_confidence: float = 0.0, freshness: float = 1.0) -> List[Dict[str, Any]]:
        scored = []
        for item in evidence:
            success = 1.0 if item.get("success") else 0.0
            score = round(0.35 * float(item.get("similarity", similarity)) + 0.3 * success + 0.2 * float(item.get("freshness", freshness)) + 0.15 * float(item.get("retrieval_confidence", retrieval_confidence)), 2)
            scored.append({**item, "score": score})
        scored.sort(key=lambda entry: entry["score"], reverse=True)
        return scored
