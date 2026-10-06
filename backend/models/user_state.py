from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class UserState(BaseModel):
    skills: Dict[str, int]
    knowledge: Dict[str, int]
    projects: Dict[str, int]
    goals: Dict[str, int]
    learning: Dict[str, int]

    def clone(
        self,
        *,
        simulation_id: Optional[str] = None,
        step: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        snapshot_id: Optional[str] = None,
        parent_snapshot_id: Optional[str] = None,
    ) -> "SimulatedState":
        from backend.models.simulated_state import SimulatedState

        return SimulatedState(
            skills=dict(self.skills),
            knowledge=dict(self.knowledge),
            projects=dict(self.projects),
            goals=dict(self.goals),
            learning=dict(self.learning),
            source_state_id=None,
            simulation_id=simulation_id,
            step=step,
            parent_snapshot_id=parent_snapshot_id,
            snapshot_id=snapshot_id,
            metadata=dict(metadata or {}),
        )
