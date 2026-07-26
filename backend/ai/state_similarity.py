from __future__ import annotations

import math
from typing import Dict, Iterable, Sequence


def _vector(state: Dict[str, float], keys: Iterable[str]) -> list[float]:
    return [float(state.get(key, 0.0) or 0.0) for key in keys]


def cosine_similarity(left: Dict[str, float], right: Dict[str, float]) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return 1.0
    left_vector = _vector(left, keys)
    right_vector = _vector(right, keys)
    left_norm = math.sqrt(sum(value * value for value in left_vector))
    right_norm = math.sqrt(sum(value * value for value in right_vector))
    if left_norm == 0 or right_norm == 0:
        return 1.0 if left_vector == right_vector else 0.0
    return sum(a * b for a, b in zip(left_vector, right_vector)) / (left_norm * right_norm)


def weighted_similarity(left: Dict[str, float], right: Dict[str, float], weights: Dict[str, float] | None = None) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return 1.0
    weights = weights or {}
    total_weight = sum(weights.get(key, 1.0) for key in keys)
    if not total_weight:
        return 0.0
    distance = sum(weights.get(key, 1.0) * abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in keys)
    scale = max(1.0, max(max(abs(float(left.get(key, 0.0))), abs(float(right.get(key, 0.0)))) for key in keys))
    return max(0.0, 1.0 - distance / (total_weight * scale))


def goal_similarity(left: str, right: str) -> float:
    left_words = set(left.lower().split())
    right_words = set(right.lower().split())
    if not left_words and not right_words:
        return 1.0
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def action_overlap(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def combined_similarity(
    state: Dict[str, float], goal: str, actions: Sequence[str],
    candidate_state: Dict[str, float], candidate_goal: str, candidate_actions: Sequence[str],
    metric: str = "hybrid",
) -> float:
    state_score = cosine_similarity(state, candidate_state)
    if metric == "cosine":
        return round(state_score, 4)
    weighted_score = weighted_similarity(state, candidate_state)
    if metric == "weighted":
        return round(weighted_score, 4)
    score = 0.6 * state_score + 0.2 * weighted_score + 0.1 * goal_similarity(goal, candidate_goal) + 0.1 * action_overlap(actions, candidate_actions)
    return round(score, 4)
