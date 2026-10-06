from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator

from backend.models.calibration_parameters import CalibrationParameters


class CalibrationResult(BaseModel):
    updated_parameters: CalibrationParameters = Field(..., description="Proposed updated calibration parameters")
    error_before: float | None = Field(None, description="Aggregate error before calibration")
    error_after_estimate: float | None = Field(None, description="Estimated aggregate error after applying the update")
    updates_applied: Dict[str, Any] = Field(default_factory=dict, description="Detailed per-parameter update magnitudes")
    confidence: float = Field(0.0, description="Confidence in calibration proposal (0..1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata about the calibration run")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: Any) -> float:
        number = float(value)
        if number < 0.0 or number > 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return number

    model_config = {"validate_assignment": True, "extra": "forbid"}
