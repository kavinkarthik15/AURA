from pydantic import BaseModel


class ActionCatalog(BaseModel):
    action_id: str
    action_name: str
    action_type: str
