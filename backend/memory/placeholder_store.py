from __future__ import annotations

from typing import Any, Dict, List

from backend.memory.memory_interfaces import MemoryStore


class PlaceholderMemoryStore(MemoryStore):
    def __init__(self, memory_type: str) -> None:
        self.memory_type = memory_type

    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return record

    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        return []

    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def delete(self, memory_id: str) -> bool:
        return False
