from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.services.action_library import action_library


class PlanSearch:
    def __init__(self, action_library_instance=None) -> None:
        self.action_library = action_library_instance or action_library

    def recommend_goal_plan(self, current_state: Dict[str, int], goal_state: GoalState) -> List[Dict]:
        candidate_actions = self.action_library.find_actions_for_goal(goal_state)
        if not candidate_actions:
            return []

        plans = []
        for index, action in enumerate(candidate_actions[:5], start=1):
            plan_name = f"Plan {chr(64 + index)}"
            supporting_actions = self._supporting_actions(action, goal_state)
            if len(supporting_actions) < 1:
                supporting_actions = ["Practice DSA"]
            plans.append(
                {
                    "name": plan_name,
                    "actions": [action["name"], *supporting_actions[:2]],
                }
            )

        if len(plans) < 5:
            fallback_actions = [
                {"name": "Complete Python Project"},
                {"name": "Participate in Hackathon"},
                {"name": "Complete DSA Course"},
                {"name": "Complete Internship"},
                {"name": "Practice DSA"},
            ]
            for entry in fallback_actions:
                if any(plan["actions"][0] == entry["name"] for plan in plans):
                    continue
                plans.append({"name": f"Plan {chr(64 + len(plans) + 1)}", "actions": [entry["name"], "Practice DSA"]})
                if len(plans) >= 5:
                    break

        return plans[:5]

    def _supporting_actions(self, anchor_action: Dict, goal_state: GoalState) -> List[str]:
        supporting = []
        target_skills = set(goal_state.target_skills.keys()) if hasattr(goal_state, "target_skills") else set()
        for action in self.action_library.list_actions():
            if action["name"] == anchor_action["name"]:
                continue
            action_skills = set(action.get("skills", [])) if "skills" in action else set()
            if target_skills & action_skills:
                supporting.append(action["name"])
            if len(supporting) >= 2:
                break
        return supporting


plan_search = PlanSearch()
