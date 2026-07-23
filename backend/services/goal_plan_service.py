import time
from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.models.objective_profile import ObjectiveProfile
from backend.services.beam_search_planner import BeamSearchPlanner
from backend.services.multi_objective_evaluator import MultiObjectiveEvaluator
from backend.services.objective_profiles import build_default_profiles
from backend.services.pareto_optimizer import ParetoOptimizer
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.planner_config import DEFAULT_BEAM_WIDTH, DEFAULT_MAX_DEPTH
from backend.services.recommendation_engine import RecommendationEngine


class GoalPlanService:
    def __init__(self, beam_search_planner: BeamSearchPlanner | None = None, plan_evaluator: PlanEvaluator | None = None, recommendation_engine: RecommendationEngine | None = None, multi_objective_evaluator: MultiObjectiveEvaluator | None = None, pareto_optimizer: ParetoOptimizer | None = None) -> None:
        self.beam_search_planner = beam_search_planner or BeamSearchPlanner()
        self.plan_evaluator = plan_evaluator or PlanEvaluator()
        self.recommendation_engine = recommendation_engine or RecommendationEngine(plan_evaluator=self.plan_evaluator)
        self.multi_objective_evaluator = multi_objective_evaluator or MultiObjectiveEvaluator()
        self.pareto_optimizer = pareto_optimizer or ParetoOptimizer()

    def recommend_goal_plan(self, current_state: Dict[str, int], goal_state: GoalState, profile: ObjectiveProfile | None = None) -> Dict:
        start_time = time.perf_counter()
        search_result = self.beam_search_planner.search(current_state, goal_state, beam_width=DEFAULT_BEAM_WIDTH, max_depth=DEFAULT_MAX_DEPTH)
        candidate_plans = [{"name": "Plan 1", "actions": search_result["best_plan"]}] if search_result["best_plan"] else []
        if not candidate_plans:
            return {
                "recommended_plan": None,
                "goal_progress": 0.0,
                "confidence": 0.0,
                "reasoning": {},
                "candidate_plans": [],
                "candidate_evaluations": [],
                "metrics": {
                    "plans_generated": 0,
                    "plans_evaluated": 0,
                    "search_time_ms": 0,
                },
                "search_metrics": {
                    "plans_generated": 0,
                    "plans_evaluated": 0,
                    "beam_width": DEFAULT_BEAM_WIDTH,
                    "search_depth": DEFAULT_MAX_DEPTH,
                },
            }

        evaluations = self.plan_evaluator.evaluate_plans(current_state, goal_state, candidate_plans)
        selected_profile = profile or build_default_profiles()["balanced_learning"]
        multi_objective_results = self.multi_objective_evaluator.evaluate_plans(current_state, goal_state, candidate_plans, profile=selected_profile)
        pareto_front = self.pareto_optimizer.find_pareto_front(multi_objective_results)
        recommendation = self.recommendation_engine.recommend_plan(current_state, goal_state, candidate_plans)
        recommendation["candidate_plans"] = candidate_plans
        recommendation["candidate_evaluations"] = [
            {
                "plan": item["plan_name"],
                "goal_progress": item["goal_progress"],
                "confidence": item["confidence"],
            }
            for item in evaluations
        ]
        recommendation["metrics"] = {
            "plans_generated": len(candidate_plans),
            "plans_evaluated": len(evaluations),
            "search_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }
        recommendation["search_metrics"] = {
            **search_result.get("search_metrics", {}),
            "search_time_ms": recommendation["metrics"]["search_time_ms"],
        }
        recommendation["search_trace"] = search_result.get("search_trace", {})
        recommendation["best_plan"] = candidate_plans[0]
        recommendation["pareto_front"] = [entry["plan"] for entry in pareto_front]
        recommendation["why_selected"] = self._build_tradeoff_reasoning(recommendation, pareto_front, selected_profile)
        recommendation["tradeoffs"] = [entry["objectives"] for entry in pareto_front]
        recommendation["alternative_plan"] = pareto_front[1]["plan"] if len(pareto_front) > 1 else None
        recommendation["selected_profile"] = selected_profile.name
        recommendation["profile_score"] = max((entry.get("profile_score") or 0.0) for entry in multi_objective_results)
        return recommendation

    def _build_tradeoff_reasoning(self, recommendation: Dict, pareto_front: List[Dict], profile: ObjectiveProfile) -> str:
        selected_plan = recommendation.get("recommended_plan")
        if not pareto_front:
            return f"Selected {selected_plan} because it provides the strongest balance of progress and confidence."

        trade_summary = []
        for entry in pareto_front[:2]:
            trade_summary.append(f"{entry['plan']['name']} -> {entry['objectives']}")
        return f"Selected {selected_plan} using the {profile.name} profile because it offers strong trade-offs for the requested objectives; alternatives remain available: {' | '.join(trade_summary)}"


goal_plan_service = GoalPlanService()
