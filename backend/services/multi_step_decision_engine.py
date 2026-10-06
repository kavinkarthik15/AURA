from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from backend.models.goal_state import GoalState
from backend.models.multi_step_decision import MultiStepDecisionResult
from backend.models.planning_horizon import PlanningHorizon
from backend.models.simulated_state import SimulatedState
from backend.planning.planning_context import PlanningContext
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.planning.trajectory_evaluator import TrajectoryEvaluator
from backend.services.simulation_engine import SimulationEngine


@dataclass
class _SequenceEvaluation:
    sequence: List[str]
    trajectory_score: float
    cumulative_probability: float
    risk: float
    uncertainty: float
    expected_goal_progress: float
    metadata: Dict[str, Any]


class MultiStepDecisionEngine:
    def __init__(
        self,
        simulation_engine: Optional[SimulationEngine] = None,
        trajectory_evaluator: Optional[TrajectoryEvaluator] = None,
        top_k: int = 3,
    ) -> None:
        self.simulation_engine = simulation_engine or SimulationEngine()
        self.trajectory_evaluator = trajectory_evaluator or TrajectoryEvaluator()
        self.top_k = max(1, int(top_k))

    def _effective_evaluator(self, horizon: PlanningHorizon) -> TrajectoryEvaluator:
        return TrajectoryEvaluator(
            discount_factor=horizon.discount_factor,
            expected_state_evaluator=self.trajectory_evaluator.expected_state_evaluator,
            risk_sensitivity=self.trajectory_evaluator.risk_sensitivity,
            uncertainty_sensitivity=self.trajectory_evaluator.uncertainty_sensitivity,
            risk_evaluator=self.trajectory_evaluator.risk_evaluator,
            uncertainty_evaluator=self.trajectory_evaluator.uncertainty_evaluator,
            adaptive_weight_provider=self.trajectory_evaluator.adaptive_weight_provider,
        )

    def decide(
        self,
        root_snapshot: SimulatedState,
        horizon: PlanningHorizon,
        goal_state: GoalState,
        context: PlanningContext,
    ) -> MultiStepDecisionResult:
        snapshot = deepcopy(root_snapshot)
        candidates = list(horizon.candidate_actions)
        if not candidates:
            raise ValueError("PlanningHorizon must contain at least one candidate action")

        sequences = self._generate_sequences(candidates, horizon.horizon_depth, horizon.max_branches)
        if not sequences:
            raise ValueError("No action sequences could be generated for the horizon")

        evaluations: List[_SequenceEvaluation] = []
        for sequence in sequences:
            evaluation = self._evaluate_sequence(snapshot, sequence, horizon, goal_state, context)
            if evaluation is not None:
                evaluations.append(evaluation)

        if not evaluations:
            raise ValueError("Unable to evaluate any candidate sequences")

        evaluations.sort(
            key=lambda item: (
                item.trajectory_score,
                item.cumulative_probability,
                item.expected_goal_progress,
            ),
            reverse=True,
        )

        best = evaluations[0]
        top_k_sequences = [item.sequence for item in evaluations[: self.top_k]]

        metadata = {
            "horizon_depth": horizon.horizon_depth,
            "candidate_actions": list(horizon.candidate_actions),
            "discount_factor": horizon.discount_factor,
            "max_branches": horizon.max_branches,
            "use_digital_twin": horizon.use_digital_twin,
            "sequence_count": len(evaluations),
            "top_k": len(top_k_sequences),
        }
        metadata.update(best.metadata)

        return MultiStepDecisionResult(
            best_sequence=list(best.sequence),
            first_action=str(best.sequence[0]) if best.sequence else "",
            trajectory_score=best.trajectory_score,
            cumulative_probability=best.cumulative_probability,
            risk=best.risk,
            uncertainty=best.uncertainty,
            expected_goal_progress=best.expected_goal_progress,
            top_k_sequences=top_k_sequences,
            metadata=metadata,
        )

    def _generate_sequences(
        self,
        candidate_actions: Sequence[str],
        horizon_depth: int,
        max_branches: Optional[int],
    ) -> List[List[str]]:
        if horizon_depth < 1:
            return []

        actions = list(candidate_actions)
        if max_branches is not None and len(actions) > max_branches:
            actions = actions[:max_branches]

        if horizon_depth == 1:
            return [[action] for action in actions]

        sequences: List[List[str]] = [[action] for action in actions]
        for _ in range(1, horizon_depth):
            expanded: List[List[str]] = []
            for sequence in sequences:
                for action in actions:
                    expanded.append([*sequence, action])
            sequences = expanded
        return sequences

    def _evaluate_sequence(
        self,
        root_snapshot: SimulatedState,
        sequence: List[str],
        horizon: PlanningHorizon,
        goal_state: GoalState,
        context: PlanningContext,
    ) -> Optional[_SequenceEvaluation]:
        if horizon.use_digital_twin:
            try:
                result = self._evaluate_sequence_with_branching(root_snapshot, sequence, horizon, goal_state, context)
                if result is not None:
                    return result
            except Exception:
                pass

        return self._evaluate_sequence_deterministic(root_snapshot, sequence, horizon, goal_state, context)

    def _evaluate_sequence_deterministic(
        self,
        root_snapshot: SimulatedState,
        sequence: List[str],
        horizon: PlanningHorizon,
        goal_state: GoalState,
        context: PlanningContext,
    ) -> Optional[_SequenceEvaluation]:
        try:
            simulation = self.simulation_engine.simulate_sequence(deepcopy(root_snapshot), sequence, context=context.to_dict())
        except Exception:
            return None

        if simulation.get("stopped_early"):
            return None

        transitions = []
        current_state = self._snapshot_to_state(root_snapshot)
        for step in simulation.get("steps", []):
            action = str(step["action"])
            next_snapshot = step["next_snapshot"]
            transitions.append(
                ProbabilisticTransition(
                    current_state=dict(current_state),
                    action=action,
                    possible_states=[self._snapshot_to_state(next_snapshot)],
                    probabilities=[1.0],
                    evidence=[f"deterministic:{action}"],
                )
            )
            current_state = self._snapshot_to_state(next_snapshot)

        evaluator = self._effective_evaluator(horizon)
        evaluation = evaluator.evaluate(transitions, goal_state, context=context)
        return _SequenceEvaluation(
            sequence=list(sequence),
            trajectory_score=evaluation.trajectory_score,
            cumulative_probability=1.0,
            risk=evaluation.cumulative_risk,
            uncertainty=evaluation.cumulative_uncertainty,
            expected_goal_progress=evaluation.goal_progress,
            metadata={"evaluation_mode": "deterministic"},
        )

    def _evaluate_sequence_with_branching(
        self,
        root_snapshot: SimulatedState,
        sequence: List[str],
        horizon: PlanningHorizon,
        goal_state: GoalState,
        context: PlanningContext,
    ) -> Optional[_SequenceEvaluation]:
        tree = self.simulation_engine.simulate_branching_trajectory(
            deepcopy(root_snapshot),
            sequence,
            context=context.to_dict(),
            max_branches=horizon.max_branches,
        )
        leaves = tree.leaves()
        if not leaves:
            return None

        best_evaluation: Optional[_SequenceEvaluation] = None
        for leaf in leaves:
            path = self._node_path(leaf)
            transitions = self._path_to_transitions(path)
            if not transitions:
                continue
            evaluator = self._effective_evaluator(horizon)
            evaluation = evaluator.evaluate(transitions, goal_state, context=context)
            probability = float(leaf.cumulative_probability())
            candidate = _SequenceEvaluation(
                sequence=list(sequence),
                trajectory_score=evaluation.trajectory_score,
                cumulative_probability=probability,
                risk=evaluation.cumulative_risk,
                uncertainty=evaluation.cumulative_uncertainty,
                expected_goal_progress=evaluation.goal_progress,
                metadata={
                    "evaluation_mode": "branching",
                    "branch_probability": probability,
                    "stopped_early": tree.stopped_early,
                },
            )
            if best_evaluation is None or self._compare_evaluations(candidate, best_evaluation):
                best_evaluation = candidate

        return best_evaluation

    def _compare_evaluations(self, left: _SequenceEvaluation, right: _SequenceEvaluation) -> bool:
        if left.trajectory_score != right.trajectory_score:
            return left.trajectory_score > right.trajectory_score
        if left.cumulative_probability != right.cumulative_probability:
            return left.cumulative_probability > right.cumulative_probability
        return left.expected_goal_progress > right.expected_goal_progress

    def _path_to_transitions(self, path: List[Any]) -> List[ProbabilisticTransition]:
        transitions: List[ProbabilisticTransition] = []
        for parent, child in zip(path[:-1], path[1:]):
            current_state = self._snapshot_to_state(parent.snapshot)
            next_state = self._snapshot_to_state(child.snapshot)
            action = str(child.action_from_parent)
            transitions.append(
                ProbabilisticTransition(
                    current_state=dict(current_state),
                    action=action,
                    possible_states=[next_state],
                    probabilities=[1.0],
                    evidence=[f"branch:{action}"],
                )
            )
        return transitions

    def _node_path(self, leaf: Any) -> List[Any]:
        path = []
        current = leaf
        while current is not None:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    def _snapshot_to_state(self, snapshot: SimulatedState) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        state.update(snapshot.skills)
        state.update(snapshot.knowledge)
        state.update(snapshot.projects)
        state.update(snapshot.goals)
        state.update(snapshot.learning)
        return state
