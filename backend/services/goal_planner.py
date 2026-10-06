from typing import Dict, List

from backend.ai.context_builder import ContextBuilder
from backend.models.action_catalog import ActionCatalog
from backend.models.goal_state import GoalState
from backend.services.action_catalog_service import ActionCatalogService
from backend.services.action_ranker import ActionRanker
from backend.services.experience_service import experience_service
from backend.services.transition_engine import TransitionEngine


DEFAULT_ACTIONS = [
    {"action_id": "ACT001", "action_name": "Complete Python Project", "action_type": "Project", "estimated_skill_gain": 10},
    {"action_id": "ACT002", "action_name": "Complete DSA Course", "action_type": "Course", "estimated_skill_gain": 8},
    {"action_id": "ACT003", "action_name": "Participate in Hackathon", "action_type": "Hackathon", "estimated_skill_gain": 8},
    {"action_id": "ACT004", "action_name": "Complete Internship", "action_type": "Internship", "estimated_skill_gain": 15},
    {"action_id": "ACT005", "action_name": "Practice DSA", "action_type": "DSA Practice", "estimated_skill_gain": 7},
    {"action_id": "ACT006", "action_name": "Attend Mock Interview", "action_type": "Mock Interviews", "estimated_skill_gain": 6},
    {"action_id": "ACT007", "action_name": "Read Research Paper", "action_type": "Research Papers", "estimated_skill_gain": 5},
]


class GoalPlanner:
    def __init__(self, action_catalog_service: ActionCatalogService | None = None, memory_manager: object | None = None) -> None:
        self.action_catalog_service = action_catalog_service or ActionCatalogService()
        self.memory_manager = memory_manager
        self.context_builder = ContextBuilder(memory_manager=self.memory_manager) if self.memory_manager is not None else None
        if not self.action_catalog_service.list_actions():
            for action in DEFAULT_ACTIONS:
                self.action_catalog_service.actions.append(
                    ActionCatalog(
                        action_id=action["action_id"],
                        action_name=action["action_name"],
                        action_type=action["action_type"],
                    )
                )
        self.transition_engine = TransitionEngine(experiences=experience_service.get_all_experiences())
        self.action_ranker = ActionRanker()

    def create_plan(self, current_state: Dict[str, int], goal_state: GoalState) -> Dict:
        planning_context = None
        if self.context_builder is not None:
            planning_context = self.context_builder.build(goal_state.goal, current_state)
        recommended_actions = []
        for skill, goal_value in goal_state.target_skills.items():
            current_value = current_state.get(skill, 0)
            gap = max(0, goal_value - current_value)
            if gap <= 0:
                continue
            action_candidates = self._find_actions_for_skill(skill)
            if not action_candidates:
                continue
            ranked_actions = self._rank_actions(action_candidates, current_state, skill)
            for action in ranked_actions:
                if action["name"] not in recommended_actions:
                    recommended_actions.append(action["name"])
            if len(recommended_actions) >= 3:
                break

        estimated_steps = max(1, len(recommended_actions))
        success_probability = self._estimate_success_probability(current_state, goal_state, recommended_actions)
        result = {
            "goal": goal_state.goal,
            "recommended_actions": recommended_actions[:3],
            "estimated_steps": estimated_steps,
            "success_probability": round(success_probability, 2),
        }
        if planning_context is not None:
            result["planning_context"] = planning_context.to_dict()
        return result

    def recommend_next_action(self, current_state: Dict[str, int], goal_state: GoalState) -> str | None:
        plan = self.create_plan(current_state, goal_state)
        return plan["recommended_actions"][0] if plan["recommended_actions"] else None

    def estimate_steps_to_goal(self, current_state: Dict[str, int], goal_state: GoalState) -> int:
        plan = self.create_plan(current_state, goal_state)
        return plan["estimated_steps"]

    def _find_actions_for_skill(self, skill: str) -> List[Dict]:
        actions = []
        skill_name = skill.lower()
        for action in self.action_catalog_service.list_actions():
            action_name = action.action_name.lower()
            if skill_name in action_name or action.action_type.lower() == "project" and skill_name in {"python", "ml"}:
                actions.append({"name": action.action_name, "estimated_gain": getattr(action, "estimated_skill_gain", 0)})
        if not actions:
            for action in self.action_catalog_service.list_actions():
                actions.append({"name": action.action_name, "estimated_gain": getattr(action, "estimated_skill_gain", 0)})
        return actions

    def _rank_actions(self, candidate_actions: List[Dict], current_state: Dict[str, int], skill: str) -> List[Dict]:
        ranked = []
        for action in candidate_actions:
            gain = max(action.get("estimated_gain", 0), self.transition_engine.predict_skill_growth(current_state, action["name"]).get(skill, 0))
            success_probability = self.transition_engine.predict_success_probability(current_state, action["name"])
            confidence = 0.7
            ranked.append(
                {
                    "name": action["name"],
                    "expected_growth": gain,
                    "success_probability": success_probability,
                    "confidence": confidence,
                    "growth": gain,
                }
            )
        ranked_actions = self.action_ranker.rank_actions(ranked, current_state, self.transition_engine)
        return [{"name": action["name"], "score": action["score"], "growth": action["growth"]} for action in ranked_actions]

    def _estimate_success_probability(self, current_state: Dict[str, int], goal_state: GoalState, recommended_actions: List[str]) -> float:
        if not recommended_actions:
            return 0.0
        base = 0.5 + (len(recommended_actions) * 0.08)
        return min(1.0, base)


goal_planner = GoalPlanner()
