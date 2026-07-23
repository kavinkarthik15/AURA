from typing import Dict, List

from backend.models.experience_log import ExperienceLog


class ContinualDatasetBuilder:
    def build_samples(self, experiences: List[ExperienceLog]) -> List[Dict]:
        samples = []
        for experience in experiences:
            next_action = experience.actions[0] if experience.actions else ""
            samples.append({
                "current_state": dict(experience.initial_state),
                "action_history": list(experience.completed_actions),
                "next_action": next_action,
                "target_delta": {
                    key: experience.actual_state.get(key, 0) - experience.initial_state.get(key, 0)
                    for key in set(experience.initial_state.keys()) | set(experience.actual_state.keys())
                },
            })
        return samples
