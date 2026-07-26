from __future__ import annotations

from typing import Any, Dict, List


class CounterfactualScorer:
    def __init__(self) -> None:
        self.version = "counterfactual_scorer_v1"

    def score(self, original_plan: List[str], variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for variant in variants:
            expected_success = 0.78 if variant.get("plan") == original_plan else 0.85
            improvement = round(expected_success - 0.78, 2)
            scored.append({
                **variant,
                "expected_success": expected_success,
                "improvement": improvement,
                "label": "Counterfactual" if variant.get("plan") != original_plan else "Original Plan",
            })
        return scored
