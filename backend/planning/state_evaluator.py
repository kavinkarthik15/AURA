from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.models.goal_state import GoalState


DEFAULT_EVALUATION_WEIGHTS: Dict[str, float] = {
    "utility": 1.0,
    "goal_alignment": 1.0,
    "risk": 0.5,
    "cost": 0.5,
    "confidence": 0.5,
}


@dataclass
class StateEvaluation:
    score: float
    components: Dict[str, float] = field(default_factory=dict)
    explanation: Dict[str, Any] = field(default_factory=dict)


class StateEvaluator:
    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = self._normalize_weights(weights or DEFAULT_EVALUATION_WEIGHTS)

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        normalized = {
            "utility": float(weights.get("utility", 1.0)),
            "goal_alignment": float(weights.get("goal_alignment", 1.0)),
            "risk": float(weights.get("risk", 0.5)),
            "cost": float(weights.get("cost", 0.5)),
            "confidence": float(weights.get("confidence", 0.5)),
        }
        for key, value in list(normalized.items()):
            if value < 0:
                normalized[key] = 0.0
        return normalized

    def evaluate_state(
        self,
        current_state: Dict[str, Any],
        predicted_state: Dict[str, Any],
        goal_state: GoalState,
        utility: float = 0.0,
        risk: float = 0.0,
        cost: float = 0.0,
        confidence: float = 0.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> StateEvaluation:
        weights = self._normalize_weights(weights or self.weights)

        goal_alignment = self._goal_alignment_score(current_state, predicted_state, goal_state)
        utility_component = float(utility)
        risk_component = float(risk)
        cost_component = float(cost)
        confidence_component = float(confidence)

        total = (
            utility_component * weights["utility"]
            + goal_alignment * weights["goal_alignment"]
            - risk_component * weights["risk"]
            - cost_component * weights["cost"]
            + confidence_component * weights["confidence"]
        )

        components = {
            "utility": utility_component * weights["utility"],
            "goal_alignment": goal_alignment * weights["goal_alignment"],
            "risk_penalty": -(risk_component * weights["risk"]),
            "cost_penalty": -(cost_component * weights["cost"]),
            "confidence": confidence_component * weights["confidence"],
        }

        explanation = {
            "score": round(total, 4),
            "components": {key: round(value, 4) for key, value in components.items()},
            "weights": {key: round(value, 4) for key, value in weights.items()},
            "goal_state": goal_state.model_dump() if hasattr(goal_state, "model_dump") else {"goal": goal_state.goal, "target_skills": goal_state.target_skills},
        }
        return StateEvaluation(score=round(total, 4), components=components, explanation=explanation)

    def evaluate_node(
        self,
        node: Any,
        goal_state: GoalState,
        weights: Optional[Dict[str, float]] = None,
    ) -> StateEvaluation:
        utility = float(getattr(node, "accumulated_utility", 0.0) or 0.0)
        risk = float(getattr(node, "accumulated_risk", 0.0) or 0.0)
        cost = float(getattr(node, "accumulated_cost", 0.0) or 0.0)
        confidence = self._infer_confidence(node)
        predicted_state = getattr(node, "predicted_state", {}) or getattr(node, "current_state", {}) or {}
        current_state = getattr(node, "current_state", {}) or {}
        goal_alignment = self._goal_alignment_score(current_state, predicted_state, goal_state)
        if weights is None:
            weights = self.weights
        weighted_components = {
            "utility": utility * weights["utility"],
            "goal_alignment": goal_alignment * weights["goal_alignment"],
            "risk_penalty": -(risk * weights["risk"]),
            "cost_penalty": -(cost * weights["cost"]),
            "confidence": confidence * weights["confidence"],
        }
        total = sum(weighted_components.values())
        explanation = {
            "score": round(total, 4),
            "components": {key: round(value, 4) for key, value in weighted_components.items()},
            "weights": {key: round(value, 4) for key, value in self._normalize_weights(weights).items()},
            "goal_state": goal_state.model_dump() if hasattr(goal_state, "model_dump") else {"goal": goal_state.goal, "target_skills": goal_state.target_skills},
        }
        return StateEvaluation(score=round(total, 4), components=weighted_components, explanation=explanation)

    def _infer_confidence(self, node: Any) -> float:
        confidence = getattr(node, "confidence", None)
        if confidence is not None:
            return float(confidence)
        goal_alignment = getattr(node, "goal_alignment", {}) or {}
        if goal_alignment:
            values = [float(v) for v in goal_alignment.values() if isinstance(v, (int, float))]
            if values:
                return sum(values) / len(values)
        return 0.0

    def _goal_alignment_score(self, current_state: Dict[str, Any], predicted_state: Dict[str, Any], goal_state: GoalState) -> float:
        if not goal_state or not getattr(goal_state, "target_skills", None):
            return 0.0

        scores: list[float] = []
        for skill, target_value in goal_state.target_skills.items():
            current_value = float(current_state.get(skill, 0) or 0)
            predicted_value = float(predicted_state.get(skill, current_value) or current_value)
            target_gap = max(1.0, float(target_value) - current_value)
            if target_gap <= 0:
                progress = 1.0 if predicted_value >= float(target_value) else 0.0
            else:
                progress = max(0.0, min(1.0, (predicted_value - current_value) / target_gap))
            scores.append(progress)
        return sum(scores) / len(scores) if scores else 0.0
