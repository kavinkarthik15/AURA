from __future__ import annotations

from typing import Any, Dict, List


class ReasoningTrace:
    def __init__(self) -> None:
        self.version = "reasoning_trace_v1"

    def build(self, goal: str, experiences: List[Dict[str, Any]], reasoning: Dict[str, Any], counterfactuals: List[Dict[str, Any]], selected_plan: List[str], explanation: Dict[str, Any], confidence: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trace": [
                goal,
                "Retrieved Experiences",
                reasoning,
                counterfactuals,
                selected_plan,
                explanation,
                confidence,
            ],
            "summary": "Goal -> Retrieved Experiences -> Reasoning -> Counterfactuals -> Selected Plan -> Explanation -> Confidence",
        }
