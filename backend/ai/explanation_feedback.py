from __future__ import annotations

from typing import Any, Dict, List


class ExplanationFeedbackLearner:
    def __init__(self) -> None:
        self.version = "feedback_learning_v1"
        self.feedback_store: Dict[str, List[Dict[str, Any]]] = {}

    def record_feedback(self, explanation_id: str, rating: str, weight: float) -> Dict[str, Any]:
        entry = {"explanation_id": explanation_id, "rating": rating, "weight": weight}
        self.feedback_store.setdefault(explanation_id, []).append(entry)
        feedback_count = len(self.feedback_store[explanation_id])
        total_weight = sum(item["weight"] for item in self.feedback_store[explanation_id])
        current_weight = round(max(0.0, min(1.0, 1.0 - total_weight / max(1, feedback_count * 2))), 2)
        return {
            "feedback_count": feedback_count,
            "current_weight": current_weight,
            "rating": rating,
            "explanation_id": explanation_id,
        }

    def summarize(self) -> Dict[str, Any]:
        return {
            "tracked_explanations": len(self.feedback_store),
            "feedback_entries": sum(len(items) for items in self.feedback_store.values()),
        }
