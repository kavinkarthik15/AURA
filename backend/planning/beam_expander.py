from __future__ import annotations

from typing import List, Optional

from backend.ai.decision_reasoner import DecisionReasoner
from backend.ai.context_builder import PlanningContext
from backend.planning.beam_node import BeamNode
from backend.services.simulation_engine import SimulationEngine


class BeamExpander:
    @staticmethod
    def expand(
        node: BeamNode,
        context: PlanningContext,
        decision_reasoner: Optional[DecisionReasoner] = None,
        simulation_engine: Optional[SimulationEngine] = None,
    ) -> List[BeamNode]:
        """Expand a single BeamNode into child BeamNodes using the DecisionReasoner.

        Rules:
        - child.current_state = parent.predicted_state
        - child.predicted_state = decision.prediction.predicted_state
        - No pruning, ranking, or beam-width logic here.
        - Inherit history and reasoning; accumulate metrics.
        """
        dr = decision_reasoner or DecisionReasoner()

        # make a shallow copy of context but set current_state to node.predicted_state
        expanded_context = PlanningContext(
            goal=context.goal,
            current_state=dict(node.predicted_state or {}),
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

        candidates = dr.generate_candidates(expanded_context)
        children: List[BeamNode] = []

        for cand in candidates:
            current_state = dict(node.predicted_state or {})
            probabilistic_transition = None
            predicted_state = dict(cand.prediction.predicted_state or {})

            if simulation_engine is not None:
                try:
                    snapshot = simulation_engine.make_snapshot(
                        current_state=current_state,
                        simulation_id=f"beam-{node.node_id}",
                        step=node.depth,
                        snapshot_id=node.node_id,
                    )
                    transition_result = simulation_engine.simulate_probabilistic_action(
                        snapshot,
                        str(cand.action),
                        context={"source": "beam_search", "action": str(cand.action), "intent": cand.expected_outcome},
                    )
                    probabilistic_transition = transition_result["transition"]
                    predicted_state = dict(probabilistic_transition.expected_state or predicted_state)

                    # If the simulation produced explicit branches, create a child per branch
                    branches = transition_result.get("branches") or []
                    if branches:
                        for branch in branches:
                            branch_snapshot = branch.get("next_snapshot")
                            branch_probability = float(branch.get("probability", 1.0))
                            branch_diff = branch.get("diff", {})
                            branch_predicted = dict(branch_snapshot.skills if branch_snapshot is not None else predicted_state)

                            child = BeamNode(
                                parent=node,
                                depth=node.depth + 1,
                                decision=cand,
                                current_state=current_state,
                                predicted_state=branch_predicted,
                                goal_alignment=cand.goal_alignment or {},
                                accumulated_reward=(node.accumulated_reward or 0.0) + float(getattr(cand.prediction, "reward", 0.0)),
                                accumulated_cost=(node.accumulated_cost or 0.0) + float(getattr(cand.prediction, "cost", 0.0)),
                                accumulated_risk=(node.accumulated_risk or 0.0) + float(getattr(cand.prediction, "risk", 0.0)),
                                accumulated_utility=(node.accumulated_utility or 0.0) + float(getattr(cand.prediction, "utility", 0.0)),
                                decision_history=list(node.decision_history or []) + [cand.decision_id],
                                reasoning_trace=list(node.reasoning_trace or []) + [{"decision_id": cand.decision_id, "reasoning": cand.evidence.reasoning}],
                                probabilistic_transition=probabilistic_transition,
                                state_diff=branch_diff,
                                branch_snapshot_id=getattr(branch_snapshot, "snapshot_id", None) if branch_snapshot is not None else None,
                                branch_snapshot=branch_snapshot,
                                branch_probability=branch_probability,
                            )
                            node.children.append(child)
                            children.append(child)
                        # we've already created branch children for this candidate, skip single-child creation
                        continue
                except Exception:
                    probabilistic_transition = None

            # default single child path (no probabilistic branches)
            child = BeamNode(
                parent=node,
                depth=node.depth + 1,
                decision=cand,
                current_state=current_state,
                predicted_state=predicted_state,
                goal_alignment=cand.goal_alignment or {},
                accumulated_reward=(node.accumulated_reward or 0.0) + float(getattr(cand.prediction, "reward", 0.0)),
                accumulated_cost=(node.accumulated_cost or 0.0) + float(getattr(cand.prediction, "cost", 0.0)),
                accumulated_risk=(node.accumulated_risk or 0.0) + float(getattr(cand.prediction, "risk", 0.0)),
                accumulated_utility=(node.accumulated_utility or 0.0) + float(getattr(cand.prediction, "utility", 0.0)),
                decision_history=list(node.decision_history or []) + [cand.decision_id],
                reasoning_trace=list(node.reasoning_trace or []) + [{"decision_id": cand.decision_id, "reasoning": cand.evidence.reasoning}],
                probabilistic_transition=probabilistic_transition,
            )
            node.children.append(child)
            children.append(child)

        node.expanded = True
        return children
