from __future__ import annotations

from copy import deepcopy
from typing import Optional, Dict, Any

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.closed_loop_validation_result import ClosedLoopValidationResult
from backend.models.calibration_result import CalibrationResult
from backend.models.decision_outcome import DecisionOutcome
from backend.services.calibration_applier import CalibrationApplier
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator


class ClosedLoopValidation:
    """Run a closed-loop validation: calibrate on Experience N and evaluate on held-out Experience N+1.

    This service is non-mutating and deterministic. It never applies proposals to production state.
    """

    def __init__(self) -> None:
        self.evaluator = PredictionErrorEvaluator()
        self.calibrator = DigitalTwinCalibrator()
        self.applier = CalibrationApplier()

    def run(
        self,
        experience_n: DecisionOutcome,
        experience_n_plus_1: DecisionOutcome,
        current_parameters: Optional[CalibrationParameters] = None,
        learning_rate: float = 0.1,
        bounds: Optional[Dict[str, Any]] = None,
    ) -> ClosedLoopValidationResult:
        # Evaluate initial prediction (Experience N)
        error_result_n = self.evaluator.evaluate(experience_n)
        initial_error = error_result_n.prediction_error

        # Produce calibration proposal from Experience N
        calibration_result: CalibrationResult = self.calibrator.calibrate(
            error_result_n, current_parameters=current_parameters, learning_rate=learning_rate, bounds=bounds
        )

        # Apply proposal non-destructively
        base_params = deepcopy(current_parameters) if current_parameters is not None else CalibrationParameters()
        calibrated_params = self.applier.apply(base_params, calibration_result)

        # Baseline evaluation on held-out Experience N+1
        baseline_error_res = self.evaluator.evaluate(experience_n_plus_1)
        baseline_future_error = baseline_error_res.prediction_error
        baseline_future_prediction = deepcopy(experience_n_plus_1.predicted_state or {})
        future_selected_action = experience_n_plus_1.selected_action
        future_actual_state = deepcopy(experience_n_plus_1.actual_state or {})

        # Simulate calibrated prediction for N+1 by applying calibrated expected_state_bias
        calibrated_pred = {}
        original_predicted = deepcopy(experience_n_plus_1.predicted_state or {})
        for key, val in original_predicted.items():
            bias = calibrated_params.expected_state_bias.get(key, 0.0)
            calibrated_pred[key] = float(val) + float(bias)
        # also include bias-only keys
        for key, bias in calibrated_params.expected_state_bias.items():
            if key not in calibrated_pred:
                calibrated_pred[key] = float(bias)

        # Build DecisionOutcome copy for calibrated future prediction
        serial = experience_n_plus_1.model_dump()
        serial["predicted_state"] = calibrated_pred
        calibrated_decision = DecisionOutcome(**serial)

        calibrated_error_res = self.evaluator.evaluate(calibrated_decision)
        calibrated_future_error = calibrated_error_res.prediction_error

        # Compute improvement
        error_improvement = None
        helped = False
        if baseline_future_error is not None and calibrated_future_error is not None:
            error_improvement = round(float(baseline_future_error) - float(calibrated_future_error), 4)
            helped = error_improvement > 0.0

        return ClosedLoopValidationResult(
            initial_prediction=deepcopy(experience_n.predicted_state or {}),
            initial_actual=deepcopy(experience_n.actual_state or {}),
            initial_error=initial_error,
            calibration_proposal=calibration_result,
            calibrated_parameters=calibrated_params,
            future_selected_action=future_selected_action,
            future_actual_state=future_actual_state,
            baseline_future_prediction=baseline_future_prediction,
            baseline_future_error=baseline_future_error,
            calibrated_future_prediction=calibrated_pred,
            calibrated_future_error=calibrated_future_error,
            error_improvement=error_improvement,
            helped=helped,
            metadata={"learning_rate": learning_rate, "bounds": bounds or {}},
        )
