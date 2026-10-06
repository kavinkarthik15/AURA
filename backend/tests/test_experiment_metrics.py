from __future__ import annotations

import json

from backend.models.experiment_metrics import ExperimentMetrics


def test_experiment_metrics_validation_and_serialization():
    metrics = ExperimentMetrics(
        baseline_mae=2.0,
        calibrated_mae=1.5,
        absolute_improvement=0.5,
        improvement_percent=25.0,
        acceptance_rate=0.75,
        rejection_rate=0.25,
        parameter_drift=0.2,
        error_by_dimension={"x": 1.0, "y": 0.5},
        error_by_action={"auto": 0.8, "manual": 0.2},
        rolling_improvement=[0.1, 0.2, 0.15],
        calibration_count=3,
        evaluation_count=3,
    )

    assert metrics.baseline_mae == 2.0
    assert metrics.calibrated_mae == 1.5
    assert metrics.improvement_percent == 25.0
    assert metrics.acceptance_rate == 0.75
    assert metrics.rejection_rate == 0.25
    assert metrics.error_by_dimension["x"] == 1.0
    assert metrics.error_by_action["auto"] == 0.8
    assert metrics.rolling_improvement == [0.1, 0.2, 0.15]

    serialized = metrics.model_dump()
    loaded = ExperimentMetrics(**serialized)

    assert loaded == metrics


def test_experiment_metrics_validation_rejects_invalid_values():
    from pydantic import ValidationError

    try:
        ExperimentMetrics(
            baseline_mae=-1.0,
            calibrated_mae=0.5,
            absolute_improvement=0.5,
            improvement_percent=25.0,
            acceptance_rate=1.0,
            rejection_rate=0.0,
            parameter_drift=0.1,
            error_by_dimension={"x": 1.0},
            error_by_action={"auto": 0.1},
            rolling_improvement=[0.1],
            calibration_count=1,
            evaluation_count=1,
        )
        assert False, "Expected validation error for negative baseline_mae"
    except ValidationError as exc:
        assert "greater than or equal to 0" in str(exc)

    try:
        ExperimentMetrics(
            baseline_mae=1.0,
            calibrated_mae=0.5,
            absolute_improvement=0.5,
            improvement_percent=25.0,
            acceptance_rate=1.5,
            rejection_rate=-0.1,
            parameter_drift=0.1,
            error_by_dimension={"x": 1.0},
            error_by_action={"auto": 0.1},
            rolling_improvement=[0.1],
            calibration_count=1,
            evaluation_count=1,
        )
        assert False, "Expected validation error for invalid acceptance_rate or rejection_rate"
    except ValidationError as exc:
        assert "greater than or equal to 0" in str(exc) or "less than or equal to 1" in str(exc)

    try:
        ExperimentMetrics(
            baseline_mae=1.0,
            calibrated_mae=0.5,
            absolute_improvement=0.5,
            improvement_percent=25.0,
            acceptance_rate=0.5,
            rejection_rate=0.5,
            parameter_drift=0.1,
            error_by_dimension={"x": -1.0},
            error_by_action={"auto": 0.1},
            rolling_improvement=[0.1],
            calibration_count=1,
            evaluation_count=1,
        )
        assert False, "Expected validation error for negative error_by_dimension"
    except ValidationError as exc:
        assert "error values must be non-negative" in str(exc)

    try:
        ExperimentMetrics(
            baseline_mae=1.0,
            calibrated_mae=0.5,
            absolute_improvement=0.5,
            improvement_percent=25.0,
            acceptance_rate=0.5,
            rejection_rate=0.5,
            parameter_drift=0.1,
            error_by_dimension={"x": 1.0},
            error_by_action={"auto": 0.1},
            rolling_improvement=[0.1],
            calibration_count=1,
            evaluation_count=2,
        )
        assert False, "Expected validation error for mismatched evaluation_count and rolling_improvement length"
    except ValidationError as exc:
        assert "evaluation_count must equal the length of rolling_improvement" in str(exc)
