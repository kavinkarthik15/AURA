from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.ai.reflection_memory import ReflectionMemory
from backend.memory.memory_interfaces import MemoryStore


class ReflectionMemoryStore(MemoryStore):
    memory_type = "reflection"

    def __init__(self, reflection_memory: ReflectionMemory | None = None) -> None:
        self.reflection_memory = reflection_memory or ReflectionMemory()

    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        entries = self.reflection_memory.list_entries()
        entries.append(record)
        self.reflection_memory.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        return record

    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        entries = self.reflection_memory.list_entries()
        return entries[-top_k:]

    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def delete(self, memory_id: str) -> bool:
        return False
