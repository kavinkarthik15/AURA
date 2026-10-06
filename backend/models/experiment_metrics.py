from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator


class ExperimentMetrics(BaseModel):
    baseline_mae: float = Field(..., ge=0.0)
    calibrated_mae: float = Field(..., ge=0.0)
    absolute_improvement: float = Field(..., description="Mean absolute reduction in prediction error")
    improvement_percent: float = Field(..., description="Percent improvement relative to baseline error")
    acceptance_rate: float = Field(..., ge=0.0, le=1.0)
    rejection_rate: float = Field(..., ge=0.0, le=1.0)
    parameter_drift: float = Field(..., ge=0.0)
    error_by_dimension: Dict[str, float] = Field(default_factory=dict)
    error_by_action: Dict[str, float] = Field(default_factory=dict)
    rolling_baseline_mae: List[float] = Field(default_factory=list)
    rolling_calibrated_mae: List[float] = Field(default_factory=list)
    rolling_improvement_pct: List[float] = Field(default_factory=list)
    rolling_improvement: List[float] = Field(default_factory=list)
    parameter_drift_progression: List[float] = Field(default_factory=list)
    stability_metrics: Dict[str, float] = Field(default_factory=dict)
    calibration_count: int = Field(..., ge=0)
    evaluation_count: int = Field(..., ge=0)

    @field_validator("error_by_dimension", "error_by_action", "stability_metrics")
    def validate_error_dicts(cls, value: Dict[str, float]) -> Dict[str, float]:
        for key, error_value in value.items():
            if error_value < 0:
                raise ValueError(f"error values must be non-negative, got {key}={error_value}")
        return value

    @field_validator("rolling_baseline_mae", "rolling_calibrated_mae", "rolling_improvement_pct", "rolling_improvement", "parameter_drift_progression")
    def validate_rolling_values(cls, value: List[float]) -> List[float]:
        for item in value:
            if item != item:
                raise ValueError("rolling metric values must be numeric and not NaN")
        return value

    @model_validator(mode="after")
    def check_counts_and_rolling(self):
        if self.rolling_baseline_mae and len(self.rolling_baseline_mae) != self.evaluation_count:
            raise ValueError("evaluation_count must equal the length of rolling_baseline_mae when rolling_baseline_mae is provided")
        if self.rolling_calibrated_mae and len(self.rolling_calibrated_mae) != self.evaluation_count:
            raise ValueError("evaluation_count must equal the length of rolling_calibrated_mae when rolling_calibrated_mae is provided")
        if self.rolling_improvement_pct and len(self.rolling_improvement_pct) != self.evaluation_count:
            raise ValueError("evaluation_count must equal the length of rolling_improvement_pct when rolling_improvement_pct is provided")
        if self.rolling_improvement and len(self.rolling_improvement) != self.evaluation_count:
            raise ValueError("evaluation_count must equal the length of rolling_improvement when rolling_improvement is provided")
        if self.parameter_drift_progression and len(self.parameter_drift_progression) != self.evaluation_count:
            raise ValueError("evaluation_count must equal the length of parameter_drift_progression when parameter_drift_progression is provided")
        return self

    model_config = {"validate_assignment": True, "extra": "forbid"}
