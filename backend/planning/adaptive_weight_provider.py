from __future__ import annotations

from typing import Dict

from backend.planning.planning_context import PlanningContext


class AdaptiveWeightProvider:
    def provide_weights(self, context: PlanningContext) -> Dict[str, float]:
        context.validate()

        confidence = max(0.0, min(1.0, float(context.confidence)))
        risk_influence = 1.0 - max(0.0, min(1.0, float(context.risk_tolerance)))
        uncertainty_influence = 1.0 - max(0.0, min(1.0, float(context.uncertainty_tolerance)))

        raw_weights = {
            "utility": 0.35 + 0.6 * max(0.0, min(1.0, float(context.risk_tolerance))) + 0.2 * confidence,
            "goal_alignment": 0.35 + 0.6 * max(0.0, min(1.0, float(context.risk_tolerance))) + 0.2 * confidence,
            "risk": 0.2 + 2.0 * risk_influence,
            "cost": 0.15 + 0.25 * (1.0 - confidence),
            "confidence": 0.3 + 0.35 * confidence + 0.2 * (1.0 - uncertainty_influence),
            "uncertainty": 0.2 + 2.0 * uncertainty_influence,
        }

        total = sum(max(0.0, float(value)) for value in raw_weights.values())
        if total <= 0.0:
            return {
                "utility": 1.0,
                "goal_alignment": 1.0,
                "risk": 1.0,
                "cost": 1.0,
                "confidence": 1.0,
                "uncertainty": 1.0,
            }

        normalized = {key: round(value / total, 4) for key, value in raw_weights.items()}
        remainder = 1.0 - sum(normalized.values())
        if abs(remainder) >= 1e-8:
            last_key = list(normalized.keys())[-1]
            normalized[last_key] = round(normalized[last_key] + remainder, 4)
        return normalized
