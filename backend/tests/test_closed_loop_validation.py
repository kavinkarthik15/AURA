from __future__ import annotations

from datetime import datetime

from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.models.goal_state import GoalState
from backend.services.closed_loop_validation import ClosedLoopValidation
from backend.services.batch_closed_loop_evaluator import BatchClosedLoopEvaluator
from backend.services.calibration_applier import CalibrationApplier
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.experiment_metrics_calculator import ExperimentMetricsCalculator
from backend.services.goal_plan_service import GoalPlanService
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator


def test_closed_loop_validation_improves_on_held_out():
    # Experience N: predicted 50, actual 60 -> large positive error will yield positive bias
    decision_n = DecisionOutcome(
        decision_id="n1",
        timestamp=datetime.utcnow(),
        initial_snapshot={"skill": 50},
        selected_action="practice",
        predicted_state={"skill": 50},
        predicted_trajectory_score=0.5,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 60},
    )

    # Experience N+1: predicted 70, actual 71 -> baseline error 1.0; after applying +1 bias becomes 0.0
    decision_n1 = DecisionOutcome(
        decision_id="n2",
        timestamp=datetime.utcnow(),
        initial_snapshot={"skill": 70},
        selected_action="practice",
        predicted_state={"skill": 70},
        predicted_trajectory_score=0.6,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 71},
    )

    params = CalibrationParameters()
    val = ClosedLoopValidation()
    res = val.run(decision_n, decision_n1, current_parameters=params, learning_rate=0.1)

    assert res.baseline_future_error == 1.0
    assert res.calibrated_future_error == 0.0
    assert res.helped is True


def test_closed_loop_learning_contract_requires_improvement_from_single_experience_pair():
    base_state = {"skill": 50}
    future_state = {"skill": 70}

    decision_n = DecisionOutcome(
        decision_id="n1",
        timestamp=datetime.utcnow(),
        initial_snapshot=base_state,
        selected_action="practice",
        predicted_state=base_state,
        predicted_trajectory_score=0.5,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 60},
    )

    decision_n1 = DecisionOutcome(
        decision_id="n2",
        timestamp=datetime.utcnow(),
        initial_snapshot=future_state,
        selected_action="practice",
        predicted_state=future_state,
        predicted_trajectory_score=0.6,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 71},
    )

    params = CalibrationParameters()
    val = ClosedLoopValidation()
    res = val.run(decision_n, decision_n1, current_parameters=params, learning_rate=0.1)

    assert res.initial_prediction == {"skill": 50}
    assert res.initial_actual == {"skill": 60}
    assert res.calibration_proposal.updated_parameters.expected_state_bias == {"skill": 1.0}
    assert res.calibrated_parameters.expected_state_bias == {"skill": 1.0}
    assert res.baseline_future_prediction == {"skill": 70}
    assert res.calibrated_future_prediction == {"skill": 71.0}
    assert res.baseline_future_error == 1.0
    assert res.calibrated_future_error == 0.0
    assert res.helped is True


def test_closed_loop_validation_is_non_mutating():
    decision_n = DecisionOutcome(
        decision_id="m1",
        timestamp=datetime.utcnow(),
        initial_snapshot={"a": 1},
        selected_action="x",
        predicted_state={"a": 1},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"a": 2},
    )
    decision_n1 = DecisionOutcome(
        decision_id="m2",
        timestamp=datetime.utcnow(),
        initial_snapshot={"a": 2},
        selected_action="x",
        predicted_state={"a": 3},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"a": 3},
    )

    params = CalibrationParameters()
    val = ClosedLoopValidation()
    res = val.run(decision_n, decision_n1, current_parameters=params, learning_rate=0.1)

    # original params remain unchanged
    assert params == CalibrationParameters()


def test_closed_loop_validation_can_reject_worse_calibration():
    # calibrator will add positive bias based on N
    decision_n = DecisionOutcome(
        decision_id="w1",
        timestamp=datetime.utcnow(),
        initial_snapshot={"skill": 50},
        selected_action="practice",
        predicted_state={"skill": 50},
        predicted_trajectory_score=0.5,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 60},
    )

    # N+1 baseline is 1.0 error (70 vs 69 actual). Adding positive bias will make it worse (2.0)
    decision_n1 = DecisionOutcome(
        decision_id="w2",
        timestamp=datetime.utcnow(),
        initial_snapshot={"skill": 70},
        selected_action="practice",
        predicted_state={"skill": 70},
        predicted_trajectory_score=0.6,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"skill": 69},
    )

    val = ClosedLoopValidation()
    res = val.run(decision_n, decision_n1, current_parameters=CalibrationParameters(), learning_rate=0.1)

    assert res.helped is False


