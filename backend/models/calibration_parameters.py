from __future__ import annotations

from copy import deepcopy
from typing import Dict, Any

from pydantic import BaseModel, Field, field_validator


class CalibrationParameters(BaseModel):
    expected_state_bias: Dict[str, float] = Field(default_factory=dict, description="Bias adjustments applied to predicted state values")
    transition_probability_bias: float = Field(0.0, description="Bias applied to predicted transition probability (additive)")
    risk_bias: float = Field(0.0, description="Bias applied to predicted risk (additive)")
    uncertainty: float = Field(0.5, description="Baseline uncertainty level (0..1)")
    confidence: float = Field(0.5, description="Baseline confidence (0..1)")

    @field_validator("expected_state_bias", mode="before")
    @classmethod
    def copy_state_bias(cls, value: Any) -> Dict[str, float]:
        if value is None:
            return {}
        return deepcopy(dict(value))

    @field_validator("uncertainty", "confidence")
    @classmethod
    def validate_probability_bounds(cls, value: Any) -> float:
        number = float(value)
        if number < 0.0 or number > 1.0:
            raise ValueError("uncertainty and confidence must be between 0 and 1")
        return number

    model_config = {"validate_assignment": True, "extra": "forbid"}
