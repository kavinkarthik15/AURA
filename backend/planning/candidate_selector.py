from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.models.simulated_state import SimulatedState
from backend.models.simulation_trajectory_tree import SimulationTrajectoryTree
from backend.planning.planning_context import PlanningContext
from backend.planning.trajectory_tree_evaluator import TrajectorySelectionResult, TrajectoryTreeEvaluator
from backend.services.simulation_engine import SimulationEngine


@dataclass
class CandidateActionResult:
    action: Optional[str]
    score: float
    probability: float
    risk: float
    uncertainty: float
    trajectory: Optional[SimulationTrajectoryTree] = None
    selection_reason: str = "fallback"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateSelector:
    enabled: bool = False
    trajectory_evaluator: Optional[TrajectoryTreeEvaluator] = None
    simulation_engine: Optional[SimulationEngine] = None
    fallback_action: Optional[str] = None

    def __post_init__(self) -> None:
        if self.trajectory_evaluator is None:
            self.trajectory_evaluator = TrajectoryTreeEvaluator()
        if self.simulation_engine is None:
            from backend.services.simulation_engine import simulation_engine
            self.simulation_engine = simulation_engine

    def select_action(
        self,
        snapshot: SimulatedState,
        candidate_actions: List[str],
        context: Optional[PlanningContext] = None,
        goal_state: Optional[GoalState] = None,
    ) -> Optional[CandidateActionResult]:
        if not self.enabled:
            return None
        if not candidate_actions:
            return CandidateActionResult(action=self.fallback_action, score=0.0, probability=0.0, risk=0.0, uncertainty=0.0, selection_reason="empty_candidates")

        results: List[CandidateActionResult] = []
        for action in candidate_actions:
            if not isinstance(action, str) or not action.strip():
                continue
            tree = self._simulate_candidate(snapshot, action, context=context)
            if tree is None:
                continue
            selection_result = self.trajectory_evaluator.select(tree, goal_state or GoalState(goal="candidate_selection", target_skills={}), context=context)
            if selection_result.best_trajectory is None:
                continue
            results.append(
                CandidateActionResult(
                    action=action,
                    score=float(selection_result.trajectory_score),
                    probability=float(selection_result.branch_probability),
                    risk=float(selection_result.risk),
                    uncertainty=float(selection_result.uncertainty),
                    trajectory=tree,
                    selection_reason=selection_result.selection_reason,
                    metadata={
                        "top_k": selection_result.top_k,
                        "planning_context": context,
                    },
                )
            )

        if not results:
            return CandidateActionResult(action=self.fallback_action, score=0.0, probability=0.0, risk=0.0, uncertainty=0.0, selection_reason="no_valid_candidates")

        ranked_results = sorted(results, key=lambda item: (-item.score, -item.probability, str(item.action or "")))
        return ranked_results[0]

    def _simulate_candidate(self, snapshot: SimulatedState, action: str, context: Optional[PlanningContext] = None) -> Optional[SimulationTrajectoryTree]:
        if self.simulation_engine is None:
            return None

        tree = self.simulation_engine.simulate_branching_trajectory(snapshot, [action], context=None, max_branches=None)
        return tree

    def select_action_with_fallback(self, snapshot: SimulatedState, candidate_actions: List[str], context: Optional[PlanningContext] = None, goal_state: Optional[GoalState] = None) -> CandidateActionResult:
        result = self.select_action(snapshot, candidate_actions, context=context, goal_state=goal_state)
        if result is not None:
            return result
        return CandidateActionResult(action=self.fallback_action, score=0.0, probability=0.0, risk=0.0, uncertainty=0.0, selection_reason="disabled")
