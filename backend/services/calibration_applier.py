from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.calibration_result import CalibrationResult


class CalibrationApplier:
    """Apply a `CalibrationResult` to a `CalibrationParameters` non-destructively and deterministically."""

    def apply(self, current_parameters: CalibrationParameters, calibration_result: CalibrationResult) -> CalibrationParameters:
        params = deepcopy(current_parameters) if current_parameters is not None else CalibrationParameters()
        updated = deepcopy(params)

        updates = calibration_result.updates_applied or {}

        # Apply state_bias updates
        state_bias_updates: Dict[str, float] = updates.get("state_bias", {})
        for key, delta in state_bias_updates.items():
            updated.expected_state_bias[key] = updated.expected_state_bias.get(key, 0.0) + float(delta)

        # Apply transition probability bias
        prob_delta = updates.get("transition_probability_bias")
        if prob_delta is not None:
            updated.transition_probability_bias = round(updated.transition_probability_bias + float(prob_delta), 4)

        # Apply risk bias
        risk_delta = updates.get("risk_bias")
        if risk_delta is not None:
            updated.risk_bias = round(updated.risk_bias + float(risk_delta), 4)

        # Apply uncertainty increment
        unc_delta = updates.get("uncertainty")
        if unc_delta is not None:
            updated.uncertainty = round(min(1.0, max(0.0, updated.uncertainty + float(unc_delta))), 4)

        # Apply confidence delta
        conf_delta = updates.get("confidence")
        if conf_delta is not None:
            updated.confidence = round(min(1.0, max(0.0, updated.confidence + float(conf_delta))), 4)

        return updated
