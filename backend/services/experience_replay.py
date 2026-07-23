from datetime import datetime, timedelta
from typing import List

from backend.models.experience import Experience
from backend.services.experience_service import experience_service


class ExperienceReplayService:
    def __init__(self, experiences: List[Experience] | None = None) -> None:
        self.experiences = experiences or experience_service.get_all_experiences()

    def get_similar_experiences(self, action: str, limit: int = 5) -> List[Experience]:
        action_key = action.lower()
        matches = [experience for experience in self.experiences if action_key in experience.action.lower()]
        return sorted(matches, key=lambda item: item.timestamp, reverse=True)[:limit]

    def get_successful_experiences(self, limit: int = 5) -> List[Experience]:
        matches = [experience for experience in self.experiences if experience.outcome_value >= 0.5]
        return sorted(matches, key=lambda item: item.timestamp, reverse=True)[:limit]

    def get_failed_experiences(self, limit: int = 5) -> List[Experience]:
        matches = [experience for experience in self.experiences if experience.outcome_value < 0.5]
        return sorted(matches, key=lambda item: item.timestamp, reverse=True)[:limit]

    def get_recent_experiences(self, days: int = 30, limit: int = 5) -> List[Experience]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        matches = [experience for experience in self.experiences if experience.timestamp >= cutoff]
        return sorted(matches, key=lambda item: item.timestamp, reverse=True)[:limit]


experience_replay_service = ExperienceReplayService()
