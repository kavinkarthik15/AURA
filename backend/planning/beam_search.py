from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.models.goal_state import GoalState
from backend.planning.beam_registry import BeamTree
from backend.planning.beam_node import BeamNode
from backend.planning.beam_expander import BeamExpander
from backend.planning.state_evaluator import StateEvaluator
from backend.planning.trajectory_evaluator import TrajectoryEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.planning.planning_context import PlanningContext as PlanningContextModel
from backend.planning.probabilistic_transition import ProbabilisticTransition
from backend.ai.decision_reasoner import DecisionReasoner
from backend.ai.context_builder import PlanningContext as AiPlanningContext
from backend.planning.candidate_selector import CandidateSelector


class BeamSearch:
    def __init__(
        self,
        beam_width: int = 3,
        max_depth: int = 3,
        decision_reasoner: Optional[DecisionReasoner] = None,
        evaluator: Optional[StateEvaluator] = None,
        trajectory_evaluator: Optional[TrajectoryEvaluator] = None,
        risk_sensitivity: float = 0.0,
        uncertainty_sensitivity: float = 0.0,
        simulation_engine: Optional[SimulationEngine] = None,
        candidate_selector: Optional[CandidateSelector] = None,
    ):
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.decision_reasoner = decision_reasoner
        self.evaluator = evaluator or StateEvaluator()
        self.risk_sensitivity = max(0.0, float(risk_sensitivity))
        self.uncertainty_sensitivity = max(0.0, float(uncertainty_sensitivity))
        self.trajectory_evaluator = trajectory_evaluator
        self.simulation_engine = simulation_engine
        self.candidate_selector = candidate_selector
        if self.trajectory_evaluator is None and (
            self.risk_sensitivity > 0.0 or self.uncertainty_sensitivity > 0.0
        ):
            self.trajectory_evaluator = TrajectoryEvaluator(
                risk_sensitivity=self.risk_sensitivity,
                uncertainty_sensitivity=self.uncertainty_sensitivity,
            )

    def search(
        self,
        root: BeamNode,
        context: AiPlanningContext,
        goal_state: Optional[GoalState] = None,
        planning_context: Optional[PlanningContextModel] = None,
    ) -> List[BeamNode]:
        tree = BeamTree(root=root, beam_width=self.beam_width, max_depth=self.max_depth)
        active = [root]
        goal = goal_state

        if self.candidate_selector is not None and self.candidate_selector.enabled:
            candidate_actions = self._collect_candidate_actions(root, context)
            if candidate_actions:
                selection = self.candidate_selector.select_action(
                    snapshot=root.branch_snapshot if getattr(root, "branch_snapshot", None) is not None else None,
                    candidate_actions=candidate_actions,
                    context=planning_context,
                    goal_state=goal_state,
                )
                if selection is not None and selection.action is not None:
                    root.metadata = {**getattr(root, "metadata", {}), **{"selected_action": selection.action, "selection_reason": selection.selection_reason}}

        for depth in range(self.max_depth):
            all_children: List[BeamNode] = []
            for node in active:
                if goal is not None:
                    eval_result = self.evaluator.evaluate_node(node, goal)
                    node.goal_alignment = getattr(node, "goal_alignment", {}) or {}
                    node.evaluation_score = eval_result.score

                expanded_context = context
                if planning_context is not None and context is not None:
                    expanded_context = self._build_expansion_context(context, planning_context)

                children = BeamExpander.expand(
                    node,
                    expanded_context,
                    decision_reasoner=self.decision_reasoner,
                    simulation_engine=self.simulation_engine,
                ) if expanded_context is not None else []
                all_children.extend(children)

            if not all_children:
                break

            if self.trajectory_evaluator is not None:
                ranked = sorted(
                    all_children,
                    key=lambda n: self._trajectory_score(n, context, goal, planning_context),
                    reverse=True,
                )
            elif goal is not None:
                ranked = sorted(
                    all_children,
                    key=lambda n: self.evaluator.evaluate_node(n, goal).score,
                    reverse=True,
                )
            else:
                ranked = sorted(all_children, key=lambda n: getattr(n, "accumulated_utility", 0.0), reverse=True)

            active = ranked[: self.beam_width]
            tree.active_nodes = list(active)

        return tree.active_nodes

    def _collect_candidate_actions(
        self,
        root: BeamNode,
        context: Optional[AiPlanningContext],
    ) -> List[str]:
        candidates: List[str] = []
        if not root or not getattr(root, "children", None):
            return candidates
        for child in root.children:
            decision = getattr(child, "decision", None)
            action = getattr(decision, "action", None)
            if isinstance(action, str) and action.strip() and action not in candidates:
                candidates.append(action)
        return candidates

    def _build_expansion_context(
        self,
        context: AiPlanningContext,
        planning_context: PlanningContextModel,
    ) -> AiPlanningContext:
        if context is None:
            return context

        return AiPlanningContext(
            goal=context.goal,
            current_state=dict(context.current_state or {}),
            working_memory=list(context.working_memory or []),
            relevant_experiences=list(context.relevant_experiences or []),
            relevant_knowledge=list(context.relevant_knowledge or []),
            relevant_reflections=list(context.relevant_reflections or []),
            constraints=list(context.constraints or []),
            preferences=list(context.preferences or []),
            habits=list(context.habits or []),
            failure_patterns=list(context.failure_patterns or []),
            success_patterns=list(context.success_patterns or []),
            candidate_plans=list(context.candidate_plans or []),
            patterns=list(context.patterns or []),
            confidence=context.confidence,
            evidence=list(context.evidence or []),
            context_summary=context.context_summary,
        )

    def _trajectory_score(
        self,
        node: BeamNode,
        context: Optional[AiPlanningContext],
        goal_state: Optional[GoalState],
        planning_context: Optional[PlanningContextModel] = None,
    ) -> float:
        if self.trajectory_evaluator is None:
            return float(getattr(node, "accumulated_utility", 0.0) or 0.0)
        evaluation = self.evaluate_trajectory(node, context, goal_state, planning_context)
        if evaluation is None:
            return float(getattr(node, "accumulated_utility", 0.0) or 0.0)
        return float(evaluation.get("trajectory_score", 0.0) or 0.0)

    def evaluate_trajectory(
        self,
        node: Optional[BeamNode],
        context: Optional[AiPlanningContext] = None,
        goal_state: Optional[GoalState] = None,
        planning_context: Optional[PlanningContextModel] = None,
    ) -> Optional[Dict[str, Any]]:
        if self.trajectory_evaluator is None:
            return None
        if node is None:
            return None

        path: List[BeamNode] = []
        current = node
        while current is not None:
            path.append(current)
            current = current.parent
        path = list(reversed(path))

        transitions: List[ProbabilisticTransition] = []
        for index in range(1, len(path)):
            parent = path[index - 1]
            child = path[index]
            parent_state = dict(parent.predicted_state if parent.predicted_state else parent.current_state or {})
            child_state = dict(child.predicted_state if child.predicted_state else child.current_state or {})
            action = getattr(child.decision, "action", None) if child.decision is not None else f"step_{index}"
            if not child_state:
                child_state = dict(parent_state)
            confidence = float(getattr(getattr(child.decision, "prediction", None), "confidence", 0.0) or 0.0)
            if confidence <= 0.0:
                confidence = 0.7
            if confidence >= 1.0:
                confidence = 0.95
            negative_state = dict(parent_state)
            all_keys = sorted(set(parent_state) | set(child_state))
            for key in all_keys:
                parent_value = float(parent_state.get(key, 0.0) or 0.0)
                child_value = float(child_state.get(key, 0.0) or 0.0)
                spread = abs(child_value - parent_value)
                shifted = parent_value + (0.35 * spread if child_value >= parent_value else -0.35 * spread)
                negative_state[key] = round(shifted, 4)
            possible_states = [dict(child_state), dict(negative_state)]
            probabilities = [confidence, max(0.05, 1.0 - confidence)]
            if possible_states[0] == possible_states[1]:
                probabilities = [1.0]
            transition = ProbabilisticTransition(
                current_state=dict(parent_state),
                action=action,
                possible_states=possible_states,
                probabilities=probabilities,
                expected_state=dict(child_state),
                confidence=confidence,
                evidence=[getattr(child.decision, "decision_id", f"step_{index}")],
            )
            transitions.append(transition)

        if not transitions:
            current_state = dict(node.current_state or {})
            predicted_state = dict(node.predicted_state or current_state)
            confidence = float(getattr(getattr(node.decision, "prediction", None), "confidence", 0.0) or 0.0)
            if confidence <= 0.0:
                confidence = 0.7
            if confidence >= 1.0:
                confidence = 0.95
            negative_state = dict(current_state)
            all_keys = sorted(set(current_state) | set(predicted_state))
            for key in all_keys:
                current_value = float(current_state.get(key, 0.0) or 0.0)
                predicted_value = float(predicted_state.get(key, 0.0) or 0.0)
                spread = abs(predicted_value - current_value)
                shifted = current_value + (0.35 * spread if predicted_value >= current_value else -0.35 * spread)
                negative_state[key] = round(shifted, 4)
            possible_states = [dict(predicted_state), dict(negative_state)]
            probabilities = [confidence, max(0.05, 1.0 - confidence)]
            if possible_states[0] == possible_states[1]:
                probabilities = [1.0]
            transitions = [
                ProbabilisticTransition(
                    current_state=dict(current_state),
                    action=getattr(node.decision, "action", "single_step"),
                    possible_states=possible_states,
                    probabilities=probabilities,
                    expected_state=dict(predicted_state),
                    confidence=confidence,
                    evidence=[getattr(node.decision, "decision_id", "single_step")],
                )
            ]

        if goal_state is None:
            goal_name = getattr(context, "goal", "trajectory_goal") if context is not None else "trajectory_goal"
            goal_state = GoalState(goal=str(goal_name), target_skills={})

        evaluation = self.trajectory_evaluator.evaluate(transitions, goal_state, planning_context)
        return {
            "trajectory_score": evaluation.trajectory_score,
            "expected_value": evaluation.expected_value,
            "cumulative_utility": evaluation.cumulative_utility,
            "cumulative_risk": evaluation.cumulative_risk,
                "cumulative_uncertainty": evaluation.cumulative_uncertainty,
            "cumulative_cost": evaluation.cumulative_cost,
            "goal_progress": evaluation.goal_progress,
            "confidence": evaluation.confidence,
            "horizon": evaluation.horizon,
            "discount_factor": evaluation.discount_factor,
            "step_evaluations": [
                {
                    "step_index": step.step_index,
                    "expected_value": step.expected_value,
                    "discounted_value": step.discounted_value,
                    "cumulative_utility": step.cumulative_utility,
                    "cumulative_risk": step.cumulative_risk,
                    "cumulative_cost": step.cumulative_cost,
                    "goal_progress": step.goal_progress,
                    "confidence": step.confidence,
                    "explanation": step.explanation,
                }
                for step in evaluation.step_evaluations
            ],
            "explanation": evaluation.explanation,
        }
