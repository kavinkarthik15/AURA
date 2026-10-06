from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from backend.models.calibration_parameters import CalibrationParameters


class CalibrationExperimentResult(BaseModel):
    baseline_error: Optional[float] = Field(None, description="Aggregate prediction error before calibration")
    calibrated_error: Optional[float] = Field(None, description="Aggregate prediction error after applying calibration proposal")
    error_delta: Optional[float] = Field(None, description="baseline_error - calibrated_error")
    improvement: Optional[float] = Field(None, description="Positive value indicates improvement")
    improved: bool = Field(False, description="Whether calibration improved predictions")
    baseline_parameters: CalibrationParameters = Field(..., description="Original parameters")
    calibrated_parameters: CalibrationParameters = Field(..., description="Proposed calibrated parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Experiment metadata")

    model_config = {"validate_assignment": True, "extra": "forbid"}
