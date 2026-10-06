from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.models.simulation_trajectory_tree import SimulationTrajectoryNode, SimulationTrajectoryTree
from backend.planning.planning_context import PlanningContext
from backend.planning.trajectory_evaluator import TrajectoryEvaluation, TrajectoryEvaluator
from backend.planning.trajectory_tree_evaluator import TrajectoryTreeEvaluator


class RecordingTrajectoryEvaluator:
    def __init__(self) -> None:
        self.contexts: List[PlanningContext | None] = []

    def evaluate(self, transitions, goal_state, context=None) -> TrajectoryEvaluation:
        self.contexts.append(context)
        total = 0.0
        for transition in transitions:
            if transition.possible_states:
                state = transition.possible_states[0]
                total += float(state.get("python", 0))
        return TrajectoryEvaluation(
            trajectory_score=total,
            expected_value=total,
            cumulative_utility=total,
            cumulative_risk=0.0,
            cumulative_cost=0.0,
            goal_progress=total,
            confidence=1.0,
            horizon=len(transitions),
            discount_factor=1.0,
        )


def make_snapshot(skills: dict[str, Any], snapshot_id: str) -> SimulatedState:
    return SimulatedState(
        skills=dict(skills),
        knowledge={},
        projects={},
        goals={},
        learning={},
        source_state_id=None,
        simulation_id="sim-tree",
        step=0,
        parent_snapshot_id=None,
        snapshot_id=snapshot_id,
        metadata={},
    )


def test_tree_evaluator_scores_each_leaf_and_keeps_probability_separate() -> None:
    root = make_snapshot({"python": 0}, "root")
    high_probability_low_quality = SimulationTrajectoryNode(
        snapshot=make_snapshot({"python": 1}, "leaf-a"),
        action_from_parent="study",
        diff_from_parent={},
        probability_from_parent=0.8,
    )
    low_probability_high_quality = SimulationTrajectoryNode(
        snapshot=make_snapshot({"python": 100}, "leaf-b"),
        action_from_parent="study",
        diff_from_parent={},
        probability_from_parent=0.2,
    )
    high_probability_low_quality.parent = SimulationTrajectoryNode(snapshot=root, action_from_parent=None, diff_from_parent=None, probability_from_parent=1.0)
    low_probability_high_quality.parent = high_probability_low_quality.parent

    # create a two-leaf tree with the same parent
    parent = SimulationTrajectoryNode(snapshot=root, action_from_parent=None, diff_from_parent=None, probability_from_parent=1.0)
    parent.children = [high_probability_low_quality, low_probability_high_quality]
    high_probability_low_quality.parent = parent
    low_probability_high_quality.parent = parent

    tree = SimulationTrajectoryTree(root=parent)
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal, risk_tolerance=0.2, uncertainty_tolerance=0.2)

    result = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator()).evaluate(tree, goal, context=context)

    assert len(result.evaluations) == 2
    assert result.best_trajectory is not None
    assert result.best_trajectory.node.snapshot.snapshot_id == "leaf-b"
    assert result.best_trajectory.branch_probability == 0.2
    assert result.best_trajectory.trajectory_evaluation.trajectory_score > 0.0
    assert result.best_trajectory.trajectory_evaluation.trajectory_score > result.evaluations[0].trajectory_evaluation.trajectory_score


def test_tree_evaluator_reuses_the_same_context_for_all_leaves() -> None:
    root = make_snapshot({"python": 0}, "root-ctx")
    left = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 10}, "left"), action_from_parent="study", diff_from_parent={}, probability_from_parent=0.5)
    right = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 20}, "right"), action_from_parent="study", diff_from_parent={}, probability_from_parent=0.5)
    parent = SimulationTrajectoryNode(snapshot=root, action_from_parent=None, diff_from_parent=None, probability_from_parent=1.0)
    parent.children = [left, right]
    left.parent = parent
    right.parent = parent
    tree = SimulationTrajectoryTree(root=parent)

    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal)
    recorder = RecordingTrajectoryEvaluator()

    TrajectoryTreeEvaluator(trajectory_evaluator=recorder).evaluate(tree, goal, context=context)

    assert recorder.contexts == [context, context]


def test_tree_evaluator_top_k_selection_is_deterministic_for_identical_inputs() -> None:
    root = make_snapshot({"python": 0}, "root-rank")
    left = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 10}, "leaf-z"), action_from_parent="study", diff_from_parent={}, probability_from_parent=0.5)
    right = SimulationTrajectoryNode(snapshot=make_snapshot({"python": 10}, "leaf-a"), action_from_parent="study", diff_from_parent={}, probability_from_parent=0.5)
    parent = SimulationTrajectoryNode(snapshot=root, action_from_parent=None, diff_from_parent=None, probability_from_parent=1.0)
    parent.children = [left, right]
    left.parent = parent
    right.parent = parent
    tree = SimulationTrajectoryTree(root=parent)

    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    context = PlanningContext(current_state={"python": 0}, goal_state=goal)

    evaluator = TrajectoryTreeEvaluator(trajectory_evaluator=TrajectoryEvaluator(), top_k=2)
    result = evaluator.evaluate(tree, goal, context=context)

    assert [item.node.snapshot.snapshot_id for item in result.ranked_trajectories] == ["leaf-a", "leaf-z"]
