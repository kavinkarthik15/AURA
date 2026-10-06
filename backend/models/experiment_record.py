from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.batch_closed_loop_result import BatchClosedLoopResult
from backend.models.calibration_parameters import CalibrationParameters


class PerExperienceRecord(BaseModel):
    index: int
    baseline_future_error: Optional[float]
    calibrated_future_error: Optional[float]
    error_improvement: Optional[float]
    helped: bool
    calibration_proposal: Dict[str, Any] = Field(default_factory=dict)
    parameter_changes: Dict[str, Any] = Field(default_factory=dict)


class ExperimentRecord(BaseModel):
    experiment_id: str
    timestamp: str
    batch_size: int
    calibration_config: Dict[str, Any] = Field(default_factory=dict)

    baseline_error_mean: Optional[float]
    calibrated_error_mean: Optional[float]
    improvement_mean: Optional[float]
    accepted_count: int
    rejected_count: int

    final_learning_parameters: CalibrationParameters
    experiment_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)

    steps: List[PerExperienceRecord] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_batch_result(cls, experiment_id: str, timestamp: str, batch_result: BatchClosedLoopResult):
        steps = []
        for s in batch_result.steps:
            v = s.validation
            proposal = v.calibration_proposal.model_dump() if hasattr(v.calibration_proposal, "model_dump") else {}
            # compute simple parameter changes
            before = v.metadata.get("baseline_parameters") if v.metadata else None
            # fallback to empty
            param_changes = {}
            try:
                # represent calibrated params as dict
                param_changes = {"calibrated": v.calibrated_parameters.model_dump()}
            except Exception:
                param_changes = {}

            steps.append(
                PerExperienceRecord(
                    index=s.index,
                    baseline_future_error=v.baseline_future_error,
                    calibrated_future_error=v.calibrated_future_error,
                    error_improvement=v.error_improvement,
                    helped=v.helped,
                    calibration_proposal=proposal,
                    parameter_changes=param_changes,
                )
            )

        return cls(
            experiment_id=experiment_id,
            timestamp=timestamp,
            batch_size=len(batch_result.steps),
            calibration_config=batch_result.metadata,
            baseline_error_mean=batch_result.mean_baseline_error,
            calibrated_error_mean=batch_result.mean_calibrated_error,
            improvement_mean=batch_result.mean_improvement,
            accepted_count=batch_result.successful_calibrations,
            rejected_count=batch_result.rejected_calibrations,
            final_learning_parameters=batch_result.final_learning_parameters,
            experiment_metrics=batch_result.metadata.get("experiment_metrics", {}),
            steps=steps,
            metadata=batch_result.metadata,
        )
