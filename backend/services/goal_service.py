from typing import Dict

from backend.models.goal_state import GoalState


def estimate_goal_progress(current_state: Dict[str, int], target_state: GoalState) -> float:
    if not target_state.target_skills:
        return 0.0

    progress_values = []
    for skill, target_value in target_state.target_skills.items():
        current_value = current_state.get(skill, 0)
        if target_value <= 0:
            continue
        progress_values.append(min(1.0, current_value / target_value))

    if not progress_values:
        return 0.0

    progress = sum(progress_values) / len(progress_values)
    if all(value >= 0.5 for value in progress_values):
        progress += 0.02
    return round(min(1.0, progress), 2)
