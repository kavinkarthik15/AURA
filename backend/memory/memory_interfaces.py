from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class MemoryStore(ABC):
    memory_type = "unknown"

    @abstractmethod
    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        raise NotImplementedError

    def search(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        return self.retrieve(query, top_k)

    def consolidate(self) -> Dict[str, Any]:
        return {"memory_type": self.memory_type, "consolidated": 0}

    def forget(self) -> Dict[str, Any]:
        return {"memory_type": self.memory_type, "forgotten": 0}
