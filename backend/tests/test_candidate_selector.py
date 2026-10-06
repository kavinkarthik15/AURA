from __future__ import annotations

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.planning.candidate_selector import CandidateSelector
from backend.planning.planning_context import PlanningContext
from backend.planning.trajectory_tree_evaluator import TrajectoryTreeEvaluator


def make_snapshot(snapshot_id: str = "root") -> SimulatedState:
    return SimulatedState(
        skills={"python": 0},
        knowledge={},
        projects={},
        goals={},
        learning={},
        source_state_id=None,
        simulation_id="sim-candidate",
        step=0,
        parent_snapshot_id=None,
        snapshot_id=snapshot_id,
        metadata={},
    )


def test_candidate_selector_ranks_candidates_and_selects_best_action() -> None:
    selector = CandidateSelector(enabled=True, trajectory_evaluator=TrajectoryTreeEvaluator(), fallback_action="fallback")
    snapshot = make_snapshot()
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal)

    result = selector.select_action(snapshot, ["study", "review"], context=context, goal_state=goal)

    assert result is not None
    assert result.action in {"study", "review"}
    assert result.score >= 0.0
    assert result.probability >= 0.0
    assert result.risk >= 0.0
    assert result.uncertainty >= 0.0


def test_candidate_selector_returns_fallback_for_empty_candidates() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    snapshot = make_snapshot()

    result = selector.select_action(snapshot, [], context=None, goal_state=None)

    assert result is not None
    assert result.action == "fallback"
    assert result.selection_reason == "empty_candidates"


def test_candidate_selector_respects_opt_in_and_preserves_snapshot() -> None:
    selector = CandidateSelector(enabled=False, fallback_action="fallback")
    snapshot = make_snapshot()

    result = selector.select_action(snapshot, ["study"], context=None, goal_state=None)

    assert result is None

    assert snapshot.snapshot_id == "root"
    assert snapshot.skills["python"] == 0
