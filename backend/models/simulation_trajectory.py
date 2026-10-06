from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.simulated_state import SimulatedState


@dataclass
class BranchInfo:
    next_snapshot: SimulatedState
    probability: float
    diff: Dict[str, Any]
    evidence: List[Any] = field(default_factory=list)


@dataclass
class SimulationTrajectory:
    initial_snapshot: SimulatedState
    actions: List[str] = field(default_factory=list)
    snapshots: List[SimulatedState] = field(default_factory=list)
    diffs: List[Dict[str, Any]] = field(default_factory=list)
    branch_info: List[Optional[List[BranchInfo]]] = field(default_factory=list)
    cumulative_probability: Optional[float] = 1.0

    def __post_init__(self) -> None:
        if not self.snapshots:
            self.cumulative_probability = 1.0

    @property
    def final_snapshot(self) -> SimulatedState:
        if self.snapshots:
            return self.snapshots[-1]
        return self.initial_snapshot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_snapshot_id": getattr(self.initial_snapshot, "snapshot_id", None),
            "actions": list(self.actions),
            "snapshot_ids": [getattr(s, "snapshot_id", None) for s in self.snapshots],
            "diffs": list(self.diffs),
            "cumulative_probability": self.cumulative_probability,
        }
