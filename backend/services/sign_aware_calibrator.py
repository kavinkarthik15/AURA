"""Sign-aware calibrator using signed error information.

This variant of DigitalTwinCalibrator uses signed error information (actual - predicted)
to apply directional calibration: negative errors decrease expected_state_bias,
positive errors increase it.

Everything else (learning rate, bounds, other parameters) remains identical to the
existing calibrator.

Formula: delta = learning_rate * (actual - predicted)
- Underestimate (predicted < actual): positive error → increase bias
- Overestimate (predicted > actual): negative error → decrease bias
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Any, Optional

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.prediction_error_result import PredictionErrorResult
from backend.models.calibration_result import CalibrationResult


class SignAwareCalibratorVariant:
    """Produce calibration proposals using directional error information.

    Differs from DigitalTwinCalibrator only in how expected_state_bias is updated:
    uses signed_state_errors (actual - predicted) rather than absolute errors,
    allowing for both positive and negative corrections.

    Formula: delta = learning_rate * signed_error
    - This applies positive delta when we underestimate (signed_error > 0)
    - This applies negative delta when we overestimate (signed_error < 0)
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

        # State bias adjustments: use SIGNED error information to determine direction
        # Signature: delta = learning_rate * signed_error
        # - If signed_error > 0 (underestimate): delta > 0 (increase bias, reduce underestimation)
        # - If signed_error < 0 (overestimate): delta < 0 (decrease bias, reduce overestimation)
        state_updates: Dict[str, float] = {}
        for key, signed_err in error_result.signed_state_errors.items():
            # Apply directional correction
            delta = learning_rate * float(signed_err)
            max_delta = float(bounds.get("state_adjustment_max", 5.0))
            applied = max(-max_delta, min(max_delta, delta))
            updated.expected_state_bias[key] = updated.expected_state_bias.get(key, 0.0) + applied
            state_updates[key] = round(applied, 4)

        updates_applied["state_bias"] = state_updates

        # Uncertainty: increase proportionally to absolute error (bounded)
        # Use absolute error here since we want uncertainty to increase with any error magnitude
        abs_error = float(error_result.state_errors.get(list(error_result.state_errors.keys())[0], 0.0)) if error_result.state_errors else 0.0
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
        new_conf = max(0.0, min(1.0, updated.confidence + conf_delta))
        applied_conf = round(new_conf - updated.confidence, 4)
        updated.confidence = round(new_conf, 4)
        updates_applied["confidence"] = applied_conf

        return CalibrationResult(
            updated_parameters=updated,
            error_before=error_before,
            error_after_estimate=None,
            updates_applied=updates_applied,
            confidence=updated.confidence,
            metadata={"type": "sign_aware", "direction_aware": True},
        )
