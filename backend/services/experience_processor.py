from typing import Dict


def build_experience_delta(state_before: Dict, state_after: Dict) -> Dict:
    """Compute a simple delta map from before/after state values."""
    keys = set(state_before.keys()) | set(state_after.keys())
    delta: Dict = {}
    for key in sorted(keys):
        before_value = state_before.get(key, 0)
        after_value = state_after.get(key, 0)
        delta[key] = after_value - before_value
    return delta


def extract_gain_summary(experience: object) -> Dict:
    """Return a simple gain summary for analytics use."""
    return {
        "experience_id": experience.experience_id,
        "action": experience.action,
        "state_delta": getattr(experience, "state_delta", {}),
        "outcome_value": getattr(experience, "outcome_value", 0.0),
    }
