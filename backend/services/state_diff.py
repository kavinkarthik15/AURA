from typing import Dict


def calculate_state_diff(state_before: Dict, state_after: Dict) -> Dict:
    keys = set(state_before.keys()) | set(state_after.keys())
    diff: Dict = {}
    for key in sorted(keys):
        before_value = state_before.get(key, 0)
        after_value = state_after.get(key, 0)
        delta = after_value - before_value
        if delta != 0:
            diff[key] = delta
    return diff
