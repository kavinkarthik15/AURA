import json
from datetime import datetime
from pathlib import Path

from backend.models.state_document import StateDocument
from backend.models.user_state import UserState


STATE_FILE = Path(__file__).resolve().parents[1] / "data" / "user_state.json"


class StateService:
    def __init__(self) -> None:
        self._document: StateDocument | None = None

    def load_state(self) -> UserState:
        with STATE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self._document = StateDocument(**data)
        return self._document.state

    def save_state(self) -> None:
        if self._document is None:
            raise ValueError("No state loaded to save")
        self._document.last_updated = datetime.utcnow()
        with STATE_FILE.open("w", encoding="utf-8") as handle:
            handle.write(self._document.model_dump_json(indent=4))

    def get_state(self) -> UserState:
        if self._document is None:
            raise ValueError("State has not been loaded")
        return self._document.state

    def update_skill(self, name: str, value: int) -> None:
        state = self.get_state()
        state.skills[name] = self._clamp_value(value)

    def update_goal(self, name: str, value: int) -> None:
        state = self.get_state()
        state.goals[name] = self._clamp_value(value)

    def increment_skill(self, name: str, delta: int) -> None:
        state = self.get_state()
        current = state.skills.get(name, 0)
        state.skills[name] = self._clamp_value(current + delta)

    def increment_goal(self, name: str, delta: int) -> None:
        state = self.get_state()
        current = state.goals.get(name, 0)
        state.goals[name] = self._clamp_value(current + delta)

    @staticmethod
    def _clamp_value(value: int) -> int:
        return max(0, min(100, value))


state_service = StateService()
