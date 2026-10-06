from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PredictionErrorResult(BaseModel):
    decision_id: str = Field(..., description="Identifier of the decision outcome evaluated")
    prediction_error: Optional[float] = Field(
        None, description="Aggregate prediction error across state dimensions; None if actuals unavailable"
    )
    state_errors: Dict[str, float] = Field(
        default_factory=dict,
        description="Absolute error values for each state dimension that was predicted or observed",
    )
    signed_state_errors: Dict[str, float] = Field(
        default_factory=dict,
        description="Signed error values (actual - predicted) for each state dimension; preserves direction",
    )
    mean_absolute_error: Optional[float] = Field(
        None, description="Mean absolute error across observed state dimensions"
    )
    max_absolute_error: Optional[float] = Field(
        None, description="Maximum absolute error across observed state dimensions"
    )
    state_dimensions: int = Field(0, description="Number of state dimensions used to compute prediction error")
    actual_available: bool = Field(False, description="Whether actual state was available for evaluation")

    @field_validator("decision_id")
    @classmethod
    def validate_decision_id(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("decision_id must be a non-empty string")
        return value.strip()

    @field_validator("state_errors", mode="before")
    @classmethod
    def copy_state_errors(cls, value: Any) -> Dict[str, float]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("state_errors must be a dictionary")
        return deepcopy(value)

    @field_validator("signed_state_errors", mode="before")
    @classmethod
    def copy_signed_state_errors(cls, value: Any) -> Dict[str, float]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("signed_state_errors must be a dictionary")
        return deepcopy(value)

    @field_validator("prediction_error", "mean_absolute_error", "max_absolute_error")
    @classmethod
    def validate_error_values(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        number = float(value)
        if number < 0.0:
            raise ValueError("Error values must be non-negative")
        return round(number, 2)

    @field_validator("state_dimensions")
    @classmethod
    def validate_state_dimensions(cls, value: Any) -> int:
        if not isinstance(value, int) or value < 0:
            raise ValueError("state_dimensions must be a non-negative integer")
        return value

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }
