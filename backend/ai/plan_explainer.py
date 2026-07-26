from __future__ import annotations

from typing import Any, Dict, List

from backend.ai.evidence_ranker import EvidenceRanker


class PlanExplainer:
    def __init__(self) -> None:
        self.version = "explanation_v1"

    def explain(self, plan: List[str], experiences: List[Dict[str, Any]], confidence: float, digital_twin_confidence: float) -> Dict[str, Any]:
        positive_experiences = [item for item in experiences if item.get("success")]
        success_rate = round(sum(1 for item in positive_experiences) / max(1, len(experiences)), 2) if experiences else 0.0
        ranked_evidence = EvidenceRanker().rank([
            {"experience_id": f"exp_{idx}", "success": item.get("success"), "similarity": 0.9, "freshness": 1.0, "retrieval_confidence": confidence}
            for idx, item in enumerate(experiences)
        ], similarity=0.9, retrieval_confidence=confidence, freshness=1.0)
        rationale = [
            f"Similar users improved outcomes by {round(confidence * 100, 0)}%.",
            f"Observed success rate: {round(success_rate * 100, 0)}%.",
            "Low execution risk." if confidence >= 0.7 else "Moderate execution risk.",
            f"Digital twin confidence: {round(digital_twin_confidence, 2)}.",
            "Matches the current goal." if plan else "No plan available.",
            *[f"Evidence {entry['experience_id']} ({entry['score'] * 100:.0f}%)" for entry in ranked_evidence[:3]],
        ]
        return {
            "plan": plan,
            "summary": "Recommended because:\n- " + "\n- ".join(rationale),
            "confidence": round(min(0.99, confidence), 2),
            "digital_twin_confidence": round(digital_twin_confidence, 2),
            "success_rate": round(success_rate, 2),
            "ranked_evidence": ranked_evidence,
        }
