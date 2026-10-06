from datetime import datetime

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.models.prediction_error_result import PredictionErrorResult
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator


def make_error_result(decision_id: str, state_errors: dict, prediction_error: float):
    return PredictionErrorResult(
        decision_id=decision_id,
        prediction_error=prediction_error,
        state_errors=state_errors,
        mean_absolute_error=prediction_error,
        max_absolute_error=max(state_errors.values()) if state_errors else None,
        state_dimensions=len(state_errors),
        actual_available=bool(state_errors),
    )


def test_zero_error_no_update():
    params = CalibrationParameters()
    err = make_error_result("d1", {}, 0.0)
    calibrator = DigitalTwinCalibrator()
    res = calibrator.calibrate(err, current_parameters=params, learning_rate=0.5)

    assert res.error_before == 0.0
    assert res.updates_applied == {}
    assert res.updated_parameters == params
    assert res.confidence == 0.0


def test_small_error_small_adjustment():
    params = CalibrationParameters()
    err = make_error_result("d2", {"python": 0.5}, 0.5)
    calibrator = DigitalTwinCalibrator()
    res = calibrator.calibrate(err, current_parameters=params, learning_rate=0.1)

    assert res.error_before == 0.5
    assert res.updated_parameters.uncertainty > params.uncertainty
    assert res.updated_parameters.risk_bias >= params.risk_bias
    assert res.updated_parameters.confidence <= 1.0


def test_large_error_larger_adjustment():
    params = CalibrationParameters()
    err = make_error_result("d3", {"python": 10.0}, 10.0)
    calibrator = DigitalTwinCalibrator()
    res = calibrator.calibrate(err, current_parameters=params, learning_rate=0.2)

    assert res.updated_parameters.expected_state_bias["python"] > 0.0
    assert res.updated_parameters.risk_bias > params.risk_bias
    assert res.updated_parameters.transition_probability_bias < params.transition_probability_bias


def test_updates_respect_bounds():
    params = CalibrationParameters()
    err = make_error_result("d4", {"python": 100.0}, 100.0)
    calibrator = DigitalTwinCalibrator()
    bounds = {"state_adjustment_max": 1.0, "probability_bias_max": 0.01, "risk_bias_max": 0.01, "uncertainty_increment_max": 0.05, "confidence_increment_max": 0.02}
    res = calibrator.calibrate(err, current_parameters=params, learning_rate=0.5, bounds=bounds)

    assert res.updates_applied["state_bias"]["python"] <= bounds["state_adjustment_max"]
    assert abs(res.updates_applied["transition_probability_bias"]) <= bounds["probability_bias_max"]
    assert res.updates_applied["risk_bias"] <= bounds["risk_bias_max"]


def test_learning_rate_scales_update():
    params = CalibrationParameters()
    err = make_error_result("d5", {"python": 5.0}, 5.0)
    calibrator = DigitalTwinCalibrator()
    res1 = calibrator.calibrate(err, current_parameters=params, learning_rate=0.1)
    res2 = calibrator.calibrate(err, current_parameters=params, learning_rate=0.5)

    assert res2.updates_applied["state_bias"]["python"] > res1.updates_applied["state_bias"]["python"]


def test_original_errors_and_params_unchanged():
    params = CalibrationParameters()
    err = make_error_result("d6", {"python": 3.0}, 3.0)
    params_copy = CalibrationParameters(**params.model_dump())

    calibrator = DigitalTwinCalibrator()
    _ = calibrator.calibrate(err, current_parameters=params, learning_rate=0.2)

    assert params == params_copy


def test_missing_error_no_calibration():
    params = CalibrationParameters()
    err = make_error_result("d7", {}, None)
    calibrator = DigitalTwinCalibrator()
    res = calibrator.calibrate(err, current_parameters=params)

    assert res.updated_parameters == params
    assert res.confidence == 0.0


def test_deterministic_same_inputs_same_outputs():
    params = CalibrationParameters()
    err = make_error_result("d8", {"a": 2.0, "b": 1.0}, 1.5)
    calibrator = DigitalTwinCalibrator()
    res1 = calibrator.calibrate(err, current_parameters=params, learning_rate=0.2)
    res2 = calibrator.calibrate(err, current_parameters=params, learning_rate=0.2)

    assert res1 == res2
