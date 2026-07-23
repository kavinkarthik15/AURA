from typing import Dict, List

from backend.models.action_catalog import ActionCatalog


class ActionCatalogService:
    def __init__(self, actions: List[ActionCatalog] | None = None) -> None:
        self.actions = actions or []

    def add_action(self, action_id: str, action_name: str, action_type: str) -> ActionCatalog:
        action = ActionCatalog(action_id=action_id, action_name=action_name, action_type=action_type)
        self.actions.append(action)
        return action

    def get_action(self, action_id: str) -> ActionCatalog | None:
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None

    def list_actions(self) -> List[ActionCatalog]:
        return self.actions
