from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class DecisionOutcome(BaseModel):
    decision_id: str = Field(..., description="Unique identifier for the decision outcome")
    timestamp: datetime = Field(..., description="Timestamp when the decision cycle was created")
    initial_snapshot: Any = Field(default_factory=dict, description="Immutable snapshot of the input state at decision time")
    selected_action: str = Field(..., description="Action selected for execution")
    predicted_state: Dict[str, Any] = Field(..., description="Predicted resulting state after executing the action")
    predicted_trajectory_score: float = Field(..., description="Predicted trajectory score from the digital twin")
    predicted_probability: float = Field(..., description="Predicted probability of the selected trajectory")
    predicted_risk: float = Field(..., description="Predicted risk for the selected trajectory")
    predicted_uncertainty: float = Field(..., description="Predicted uncertainty for the selected trajectory")
    actual_state: Optional[Dict[str, Any]] = Field(None, description="Actual observed state after execution")
    actual_outcome: Optional[str] = Field(None, description="Actual outcome label or description")
    prediction_error: Any = Field(None, description="Optional stored prediction error, not generated automatically")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional immutable metadata for the decision outcome")

    @field_validator("decision_id", "selected_action")
    @classmethod
    def validate_non_empty_identifier(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("decision_id and selected_action must be non-empty strings")
        return value.strip()

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError("timestamp must be a datetime or ISO formatted timestamp string")

    @field_validator("initial_snapshot", "predicted_state", "actual_state", "metadata", mode="before")
    @classmethod
    def copy_data_structures(cls, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return deepcopy(value)
        return value

    @field_validator("predicted_state")
    @classmethod
    def validate_predicted_state(cls, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("predicted_state must be a dictionary")
        return value

    @field_validator("predicted_probability", "predicted_risk", "predicted_uncertainty", "predicted_trajectory_score")
    @classmethod
    def validate_non_negative_numbers(cls, value: Any) -> float:
        number = float(value)
        if number < 0.0:
            raise ValueError("Predicted numeric fields must be non-negative")
        return number

    @field_validator("predicted_probability")
    @classmethod
    def validate_probability(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("predicted_probability must be between 0 and 1")
        return value

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }
