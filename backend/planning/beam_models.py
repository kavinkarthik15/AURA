from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class BeamEvaluation:
    accumulated_reward: float = 0.0
    accumulated_cost: float = 0.0
    accumulated_risk: float = 0.0
    accumulated_utility: float = 0.0
    accumulated_goal_alignment: Dict[str, float] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    decisions: List[Any] = field(default_factory=list)
    predicted_final_state: Dict[str, float] = field(default_factory=dict)
    total_utility: float = 0.0
    total_cost: float = 0.0
    total_risk: float = 0.0
    goal_alignment: Dict[str, float] = field(default_factory=dict)
    reasoning_trace: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: Dict[str, List[str]] = field(default_factory=dict)
