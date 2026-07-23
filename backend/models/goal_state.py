from typing import Dict

from pydantic import BaseModel


class GoalState(BaseModel):
    goal: str
    target_skills: Dict[str, int]
