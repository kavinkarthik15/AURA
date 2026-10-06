from __future__ import annotations

from copy import deepcopy
from typing import Optional, Dict, Any

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.calibration_experiment_result import CalibrationExperimentResult
from backend.models.calibration_result import CalibrationResult
from backend.models.decision_outcome import DecisionOutcome
from backend.services.calibration_applier import CalibrationApplier
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.models.prediction_error_result import PredictionErrorResult


class CalibrationExperiment:
    """Run an isolated calibration experiment: compare baseline vs calibrated prediction error.

    Does not mutate inputs; produces a `CalibrationExperimentResult` describing the outcome.
    """

    def __init__(self) -> None:
        self.evaluator = PredictionErrorEvaluator()
        self.calibrator = DigitalTwinCalibrator()
        self.applier = CalibrationApplier()

    def run(
        self,
        decision_outcome: DecisionOutcome,
        current_parameters: Optional[CalibrationParameters] = None,
        learning_rate: float = 0.1,
        bounds: Optional[Dict[str, Any]] = None,
    ) -> CalibrationExperimentResult:
        # Baseline evaluation
        baseline_error_result: PredictionErrorResult = self.evaluator.evaluate(decision_outcome)
        baseline_error = baseline_error_result.prediction_error

        # Compute calibration proposal
        calibration_result: CalibrationResult = self.calibrator.calibrate(
            baseline_error_result, current_parameters=current_parameters, learning_rate=learning_rate, bounds=bounds
        )

        # Apply calibration proposal non-destructively
        current_params = deepcopy(current_parameters) if current_parameters is not None else CalibrationParameters()
        calibrated_params = self.applier.apply(current_params, calibration_result)

        # Simulate calibrated predicted_state by applying expected_state_bias
        original_predicted = deepcopy(decision_outcome.predicted_state or {})
        calibrated_predicted = {}
        for key, val in original_predicted.items():
            bias = calibrated_params.expected_state_bias.get(key, 0.0)
            calibrated_predicted[key] = float(val) + float(bias)
        # Also include bias-only keys not in original_predicted
        for key, bias in calibrated_params.expected_state_bias.items():
            if key not in calibrated_predicted:
                calibrated_predicted[key] = float(bias)

        # Build a new DecisionOutcome copy with adjusted predicted_state
        serial = decision_outcome.model_dump()
        serial["predicted_state"] = calibrated_predicted
        calibrated_decision = DecisionOutcome(**serial)

        calibrated_error_result: PredictionErrorResult = self.evaluator.evaluate(calibrated_decision)
        calibrated_error = calibrated_error_result.prediction_error

        # Compute deltas
        error_delta = None
        improvement = None
        improved = False
        if baseline_error is not None and calibrated_error is not None:
            error_delta = round(float(baseline_error) - float(calibrated_error), 4)
            improvement = error_delta
            improved = error_delta > 0.0

        return CalibrationExperimentResult(
            baseline_error=baseline_error,
            calibrated_error=calibrated_error,
            error_delta=error_delta,
            improvement=improvement,
            improved=improved,
            baseline_parameters=current_params,
            calibrated_parameters=calibrated_params,
            metadata={"learning_rate": learning_rate, "bounds": bounds or {}},
        )
