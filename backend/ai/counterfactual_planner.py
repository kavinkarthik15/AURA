from __future__ import annotations

from typing import Any, Dict, List

from backend.ai.counterfactual_scorer import CounterfactualScorer


class CounterfactualPlanner:
    def __init__(self) -> None:
        self.version = "counterfactual_v1"

    def generate(self, plan: List[str], alternatives: List[List[str]] | None = None) -> List[Dict[str, Any]]:
        variants = []
        base_plan = list(plan)
        for index, action in enumerate(base_plan):
            if action:
                lowered = action.lower()
                if "python" in lowered:
                    alt = base_plan.copy()
                    alt[index] = "DSA"
                    variants.append({"plan": alt, "reason": "What if Python is replaced by DSA?"})
                if "project" in lowered:
                    alt = base_plan.copy()
                    alt[index] = "Revision"
                    variants.append({"plan": alt, "reason": "What if project work is replaced by revision?"})
        for extra in alternatives or []:
            variants.append({"plan": extra, "reason": "Alternative plan variant"})
        scored = CounterfactualScorer().score(plan, variants[:5])
        return scored
