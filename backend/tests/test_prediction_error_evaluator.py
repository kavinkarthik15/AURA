from datetime import datetime

import pytest

from backend.models.decision_outcome import DecisionOutcome
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator


def test_evaluate_prediction_error_with_actual_state() -> None:
    decision_outcome = DecisionOutcome(
        decision_id="dec-201",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 60, "dsa": 20},
        predicted_trajectory_score=0.8,
        predicted_probability=0.7,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 58, "dsa": 18},
    )

    evaluator = PredictionErrorEvaluator()
    result = evaluator.evaluate(decision_outcome)

    assert result.decision_id == "dec-201"
    assert result.actual_available is True
    assert result.state_errors == {"dsa": 2.0, "python": 2.0}
    assert result.prediction_error == 2.0
    assert result.mean_absolute_error == 2.0
    assert result.max_absolute_error == 2.0
    assert result.state_dimensions == 2


def test_evaluate_prediction_error_without_actual_state() -> None:
    decision_outcome = DecisionOutcome(
        decision_id="dec-202",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="review",
        predicted_state={"python": 60, "dsa": 20},
        predicted_trajectory_score=0.6,
        predicted_probability=0.5,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
    )

    evaluator = PredictionErrorEvaluator()
    result = evaluator.evaluate(decision_outcome)

    assert result.actual_available is False
    assert result.prediction_error is None
    assert result.mean_absolute_error is None
    assert result.max_absolute_error is None
    assert result.state_errors == {}
    assert result.state_dimensions == 0


def test_prediction_error_preserves_decision_outcome_immutability() -> None:
    actual_state = {"python": 57}
    predicted_state = {"python": 60}
    decision_outcome = DecisionOutcome(
        decision_id="dec-203",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state=predicted_state,
        predicted_trajectory_score=0.75,
        predicted_probability=0.6,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state=actual_state,
    )

    evaluator = PredictionErrorEvaluator()
    result = evaluator.evaluate(decision_outcome)

    assert decision_outcome.predicted_state == {"python": 60}
    assert decision_outcome.actual_state == {"python": 57}
    assert result.state_errors == {"python": 3.0}


def test_evaluate_prediction_error_with_missing_predicted_dimensions() -> None:
    decision_outcome = DecisionOutcome(
        decision_id="dec-204",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 60},
        predicted_trajectory_score=0.7,
        predicted_probability=0.65,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 60, "dsa": 20},
    )

    evaluator = PredictionErrorEvaluator()
    result = evaluator.evaluate(decision_outcome)

    assert result.state_errors == {"dsa": 20.0, "python": 0.0}
    assert result.prediction_error == 10.0
    assert result.state_dimensions == 2


def test_prediction_error_uses_sorted_state_keys_for_determinism() -> None:
    decision_outcome = DecisionOutcome(
        decision_id="dec-205",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"dsa": 20, "python": 60},
        predicted_trajectory_score=0.7,
        predicted_probability=0.65,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        actual_state={"python": 58, "dsa": 18},
    )

    evaluator = PredictionErrorEvaluator()
    result = evaluator.evaluate(decision_outcome)

    assert list(result.state_errors.keys()) == ["dsa", "python"]


def test_invalid_actual_state_type_raises() -> None:
    with pytest.raises(ValueError):
        DecisionOutcome(
            decision_id="dec-206",
            timestamp=datetime.utcnow(),
            initial_snapshot={"python": 50},
            selected_action="practice",
            predicted_state={"python": 60},
            predicted_trajectory_score=0.7,
            predicted_probability=0.65,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
            actual_state="invalid",
        )
