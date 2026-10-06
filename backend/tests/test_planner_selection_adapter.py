from __future__ import annotations

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.models.simulation_trajectory_tree import SimulationTrajectoryNode, SimulationTrajectoryTree
from backend.planning.planning_context import PlanningContext
from backend.planning.planner_selection_adapter import PlannerSelectionAdapter
from backend.planning.trajectory_evaluator import TrajectoryEvaluator
from backend.planning.trajectory_tree_evaluator import TrajectorySelectionResult, TrajectoryTreeEvaluationEntry, TrajectoryTreeEvaluator


def make_snapshot(skills: dict[str, float], snapshot_id: str) -> SimulatedState:
    return SimulatedState(
        skills=dict(skills),
        knowledge={},
        projects={},
        goals={},
        learning={},
        source_state_id=None,
        simulation_id="sim-adapter",
        step=0,
        parent_snapshot_id=None,
        snapshot_id=snapshot_id,
        metadata={},
    )


def build_selection_result() -> TrajectorySelectionResult:
    root = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 0}, "root"), probability_from_parent=1.0)
    first = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 5}, "leaf-a"), action_from_parent="study", probability_from_parent=0.8)
    second = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 100}, "leaf-b"), action_from_parent="review", probability_from_parent=0.2)
    root.children = [first, second]
    first.parent = root
    second.parent = root
    tree = SimulationTrajectoryTree(root=root)
    evaluator = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator(), top_k=2)
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal)
    return evaluator.select(tree, goal, context=context)


def test_adapter_returns_first_action_from_best_trajectory() -> None:
    selection = build_selection_result()
    adapter = PlannerSelectionAdapter(enabled=True, fallback_action="fallback")

    adapted = adapter.adapt(selection, context=PlanningContext(current_state={"python": 0}, goal_state=GoalState(goal="Improve Python", target_skills={"python": 80})))

    assert adapted["action"] == "review"
    assert adapted["metadata"]["trajectory_score"] >= 0.0
    assert adapted["metadata"]["branch_probability"] == 0.2


def test_adapter_preserves_metadata_and_context() -> None:
    selection = build_selection_result()
    context = PlanningContext(current_state={"python": 0}, goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}))
    adapter = PlannerSelectionAdapter(enabled=True, fallback_action="fallback", fallback_metadata={"source": "unit-test"})

    adapted = adapter.adapt(selection, context=context)

    assert adapted["metadata"]["source"] == "unit-test"
    assert adapted["planning_context"] is context
    assert adapted["selection_result"] is selection


def test_adapter_returns_safe_fallback_when_no_selection_exists() -> None:
    adapter = PlannerSelectionAdapter(enabled=True, fallback_action="fallback")
    adapted = adapter.adapt(None, context=PlanningContext(current_state={"python": 0}, goal_state=GoalState(goal="Improve Python", target_skills={"python": 80})))

    assert adapted["action"] == "fallback"
    assert adapted["metadata"]["trajectory_score"] == 0.0
    assert adapted["metadata"]["branch_probability"] == 0.0


def test_disabled_adapter_leaves_behavior_unchanged() -> None:
    selection = build_selection_result()
    adapter = PlannerSelectionAdapter(enabled=False, fallback_action="fallback")

    adapted = adapter.adapt(selection, context=None)

    assert adapted["enabled"] is False
    assert adapted["action"] == "fallback"
    assert adapted["selection_result"] is None


def test_adapter_does_not_mutate_tree() -> None:
    selection = build_selection_result()
    adapter = PlannerSelectionAdapter(enabled=True)
    tree_snapshot = [child.snapshot.snapshot_id for child in selection.best_trajectory.node.parent.children] if selection.best_trajectory.node.parent is not None else []

    adapter.adapt(selection)

    if selection.best_trajectory.node.parent is not None:
        assert [child.snapshot.snapshot_id for child in selection.best_trajectory.node.parent.children] == tree_snapshot
    else:
        assert True
