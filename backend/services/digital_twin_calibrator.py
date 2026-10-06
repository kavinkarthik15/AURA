from __future__ import annotations

from copy import deepcopy
from typing import Dict, Any, Optional

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.prediction_error_result import PredictionErrorResult
from backend.models.calibration_result import CalibrationResult


class DigitalTwinCalibrator:
    """Produce a deterministic, bounded calibration proposal from observed prediction errors.

    The calibrator is non-mutating: it returns a new `CalibrationParameters` instance and a
    `CalibrationResult` describing the proposed updates. It accepts an optional `learning_rate`
    and `bounds` that control maximum adjustments.
    """

    def calibrate(
        self,
        error_result: PredictionErrorResult,
        current_parameters: CalibrationParameters | None = None,
        learning_rate: float = 0.1,
        bounds: Dict[str, float] | None = None,
    ) -> CalibrationResult:
        params = deepcopy(current_parameters) if current_parameters is not None else CalibrationParameters()
        bounds = bounds or {
            "state_adjustment_max": 5.0,
            "probability_bias_max": 0.2,
            "risk_bias_max": 0.2,
            "uncertainty_increment_max": 0.3,
            "confidence_increment_max": 0.1,
        }

        # Preserve originals (non-mutating)
        updated = deepcopy(params)
        updates_applied: Dict[str, Any] = {}

        error_before = float(error_result.prediction_error) if error_result.prediction_error is not None else None

        if not error_result.actual_available or error_before is None:
            # Nothing to calibrate; return unchanged parameters with zero confidence
            return CalibrationResult(
                updated_parameters=updated,
                error_before=error_before,
                error_after_estimate=None,
                updates_applied={},
                confidence=0.0,
                metadata={"reason": "no_actuals"},
            )

        # If there is zero prediction error, avoid applying any calibration.
        if error_before == 0.0:
            return CalibrationResult(
                updated_parameters=updated,
                error_before=error_before,
                error_after_estimate=0.0,
                updates_applied={},
                confidence=0.0,
                metadata={"reason": "zero_error"},
            )

        # Aggregate directional info is not available from PredictionErrorResult alone.
        # We'll base adjustments on absolute errors but remain conservative about state shifts.

        # State bias adjustments: scale per-dimension by learning_rate, capped by bounds
        state_updates: Dict[str, float] = {}
        for key, abs_err in error_result.state_errors.items():
            # proposed change proportional to error and learning rate
            delta = learning_rate * float(abs_err)
            max_delta = float(bounds.get("state_adjustment_max", 5.0))
            applied = max(-max_delta, min(max_delta, delta))
            # since direction unknown, we apply a symmetric bias increase to reduce overconfidence
            updated.expected_state_bias[key] = updated.expected_state_bias.get(key, 0.0) + applied
            state_updates[key] = round(applied, 4)

        updates_applied["state_bias"] = state_updates

        # Uncertainty: increase proportionally to error (bounded)
        unc_inc = min(bounds.get("uncertainty_increment_max", 0.3), learning_rate * (error_before / (1.0 + error_before)))
        new_unc = min(1.0, updated.uncertainty + unc_inc)
        applied_unc = round(new_unc - updated.uncertainty, 4)
        updated.uncertainty = round(new_unc, 4)
        updates_applied["uncertainty"] = applied_unc

        # Risk: increase with error, bounded
        risk_inc = min(bounds.get("risk_bias_max", 0.2), learning_rate * error_before)
        updated.risk_bias = round(updated.risk_bias + risk_inc, 4)
        updates_applied["risk_bias"] = round(risk_inc, 4)

        # Transition probability bias: decrease confidence in probability proportional to error
        prob_delta = -min(bounds.get("probability_bias_max", 0.2), learning_rate * error_before)
        updated.transition_probability_bias = round(updated.transition_probability_bias + prob_delta, 4)
        updates_applied["transition_probability_bias"] = round(prob_delta, 4)

        # Confidence: if error is small, slightly increase confidence, otherwise decrease a bit
        if error_before < 0.1:
            conf_delta = min(bounds.get("confidence_increment_max", 0.1), learning_rate * (0.1 - error_before))
        else:
            conf_delta = -min(bounds.get("confidence_increment_max", 0.1), learning_rate * error_before)
        updated.confidence = round(max(0.0, min(1.0, updated.confidence + conf_delta)), 4)
        updates_applied["confidence"] = round(conf_delta, 4)

        # Estimate error after applying updates: simple heuristic that calibration reduces error by learning_rate factor
        error_after_estimate = round(max(0.0, error_before * (1.0 - learning_rate)), 4)

        # Confidence in calibration proposal: inversely proportional to remaining error fraction
        confidence = round(min(1.0, max(0.0, 1.0 - error_after_estimate / (error_before + 1e-9))), 4)

        return CalibrationResult(
            updated_parameters=updated,
            error_before=error_before,
            error_after_estimate=error_after_estimate,
            updates_applied=updates_applied,
            confidence=confidence,
            metadata={"learning_rate": learning_rate, "bounds": bounds},
        )
