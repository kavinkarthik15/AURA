from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StateTransition:
    current_state: Dict[str, Any] = field(default_factory=dict)
    action: Any = None
    predicted_state: Dict[str, Any] = field(default_factory=dict)
    state_change: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    supporting_evidence: List[str] = field(default_factory=list)
    transition_explanation: str = ""

    def __post_init__(self) -> None:
        if not self.state_change and self.current_state and self.predicted_state:
            self.state_change = {
                key: float(predicted_value) - float(self.current_state.get(key, 0) or 0)
                for key, predicted_value in self.predicted_state.items()
            }
        self.confidence = float(self.confidence or 0.0)
        if not self.transition_explanation:
            self.transition_explanation = (
                f"Applying {self.action} moves the state from {self.current_state} to {self.predicted_state}."
            )
