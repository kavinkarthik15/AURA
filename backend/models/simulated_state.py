from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from pydantic import Field

from backend.models.user_state import UserState


class SimulatedState(UserState):
    source_state_id: Optional[str] = None
    simulation_id: Optional[str] = None
    step: int = 0
    parent_snapshot_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def branch(self, *, simulation_id: Optional[str] = None, step: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> "SimulatedState":
        return SimulatedState(
            skills=deepcopy(self.skills),
            knowledge=deepcopy(self.knowledge),
            projects=deepcopy(self.projects),
            goals=deepcopy(self.goals),
            learning=deepcopy(self.learning),
            source_state_id=self.snapshot_id or self.source_state_id,
            simulation_id=simulation_id or self.simulation_id,
            step=self.step if step is None else step,
            parent_snapshot_id=self.snapshot_id,
            snapshot_id=None,
            metadata=dict(self.metadata, **(metadata or {})),
        )

    def advance(self, *, step: int | None = None, metadata: Optional[Dict[str, Any]] = None) -> "SimulatedState":
        return SimulatedState(
            skills=deepcopy(self.skills),
            knowledge=deepcopy(self.knowledge),
            projects=deepcopy(self.projects),
            goals=deepcopy(self.goals),
            learning=deepcopy(self.learning),
            source_state_id=self.snapshot_id or self.source_state_id,
            simulation_id=self.simulation_id,
            step=self.step + 1 if step is None else step,
            parent_snapshot_id=self.snapshot_id,
            snapshot_id=None,
            metadata=dict(self.metadata, **(metadata or {})),
        )
