from typing import Dict

from pydantic import BaseModel


class UserState(BaseModel):
    skills: Dict[str, int]
    knowledge: Dict[str, int]
    projects: Dict[str, int]
    goals: Dict[str, int]
    learning: Dict[str, int]
