import time
from typing import Dict, List, cast

from backend.ai.assumption_detector import AssumptionDetector
from backend.ai.counterfactual_planner import CounterfactualPlanner
from backend.ai.explanation_consistency import ExplanationConsistencyChecker
from backend.ai.experience_reasoner import ExperienceReasoner
from backend.ai.experience_retriever import ExperienceRetriever
from backend.ai.meta_reasoner import MetaReasoner
from backend.ai.plan_explainer import PlanExplainer
from backend.ai.planning_policy import PlanningPolicy
from backend.ai.reasoning_analytics import ReasoningAnalytics
from backend.ai.reasoning_dashboard import ReasoningDashboard
from backend.ai.reasoning_trace import ReasoningTrace
from backend.ai.self_critique import SelfCritiqueEngine
from backend.ai.strategy_selector import StrategySelector
from backend.config.retrieval_config import RETRIEVAL_WEIGHT
from backend.models.goal_state import GoalState
from backend.models.search_metrics import SearchMetrics
from backend.services.action_library import action_library
from backend.services.plan_expander import PlanExpander
from backend.services.planner_config import (
    DEFAULT_BEAM_WIDTH,
    DEFAULT_MAX_DEPTH,
    DEFAULT_POLICY_ENABLED,
    DEFAULT_POLICY_WEIGHT,
)
from backend.services.search_state import SearchState


