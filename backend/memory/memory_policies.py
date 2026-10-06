from __future__ import annotations

from typing import Any, Dict, Iterable, List


class RetrievalPolicy:
    """Selects memory stores for a query without owning memory data."""

    def select_memory_types(self, query: Dict[str, Any]) -> List[str]:
        requested = query.get("memory_types")
        if requested:
            return list(dict.fromkeys(str(memory_type) for memory_type in requested))
        if query.get("reflection_only"):
            return ["reflection"]
        if query.get("context_only"):
            return ["context"]
        return ["working", "episodic", "semantic", "procedural", "reflection", "context"]


class ImportancePolicy:
    def score(self, record: Dict[str, Any]) -> float:
        if isinstance(record, dict):
            return float(record.get("importance", 0.5))
        return float(getattr(record, "importance", 0.5))

    def rank(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(records, key=self.score, reverse=True)


class ConsolidationPolicy:
    def should_consolidate(self, record: Dict[str, Any]) -> bool:
        return bool(record.get("success", False) and self._confidence(record) >= 0.75)

    def _confidence(self, record: Dict[str, Any]) -> float:
        return float(record.get("confidence", record.get("similarity", 0.0)))


class ForgettingPolicy:
    def should_forget(self, record: Dict[str, Any]) -> bool:
        return bool(record.get("forget", False))


class MemoryPolicies:
    """Policy bundle owned by MemoryManager; policies remain stateless in 13.2."""

    def __init__(
        self,
        retrieval: RetrievalPolicy | None = None,
        importance: ImportancePolicy | None = None,
        consolidation: ConsolidationPolicy | None = None,
        forgetting: ForgettingPolicy | None = None,
    ) -> None:
        self.retrieval = retrieval or RetrievalPolicy()
        self.importance = importance or ImportancePolicy()
        self.consolidation = consolidation or ConsolidationPolicy()
        self.forgetting = forgetting or ForgettingPolicy()
