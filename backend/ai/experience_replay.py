import random
from typing import Dict, List

from backend.models.experience_log import ExperienceLog


class ExperienceReplayBuffer:
    def __init__(self, experiences: List[ExperienceLog] | None = None) -> None:
        self.experiences = list(experiences or [])

    def load_experiences(self, experiences: List[ExperienceLog]) -> None:
        self.experiences = list(experiences)

    def filter_valid(self) -> List[ExperienceLog]:
        valid = []
        seen = set()
        for experience in self.experiences:
            key = (experience.execution_id, experience.experience_id)
            if key in seen:
                continue
            seen.add(key)
            if not experience.execution_id:
                continue
            valid.append(experience)
        return valid

    def prioritize_successful(self, experiences: List[ExperienceLog]) -> List[ExperienceLog]:
        return sorted(experiences, key=lambda item: (0 if getattr(item, "success", False) else 1, item.prediction_error), reverse=False)

    def sample(self, batch_size: int, shuffle: bool = True) -> List[ExperienceLog]:
        filtered = self.filter_valid()
        prioritized = self.prioritize_successful(filtered)
        if shuffle:
            randomized = list(prioritized)
            random.shuffle(randomized)
            prioritized = randomized
        return prioritized[:batch_size]

    def sample_incremental(self, batch_size: int, start_index: int = 0, shuffle: bool = True) -> List[ExperienceLog]:
        filtered = self.filter_valid()
        prioritized = self.prioritize_successful(filtered)
        if shuffle:
            randomized = list(prioritized)
            random.shuffle(randomized)
            prioritized = randomized
        return prioritized[start_index:start_index + batch_size]

    def get_statistics(self) -> Dict[str, int | float]:
        valid = self.filter_valid()
        successful = sum(1 for item in valid if getattr(item, "success", False))
        failed = len(valid) - successful
        sampled = len(valid)
        average_goal_progress = 0.0
        if valid:
            average_goal_progress = sum(float(getattr(item, "prediction_error", 0.0)) for item in valid) / len(valid)
        return {
            "total_experiences": len(self.experiences),
            "duplicates_removed": len(self.experiences) - len(valid),
            "successful": successful,
            "failed": failed,
            "sampled": sampled,
            "average_goal_progress": round(average_goal_progress, 4),
        }
