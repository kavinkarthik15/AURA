from __future__ import annotations

from typing import Any, Dict, List


class ReasoningGraphBuilder:
    def __init__(self) -> None:
        self.version = "reasoning_graph_v1"

    def build(self, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        nodes = []
        edges = []
        for index, experience in enumerate(experiences):
            node_id = f"exp_{index}"
            nodes.append({"id": node_id, "goal": experience.get("goal_name"), "actions": experience.get("actions", [])})
            if index > 0:
                edges.append({"from": f"exp_{index - 1}", "to": node_id, "type": "sequential"})
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
