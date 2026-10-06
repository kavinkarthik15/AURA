from __future__ import annotations

from backend.models.calibration_parameters import CalibrationParameters
from backend.services.batch_closed_loop_evaluator import BatchClosedLoopEvaluator
from backend.services.experiment_metrics_calculator import ExperimentMetricsCalculator


def test_experiment_metrics_calculator_derives_metrics_without_mutation():
    evaluator = BatchClosedLoopEvaluator()
    from backend.models.decision_outcome import DecisionOutcome
    from datetime import datetime as dt

    n = DecisionOutcome(
        decision_id="m1",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 10},
        selected_action="auto",
        predicted_state={"x": 10},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 12},
    )
    n1 = DecisionOutcome(
        decision_id="m2",
        timestamp=dt.utcnow(),
        initial_snapshot={"x": 20},
        selected_action="auto",
        predicted_state={"x": 20},
        predicted_trajectory_score=0.1,
        predicted_probability=0.1,
        predicted_risk=0.0,
        predicted_uncertainty=0.0,
        actual_state={"x": 21},
    )

    initial_params = CalibrationParameters()
    batch_result = evaluator.run([n, n1], current_parameters=initial_params, learning_rate=0.1)
    original_dump = batch_result.model_dump()

    metrics = ExperimentMetricsCalculator.calculate(batch_result)

    assert metrics.baseline_mae == batch_result.mean_baseline_error
    assert metrics.calibrated_mae == batch_result.mean_calibrated_error
    assert metrics.absolute_improvement == round(metrics.baseline_mae - metrics.calibrated_mae, 4)
    assert metrics.improvement_percent == (0.0 if metrics.baseline_mae == 0.0 else round((metrics.absolute_improvement / metrics.baseline_mae) * 100.0, 4))
    assert metrics.calibration_count == len(batch_result.steps)
    assert metrics.evaluation_count == len(batch_result.steps)
    assert metrics.acceptance_rate == round(batch_result.successful_calibrations / len(batch_result.steps), 4)
    assert metrics.rejection_rate == round(batch_result.rejected_calibrations / len(batch_result.steps), 4)
    assert metrics.parameter_drift == ExperimentMetricsCalculator._calibration_parameter_distance(
        CalibrationParameters(), batch_result.final_learning_parameters
    )

    assert batch_result.model_dump() == original_dump


def test_experiment_metrics_calculator_returns_zero_for_empty_batch():
    from backend.models.batch_closed_loop_result import BatchClosedLoopResult
    from backend.models.calibration_parameters import CalibrationParameters

    batch_result = BatchClosedLoopResult(final_learning_parameters=CalibrationParameters())
    metrics = ExperimentMetricsCalculator.calculate(batch_result)

    assert metrics.baseline_mae == 0.0
    assert metrics.calibrated_mae == 0.0
    assert metrics.absolute_improvement == 0.0
    assert metrics.improvement_percent == 0.0
    assert metrics.acceptance_rate == 0.0
    assert metrics.rejection_rate == 0.0
    assert metrics.calibration_count == 0
    assert metrics.evaluation_count == 0
    assert metrics.parameter_drift == 0.0
    assert metrics.error_by_action == {}
    assert metrics.error_by_dimension == {}


def test_experiment_metrics_calculator_groups_errors_by_action_and_dimension():
    from backend.models.batch_closed_loop_result import BatchClosedLoopResult, BatchStepResult
    from backend.models.closed_loop_validation_result import ClosedLoopValidationResult
    from backend.models.calibration_result import CalibrationResult

    step_one = BatchStepResult(
        index=0,
        validation=ClosedLoopValidationResult(
            initial_prediction={"x": 0.0},
            initial_actual={"x": 0.0},
            initial_error=0.0,
            calibration_proposal=CalibrationResult(updated_parameters=CalibrationParameters()),
            calibrated_parameters=CalibrationParameters(),
            future_selected_action="auto",
            future_actual_state={"x": 10.0, "y": 5.0},
            baseline_future_prediction={"x": 9.0, "y": 5.0},
            baseline_future_error=1.0,
            calibrated_future_prediction={"x": 10.5, "y": 4.8},
            calibrated_future_error=1.0,
            error_improvement=0.0,
            helped=False,
        ),
    )

    step_two = BatchStepResult(
        index=1,
        validation=ClosedLoopValidationResult(
            initial_prediction={"x": 0.0},
            initial_actual={"x": 0.0},
            initial_error=0.0,
            calibration_proposal=CalibrationResult(updated_parameters=CalibrationParameters()),
            calibrated_parameters=CalibrationParameters(),
            future_selected_action="manual",
            future_actual_state={"x": 8.0, "y": 3.0},
            baseline_future_prediction={"x": 7.5, "y": 2.5},
            baseline_future_error=1.0,
            calibrated_future_prediction={"x": 8.2, "y": 2.7},
            calibrated_future_error=0.9,
            error_improvement=0.1,
            helped=True,
        ),
    )

    step_three = BatchStepResult(
        index=2,
        validation=ClosedLoopValidationResult(
            initial_prediction={"x": 0.0},
            initial_actual={"x": 0.0},
            initial_error=0.0,
            calibration_proposal=CalibrationResult(updated_parameters=CalibrationParameters()),
            calibrated_parameters=CalibrationParameters(),
            future_selected_action="auto",
            future_actual_state=None,
            baseline_future_prediction={"x": 9.0},
            baseline_future_error=1.0,
            calibrated_future_prediction={"x": 8.8},
            calibrated_future_error=1.1,
            error_improvement=-0.1,
            helped=False,
        ),
    )

    batch_result = BatchClosedLoopResult(
        steps=[step_one, step_two, step_three],
        mean_baseline_error=1.0,
        mean_calibrated_error=1.0,
        mean_improvement=0.0,
        successful_calibrations=1,
        rejected_calibrations=2,
        final_learning_parameters=CalibrationParameters(),
    )

    metrics = ExperimentMetricsCalculator.calculate(batch_result)

    assert metrics.error_by_action == {"auto": 1.05, "manual": 0.9}
    assert metrics.error_by_dimension == {
        "x": 0.35,
        "y": 0.25,
    }
    assert metrics.error_by_action.keys() == {"auto", "manual"}
    assert metrics.error_by_dimension.keys() == {"x", "y"}
