from typing import Dict, List, Tuple

from backend.models.experience import Experience


def calculate_state_similarity(state_a: Dict, state_b: Dict) -> float:
    if not state_a and not state_b:
        return 1.0
    if not state_a or not state_b:
        return 0.0

    shared_keys = set(state_a.keys()) & set(state_b.keys())
    if not shared_keys:
        return 0.0

    total_score = 0.0
    for key in shared_keys:
        a_value = float(state_a.get(key, 0))
        b_value = float(state_b.get(key, 0))
        if a_value == 0 and b_value == 0:
            continue
        total_score += 1.0 - min(abs(a_value - b_value) / max(abs(a_value), abs(b_value), 1), 1.0)

    return round(total_score / len(shared_keys), 2)


def find_similar_users(experiences: List[Experience], target_state: Dict) -> List[Tuple[Experience, float]]:
    scored: List[Tuple[Experience, float]] = []
    for experience in experiences:
        similarity = calculate_state_similarity(target_state, experience.state_before)
        if similarity > 0:
            scored.append((experience, similarity))
    return sorted(scored, key=lambda item: item[1], reverse=True)


def find_similar_transitions(experiences: List[Experience], current_state: Dict, action: str) -> List[Tuple[Experience, float]]:
    scored: List[Tuple[Experience, float]] = []
    action_tokens = set(action.lower().replace("_", " ").split())
    for experience in experiences:
        experience_tokens = set(experience.action.lower().replace("_", " ").split())
        action_similarity = 1.0 if experience.action.lower() == action.lower() else 0.0
        if not action_similarity:
            if experience_tokens.intersection(action_tokens):
                action_similarity = 0.6
            else:
                action_similarity = 0.2

        state_similarity = calculate_state_similarity(current_state, experience.state_before)
        combined_similarity = round((action_similarity * 0.6) + (state_similarity * 0.4), 2)
        if combined_similarity > 0:
            scored.append((experience, combined_similarity))
    return sorted(scored, key=lambda item: item[1], reverse=True)
