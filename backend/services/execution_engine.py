from datetime import datetime
from typing import Dict, List

from backend.models.execution_state import ExecutionState
from backend.services.execution_tracker import ExecutionTracker

class ExecutionEngine:
    def __init__(self, tracker: ExecutionTracker | None = None) -> None:
        self.tracker = tracker or ExecutionTracker()
        self.execution_state: ExecutionState | None = None

    def start_execution(self, plan_name: str, goal_name: str, actions: List[str], confidence: float = 0.0) -> ExecutionState:
        self.execution_state = ExecutionState(
            execution_id=self._build_execution_id(),
            plan_name=plan_name,
            goal_name=goal_name,
            status="RUNNING",
            current_step=1,
            total_steps=len(actions),
            pending_actions=list(actions),
            started_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            confidence=confidence,
        )
        self.execution_state.mark_updated()
        self.tracker.record_event(actions[0] if actions else "", "started", 1)
        return self.execution_state

    def complete_current_action(self) -> ExecutionState:
        if not self.execution_state:
            raise ValueError("No execution started")
        current_action = self._current_action()
        if current_action:
            self.execution_state.completed_actions.append(current_action)
            self.execution_state.pending_actions.remove(current_action)
            self.tracker.record_event(current_action, "completed", self.execution_state.current_step)
            self._advance_step()
        self._refresh_progress()
        self.execution_state.mark_updated()
        return self.execution_state

    def skip_current_action(self) -> ExecutionState:
        if not self.execution_state:
            raise ValueError("No execution started")
        current_action = self._current_action()
        if current_action:
            self.execution_state.skipped_actions.append(current_action)
            self.execution_state.pending_actions.remove(current_action)
            self.tracker.record_event(current_action, "skipped", self.execution_state.current_step)
            self._advance_step()
        self._refresh_progress()
        self.execution_state.mark_updated()
        return self.execution_state

    def fail_current_action(self) -> ExecutionState:
        if not self.execution_state:
            raise ValueError("No execution started")
        current_action = self._current_action()
        if current_action:
            self.execution_state.failed_actions.append(current_action)
            self.execution_state.pending_actions.remove(current_action)
            self.tracker.record_event(current_action, "failed", self.execution_state.current_step)
            self._advance_step()
        self._refresh_progress()
        self.execution_state.mark_updated()
        return self.execution_state

    def next_action(self) -> str | None:
        if not self.execution_state:
            return None
        if self.execution_state.pending_actions:
            return self.execution_state.pending_actions[0]
        return None

    def finish_execution(self) -> ExecutionState:
        if not self.execution_state:
            raise ValueError("No execution started")
        if self.execution_state.pending_actions:
            self.execution_state.pending_actions = []
        self.execution_state.status = "COMPLETED"
        self.execution_state.current_step = max(self.execution_state.current_step, self.execution_state.total_steps)
        self.execution_state.progress = 1.0
        self.execution_state.completed_at = datetime.utcnow().isoformat()
        self.execution_state.mark_updated()
        self.tracker.record_event("", "finished", self.execution_state.current_step)
        return self.execution_state

    def get_execution(self) -> ExecutionState | None:
        return self.execution_state

    def _build_execution_id(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"exec_{timestamp}_001"

    def _current_action(self) -> str | None:
        if not self.execution_state:
            return None
        return self.execution_state.pending_actions[0] if self.execution_state.pending_actions else None

    def _advance_step(self) -> None:
        if not self.execution_state:
            return
        if self.execution_state.pending_actions:
            self.execution_state.current_step = min(self.execution_state.current_step + 1, self.execution_state.total_steps)
        else:
            self.execution_state.current_step = self.execution_state.total_steps

    def _refresh_progress(self) -> None:
        if not self.execution_state:
            return
        total = max(1, self.execution_state.total_steps)
        completed = len(self.execution_state.completed_actions)
        self.execution_state.progress = round(completed / total, 2)
        if self.execution_state.progress >= 1.0:
            self.execution_state.status = "COMPLETED"