def test_full_experience_learning_loop_improves_next_decision_prediction():
    service = GoalPlanService()
    evaluator = PredictionErrorEvaluator()
    calibrator = DigitalTwinCalibrator()
    applier = CalibrationApplier()

    state_n = {"python": 15, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result_n = service.recommend_goal_plan(state_n, goal_state, use_digital_twin=True)
    predicted_state_n = result_n["evaluation"]["simulation"]["predicted_future_state"]
    actual_state_n = {**predicted_state_n, "python": predicted_state_n.get("python", 0) + 2}

    decision_n = DecisionOutcome(
        decision_id="experience_n",
        timestamp=datetime.utcnow(),
        initial_snapshot=state_n,
        selected_action=result_n["recommended_action"],
        predicted_state=predicted_state_n,
        predicted_trajectory_score=result_n["evaluation"]["success_probability"],
        predicted_probability=result_n["evaluation"]["success_probability"],
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state=actual_state_n,
    )

    error_n = evaluator.evaluate(decision_n)
    calibration_result = calibrator.calibrate(error_n, current_parameters=CalibrationParameters(), learning_rate=0.5)
    calibrated_params = applier.apply(CalibrationParameters(), calibration_result)
    assert calibrated_params.expected_state_bias.get("python", 0.0) > 0.0

    state_n1 = {"python": 18, "dsa": 5, "projects": 1}
    baseline_result_n1 = service.recommend_goal_plan(state_n1, goal_state, use_digital_twin=True)
    predicted_state_n1_baseline = baseline_result_n1["evaluation"]["simulation"]["predicted_future_state"]
    expected_bias = float(calibrated_params.expected_state_bias.get("python", 0.0))
    assert expected_bias > 0.0
    num_actions = len(baseline_result_n1["best_plan"]["actions"])
    actual_state_n1 = {
        **predicted_state_n1_baseline,
        "python": predicted_state_n1_baseline.get("python", 0) + int(expected_bias * num_actions),
    }

    baseline_decision_n1 = DecisionOutcome(
        decision_id="experience_n1_baseline",
        timestamp=datetime.utcnow(),
        initial_snapshot=state_n1,
        selected_action=baseline_result_n1["recommended_action"],
        predicted_state=predicted_state_n1_baseline,
        predicted_trajectory_score=baseline_result_n1["evaluation"]["success_probability"],
        predicted_probability=baseline_result_n1["evaluation"]["success_probability"],
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state=actual_state_n1,
    )
    baseline_error_n1 = evaluator.evaluate(baseline_decision_n1).prediction_error

    calibrated_result_n1 = service.recommend_goal_plan(
        state_n1,
        goal_state,
        use_digital_twin=True,
        calibration_parameters=calibrated_params,
    )
    predicted_state_n1_calibrated = calibrated_result_n1["evaluation"]["simulation"]["predicted_future_state"]

    calibrated_decision_n1 = DecisionOutcome(
        decision_id="experience_n1_calibrated",
        timestamp=datetime.utcnow(),
        initial_snapshot=state_n1,
        selected_action=calibrated_result_n1["recommended_action"],
        predicted_state=predicted_state_n1_calibrated,
        predicted_trajectory_score=calibrated_result_n1["evaluation"]["success_probability"],
        predicted_probability=calibrated_result_n1["evaluation"]["success_probability"],
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state=actual_state_n1,
    )
    calibrated_error_n1 = evaluator.evaluate(calibrated_decision_n1).prediction_error

    assert baseline_error_n1 is not None
    assert calibrated_error_n1 is not None
    assert calibrated_error_n1 < baseline_error_n1


def test_closed_loop_learning_pipeline_is_deterministic_and_accumulates_calibration():
    from backend.models.calibration_parameters import CalibrationParameters

    experiences = []
    experiences.append(
        DecisionOutcome(
            decision_id="n",
            timestamp=datetime.utcnow(),
            initial_snapshot={"skill": 50},
            selected_action="practice",
            predicted_state={"skill": 50},
            predicted_trajectory_score=0.5,
            predicted_probability=0.5,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
            actual_state={"skill": 60},
        )
    )
    experiences.append(
        DecisionOutcome(
            decision_id="n1",
            timestamp=datetime.utcnow(),
            initial_snapshot={"skill": 70},
            selected_action="practice",
            predicted_state={"skill": 70},
            predicted_trajectory_score=0.6,
            predicted_probability=0.6,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
            actual_state={"skill": 76},
        )
    )
    experiences.append(
        DecisionOutcome(
            decision_id="n2",
            timestamp=datetime.utcnow(),
            initial_snapshot={"skill": 80},
            selected_action="practice",
            predicted_state={"skill": 80},
            predicted_trajectory_score=0.7,
            predicted_probability=0.7,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
            actual_state={"skill": 90},
        )
    )
    experiences.append(
        DecisionOutcome(
            decision_id="n3",
            timestamp=datetime.utcnow(),
            initial_snapshot={"skill": 100},
            selected_action="practice",
            predicted_state={"skill": 100},
            predicted_trajectory_score=0.8,
            predicted_probability=0.8,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
            actual_state={"skill": 102},
        )
    )

    initial_parameters = CalibrationParameters()
    evaluator = BatchClosedLoopEvaluator()

    batch_result_one = evaluator.run(
        experiences,
        current_parameters=initial_parameters,
        learning_rate=0.1,
        apply_accepted=True,
    )
    batch_result_two = evaluator.run(
        experiences,
        current_parameters=initial_parameters,
        learning_rate=0.1,
        apply_accepted=True,
    )

    assert batch_result_one == batch_result_two
    assert initial_parameters == CalibrationParameters()
    assert batch_result_one.steps[0].validation.baseline_future_error == 6.0
    assert batch_result_one.steps[0].validation.calibrated_future_error == 5.0
    assert batch_result_one.steps[0].validation.calibrated_future_error < batch_result_one.steps[0].validation.baseline_future_error
    assert batch_result_one.steps[1].validation.baseline_future_error == 2.0
    assert batch_result_one.steps[1].validation.calibrated_future_error == 0.0
    assert batch_result_one.steps[1].validation.calibrated_future_error < batch_result_one.steps[1].validation.baseline_future_error

    first_step_bias = batch_result_one.steps[0].validation.calibrated_parameters.expected_state_bias["skill"]
    second_step_bias = batch_result_one.steps[1].validation.calibrated_parameters.expected_state_bias["skill"]
    final_bias = batch_result_one.final_learning_parameters.expected_state_bias["skill"]

    assert first_step_bias == 1.0
    assert second_step_bias == 2.0
    assert final_bias == 2.0
    assert final_bias > first_step_bias

    metrics = ExperimentMetricsCalculator.calculate(batch_result_one)
    assert metrics.baseline_mae == 4.0
    assert metrics.calibrated_mae == 2.5
    assert metrics.absolute_improvement == 1.5
    assert metrics.improvement_percent == 37.5
    assert len(metrics.parameter_drift_progression) == len(batch_result_one.steps)
    assert metrics.parameter_drift_progression[0] > 0.0
    assert metrics.parameter_drift_progression[1] > metrics.parameter_drift_progression[0]
    assert metrics.calibration_count == len(batch_result_one.steps)
    assert metrics.evaluation_count == len(batch_result_one.steps)


def test_closed_loop_validation_is_deterministic():
    decision_n = DecisionOutcome(
        decision_id="d1",
        timestamp=datetime.utcnow(),
        initial_snapshot={"x": 10},
        selected_action="a",
        predicted_state={"x": 10},
        predicted_trajectory_score=0.5,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"x": 12},
    )
    decision_n1 = DecisionOutcome(
        decision_id="d2",
        timestamp=datetime.utcnow(),
        initial_snapshot={"x": 20},
        selected_action="a",
        predicted_state={"x": 20},
        predicted_trajectory_score=0.6,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"x": 22},
    )

    val = ClosedLoopValidation()
    r1 = val.run(decision_n, decision_n1, current_parameters=CalibrationParameters(), learning_rate=0.1)
    r2 = val.run(decision_n, decision_n1, current_parameters=CalibrationParameters(), learning_rate=0.1)

    assert r1 == r2
