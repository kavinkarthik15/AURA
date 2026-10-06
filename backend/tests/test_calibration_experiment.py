from datetime import datetime

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.calibration_experiment import CalibrationExperiment


def test_calibration_application_is_non_mutating() -> None:
    params = CalibrationParameters()
    decision = DecisionOutcome(
        decision_id="c1",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 60},
        predicted_trajectory_score=0.7,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 62},
    )

    params_copy = CalibrationParameters(**params.model_dump())
    decision_copy = DecisionOutcome(**decision.model_dump())

    exp = CalibrationExperiment()
    result = exp.run(decision, current_parameters=params, learning_rate=0.2)

    assert params == params_copy
    assert decision == decision_copy


def test_calibration_improves_when_bias_reduces_error() -> None:
    params = CalibrationParameters()
    # predicted lower than actual -> bias increase should reduce error
    decision = DecisionOutcome(
        decision_id="c2",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 50},
        predicted_trajectory_score=0.7,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 60},
    )

    exp = CalibrationExperiment()
    result = exp.run(decision, current_parameters=params, learning_rate=0.5)

    assert result.baseline_error is not None
    assert result.calibrated_error is not None
    assert result.improvement == result.baseline_error - result.calibrated_error
    assert result.improved is True


def test_zero_error_introduces_no_change():
    params = CalibrationParameters()
    decision = DecisionOutcome(
        decision_id="c3",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 60},
        predicted_trajectory_score=0.7,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 60},
    )

    exp = CalibrationExperiment()
    res = exp.run(decision, current_parameters=params, learning_rate=0.5)

    assert res.baseline_error == 0.0
    assert res.calibrated_error == 0.0
    assert res.calibrated_parameters == params


def test_deterministic_experiment_results():
    params = CalibrationParameters()
    decision = DecisionOutcome(
        decision_id="c4",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"a": 10, "b": 5},
        predicted_trajectory_score=0.7,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"a": 12, "b": 7},
    )

    exp = CalibrationExperiment()
    r1 = exp.run(decision, current_parameters=params, learning_rate=0.2)
    r2 = exp.run(decision, current_parameters=params, learning_rate=0.2)

    assert r1 == r2
