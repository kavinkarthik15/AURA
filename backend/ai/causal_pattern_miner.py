from __future__ import annotations

from typing import Any, Dict, List


class CausalPatternMiner:
    def __init__(self) -> None:
        self.version = "causal_v1"

    def mine(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        patterns = []
        for experience in experiences:
            actions = experience.get("actions") or []
            completed = experience.get("completed_actions") or []
            if experience.get("success") and completed:
                for action in completed:
                    patterns.append({
                        "cause": str(action),
                        "effect": "Higher completion rate",
                        "confidence": 0.8,
                    })
        return patterns[:5]
