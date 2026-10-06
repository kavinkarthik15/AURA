from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.models.simulation_trajectory_tree import SimulationTrajectoryNode, SimulationTrajectoryTree
from backend.planning.planning_context import PlanningContext
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.trajectory_evaluator import TrajectoryEvaluation, TrajectoryEvaluator


@dataclass
class TrajectorySelectionResult:
    best_trajectory: Optional["TrajectoryTreeEvaluationEntry"]
    top_k: int
    selection_reason: str
    trajectory_score: float
    branch_probability: float
    risk: float
    uncertainty: float
    context: Optional[PlanningContext] = None
    ranked_trajectories: List["TrajectoryTreeEvaluationEntry"] = field(default_factory=list)


@dataclass
class TrajectoryTreeEvaluationEntry:
    node: SimulationTrajectoryNode
    branch_probability: float
    path_snapshot_ids: List[str]
    trajectory_evaluation: TrajectoryEvaluation
    path: List[ProbabilisticTransition] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryTreeEvaluation:
    evaluations: List[TrajectoryTreeEvaluationEntry]
    best_trajectory: Optional[TrajectoryTreeEvaluationEntry] = None
    ranked_trajectories: List[TrajectoryTreeEvaluationEntry] = field(default_factory=list)


class TrajectoryTreeEvaluator:
    def __init__(self, trajectory_evaluator: Optional[Any] = None, top_k: int = 3) -> None:
        self.trajectory_evaluator = trajectory_evaluator or TrajectoryEvaluator()
        self.top_k = max(1, int(top_k))

    def evaluate(
        self,
        tree: SimulationTrajectoryTree,
        goal_state: GoalState,
        context: Optional[PlanningContext] = None,
    ) -> TrajectoryTreeEvaluation:
        leaves = tree.leaves() if tree is not None else []
        evaluations: List[TrajectoryTreeEvaluationEntry] = []

        for leaf in leaves:
            path_nodes = self._path_to_node(tree.root, leaf)
            transitions = self._build_transitions(path_nodes)
            trajectory_evaluation = self.trajectory_evaluator.evaluate(transitions, goal_state, context=context)
            entry = TrajectoryTreeEvaluationEntry(
                node=leaf,
                branch_probability=float(leaf.cumulative_probability()),
                path_snapshot_ids=[node.snapshot.snapshot_id for node in path_nodes if getattr(node.snapshot, "snapshot_id", None) is not None],
                trajectory_evaluation=trajectory_evaluation,
                path=transitions,
                explanation={
                    "branch_probability": round(float(leaf.cumulative_probability()), 6),
                    "path_length": len(path_nodes),
                    "trajectory_score": round(trajectory_evaluation.trajectory_score, 4),
                    "goal_progress": round(trajectory_evaluation.goal_progress, 4),
                    "risk": round(trajectory_evaluation.cumulative_risk, 4),
                    "uncertainty": round(trajectory_evaluation.cumulative_uncertainty, 4),
                },
            )
            evaluations.append(entry)

        ranked = self._rank_evaluations(evaluations)
        return TrajectoryTreeEvaluation(
            evaluations=evaluations,
            best_trajectory=ranked[0] if ranked else None,
            ranked_trajectories=ranked[: self.top_k],
        )

    def select(
        self,
        tree: SimulationTrajectoryTree,
        goal_state: GoalState,
        context: Optional[PlanningContext] = None,
    ) -> TrajectorySelectionResult:
        evaluation = self.evaluate(tree, goal_state, context=context)
        best = evaluation.best_trajectory
        ranked = evaluation.ranked_trajectories or []
        if best is None:
            return TrajectorySelectionResult(
                best_trajectory=None,
                top_k=self.top_k,
                selection_reason="no_trajectories",
                trajectory_score=0.0,
                branch_probability=0.0,
                risk=0.0,
                uncertainty=0.0,
                context=context,
                ranked_trajectories=ranked,
            )

        return TrajectorySelectionResult(
            best_trajectory=best,
            top_k=self.top_k,
            selection_reason="trajectory_score",
            trajectory_score=float(best.trajectory_evaluation.trajectory_score),
            branch_probability=float(best.branch_probability),
            risk=float(best.trajectory_evaluation.cumulative_risk),
            uncertainty=float(best.trajectory_evaluation.cumulative_uncertainty),
            context=context,
            ranked_trajectories=ranked,
        )

    def _path_to_node(self, root: SimulationTrajectoryNode, leaf: SimulationTrajectoryNode) -> List[SimulationTrajectoryNode]:
        path: List[SimulationTrajectoryNode] = []
        current: Optional[SimulationTrajectoryNode] = leaf
        while current is not None:
            path.append(current)
            current = current.parent
        path.reverse()
        if path and path[0] is not root and root is not None:
            path = [root, *path] if path[0] is not root else path
        return path

    def _build_transitions(self, path_nodes: List[SimulationTrajectoryNode]) -> List[ProbabilisticTransition]:
        transitions: List[ProbabilisticTransition] = []
        for parent, child in zip(path_nodes[:-1], path_nodes[1:]):
            transitions.append(
                ProbabilisticTransition(
                    current_state=self._snapshot_state(parent.snapshot),
                    action=child.action_from_parent,
                    possible_states=[self._snapshot_state(child.snapshot)],
                    probabilities=[1.0],
                    confidence=float(child.snapshot.metadata.get("confidence", 0.0) if isinstance(child.snapshot.metadata, dict) else 0.0),
                    evidence=[str(child.action_from_parent or "")],
                )
            )
        return transitions

    def _snapshot_state(self, snapshot: SimulatedState) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        merged.update(snapshot.skills)
        merged.update(snapshot.knowledge)
        merged.update(snapshot.projects)
        merged.update(snapshot.goals)
        merged.update(snapshot.learning)
        return merged

    def _rank_evaluations(self, evaluations: List[TrajectoryTreeEvaluationEntry]) -> List[TrajectoryTreeEvaluationEntry]:
        def sort_key(item: TrajectoryTreeEvaluationEntry) -> tuple[float, float, str]:
            score = float(item.trajectory_evaluation.trajectory_score)
            branch_probability = float(item.branch_probability)
            snapshot_id = str(item.node.snapshot.snapshot_id or "")
            return (-score, -branch_probability, snapshot_id)

        return sorted(evaluations, key=sort_key)
