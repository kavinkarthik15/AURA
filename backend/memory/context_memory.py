from backend.memory.placeholder_store import PlaceholderMemoryStore


class ContextMemory(PlaceholderMemoryStore):
    def __init__(self) -> None:
        super().__init__("context")
