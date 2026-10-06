from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import weakref

from backend.models.simulated_state import SimulatedState


@dataclass
class SimulationTrajectoryNode:
    snapshot: SimulatedState
    action_from_parent: Optional[str] = None
    diff_from_parent: Optional[Dict[str, Any]] = None
    probability_from_parent: float = 1.0
    children: List["SimulationTrajectoryNode"] = field(default_factory=list)
    # weak reference to avoid recursive serialization
    _parent_ref: Optional[weakref.ref] = field(default=None, repr=False)

    @property
    def parent(self) -> Optional["SimulationTrajectoryNode"]:
        if self._parent_ref is None:
            return None
        return self._parent_ref()

    @parent.setter
    def parent(self, value: Optional["SimulationTrajectoryNode"]) -> None:
        if value is None:
            self._parent_ref = None
        else:
            self._parent_ref = weakref.ref(value)

    def cumulative_probability(self) -> float:
        p = float(self.probability_from_parent or 0.0)
        node = self.parent
        while node is not None:
            p *= float(node.probability_from_parent or 1.0)
            node = node.parent
        return p


@dataclass
class SimulationTrajectoryTree:
    root: SimulationTrajectoryNode
    stopped_early: bool = False

    def leaves(self) -> List[SimulationTrajectoryNode]:
        return [n for n in self.traverse() if not n.children]

    def traverse(self) -> List[SimulationTrajectoryNode]:
        out: List[SimulationTrajectoryNode] = []
        stack: List[SimulationTrajectoryNode] = [self.root]
        while stack:
            node = stack.pop()
            out.append(node)
            # iterate children in insertion order
            for child in reversed(node.children):
                stack.append(child)
        return out
