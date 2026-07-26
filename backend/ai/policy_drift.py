from __future__ import annotations

import math
from typing import Dict, Iterable, List

from backend.ai.planning_policy import PlanningPolicy


class PolicyDriftDetector:
    def compare(
        self,
        previous: PlanningPolicy,
        current: PlanningPolicy,
        actions: Iterable[str] | None = None,
        threshold: float = 0.1,
    ) -> Dict:
        action_list: List[str] = list(actions or set(previous.action_scores) | set(current.action_scores))
        if not action_list:
            return {"kl_divergence": 0.0, "total_variation": 0.0, "threshold": threshold, "significant": False, "retraining_recommended": False}
        previous_distribution = self._distribution(previous, action_list)
        current_distribution = self._distribution(current, action_list)
        kl_divergence = sum(
            current_probability * math.log(current_probability / previous_probability)
            for current_probability, previous_probability in zip(current_distribution, previous_distribution)
            if current_probability > 0
        )
        total_variation = 0.5 * sum(
            abs(current_probability - previous_probability)
            for current_probability, previous_probability in zip(current_distribution, previous_distribution)
        )
        significant = kl_divergence >= threshold or total_variation >= threshold
        return {
            "kl_divergence": round(kl_divergence, 4),
            "total_variation": round(total_variation, 4),
            "threshold": threshold,
            "significant": significant,
            "retraining_recommended": significant,
        }

    def _distribution(self, policy: PlanningPolicy, actions: List[str]) -> List[float]:
        scores = [policy.action_scores.get(action, 0.0) + policy.smoothing for action in actions]
        total = sum(scores)
        return [score / total for score in scores] if total else [1.0 / len(actions)] * len(actions)
