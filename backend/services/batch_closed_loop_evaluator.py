from __future__ import annotations

from copy import deepcopy
from typing import List, Optional, Dict, Any

from backend.models.batch_closed_loop_result import BatchClosedLoopResult, BatchStepResult
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.closed_loop_validation import ClosedLoopValidation


class BatchClosedLoopEvaluator:
    """Run batch closed-loop evaluation across a sequence of experiences.

    Experiences should be ordered. The evaluator processes them in pairs: (N, N+1) where N is
    used for calibration and N+1 is used for held-out evaluation. If `apply_accepted` is True,
    accepted calibrations are accumulated into the learning parameters and used for subsequent steps.
    The baseline parameters are never mutated.
    """

    def __init__(self) -> None:
        self.validator = ClosedLoopValidation()

    def run(
        self,
        experiences: List[DecisionOutcome],
        current_parameters: Optional[CalibrationParameters] = None,
        learning_rate: float = 0.1,
        bounds: Optional[Dict[str, Any]] = None,
        apply_accepted: bool = True,
    ) -> BatchClosedLoopResult:
        base_params = deepcopy(current_parameters) if current_parameters is not None else CalibrationParameters()
        learning_params = deepcopy(base_params)

        steps: List[BatchStepResult] = []

        baseline_errors = []
        calibrated_errors = []
        improvements = []
        successful = 0
        failed = 0
        rejected = 0

        # Process in pairs
        for i in range(0, len(experiences) - 1, 2):
            n = experiences[i]
            n1 = experiences[i + 1]

            # Run closed-loop validation using current learning params
            res = self.validator.run(n, n1, current_parameters=learning_params, learning_rate=learning_rate, bounds=bounds)

            steps.append(BatchStepResult(index=i, validation=res))

            # Aggregate
            baseline = res.baseline_future_error
            calibrated = res.calibrated_future_error
            if baseline is not None:
                baseline_errors.append(baseline)
            if calibrated is not None:
                calibrated_errors.append(calibrated)
            if res.error_improvement is not None:
                improvements.append(res.error_improvement)

            if res.helped:
                successful += 1
                # accept calibration into learning_params if requested
                if apply_accepted:
                    learning_params = deepcopy(res.calibrated_parameters)
            else:
                # not helpful
                failed += 1
                rejected += 1

        mean_baseline = round(sum(baseline_errors) / len(baseline_errors), 4) if baseline_errors else None
        mean_calibrated = round(sum(calibrated_errors) / len(calibrated_errors), 4) if calibrated_errors else None
        mean_improv = round(sum(improvements) / len(improvements), 4) if improvements else None

        result = BatchClosedLoopResult(
            steps=steps,
            mean_baseline_error=mean_baseline,
            mean_calibrated_error=mean_calibrated,
            mean_improvement=mean_improv,
            successful_calibrations=successful,
            failed_calibrations=failed,
            rejected_calibrations=rejected,
            final_learning_parameters=learning_params,
            metadata={
                "pairs_processed": len(steps),
                "apply_accepted": apply_accepted,
                "learning_rate": learning_rate,
                "bounds": bounds or {},
                "baseline_parameters": base_params.model_dump(),
            },
        )

        return result
