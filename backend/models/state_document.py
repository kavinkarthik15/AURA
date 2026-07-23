from datetime import datetime

from pydantic import BaseModel

from backend.models.user_state import UserState


class StateDocument(BaseModel):
    version: int
    last_updated: datetime
    state: UserState
