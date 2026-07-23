from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.services.goal_planner import GoalPlanner


class PlanGenerator:
    def __init__(self, goal_planner: GoalPlanner | None = None) -> None:
        self.goal_planner = goal_planner or GoalPlanner()

    def generate_candidate_plans(self, current_state: Dict[str, int], goal_state: GoalState) -> List[Dict]:
        ranked_actions = self.goal_planner.create_plan(current_state, goal_state)["recommended_actions"]
        if not ranked_actions:
            return []

        base_actions = list(ranked_actions)
        return [
            {"name": "Plan A", "actions": [base_actions[0], "Practice DSA", "Participate in Hackathon"]},
            {"name": "Plan B", "actions": ["Complete DSA Course", "Complete Internship", "Attend Mock Interview"]},
            {"name": "Plan C", "actions": ["Read Research Paper", base_actions[0], "Complete Python Project"]},
        ]


plan_generator = PlanGenerator()
