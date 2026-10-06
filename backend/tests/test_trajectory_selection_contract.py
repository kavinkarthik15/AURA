from __future__ import annotations

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.models.simulation_trajectory_tree import SimulationTrajectoryNode, SimulationTrajectoryTree
from backend.planning.planning_context import PlanningContext
from backend.planning.trajectory_evaluator import TrajectoryEvaluator
from backend.planning.trajectory_tree_evaluator import TrajectoryTreeEvaluator


def make_snapshot(skills: dict[str, float], snapshot_id: str) -> SimulatedState:
    return SimulatedState(
        skills=dict(skills),
        knowledge={},
        projects={},
        goals={},
        learning={},
        source_state_id=None,
        simulation_id="sim-selection",
        step=0,
        parent_snapshot_id=None,
        snapshot_id=snapshot_id,
        metadata={},
    )


def build_tree() -> SimulationTrajectoryTree:
    root = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 0}, "root"), probability_from_parent=1.0)
    high_prob_low_quality = SimulationTrajectoryNode(
        snapshot=make_snapshot({"python": 5}, "leaf-a"),
        action_from_parent="study",
        probability_from_parent=0.8,
    )
    low_prob_high_quality = SimulationTrajectoryNode(
        snapshot=make_snapshot({"python": 100}, "leaf-b"),
        action_from_parent="study",
        probability_from_parent=0.2,
    )
    root.children = [high_prob_low_quality, low_prob_high_quality]
    high_prob_low_quality.parent = root
    low_prob_high_quality.parent = root
    return SimulationTrajectoryTree(root=root)


def test_selection_result_exposes_best_trajectory_and_metrics() -> None:
    tree = build_tree()
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal, risk_tolerance=0.2, uncertainty_tolerance=0.2)

    evaluator = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator(), top_k=2)
    selection = evaluator.select(tree, goal, context=context)

    assert selection.best_trajectory is not None
    assert selection.best_trajectory.node.snapshot.snapshot_id == "leaf-b"
    assert selection.top_k == 2
    assert selection.selection_reason == "trajectory_score"
    assert selection.trajectory_score > 0.0
    assert selection.branch_probability == 0.2
    assert selection.risk >= 0.0
    assert selection.uncertainty >= 0.0
    assert selection.context is context


def test_selection_does_not_mutate_tree() -> None:
    tree = build_tree()
    original_leaves = [leaf.snapshot.snapshot_id for leaf in tree.leaves()]

    evaluator = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator())
    evaluator.select(tree, GoalState(goal="Improve Python", target_skills={"python": 80}))

    assert [leaf.snapshot.snapshot_id for leaf in tree.leaves()] == original_leaves
    assert tree.root.children[0].snapshot.snapshot_id == "leaf-a"
    assert tree.root.children[1].snapshot.snapshot_id == "leaf-b"


def test_selection_top_k_remains_deterministic_for_identical_inputs() -> None:
    tree = build_tree()
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal)

    evaluator = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator(), top_k=2)
    first = evaluator.select(tree, goal, context=context)
    second = evaluator.select(tree, goal, context=context)

    assert [item.node.snapshot.snapshot_id for item in first.ranked_trajectories] == [
        item.node.snapshot.snapshot_id for item in second.ranked_trajectories
    ]
