from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ExperienceLog:
    experience_id: str = ""
    execution_id: str = ""
    plan_name: str = ""
    goal_name: str = ""
    initial_state: Dict[str, Any] = field(default_factory=dict)
    predicted_state: Dict[str, Any] = field(default_factory=dict)
    actual_state: Dict[str, Any] = field(default_factory=dict)
    predicted_growth: Dict[str, Any] = field(default_factory=dict)
    actual_growth: Dict[str, Any] = field(default_factory=dict)
    prediction_error: float = 0.0
    actions: List[str] = field(default_factory=list)
    completed_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    skipped_actions: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    success: bool = False
    created_at: Optional[str] = None
    experience_version: str = "v1"
    model_version: str = "v2"
    planner_version: str = "beam_search_v1"
    objective_profile: str = "balanced_learning"
    dataset_version: str = "v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "execution_id": self.execution_id,
            "plan_name": self.plan_name,
            "goal_name": self.goal_name,
            "initial_state": self.initial_state,
            "predicted_state": self.predicted_state,
            "actual_state": self.actual_state,
            "predicted_growth": self.predicted_growth,
            "actual_growth": self.actual_growth,
            "prediction_error": round(self.prediction_error, 2),
            "actions": self.actions,
            "completed_actions": self.completed_actions,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "execution_time": round(self.execution_time, 2),
            "success": self.success,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "experience_version": self.experience_version,
            "model_version": self.model_version,
            "planner_version": self.planner_version,
            "objective_profile": self.objective_profile,
            "dataset_version": self.dataset_version,
        }
