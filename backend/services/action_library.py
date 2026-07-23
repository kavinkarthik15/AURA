import json
from pathlib import Path
from typing import Any, Dict, List


class ActionLibrary:
    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or Path(__file__).resolve().parents[1] / "data" / "action_catalog.json"
        self.actions = self._load_actions()

    def _load_actions(self) -> List[Dict[str, Any]]:
        with self.catalog_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload

    def list_actions(self) -> List[Dict[str, Any]]:
        return list(self.actions)

    def get_action(self, name: str) -> Dict[str, Any] | None:
        for action in self.actions:
            if action.get("name", "").lower() == name.lower():
                return action
        return None

    def find_actions_for_goal(self, goal_state) -> List[Dict[str, Any]]:
        target_skills = set(goal_state.target_skills.keys()) if hasattr(goal_state, "target_skills") else set()
        scored = []
        for action in self.actions:
            action_skills = set(action.get("skills", [])) if "skills" in action else set()
            overlap = len(target_skills & action_skills)
            score = overlap + int(action.get("estimated_skill_gain", 0) / 10)
            scored.append((score, action))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [action for _, action in scored[:5]]


action_library = ActionLibrary()
