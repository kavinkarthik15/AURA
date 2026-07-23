from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.services.action_library import action_library


class PlanExpander:
    def __init__(self, action_library_instance=None) -> None:
        self.action_library = action_library_instance or action_library

    def get_possible_next_actions(self, current_state: Dict[str, int], goal_state: GoalState) -> List[str]:
        relevant_actions = self.action_library.find_actions_for_goal(goal_state)
        return [action.get("name") for action in relevant_actions if action.get("name")]
