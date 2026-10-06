from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PlanningHorizon(BaseModel):
    horizon_depth: int = Field(..., description="Depth of the planning horizon, must be 1 or more")
    candidate_actions: List[str] = Field(..., description="List of candidate actions for the first step")
    discount_factor: float = Field(1.0, description="Discount factor for future reward, 0 < discount_factor <= 1")
    max_branches: Optional[int] = Field(None, description="Maximum branches to explore per step")
    use_digital_twin: bool = Field(False, description="Whether the digital twin should be used for this horizon")

    @field_validator("horizon_depth")
    @classmethod
    def validate_horizon_depth(cls, value: int) -> int:
        if not isinstance(value, int) or value < 1:
            raise ValueError("horizon_depth must be an integer >= 1")
        return value

    @field_validator("candidate_actions", mode="before")
    @classmethod
    def validate_candidate_actions(cls, value: Any) -> List[str]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("candidate_actions must be a non-empty list of action names")
        actions = [str(item).strip() for item in value if item is not None]
        if not actions or any(not action for action in actions):
            raise ValueError("candidate_actions must contain at least one non-empty action name")
        return list(actions)

    @field_validator("discount_factor")
    @classmethod
    def validate_discount_factor(cls, value: float) -> float:
        value = float(value)
        if value <= 0.0 or value > 1.0:
            raise ValueError("discount_factor must be > 0 and <= 1")
        return value

    @field_validator("max_branches")
    @classmethod
    def validate_max_branches(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if not isinstance(value, int) or value < 1:
            raise ValueError("max_branches must be an integer >= 1 when provided")
        return value

    @field_validator("candidate_actions")
    @classmethod
    def copy_candidate_actions(cls, value: List[str]) -> List[str]:
        return deepcopy(value)

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }
