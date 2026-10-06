from backend.memory.placeholder_store import PlaceholderMemoryStore


class ProceduralMemory(PlaceholderMemoryStore):
    def __init__(self) -> None:
        super().__init__("procedural")
