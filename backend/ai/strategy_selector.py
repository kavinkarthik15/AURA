from __future__ import annotations

from typing import Dict, Any, List


class StrategySelector:
    def select(self, goal: str, confidence: float, evidence_count: int, contradictions: bool) -> Dict[str, Any]:
        graph: List[str] = []
        if "Simple" in goal and evidence_count >= 2 and not contradictions:
            graph = ["Retrieve Experience", "Check Evidence Sufficiency", "Plan"]
            strategy = "retrieval_only"
        elif "Novel" in goal or contradictions or evidence_count < 2:
            graph = ["Beam Search", "Counterfactuals", "Reflection", "Plan"]
            strategy = "beam_search_counterfactuals"
        elif confidence < 0.7:
            graph = ["Retrieval", "Reasoning", "Evidence Sufficiency", "Plan"]
            strategy = "retrieval_reasoning"
        else:
            graph = ["Retrieve Experience", "Plan"]
            strategy = "retrieval"
        return {
            "strategy": strategy,
            "goal": goal,
            "confidence": round(confidence, 4),
            "decision_graph": graph,
        }