class BeamSearchPlanner:
    def __init__(
        self,
        action_library_instance=None,
        expander: PlanExpander | None = None,
        policy: PlanningPolicy | None = None,
        policy_weight: float = DEFAULT_POLICY_WEIGHT,
        retriever: ExperienceRetriever | None = None,
        retrieval_weight: float = RETRIEVAL_WEIGHT,
    ) -> None:
        self.action_library = action_library_instance or action_library
        self.expander = expander or PlanExpander(action_library_instance=self.action_library)
        self.policy = policy
        self.policy_weight = policy_weight
        self.retriever = retriever
        self.retrieval_weight = retrieval_weight

    def search(
        self,
        current_state: Dict[str, int],
        goal_state: GoalState,
        beam_width: int = DEFAULT_BEAM_WIDTH,
        max_depth: int = DEFAULT_MAX_DEPTH,
        use_policy: bool | None = None,
        use_retrieval: bool | None = None,
    ) -> Dict:
        start_time = time.perf_counter()
        policy_enabled = (
            DEFAULT_POLICY_ENABLED and self.policy is not None
            if use_policy is None
            else bool(use_policy) and self.policy is not None
        )
        retrieval_enabled = (
            self.retriever is not None if use_retrieval is None else bool(use_retrieval) and self.retriever is not None
        )
        adaptive_retrieval_weight = self.retrieval_weight
        confidence_breakdown = {"policy": 0.0, "retrieval": 0.0, "digital_twin": 0.0, "planner": 0.0}
        root = SearchState(actions=[], current_state=current_state.copy(), score=0.0, depth=0)
        beam = [root]
        metrics = SearchMetrics(beam_width=beam_width, search_depth=max_depth)
        search_trace: Dict[str, List[Dict]] = {}
        policy_inference_ms = 0.0
        retrieval_time_ms = 0.0
        retrieval_matches = []

        for depth in range(max_depth):
            expanded_states: List[SearchState] = []
            for state in beam:
                next_actions = self.expander.get_possible_next_actions(state.current_state, goal_state)
                policy_scores: Dict[str, float] = {}
                retrieval_scores: Dict[str, float] = {}
                if policy_enabled and self.policy is not None:
                    policy_started = time.perf_counter()
                    policy_scores = {
                        prediction.action: prediction.probability
                        for prediction in self.policy.predict(
                            cast(Dict[str, float], state.current_state), goal_state.goal, next_actions
                        )
                    }
                    policy_inference_ms += (time.perf_counter() - policy_started) * 1000
                if retrieval_enabled and self.retriever is not None:
                    retrieval_result = self.retriever.retrieve(
                        cast(Dict[str, float], state.current_state), goal_state.goal, next_actions
                    )
                    retrieval_time_ms += retrieval_result["retrieval_time_ms"]
                    retrieval_matches = retrieval_result["matches"]
                    for match in retrieval_matches:
                        for match_action in match.completed_actions or match.actions:
                            retrieval_scores[match_action] = max(
                                retrieval_scores.get(match_action, 0.0), match.similarity
                            )
                    if self.retriever and hasattr(self.retriever, "compute_adaptive_weight"):
                        adaptive_retrieval_weight = self.retriever.compute_adaptive_weight(
                            policy_confidence=(
                                policy_scores.get(next_actions[0], 0.0) if policy_enabled and next_actions else 0.0
                            ),
                            retrieval_confidence=max((match.similarity for match in retrieval_matches), default=0.0),
                            goal_type="exploration" if not goal_state.target_skills else "optimization",
                        )
                metrics.plans_generated += len(next_actions)
                for action in next_actions:
                    next_state = state.current_state.copy()
                    next_state = self._apply_action(next_state, action)
                    new_state = SearchState(
                        actions=[*state.actions, action],
                        current_state=next_state,
                        score=self._score_state(next_state, goal_state),
                        depth=state.depth + 1,
                        goal_progress=self._goal_progress(next_state, goal_state),
                        confidence=self._confidence(next_state, goal_state),
                    )
                    if policy_enabled:
                        new_state.policy_score = policy_scores.get(action, 0.0)
                    new_state.retrieval_score = retrieval_scores.get(action, 0.0)
                    expanded_states.append(new_state)

            if not expanded_states:
                break

            ranked_states = sorted(
                expanded_states,
                key=lambda item: (
                    item.score
                    + self.policy_weight * getattr(item, "policy_score", 0.0)
                    + adaptive_retrieval_weight * getattr(item, "retrieval_score", 0.0),
                    item.goal_progress,
                    item.confidence,
                ),
                reverse=True,
            )
            beam = ranked_states[:beam_width]
            metrics.plans_evaluated += len(ranked_states)
            search_trace[f"depth_{depth + 1}"] = [
                {
                    "actions": state.actions,
                    "score": state.score,
                    "goal_progress": state.goal_progress,
                    "confidence": state.confidence,
                    "policy_score": getattr(state, "policy_score", 0.0),
                    "retrieval_score": getattr(state, "retrieval_score", 0.0),
                }
                for state in ranked_states[:beam_width]
            ]

        if not beam:
            return {
                "best_plan": [],
                "score": 0.0,
                "plans_evaluated": metrics.plans_evaluated,
                "search_depth": max_depth,
                "beam_width": beam_width,
                "search_metrics": metrics.to_dict(),
                "policy_enabled": policy_enabled,
                "retrieval_enabled": retrieval_enabled,
            }

        best_state = max(beam, key=lambda item: (item.score, item.goal_progress, item.confidence))
        metrics.search_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        action_explanations = []
        policy_entropy = 0.0
        policy_confidence = 0.0
        if policy_enabled and self.policy is not None:
            first_actions = self.expander.get_possible_next_actions(current_state, goal_state)
            explanations = self.policy.explain_actions(
                cast(Dict[str, float], current_state), goal_state.goal, first_actions
            )
            action_explanations = [item for item in explanations if item["action"] in best_state.actions]
            policy_entropy = self.policy.normalized_entropy(
                cast(Dict[str, float], current_state), goal_state.goal, first_actions
            )
            policy_confidence = max((item["confidence"] for item in action_explanations), default=0.0)
        retrieval_confidence = max((match.similarity for match in retrieval_matches), default=0.0)
        if retrieval_enabled and self.retriever is not None:
            first_actions = self.expander.get_possible_next_actions(current_state, goal_state)
            final_retrieval = self.retriever.retrieve(
                cast(Dict[str, float], current_state), goal_state.goal, first_actions
            )
            retrieval_matches = final_retrieval["matches"]
            retrieval_time_ms += final_retrieval["retrieval_time_ms"]
            retrieval_confidence = max((match.similarity for match in retrieval_matches), default=0.0)
        digital_twin_confidence = 0.0
        if self.policy is not None:
            digital_twin_confidence = round(max(0.0, min(1.0, 0.5 + (0.1 * len(best_state.actions)))), 4)
        planner_confidence = round(
            0.25 * best_state.confidence
            + 0.2 * policy_confidence
            + 0.2 * retrieval_confidence
            + 0.15 * digital_twin_confidence
            + 0.2 * max(best_state.confidence, retrieval_confidence, policy_confidence, digital_twin_confidence),
            4,
        )
        confidence_breakdown = {
            "policy": round(policy_confidence, 4),
            "retrieval": round(retrieval_confidence, 4),
            "digital_twin": round(digital_twin_confidence, 4),
            "planner": round(planner_confidence, 4),
        }
        reasoning_experiences = [
            {
                "goal_name": goal_state.goal,
                "actions": best_state.actions,
                "completed_actions": best_state.actions,
                "success": True,
            }
        ]
        reasoning_experiences.extend(
            [
                {
                    "goal_name": goal_state.goal,
                    "actions": [match.reason or "Previous action"],
                    "completed_actions": getattr(match, "completed_actions", [])
                    or getattr(match, "actions", [])
                    or [match.reason or "Previous action"],
                    "success": bool(getattr(match, "success", False)),
                }
                for match in retrieval_matches
            ]
        )
        reasoner = ExperienceReasoner()
        reasoning = reasoner.analyze(reasoning_experiences)
        explanation = PlanExplainer().explain(
            best_state.actions,
            reasoning_experiences,
            confidence=max(planner_confidence, retrieval_confidence),
            digital_twin_confidence=digital_twin_confidence,
        )
        counterfactuals = CounterfactualPlanner().generate(
            best_state.actions,
            alternatives=[state.actions for state in beam if state.actions and state.actions != best_state.actions][:2],
        )
        consistency_status = ExplanationConsistencyChecker().check(
            best_state.actions, reasoning, explanation.get("ranked_evidence", [])
        )
        reasoning_trace = ReasoningTrace().build(
            goal_state.goal,
            reasoning_experiences,
            reasoning,
            counterfactuals,
            best_state.actions,
            explanation,
            {
                "reasoning_confidence": reasoning.get("reasoning_confidence", 0.0),
                "evidence_support": reasoning.get("evidence_support", 0),
                "coverage": reasoning.get("coverage", 0.0),
            },
        )
        reasoning_analytics = ReasoningAnalytics().record(
            reasoning_time_ms=metrics.search_time_ms,
            evidence_count=len(reasoning_experiences),
            counterfactuals_generated=len(counterfactuals),
            contradictions_detected=1 if not consistency_status["consistent"] else 0,
            explanation_length=len(explanation.get("summary", "")),
            coverage=reasoning.get("coverage", 0.0),
        )
        reasoning_dashboard = ReasoningDashboard().render(
            {"reasoning_confidence": reasoning.get("reasoning_confidence", 0.0)},
            explanation.get("ranked_evidence", []),
            counterfactuals,
            {"detected": not consistency_status["consistent"]},
            reasoning.get("coverage", 0.0),
        )
        assumptions = AssumptionDetector().detect(
            goal=goal_state.goal,
            context={"time_available_hours": 3, "skill_level": 80, "internet_available": True},
            evidence={"time_available_hours": True, "skill_level": False},
        )
        contributors = ["reasoner"]
        if retrieval_enabled:
            contributors.append("retrieval")
        if policy_enabled:
            contributors.append("policy")
        if counterfactuals:
            contributors.append("counterfactual")
        meta_reasoner = MetaReasoner()
        meta_reasoning = meta_reasoner.evaluate(
            reasoning_trace={"confidence": planner_confidence, "coverage": reasoning.get("coverage", 0.0)},
            reasoning_metadata={"consistency_status": consistency_status},
            confidence_breakdown=confidence_breakdown,
            retrieved_experiences=retrieval_matches,
            goal=goal_state.goal,
            assumptions=assumptions,
            contributors=contributors,
        )
        critique = SelfCritiqueEngine().critique(
            confidence=planner_confidence,
            consistency=consistency_status["consistent"],
            evidence_count=len(retrieval_matches),
            counterfactuals=counterfactuals,
        )
        strategy = StrategySelector().select(
            goal=goal_state.goal,
            confidence=planner_confidence,
            evidence_count=len(retrieval_matches),
            contradictions=not consistency_status["consistent"],
        )
        return {
            "best_plan": best_state.actions,
            "score": round(best_state.score, 2),
            "plans_evaluated": metrics.plans_evaluated,
            "search_depth": max_depth,
            "beam_width": beam_width,
            "search_metrics": metrics.to_dict(),
            "search_trace": search_trace,
            "policy_enabled": policy_enabled,
            "performance_timings_ms": {
                "beam_search": metrics.search_time_ms,
                "policy_inference": round(policy_inference_ms, 4),
                "retrieval": round(retrieval_time_ms, 4),
            },
            "planner_confidence": planner_confidence,
            "confidence_breakdown": confidence_breakdown,
            "policy_entropy": policy_entropy,
            "action_explanations": action_explanations,
            "retrieval_enabled": retrieval_enabled,
            "retrieval_weight": adaptive_retrieval_weight,
            "retrieval_analytics": (
                self.retriever.get_analytics_summary()
                if self.retriever and hasattr(self.retriever, "get_analytics_summary")
                else {}
            ),
            "retrieved_experiences": [
                {
                    "experience_id": match.experience_id,
                    "similarity": match.similarity,
                    "success": match.success,
                    "reason": match.reason,
                }
                for match in retrieval_matches
            ],
            "retrieval_explanation": (
                f"Recommended because a similar previous execution achieved {retrieval_matches[0].goal_completion:.0%} goal completion."
                if retrieval_matches
                else "No similar prior experience was retrieved."
            ),
            "reasoning_confidence": reasoning.get("reasoning_confidence", 0.0),
            "counterfactual_comparison": counterfactuals,
            "reasoning_trace": reasoning_trace,
            "consistency_status": consistency_status,
            "reasoning_metadata": {
                "reasoning_confidence": reasoning.get("reasoning_confidence", 0.0),
                "reasoning": reasoning,
                "explanation": explanation,
                "counterfactual_comparison": counterfactuals,
                "consistency_status": consistency_status,
                "reasoning_trace": reasoning_trace,
                "reasoning_analytics": reasoning_analytics,
                "reasoning_dashboard": reasoning_dashboard,
                "meta_reasoning": meta_reasoning,
                "assumptions": assumptions,
                "self_critique": critique,
                "strategy_selection": strategy,
            },
        }

    def _apply_action(self, state: Dict[str, int], action_name: str) -> Dict[str, int]:
        updated = state.copy()
        action = self.action_library.get_action(action_name)
        if not action:
            return updated

        for skill in ["python", "dsa", "projects"]:
            if skill in updated:
                updated[skill] = updated.get(skill, 0) + int(action.get("estimated_skill_gain", 0) / 3)
        if "projects" in updated:
            updated["projects"] = updated.get("projects", 0) + 1
        return updated

    def _score_state(self, state: Dict[str, int], goal_state: GoalState) -> float:
        if not goal_state.target_skills:
            return 0.0

        progress_values = []
        for skill, target_goal in goal_state.target_skills.items():
            current_value = state.get(skill, 0)
            progress_values.append(max(0, min(1, current_value / max(1, target_goal))))
        return round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0

    def _goal_progress(self, state: Dict[str, int], goal_state: GoalState) -> float:
        progress_values = []
        for skill, target_goal in goal_state.target_skills.items():
            current = state.get(skill, 0)
            progress_values.append(min(1.0, current / max(1, target_goal)))
        return round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0

    def _confidence(self, state: Dict[str, int], goal_state: GoalState) -> float:
        return round(min(1.0, self._goal_progress(state, goal_state) + 0.1), 2)
