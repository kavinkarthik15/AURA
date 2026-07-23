from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field, field_validator


class Experience(BaseModel):
    experience_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = "default_user"
    experience_type: str = "learning"
    state_before: Dict
    action: str
    context: Dict
    state_after: Dict
    state_delta: Dict = Field(default_factory=dict)
    outcome_value: float
    experience_confidence: float = 0.5
    experience_weight: float = 1.0

    @field_validator("experience_id")
    @classmethod
    def validate_experience_id(cls, value: str) -> str:
        if not value.startswith("exp_"):
            raise ValueError("experience_id must start with 'exp_'")
        return value

    @field_validator("outcome_value")
    @classmethod
    def validate_outcome_value(cls, value: float) -> float:
        if not -1.0 <= value <= 1.0:
            raise ValueError("outcome_value must be between -1.0 and 1.0")
        return value

    @field_validator("experience_confidence")
    @classmethod
    def validate_experience_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("experience_confidence must be between 0.0 and 1.0")
        return value

    @field_validator("experience_weight")
    @classmethod
    def validate_experience_weight(cls, value: float) -> float:
        if value < 0:
            raise ValueError("experience_weight must be non-negative")
        return value

    @field_validator("state_before", "state_after", "state_delta", "context")
    @classmethod
    def validate_mapping(cls, value: Dict) -> Dict:
        if value is None:
            raise ValueError("mapping fields must not be None")
        return value

    @field_validator("state_before")
    @classmethod
    def validate_state_before(cls, value: Dict) -> Dict:
        if not value:
            raise ValueError("state_before must not be empty")
        return value

    @field_validator("state_after")
    @classmethod
    def validate_state_after(cls, value: Dict) -> Dict:
        if not value:
            raise ValueError("state_after must not be empty")
        return value
