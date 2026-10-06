from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.models.goal_state import GoalState


@dataclass
class PlanningContext:
    current_state: Dict[str, Any]
    goal_state: GoalState
    risk_tolerance: float = 0.5
    uncertainty_tolerance: float = 0.5
    constraints: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.goal_state, GoalState):
            raise ValueError("goal_state must be a GoalState instance")

        if not 0.0 <= self.risk_tolerance <= 1.0:
            raise ValueError("risk_tolerance must be between 0 and 1")

        if not 0.0 <= self.uncertainty_tolerance <= 1.0:
            raise ValueError("uncertainty_tolerance must be between 0 and 1")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        goal_state_dict = None
        if hasattr(self.goal_state, "model_dump"):
            goal_state_dict = self.goal_state.model_dump()
        elif hasattr(self.goal_state, "dict"):
            goal_state_dict = self.goal_state.dict()
        else:
            goal_state_dict = self.goal_state

        return {
            "current_state": dict(self.current_state),
            "goal_state": goal_state_dict,
            "risk_tolerance": self.risk_tolerance,
            "uncertainty_tolerance": self.uncertainty_tolerance,
            "constraints": list(self.constraints),
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }
