from __future__ import annotations

from datetime import datetime

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.batch_closed_loop_evaluator import BatchClosedLoopEvaluator


def _make_decision(pred, actual, id_suffix):
    return DecisionOutcome(
        decision_id=f"e{id_suffix}",
        timestamp=datetime.utcnow(),
        initial_snapshot={"x": pred},
        selected_action="act",
        predicted_state={"x": pred},
        predicted_trajectory_score=0.5,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"x": actual},
    )


def test_batch_closed_loop_basic_improvement():
    # Build experiences: pair1 calibrate on (10->12) then evaluate (20->21)
    e1 = _make_decision(10, 12, "1")
    e2 = _make_decision(20, 21, "2")

    # pair2 calibrate on (5->8) then evaluate (30->33)
    e3 = _make_decision(5, 8, "3")
    e4 = _make_decision(30, 33, "4")

    evaluator = BatchClosedLoopEvaluator()
    res = evaluator.run([e1, e2, e3, e4], current_parameters=CalibrationParameters(), learning_rate=0.1)

    assert res.metadata["pairs_processed"] == 2
    assert res.successful_calibrations + res.failed_calibrations == 2
    # mean improvement should be present (could be positive or negative depending on toy data)
    assert res.mean_baseline_error is not None


def test_batch_closed_loop_sequential_learning_across_multiple_experiences():
    e1 = _make_decision(50, 60, "1")
    e2 = _make_decision(70, 71, "2")
    e3 = _make_decision(20, 22, "3")
    e4 = _make_decision(30, 31, "4")

    evaluator = BatchClosedLoopEvaluator()
    res = evaluator.run([e1, e2, e3, e4], current_parameters=CalibrationParameters(), learning_rate=0.1, apply_accepted=True)

    assert res.successful_calibrations == 2
    assert res.rejected_calibrations == 0
    assert res.mean_baseline_error == 1.0
    assert res.mean_calibrated_error == 0.1
    assert res.mean_improvement == 0.9
    assert res.final_learning_parameters.expected_state_bias == {"x": 1.2}
    assert res.final_learning_parameters.transition_probability_bias == -0.4
    assert res.final_learning_parameters.risk_bias == 0.4


def test_batch_closed_loop_is_deterministic_and_non_mutating():
    e1 = _make_decision(10, 12, "a")
    e2 = _make_decision(20, 21, "b")

    params = CalibrationParameters()
    evaluator = BatchClosedLoopEvaluator()
    r1 = evaluator.run([e1, e2], current_parameters=params, learning_rate=0.1)
    r2 = evaluator.run([e1, e2], current_parameters=params, learning_rate=0.1)

    assert r1 == r2
    assert params == CalibrationParameters()
