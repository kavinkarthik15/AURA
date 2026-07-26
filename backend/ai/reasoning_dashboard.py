from __future__ import annotations

from typing import Any, Dict


class ReasoningDashboard:
    def __init__(self) -> None:
        self.version = "dashboard_v1"

    def render(self, confidence: Dict[str, Any], evidence: list[Dict[str, Any]], counterfactuals: list[Dict[str, Any]], contradictions: Dict[str, Any], coverage: float) -> str:
        top_counterfactual = counterfactuals[0] if counterfactuals else {}
        return "\n".join([
            "# Reasoning",
            "",
            "## Evidence Used",
            *[f"- {item.get('experience_id', 'unknown')}" for item in evidence[:3]],
            "",
            "## Top Counterfactual",
            f"- {top_counterfactual.get('reason', 'None')}",
            "",
            "## Confidence",
            f"- reasoning_confidence: {confidence.get('reasoning_confidence', 0.0)}",
            "",
            "## Contradictions",
            f"- detected: {contradictions.get('detected', False)}",
            "",
            "## Coverage",
            f"- coverage: {coverage}",
            "",
            "## Success Prediction",
            "- pending",
        ])
