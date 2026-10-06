from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.calibration_result import CalibrationResult


class ClosedLoopValidationResult(BaseModel):
    # Experience N (used to calibrate)
    initial_prediction: Dict[str, Any] = Field(..., description="Predicted state used for calibration (experience N)")
    initial_actual: Dict[str, Any] = Field(..., description="Observed actual state for experience N")
    initial_error: Optional[float] = Field(None, description="Aggregate prediction error on experience N")

    # Calibration proposal produced from experience N
    calibration_proposal: CalibrationResult = Field(..., description="Calibration proposal produced from experience N")
    calibrated_parameters: CalibrationParameters = Field(..., description="Parameters after applying proposal (non-mutating)")

    # Evaluation on held-out future experience (N+1)
    future_selected_action: str = Field(..., description="Action selected for the held-out future decision")
    future_actual_state: Optional[Dict[str, Any]] = Field(None, description="Actual observed state for the held-out future decision")
    baseline_future_prediction: Dict[str, Any] = Field(..., description="Original prediction for experience N+1")
    baseline_future_error: Optional[float] = Field(None, description="Baseline error on experience N+1 before calibration")
    calibrated_future_prediction: Dict[str, Any] = Field(..., description="Calibrated prediction for experience N+1")
    calibrated_future_error: Optional[float] = Field(None, description="Error on experience N+1 after calibration")

    # Summary
    error_improvement: Optional[float] = Field(None, description="baseline_future_error - calibrated_future_error")
    helped: bool = Field(False, description="Whether calibration improved held-out prediction")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Experiment metadata")

    model_config = {"validate_assignment": True, "extra": "forbid"}
