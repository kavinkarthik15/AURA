from statistics import mean
from typing import List

from backend.models.experience import Experience


class AnalyticsService:
    def __init__(self, experiences: List[Experience] | None = None) -> None:
        self.experiences = experiences or []

    def get_skill_growth(self) -> dict:
        growth = {}
        for experience in self.experiences:
            for skill, delta in experience.state_delta.items():
                growth[skill] = growth.get(skill, 0) + delta
        return growth

    def get_most_effective_actions(self) -> List[tuple]:
        actions = {}
        for experience in self.experiences:
            actions[experience.action] = actions.get(experience.action, []) + [experience.outcome_value]
        return sorted(
            ((action, round(mean(values), 3)) for action, values in actions.items()),
            key=lambda item: item[1],
            reverse=True,
        )

    def get_average_outcome(self) -> float:
        if not self.experiences:
            return 0.0
        return round(mean(experience.outcome_value for experience in self.experiences), 3)

    def get_growth_history(self) -> List[dict]:
        history = []
        for experience in self.experiences:
            history.append(
                {
                    "experience_id": experience.experience_id,
                    "action": experience.action,
                    "state_delta": experience.state_delta,
                    "outcome_value": experience.outcome_value,
                }
            )
        return history
