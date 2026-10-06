import copy
from datetime import datetime

import pytest

from backend.models.decision_outcome import DecisionOutcome


def test_valid_decision_outcome_prediction_record() -> None:
    snapshot = {"python": 50, "dsa": 20}
    metadata = {"source": "digital_twin"}
    outcome = DecisionOutcome(
        decision_id="dec-123",
        timestamp=datetime.utcnow().isoformat(),
        initial_snapshot=snapshot,
        selected_action="complete_project",
        predicted_state={"python": 60, "dsa": 22},
        predicted_trajectory_score=0.75,
        predicted_probability=0.8,
        predicted_risk=0.2,
        predicted_uncertainty=0.1,
        metadata=metadata,
    )

    assert outcome.decision_id == "dec-123"
    assert outcome.selected_action == "complete_project"
    assert outcome.predicted_state == {"python": 60, "dsa": 22}
    assert outcome.actual_state is None
    assert outcome.actual_outcome is None
    assert outcome.prediction_error is None
    assert outcome.metadata == metadata
    assert outcome.metadata is not metadata


def test_valid_record_before_execution() -> None:
    outcome = DecisionOutcome(
        decision_id="dec-124",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="review_notes",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.5,
        predicted_probability=0.6,
        predicted_risk=0.05,
        predicted_uncertainty=0.02,
        metadata={},
    )

    assert outcome.actual_state is None
    assert outcome.actual_outcome is None
    assert outcome.prediction_error is None


def test_actual_state_can_be_attached_later() -> None:
    outcome = DecisionOutcome(
        decision_id="dec-125",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.6,
        predicted_probability=0.7,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
    )

    outcome.actual_state = {"python": 53}
    outcome.actual_outcome = "partial_success"
    outcome.prediction_error = {"error_type": "magnitude"}

    assert outcome.actual_state == {"python": 53}
    assert outcome.actual_outcome == "partial_success"
    assert outcome.prediction_error == {"error_type": "magnitude"}


def test_prediction_fields_remain_unchanged_after_actual_outcome() -> None:
    outcome = DecisionOutcome(
        decision_id="dec-126",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="review",
        predicted_state={"python": 52},
        predicted_trajectory_score=0.55,
        predicted_probability=0.65,
        predicted_risk=0.05,
        predicted_uncertainty=0.02,
    )

    predicted_state_before = copy.deepcopy(outcome.predicted_state)
    predicted_score_before = outcome.predicted_trajectory_score

    outcome.actual_state = {"python": 51}
    outcome.actual_outcome = "close"

    assert outcome.predicted_state == predicted_state_before
    assert outcome.predicted_trajectory_score == predicted_score_before


def test_prediction_error_not_generated_automatically() -> None:
    outcome = DecisionOutcome(
        decision_id="dec-127",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.7,
        predicted_probability=0.75,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
    )

    assert outcome.prediction_error is None


def test_empty_selected_action_rejected() -> None:
    with pytest.raises(ValueError):
        DecisionOutcome(
            decision_id="dec-128",
            timestamp=datetime.utcnow(),
            initial_snapshot={"python": 50},
            selected_action="",
            predicted_state={"python": 55},
            predicted_trajectory_score=0.7,
            predicted_probability=0.75,
            predicted_risk=0.1,
            predicted_uncertainty=0.05,
        )


def test_snapshot_input_is_not_mutated() -> None:
    snapshot = {"python": 50}
    outcome = DecisionOutcome(
        decision_id="dec-129",
        timestamp=datetime.utcnow(),
        initial_snapshot=snapshot,
        selected_action="practice",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.7,
        predicted_probability=0.75,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
    )

    snapshot["python"] = 100
    assert outcome.initial_snapshot == {"python": 50}


def test_metadata_input_is_not_mutated() -> None:
    metadata = {"source": "digital_twin"}
    outcome = DecisionOutcome(
        decision_id="dec-130",
        timestamp=datetime.utcnow(),
        initial_snapshot={"python": 50},
        selected_action="practice",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.7,
        predicted_probability=0.75,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        metadata=metadata,
    )

    metadata["source"] = "modified"
    assert outcome.metadata == {"source": "digital_twin"}


def test_deterministic_serialization_and_representation() -> None:
    snapshot = {"python": 50}
    metadata = {"source": "digital_twin"}
    outcome = DecisionOutcome(
        decision_id="dec-131",
        timestamp=datetime.utcnow(),
        initial_snapshot=snapshot,
        selected_action="practice",
        predicted_state={"python": 55},
        predicted_trajectory_score=0.7,
        predicted_probability=0.75,
        predicted_risk=0.1,
        predicted_uncertainty=0.05,
        metadata=metadata,
    )

    serial = outcome.model_dump()
    restored = DecisionOutcome(**serial)

    assert restored == outcome
    assert restored.model_dump() == serial
