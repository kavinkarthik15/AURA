from copy import deepcopy

import pytest

from backend.models.goal_state import GoalState
from backend.models.multi_step_decision import MultiStepDecisionResult
from backend.models.planning_horizon import PlanningHorizon
from backend.services.multi_step_decision_engine import MultiStepDecisionEngine
from backend.services.simulation_engine import SimulationEngine
from backend.planning.planning_context import PlanningContext


def make_root_snapshot() -> object:
    engine = SimulationEngine()
    return engine.make_snapshot({"python": 10, "dsa": 5, "projects": 1}, simulation_id="root", step=0, snapshot_id="root")


def test_single_step_sequence_evaluates() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert isinstance(result, MultiStepDecisionResult)
    assert result.best_sequence == ["Complete Python Project"]
    assert result.first_action == "Complete Python Project"
    assert result.cumulative_probability == 1.0


def test_multi_step_sequence_evaluates_and_preserves_probability() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=2, candidate_actions=["Complete Python Project", "Review"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert result.best_sequence[0] == result.first_action
    assert result.cumulative_probability == 1.0
    assert len(result.top_k_sequences) == engine.top_k


def test_horizon_depth_enforced() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=2, candidate_actions=["Complete Python Project"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert len(result.best_sequence) == 2


def test_discount_factor_changes_score() -> None:
    root = make_root_snapshot()
    horizon1 = PlanningHorizon(horizon_depth=2, candidate_actions=["Complete Python Project", "Review"], discount_factor=1.0)
    horizon2 = PlanningHorizon(horizon_depth=2, candidate_actions=["Complete Python Project", "Review"], discount_factor=0.5)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result1 = engine.decide(root, horizon1, goal, context)
    result2 = engine.decide(root, horizon2, goal, context)

    assert result1.trajectory_score != result2.trajectory_score


def test_top_k_ordering_is_deterministic() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project", "Review", "Study"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine(top_k=2)
    result = engine.decide(root, horizon, goal, context)

    assert len(result.top_k_sequences) == 2
    assert result.top_k_sequences[0] != result.top_k_sequences[1]


def test_risk_and_uncertainty_are_reported() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert result.risk >= 0.0
    assert result.uncertainty >= 0.0
    assert result.expected_goal_progress >= 0.0


def test_deterministic_fallback_when_branching_fails() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project"], discount_factor=1.0, use_digital_twin=True)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    engine.simulation_engine = type("BrokenEngine", (), {"simulate_branching_trajectory": lambda *args, **kwargs: (_ for _ in ()).throw(Exception("boom")), "simulate_sequence": engine.simulation_engine.simulate_sequence})()

    result = engine.decide(root, horizon, goal, context)

    assert result.metadata["evaluation_mode"] == "deterministic" or result.best_sequence


def test_digital_twin_branching_respects_max_branches() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project", "Review"], discount_factor=1.0, max_branches=1, use_digital_twin=True)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert isinstance(result, MultiStepDecisionResult)
    assert result.cumulative_probability <= 1.0


def test_empty_candidate_actions_raise() -> None:
    with pytest.raises(ValueError):
        PlanningHorizon(horizon_depth=1, candidate_actions=[])


def test_original_state_is_not_mutated() -> None:
    root = make_root_snapshot()
    original = deepcopy(root)
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project"], discount_factor=1.0)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    engine.decide(root, horizon, goal, context)

    assert root.skills == original.skills
    assert root.metadata == original.metadata


def test_multi_step_decision_result_equality() -> None:
    result = MultiStepDecisionResult(
        best_sequence=["Complete Python Project"],
        first_action="Complete Python Project",
        trajectory_score=1.0,
        cumulative_probability=1.0,
        risk=0.1,
        uncertainty=0.1,
        expected_goal_progress=0.5,
        top_k_sequences=[["Complete Python Project"]],
        metadata={"source": "test"},
    )

    clone = MultiStepDecisionResult(**result.model_dump())
    assert result == clone


def test_decision_result_metadata_includes_evaluation_mode() -> None:
    root = make_root_snapshot()
    horizon = PlanningHorizon(horizon_depth=1, candidate_actions=["Complete Python Project"], discount_factor=1.0, use_digital_twin=True)
    goal = GoalState(goal="Python Growth", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 10, "dsa": 5}, goal_state=goal)

    engine = MultiStepDecisionEngine()
    result = engine.decide(root, horizon, goal, context)

    assert "evaluation_mode" in result.metadata
    assert result.metadata["evaluation_mode"] in {"deterministic", "branching"}
