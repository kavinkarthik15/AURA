from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MultiStepDecisionResult(BaseModel):
    best_sequence: List[str] = Field(..., description="Best action sequence discovered for the horizon")
    first_action: str = Field(..., description="The first action to execute from the best sequence")
    trajectory_score: float = Field(..., description="Score assigned to the best trajectory")
    cumulative_probability: float = Field(..., description="Probability of the full trajectory sequence")
    risk: float = Field(..., description="Accumulated risk for the trajectory")
    uncertainty: float = Field(..., description="Accumulated uncertainty for the trajectory")
    expected_goal_progress: float = Field(..., description="Expected goal progress from the sequence")
    top_k_sequences: List[List[str]] = Field(..., description="Top-K alternative sequences")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional advisory metadata")

    @field_validator("best_sequence", "top_k_sequences", mode="before")
    @classmethod
    def validate_sequences(cls, value: Any) -> List[Any]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("Sequences must be a list of actions")
        return list(value)

    @field_validator("first_action")
    @classmethod
    def validate_first_action(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("first_action must be a non-empty action name")
        return value.strip()

    @field_validator("best_sequence")
    @classmethod
    def validate_best_sequence(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("best_sequence must contain at least one action")
        return [str(item).strip() for item in value if item is not None]

    @field_validator("cumulative_probability", "risk", "uncertainty", "expected_goal_progress")
    @classmethod
    def validate_non_negative(cls, value: float) -> float:
        value = float(value)
        if value < 0.0:
            raise ValueError("Probability, risk, uncertainty, and expected_goal_progress must be non-negative")
        return value

    @field_validator("cumulative_probability")
    @classmethod
    def validate_probability(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("cumulative_probability must be between 0 and 1")
        return value

    @field_validator("top_k_sequences")
    @classmethod
    def validate_top_k_sequences(cls, value: List[List[str]]) -> List[List[str]]:
        if any(not isinstance(sequence, list) or not sequence for sequence in value):
            raise ValueError("top_k_sequences must be a list of non-empty action sequences")
        return [[str(item).strip() for item in sequence if item is not None] for sequence in value]

    @field_validator("metadata", mode="before")
    @classmethod
    def copy_metadata(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        return deepcopy(dict(value))

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }
