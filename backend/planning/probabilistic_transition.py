from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProbabilisticTransition:
    current_state: Dict[str, Any] = field(default_factory=dict)
    action: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    possible_states: List[Dict[str, Any]] = field(default_factory=list)
    probabilities: List[float] = field(default_factory=list)
    expected_state: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.expected_state and self.possible_states:
            self.expected_state = self._compute_expected_state()
        if not self.probabilities and self.possible_states:
            self.probabilities = [1.0 / max(1, len(self.possible_states)) for _ in self.possible_states]
        self.confidence = float(self.confidence or 0.0)

    def _compute_expected_state(self) -> Dict[str, Any]:
        if not self.possible_states or not self.probabilities:
            return dict(self.current_state)
        expected: Dict[str, Any] = {}
        keys = sorted({key for state in self.possible_states for key in state.keys()})
        for key in keys:
            total = 0.0
            for state, probability in zip(self.possible_states, self.probabilities):
                total += float(state.get(key, 0) or 0) * float(probability)
            expected[key] = round(total, 4)
        return expected


@dataclass
class ProbabilisticTransitionModel:
    default_probabilities: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_probabilities is None:
            self.default_probabilities = [0.7, 0.2, 0.1]

    def predict(self, current_state: Dict[str, Any], action: Any, context: Optional[Dict[str, Any]] = None) -> ProbabilisticTransition:
        current = dict(current_state or {})
        action_name = str(action)
        context_map = dict(context or {})

        base = self._base_distribution(current, action_name)
        possible_states = [
            {**current, **{key: float(value) for key, value in state.items()}} for state in base["states"]
        ]
        probs = list(base["probabilities"])

        expected_state = {
            key: round(sum(state.get(key, 0) * prob for state, prob in zip(possible_states, probs)), 4)
            for key in sorted({key for state in possible_states for key in state.keys()})
        }

        evidence = list(context_map.get("supporting_evidence", [])) if isinstance(context_map, dict) else []
        evidence.append(f"Probabilistic transition for '{action_name}'")

        return ProbabilisticTransition(
            current_state=current,
            action=action_name,
            context=context_map,
            possible_states=possible_states,
            probabilities=probs,
            expected_state=expected_state,
            confidence=float(context_map.get("confidence", 0.7)),
            evidence=evidence,
        )

    def _base_distribution(self, current_state: Dict[str, Any], action: str) -> Dict[str, Any]:
        normalized = action.lower()
        states = []
        if "python" in normalized:
            states = [
                {"python": current_state.get("python", 0) + 3, "confidence": 0.65},
                {"python": current_state.get("python", 0) + 1, "confidence": 0.55},
                {"python": current_state.get("python", 0), "confidence": 0.50},
            ]
            probs = [0.7, 0.2, 0.1]
        elif "dsa" in normalized:
            states = [
                {"dsa": current_state.get("dsa", 0) + 2, "confidence": 0.6},
                {"dsa": current_state.get("dsa", 0) + 1, "confidence": 0.5},
                {"dsa": current_state.get("dsa", 0), "confidence": 0.45},
            ]
            probs = [0.65, 0.25, 0.1]
        else:
            states = [
                {"confidence": 0.6},
                {"confidence": 0.5},
                {"confidence": 0.4},
            ]
            probs = [0.6, 0.3, 0.1]

        if len(states) != len(probs):
            probs = [1.0 / max(1, len(states)) for _ in states]
        return {"states": states, "probabilities": probs}
