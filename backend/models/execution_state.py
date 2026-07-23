from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionState:
    execution_id: str = ""
    plan_name: str = ""
    goal_name: str = ""
    status: str = "NOT_STARTED"
    current_step: int = 0
    total_steps: int = 0
    completed_actions: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    skipped_actions: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_name": self.plan_name,
            "goal_name": self.goal_name,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_actions": self.completed_actions,
            "pending_actions": self.pending_actions,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "progress": round(self.progress, 2),
            "confidence": round(self.confidence, 2),
        }

    def mark_updated(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()
