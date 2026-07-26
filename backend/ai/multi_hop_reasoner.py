from __future__ import annotations

from typing import Any, Dict, List


class MultiHopReasoner:
    def __init__(self) -> None:
        self.version = "multi_hop_reasoning_v1"

    def chain_experiences(self, experiences: List[Dict[str, Any]], target_action: str) -> Dict[str, Any]:
        selected_actions: List[str] = []
        for experience in experiences:
            actions = experience.get("actions") or []
            completed = experience.get("completed_actions") or []
            selected_actions.extend([action for action in actions if action])
            if target_action in completed or target_action in actions:
                selected_actions.append(target_action)
                break
            if completed:
                selected_actions.extend([action for action in completed if action])
        return {
            "selected_actions": selected_actions,
            "hop_count": max(1, len(selected_actions)),
            "target_action": target_action,
        }
