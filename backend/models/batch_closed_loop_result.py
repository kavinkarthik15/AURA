from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.closed_loop_validation_result import ClosedLoopValidationResult


class BatchStepResult(BaseModel):
    index: int
    validation: ClosedLoopValidationResult


class BatchClosedLoopResult(BaseModel):
    steps: List[BatchStepResult] = Field(default_factory=list)

    # Aggregates
    mean_baseline_error: Optional[float] = Field(None)
    mean_calibrated_error: Optional[float] = Field(None)
    mean_improvement: Optional[float] = Field(None)
    successful_calibrations: int = Field(0)
    failed_calibrations: int = Field(0)
    rejected_calibrations: int = Field(0)

    final_learning_parameters: CalibrationParameters = Field(...)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"validate_assignment": True, "extra": "forbid"}
