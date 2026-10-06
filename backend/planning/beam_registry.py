from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.planning.beam_node import BeamNode


@dataclass
class BeamTree:
    root: BeamNode
    active_nodes: List[BeamNode] = field(default_factory=list)
    completed_nodes: List[BeamNode] = field(default_factory=list)
    beam_width: int = 3
    max_depth: int = 3

    def __post_init__(self):
        self.active_nodes = [self.root]

    def add_active(self, node: BeamNode) -> None:
        if node not in self.active_nodes:
            self.active_nodes.append(node)

    def mark_completed(self, node: BeamNode) -> None:
        if node in self.active_nodes:
            self.active_nodes.remove(node)
        if node not in self.completed_nodes:
            self.completed_nodes.append(node)
