from __future__ import annotations

from typing import Any, Dict, List


class ContradictionDetector:
    def __init__(self) -> None:
        self.version = "contradiction_v1"

    def detect(self, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for experience in experiences:
            key = str(experience.get("goal_name") or experience.get("goal") or "general")
            grouped.setdefault(key, []).append(experience)

        contradictions = []
        for key, items in grouped.items():
            successes = [item for item in items if item.get("success")]
            failures = [item for item in items if not item.get("success")]
            if successes and failures:
                contradictions.append({
                    "goal": key,
                    "reason": "Conflicting outcomes observed under similar conditions.",
                    "factors": ["motivation", "sleep", "stress", "goal_priority", "context"],
                })
        return {"contradictions": contradictions, "detected": bool(contradictions)}
