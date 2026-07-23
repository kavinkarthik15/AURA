import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.experience_log import ExperienceLog


class ExperienceLogger:
    def __init__(self, dataset_path: Path | None = None) -> None:
        self.dataset_path = dataset_path or Path(__file__).resolve().parents[1] / "data" / "experience_dataset.json"
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        self._experiences: List[Dict] = self.load()

    def log_experience(self, execution_id: str, plan_name: str, goal_name: str, initial_state: Dict, predicted_state: Dict, actual_state: Dict, actions: List[str], completed_actions: List[str], failed_actions: List[str], skipped_actions: List[str], execution_time: float, success: bool, confidence: float = 0.0, experience_version: str = "v1", model_version: str = "v2", planner_version: str = "beam_search_v1", objective_profile: str = "balanced_learning", dataset_version: str = "v1") -> ExperienceLog:
        experience = ExperienceLog(
            experience_id=self._next_experience_id(),
            execution_id=execution_id,
            plan_name=plan_name,
            goal_name=goal_name,
            initial_state=initial_state,
            predicted_state=predicted_state,
            actual_state=actual_state,
            predicted_growth={key: value - initial_state.get(key, 0) for key, value in predicted_state.items()},
            actual_growth={key: value - initial_state.get(key, 0) for key, value in actual_state.items()},
            prediction_error=self._calculate_prediction_error(predicted_state, actual_state),
            actions=actions,
            completed_actions=completed_actions,
            failed_actions=failed_actions,
            skipped_actions=skipped_actions,
            execution_time=execution_time,
            success=success,
            created_at=datetime.utcnow().isoformat(),
            experience_version=experience_version,
            model_version=model_version,
            planner_version=planner_version,
            objective_profile=objective_profile,
            dataset_version=dataset_version,
        )
        self._experiences.append(experience.to_dict())
        self.save()
        return experience

    def save(self) -> None:
        with self.dataset_path.open("w", encoding="utf-8") as handle:
            json.dump(self._experiences, handle, indent=2)

    def load(self) -> List[Dict]:
        if not self.dataset_path.exists():
            return []
        with self.dataset_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []

    def get_experience(self, experience_id: str) -> Optional[Dict]:
        for experience in self._experiences:
            if experience.get("experience_id") == experience_id:
                return experience
        return None

    def list_experiences(self) -> List[Dict]:
        return list(self._experiences)

    def _next_experience_id(self) -> str:
        count = len(self._experiences) + 1
        return f"exp_{count:04d}"

    def _calculate_prediction_error(self, predicted_state: Dict, actual_state: Dict) -> float:
        keys = set(predicted_state.keys()) | set(actual_state.keys())
        if not keys:
            return 0.0
        errors = []
        for key in keys:
            predicted_value = predicted_state.get(key, 0)
            actual_value = actual_state.get(key, 0)
            errors.append(abs(predicted_value - actual_value))
        return round(sum(errors) / len(errors), 2)
