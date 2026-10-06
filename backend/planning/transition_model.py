from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.planning.state_transition import StateTransition


@dataclass
class TransitionModel(ABC):
    """Reusable interface for translating current state + action + context into a StateTransition."""

    name: str = "transition_model"
    context: Optional[Dict[str, Any]] = None

    @abstractmethod
    def predict(self, current_state: Dict[str, Any], action: Any, context: Optional[Dict[str, Any]] = None) -> StateTransition:
        raise NotImplementedError


@dataclass
class DeterministicTransitionModel(TransitionModel):
    """Initial deterministic transition model.

    It reuses expected_state_change metadata when present and otherwise falls back to simple additive deltas.
    """

    default_confidence: float = 0.7
    evidence: List[str] = field(default_factory=list)

    def predict(self, current_state: Dict[str, Any], action: Any, context: Optional[Dict[str, Any]] = None) -> StateTransition:
        current = dict(current_state or {})
        action_name = str(action)

        state_change = {}
        if isinstance(action, dict) and action.get("expected_state_change"):
            state_change = {key: float(value) for key, value in action["expected_state_change"].items()}
        elif isinstance(action, dict) and action.get("prediction") and action["prediction"].get("expected_state_change"):
            state_change = {
                key: float(value)
                for key, value in action["prediction"]["expected_state_change"].items()
            }
        elif isinstance(action, dict) and action.get("expected_state_change") is None and action.get("predicted_state"):
            predicted = dict(action["predicted_state"])
            state_change = {
                key: float(predicted_value) - float(current.get(key, 0) or 0)
                for key, predicted_value in predicted.items()
            }
        elif isinstance(action, dict) and action.get("state_change"):
            state_change = {key: float(value) for key, value in action["state_change"].items()}
        else:
            state_change = self._infer_state_change(current, action_name)

        predicted_state = {
            key: float(current.get(key, 0) or 0) + float(value)
            for key, value in state_change.items()
        }

        evidence = list(self.evidence)
        if isinstance(context, dict):
            for key in ("supporting_evidence", "evidence"):
                items = context.get(key, [])
                if isinstance(items, list):
                    evidence.extend(str(item) for item in items)

        confidence = float(self.default_confidence)
        if isinstance(context, dict):
            confidence = float(context.get("confidence", confidence))

        explanation = (
            f"Action '{action_name}' applied to the current state produces the following transition: "
            f"{state_change}."
        )

        return StateTransition(
            current_state=current,
            action=action_name,
            predicted_state=predicted_state,
            state_change=state_change,
            confidence=confidence,
            supporting_evidence=evidence,
            transition_explanation=explanation,
        )

    def _infer_state_change(self, current_state: Dict[str, Any], action: str) -> Dict[str, Any]:
        normalized = action.lower()
        deltas: Dict[str, Any] = {}
        if "python" in normalized:
            deltas["python"] = 5.0
        if "dsa" in normalized:
            deltas["dsa"] = 3.0
        if "project" in normalized:
            deltas["projects"] = 4.0
        if "ml" in normalized or "machine" in normalized:
            deltas["ml"] = 4.0
        if not deltas:
            deltas["confidence"] = 0.2
        return deltas
