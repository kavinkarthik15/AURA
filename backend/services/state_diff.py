from __future__ import annotations

from typing import Any, Dict


def _normalize_state(state: Any) -> Dict[str, Dict[str, int]]:
    if hasattr(state, "model_dump"):
        data = state.model_dump()
    elif hasattr(state, "dict"):
        data = state.dict()
    elif isinstance(state, dict):
        data = state
    else:
        raise TypeError(f"Unsupported state type: {type(state)!r}")

    normalized: Dict[str, Dict[str, int]] = {}
    for category in ["skills", "knowledge", "projects", "goals", "learning"]:
        value = data.get(category)
        if isinstance(value, dict):
            normalized[category] = {str(key): int(item) for key, item in value.items()}
        elif value is None:
            normalized[category] = {}
        else:
            normalized[category] = {str(category): int(value)}

    return normalized


def calculate_state_diff(state_before: Any, state_after: Any) -> Dict[str, Dict[str, int]]:
    if _is_flat_state_mapping(state_before) and _is_flat_state_mapping(state_after):
        before_values = {str(key): int(value) for key, value in dict(state_before).items() if isinstance(value, (int, float))}
        after_values = {str(key): int(value) for key, value in dict(state_after).items() if isinstance(value, (int, float))}
        diff: Dict[str, int] = {}
        for key in sorted(set(before_values.keys()) | set(after_values.keys())):
            delta = after_values.get(key, 0) - before_values.get(key, 0)
            if delta != 0:
                diff[key] = delta
        return diff

    before_state = _normalize_state(state_before)
    after_state = _normalize_state(state_after)

    diff: Dict[str, Dict[str, int]] = {}
    categories = set(before_state.keys()) | set(after_state.keys())

    for category in sorted(categories):
        before_values = before_state.get(category, {}) or {}
        after_values = after_state.get(category, {}) or {}
        keys = set(before_values.keys()) | set(after_values.keys())
        category_diff: Dict[str, int] = {}

        for key in sorted(keys):
            before_value = before_values.get(key, 0)
            after_value = after_values.get(key, 0)
            delta = after_value - before_value
            if delta != 0:
                category_diff[key] = delta

        if category_diff:
            diff[category] = category_diff

    return diff


def _is_flat_state_mapping(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    if not state:
        return True
    category_keys = {"skills", "knowledge", "projects", "goals", "learning"}
    return not any(key in category_keys for key in state.keys())
