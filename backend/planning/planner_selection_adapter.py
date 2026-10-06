from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.planning.planning_context import PlanningContext
from backend.planning.trajectory_tree_evaluator import TrajectorySelectionResult


@dataclass
class PlannerSelectionAdapter:
    enabled: bool = False
    fallback_action: Optional[str] = None
    fallback_metadata: Dict[str, Any] = field(default_factory=dict)

    def adapt(self, selection_result: Optional[TrajectorySelectionResult], context: Optional[PlanningContext] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "enabled": False,
                "action": self.fallback_action,
                "metadata": dict(self.fallback_metadata),
                "selection_result": None,
                "planning_context": context,
            }

        if selection_result is None or selection_result.best_trajectory is None:
            return {
                "enabled": True,
                "action": self.fallback_action,
                "metadata": {
                    **dict(self.fallback_metadata),
                    "selection_reason": getattr(selection_result, "selection_reason", "no_trajectory"),
                    "trajectory_score": 0.0,
                    "branch_probability": 0.0,
                    "risk": 0.0,
                    "uncertainty": 0.0,
                },
                "selection_result": selection_result,
                "planning_context": context,
            }

        first_action = None
        for node in selection_result.best_trajectory.path:
            if getattr(node, "action", None) is not None:
                first_action = getattr(node, "action", None)
                break

        if first_action is None:
            first_action = self.fallback_action

        return {
            "enabled": True,
            "action": first_action,
            "metadata": {
                **dict(self.fallback_metadata),
                "trajectory_score": float(selection_result.trajectory_score),
                "branch_probability": float(selection_result.branch_probability),
                "risk": float(selection_result.risk),
                "uncertainty": float(selection_result.uncertainty),
                "selection_reason": selection_result.selection_reason,
                "top_k": int(selection_result.top_k),
                "planning_context": context,
            },
            "selection_result": selection_result,
            "planning_context": context,
        }
