from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from backend.config.policy_config import POLICY_ENTROPY_EXPLORE_THRESHOLD, POLICY_SMOOTHING, POLICY_VERSION

@dataclass
class PolicySample:
    state: Dict[str, float]
    goal: str
    action: str
    action_history: List[str] = field(default_factory=list)
    success: bool = False
    weight: float = 1.0


@dataclass
class PolicyPrediction:
    action: str
    probability: float
    support_count: int
    confidence: float
    source: str = "planning_policy"

    @property
    def evidence_count(self) -> int:
        return self.support_count


class PlanningPolicy:
    """Empirical policy estimating P(action | state, goal) from execution outcomes."""

    def __init__(self, smoothing: float = POLICY_SMOOTHING) -> None:
        self.smoothing = smoothing
        self.policy_version = POLICY_VERSION
        self.training_date = None
        self.action_scores: Dict[str, float] = {}
        self.context_scores: Dict[str, Dict[str, float]] = {}
        self.action_counts: Dict[str, int] = {}
        self.support_counts: Dict[str, int] = {}
        self.trained_samples = 0

    def _context_key(self, goal: str, state: Dict[str, float]) -> str:
        state_key = ",".join(f"{key}={state[key]}" for key in sorted(state))
        return f"{goal.strip().lower()}|{state_key}"

    def fit(self, samples: Sequence[PolicySample]) -> "PlanningPolicy":
        self.action_scores = {}
        self.context_scores = {}
        self.action_counts = {}
        self.support_counts = {}
        self.trained_samples = len(samples)
        for sample in samples:
            if not sample.action:
                continue
            outcome_weight = max(0.1, sample.weight) * (1.0 if sample.success else 0.25)
            self.action_scores[sample.action] = self.action_scores.get(sample.action, 0.0) + outcome_weight
            self.action_counts[sample.action] = self.action_counts.get(sample.action, 0) + 1
            if sample.success:
                self.support_counts[sample.action] = self.support_counts.get(sample.action, 0) + 1
            context = self._context_key(sample.goal, sample.state)
            context_scores = self.context_scores.setdefault(context, {})
            context_scores[sample.action] = context_scores.get(sample.action, 0.0) + outcome_weight
        return self

    def predict(self, state: Dict[str, float], goal: str, actions: Sequence[str]) -> List[PolicyPrediction]:
        if not actions:
            return []
        context_scores = self.context_scores.get(self._context_key(goal, state), {})
        total = sum(context_scores.get(action, self.action_scores.get(action, 0.0)) + self.smoothing for action in actions)
        predictions = []
        for action in actions:
            score = context_scores.get(action, self.action_scores.get(action, 0.0)) + self.smoothing
            predictions.append(PolicyPrediction(
                action=action,
                probability=score / total if total else 1.0 / len(actions),
                support_count=self.support_counts.get(action, 0),
                confidence=self._confidence(self.support_counts.get(action, 0)),
            ))
        return sorted(predictions, key=lambda item: item.probability, reverse=True)

    def _confidence(self, support_count: int) -> float:
        return round(support_count / (support_count + 2.0), 4) if support_count else 0.0

    def entropy(self, state: Dict[str, float], goal: str, actions: Sequence[str]) -> float:
        predictions = self.predict(state, goal, actions)
        if not predictions:
            return 0.0
        return round(-sum(item.probability * math.log(item.probability) for item in predictions if item.probability > 0), 4)

    def normalized_entropy(self, state: Dict[str, float], goal: str, actions: Sequence[str]) -> float:
        predictions = self.predict(state, goal, actions)
        if len(predictions) <= 1:
            return 0.0
        return round(self.entropy(state, goal, actions) / math.log(len(predictions)), 4)

    def exploration_mode(self, state: Dict[str, float], goal: str, actions: Sequence[str], threshold: float = POLICY_ENTROPY_EXPLORE_THRESHOLD) -> str:
        return "explore" if self.normalized_entropy(state, goal, actions) >= threshold else "exploit"

    def explain_actions(self, state: Dict[str, float], goal: str, actions: Sequence[str]) -> List[Dict]:
        predictions = self.predict(state, goal, actions)
        entropy = self.normalized_entropy(state, goal, actions)
        return [
            {
                "action": item.action,
                "probability": item.probability,
                "support": item.support_count,
                "confidence": item.confidence,
                "policy_entropy": entropy,
                "reason": f"Highest historical support for {goal} goals." if item == predictions[0] else f"Historical support for {goal} goals is below the leading action.",
            }
            for item in predictions
        ]

    def score(self, state: Dict[str, float], goal: str, action: str) -> float:
        predictions = self.predict(state, goal, [action])
        return predictions[0].probability if predictions else 0.0

    def to_dict(self) -> Dict:
        return {
            "smoothing": self.smoothing,
            "policy_version": self.policy_version,
            "training_date": self.training_date,
            "action_scores": self.action_scores,
            "context_scores": self.context_scores,
            "action_counts": self.action_counts,
            "support_counts": self.support_counts,
            "trained_samples": self.trained_samples,
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "PlanningPolicy":
        policy = cls(smoothing=float(payload.get("smoothing", POLICY_SMOOTHING)))
        policy.policy_version = payload.get("policy_version", POLICY_VERSION)
        policy.training_date = payload.get("training_date")
        policy.action_scores = dict(payload.get("action_scores", {}))
        policy.context_scores = {key: dict(value) for key, value in payload.get("context_scores", {}).items()}
        policy.action_counts = {key: int(value) for key, value in payload.get("action_counts", {}).items()}
        policy.support_counts = {key: int(value) for key, value in payload.get("support_counts", {}).items()}
        policy.trained_samples = int(payload.get("trained_samples", 0))
        return policy
