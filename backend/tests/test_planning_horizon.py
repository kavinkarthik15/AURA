import copy

import pytest

from backend.models.multi_step_decision import MultiStepDecisionResult
from backend.models.planning_horizon import PlanningHorizon


def test_valid_planning_horizon_construction() -> None:
    horizon = PlanningHorizon(
        horizon_depth=3,
        candidate_actions=["study", "review"],
        discount_factor=0.9,
        max_branches=5,
        use_digital_twin=True,
    )

    assert horizon.horizon_depth == 3
    assert horizon.candidate_actions == ["study", "review"]
    assert horizon.discount_factor == 0.9
    assert horizon.max_branches == 5
    assert horizon.use_digital_twin is True


def test_planning_horizon_default_values() -> None:
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["study"])

    assert horizon.discount_factor == 1.0
    assert horizon.max_branches is None
    assert horizon.use_digital_twin is False


def test_invalid_horizon_depth_raises() -> None:
    with pytest.raises(ValueError):
        PlanningHorizon(horizon_depth=0, candidate_actions=["study"])


def test_invalid_discount_factor_raises() -> None:
    with pytest.raises(ValueError):
        PlanningHorizon(horizon_depth=2, candidate_actions=["study"], discount_factor=0.0)


def test_invalid_max_branches_raises() -> None:
    with pytest.raises(ValueError):
        PlanningHorizon(horizon_depth=2, candidate_actions=["study"], max_branches=0)


def test_empty_candidate_actions_raises() -> None:
    with pytest.raises(ValueError):
        PlanningHorizon(horizon_depth=2, candidate_actions=[])


def test_single_action_sequence_result() -> None:
    result = MultiStepDecisionResult(
        best_sequence=["study"],
        first_action="study",
        trajectory_score=1.0,
        cumulative_probability=0.8,
        risk=0.1,
        uncertainty=0.05,
        expected_goal_progress=0.6,
        top_k_sequences=[["study"]],
        metadata={"source": "test"},
    )

    assert result.best_sequence == ["study"]
    assert result.first_action == "study"
    assert result.top_k_sequences == [["study"]]
    assert result.metadata == {"source": "test"}


def test_multi_action_sequence_result() -> None:
    result = MultiStepDecisionResult(
        best_sequence=["study", "practice", "review"],
        first_action="study",
        trajectory_score=2.5,
        cumulative_probability=0.8 * 0.7 * 0.9,
        risk=0.2,
        uncertainty=0.1,
        expected_goal_progress=0.9,
        top_k_sequences=[["study", "practice", "review"], ["review", "practice"]],
        metadata={"depth": 3},
    )

    assert result.best_sequence == ["study", "practice", "review"]
    assert result.first_action == "study"
    assert result.cumulative_probability == pytest.approx(0.504, rel=1e-3)
    assert result.top_k_sequences[0] == ["study", "practice", "review"]
    assert result.metadata["depth"] == 3


def test_first_action_extraction_matches_best_sequence() -> None:
    result = MultiStepDecisionResult(
        best_sequence=["plan", "execute"],
        first_action="plan",
        trajectory_score=1.0,
        cumulative_probability=0.5,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.4,
        top_k_sequences=[["plan", "execute"]],
        metadata={},
    )

    assert result.first_action == result.best_sequence[0]


def test_probability_preservation_for_sequence() -> None:
    probability = 0.8 * 0.7 * 0.9
    result = MultiStepDecisionResult(
        best_sequence=["a", "b", "c"],
        first_action="a",
        trajectory_score=1.2,
        cumulative_probability=probability,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.5,
        top_k_sequences=[["a", "b", "c"]],
        metadata={},
    )

    assert result.cumulative_probability == pytest.approx(0.504, rel=1e-3)


def test_top_k_sequence_preservation() -> None:
    sequences = [["a", "b"], ["b", "c"]]
    result = MultiStepDecisionResult(
        best_sequence=["a", "b"],
        first_action="a",
        trajectory_score=1.0,
        cumulative_probability=0.5,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.4,
        top_k_sequences=sequences,
        metadata={},
    )

    assert result.top_k_sequences == sequences
    assert result.top_k_sequences is not sequences


def test_metadata_preservation() -> None:
    meta = {"source": "test"}
    result = MultiStepDecisionResult(
        best_sequence=["a"],
        first_action="a",
        trajectory_score=1.0,
        cumulative_probability=0.5,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.4,
        top_k_sequences=[["a"]],
        metadata=meta,
    )

    assert result.metadata == meta
    assert result.metadata is not meta


def test_no_mutation_of_supplied_actions_and_state() -> None:
    actions = ["a", "b"]
    horizon_data = {"horizon_depth": 2, "candidate_actions": actions, "discount_factor": 0.9}
    original_actions = copy.deepcopy(actions)

    horizon = PlanningHorizon(**horizon_data)

    assert actions == original_actions
    assert horizon.candidate_actions == original_actions
    assert horizon.candidate_actions is not actions


def test_deterministic_serialization_and_equality() -> None:
    horizon = PlanningHorizon(horizon_depth=2, candidate_actions=["a"], discount_factor=0.95)
    same_horizon = PlanningHorizon(horizon_depth=2, candidate_actions=["a"], discount_factor=0.95)

    assert horizon.model_dump() == same_horizon.model_dump()
    assert horizon == same_horizon

    result = MultiStepDecisionResult(
        best_sequence=["a"],
        first_action="a",
        trajectory_score=1.0,
        cumulative_probability=0.5,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.4,
        top_k_sequences=[["a"]],
        metadata={"source": "test"},
    )
    same_result = MultiStepDecisionResult(**result.model_dump())

    assert result == same_result
