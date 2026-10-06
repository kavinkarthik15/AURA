from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.ai.decision_reasoner import DecisionCandidate
from typing import Any
from backend.models.simulated_state import SimulatedState


@dataclass
class BeamNode:
    node_id: str = field(default_factory=lambda: f"BN-{uuid4().hex[:12].upper()}")
    depth: int = 0
    parent: Optional["BeamNode"] = None
    decision: Optional[DecisionCandidate] = None
    current_state: Dict[str, float] = field(default_factory=dict)
    predicted_state: Dict[str, float] = field(default_factory=dict)
    goal_alignment: Dict[str, float] = field(default_factory=dict)
    accumulated_reward: float = 0.0
    accumulated_cost: float = 0.0
    accumulated_risk: float = 0.0
    accumulated_utility: float = 0.0
    decision_history: List[str] = field(default_factory=list)
    reasoning_trace: List[Dict[str, Any]] = field(default_factory=list)
    children: List["BeamNode"] = field(default_factory=list)
    expanded: bool = False
    probabilistic_transition: Optional["ProbabilisticTransition"] = None
    state_diff: Dict[str, Any] = field(default_factory=dict)
    branch_snapshot_id: Optional[str] = None
    branch_snapshot: Optional[SimulatedState] = None
    branch_probability: float = 1.0

    @classmethod
    def root(cls, current_state: Dict[str, float]) -> "BeamNode":
        return cls(node_id="ROOT", depth=0, parent=None, decision=None, current_state=dict(current_state), predicted_state=dict(current_state))

    def add_child(self, child: "BeamNode") -> None:
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)

    @classmethod
    def from_decision(cls, decision: DecisionCandidate, parent: Optional["BeamNode"]) -> "BeamNode":
        current = dict(parent.predicted_state if parent is not None else {})
        predicted = dict(decision.prediction.predicted_state or {})

        # merge predicted over current: if keys missing, keep current
        merged = dict(current)
        for k, v in predicted.items():
            try:
                merged[k] = float(v)
            except Exception:
                merged[k] = v

        node = cls(
            node_id=f"BN-{uuid4().hex[:12].upper()}",
            decision=decision,
            current_state=current,
            predicted_state=merged,
            goal_alignment=decision.goal_alignment or {},
            accumulated_reward=(parent.accumulated_reward if parent else 0.0) + float(decision.prediction.reward),
            accumulated_cost=(parent.accumulated_cost if parent else 0.0) + float(decision.prediction.cost),
            accumulated_risk=(parent.accumulated_risk if parent else 0.0) + float(decision.prediction.risk),
            accumulated_utility=(parent.accumulated_utility if parent else 0.0) + float(decision.prediction.utility),
            decision_history=(list(parent.decision_history) if parent else []) + [decision.decision_id],
            reasoning_trace=(list(parent.reasoning_trace) if parent else []) + [ {"decision_id": decision.decision_id, "reasoning": decision.evidence.reasoning} ],
        )
        return node
