from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.memory.knowledge_index import KnowledgeIndex
from backend.memory.memory_interfaces import MemoryStore
from backend.memory.memory_models import KnowledgeRecord, MemoryStatus
from backend.memory.knowledge_retriever import KnowledgeRetriever


class SemanticMemory(MemoryStore):
    memory_type = "semantic"

    def __init__(self, retriever: KnowledgeRetriever | None = None, index: KnowledgeIndex | None = None) -> None:
        self.retriever = retriever or KnowledgeRetriever()
        self.index = index or KnowledgeIndex(self.retriever.index_path)
        self.retriever.index = self.index
        self._records: Dict[str, KnowledgeRecord] = {}
        self.events: List[Dict[str, Any]] = []
        for record in self.retriever.knowledge_records:
            self._add_canonical(record)
        if self._records:
            self._sync_index()

    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        canonical = self._add_canonical(record)
        self._sync_index()
        self._emit_event("KnowledgeCreated", knowledge_id=canonical.knowledge_id)
        return self._to_dict(canonical)

    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        query = query or {}
        search_text = query.get("query") or query.get("concept") or ""
        result = self.retriever.retrieve(search_text, top_k=top_k)
        self._touch_matches(result["matches"])
        self._emit_event("KnowledgeRetrieved", knowledge_ids=[self._extract_knowledge_id(item) for item in result["matches"]])
        return [
            {
                **self._to_dict(self._find(self._extract_knowledge_id(item))),
                "score": self._extract_score(item),
                "reason": self._extract_reason(item),
            }
            for item in result["matches"]
        ]

    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        record = self._find(memory_id)
        if record is None or record.status != MemoryStatus.ACTIVE:
            return None
        if "status" in updates:
            record.status = MemoryStatus.coerce(updates["status"])
        if "confidence_source" in updates:
            record.confidence_source = updates["confidence_source"]
        if "importance_reason" in updates:
            record.importance_reason = updates["importance_reason"]
        if "importance_source" in updates:
            record.importance_source = updates["importance_source"]
        if "concept" in updates:
            record.concept = str(updates["concept"])
        if "statement" in updates:
            record.statement = str(updates["statement"])
        if "knowledge_type" in updates:
            record.knowledge_type = str(updates["knowledge_type"])
        if "confidence" in updates:
            record.confidence = float(updates["confidence"])
        if "importance" in updates:
            record.importance = float(updates["importance"])
        if "supporting_episode_ids" in updates:
            record.supporting_episode_ids = list(updates["supporting_episode_ids"])
        if "related_knowledge_ids" in updates:
            record.related_knowledge_ids = list(updates["related_knowledge_ids"])
        if "metadata" in updates:
            record.metadata = dict(updates["metadata"])
        record.updated_at = datetime.now(timezone.utc)
        self._sync_index()
        self._emit_event("KnowledgeUpdated", knowledge_id=record.knowledge_id)
        return self._to_dict(record)

    def delete(self, memory_id: str) -> bool:
        record = self._find(memory_id)
        if record is None:
            return False
        record.status = MemoryStatus.DEPRECATED
        record.updated_at = datetime.now(timezone.utc)
        self._sync_index()
        self._emit_event("KnowledgeDeleted", knowledge_id=record.knowledge_id)
        return True

    def archive(self, memory_id: str) -> bool:
        record = self._find(memory_id)
        if record is None:
            return False
        record.status = MemoryStatus.ARCHIVED
        record.updated_at = datetime.now(timezone.utc)
        self._sync_index()
        self._emit_event("KnowledgeArchived", knowledge_id=record.knowledge_id)
        return True

    def revise(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        previous = self._find(memory_id)
        if previous is None:
            return None
        revised = dict(previous.metadata)
        revised.update(updates)
        revised.update(
            {
                "knowledge_id": f"KNW-{uuid4().hex[:12].upper()}",
                "concept": previous.concept,
                "statement": previous.statement,
                "knowledge_type": previous.knowledge_type,
                "confidence": previous.confidence,
                "confidence_source": previous.confidence_source,
                "importance": previous.importance,
                "importance_source": previous.importance_source,
                "importance_reason": previous.importance_reason,
                "revision": previous.revision + 1,
                "parent_knowledge_id": previous.knowledge_id,
            }
        )
        previous.status = MemoryStatus.DEPRECATED
        result = self._add_canonical(revised)
        self._sync_index()
        self._emit_event("KnowledgeUpdated", knowledge_id=result.knowledge_id, parent_knowledge_id=previous.knowledge_id)
        return self._to_dict(result)

    def relate(self, memory_id: str, related_memory_id: str) -> bool:
        record = self._find(memory_id)
        related = self._find(related_memory_id)
        if record is None or related is None:
            return False
        if related.knowledge_id not in record.related_knowledge_ids:
            record.related_knowledge_ids.append(related.knowledge_id)
        self._sync_index()
        return True

    def statistics(self) -> Dict[str, Any]:
        return {
            "count": self.count(),
            "active_count": sum(record.status == MemoryStatus.ACTIVE for record in self._records.values()),
            "archived_count": sum(record.status == MemoryStatus.ARCHIVED for record in self._records.values()),
            "status_distribution": self.status_distribution(),
            "index": self.index.statistics(),
        }

    def count(self) -> int:
        return len(self._records)

    def status_distribution(self) -> Dict[str, int]:
        return dict(Counter(record.status.value for record in self._records.values()))

    def _add_canonical(self, record: Dict[str, Any]) -> KnowledgeRecord:
        raw = dict(record)
        knowledge_id = str(raw.get("knowledge_id") or f"KNW-{uuid4().hex[:12].upper()}")
        now = datetime.now(timezone.utc)
        canonical = KnowledgeRecord(
            knowledge_id=knowledge_id,
            concept=str(raw.get("concept", "")),
            statement=str(raw.get("statement", "")),
            knowledge_type=str(raw.get("knowledge_type", "general")),
            confidence=float(raw.get("confidence", 0.5)),
            confidence_source=raw.get("confidence_source"),
            importance=float(raw.get("importance", 0.5)),
            importance_source=raw.get("importance_source"),
            importance_reason=raw.get("importance_reason"),
            status=MemoryStatus.coerce(raw.get("status", MemoryStatus.ACTIVE.value)),
            revision=int(raw.get("revision", 1)),
            created_at=self._datetime(raw.get("created_at"), now),
            updated_at=self._datetime(raw.get("updated_at"), now),
            last_accessed=self._datetime(raw.get("last_accessed"), now),
            retrieval_count=int(raw.get("retrieval_count", 0)),
            supporting_episode_ids=list(raw.get("supporting_episode_ids", [])),
            related_knowledge_ids=list(raw.get("related_knowledge_ids", [])),
            metadata=dict(raw.get("metadata", {})),
        )
        self._records[knowledge_id] = canonical
        return canonical

    def _sync_index(self) -> None:
        payload = []
        for record in self._records.values():
            payload.append(
                {
                    "knowledge_id": record.knowledge_id,
                    "concept": record.concept,
                    "statement": record.statement,
                    "knowledge_type": record.knowledge_type,
                    "confidence": record.confidence,
                    "confidence_source": record.confidence_source,
                    "importance": record.importance,
                    "importance_source": record.importance_source,
                    "importance_reason": record.importance_reason,
                    "status": record.status.value,
                    "revision": record.revision,
                    "supporting_episode_ids": record.supporting_episode_ids,
                    "related_knowledge_ids": record.related_knowledge_ids,
                    "metadata": record.metadata,
                }
            )
        self.retriever.knowledge_records = payload
        self.retriever.build_index(payload)
        self.index.rebuild(payload)

    def _touch_matches(self, matches: List[Any]) -> None:
        for match in matches:
            record = self._find(self._extract_knowledge_id(match))
            if record is not None:
                record.touch()

    def _extract_knowledge_id(self, match: Any) -> str:
        if isinstance(match, dict):
            record = match.get("knowledge") if isinstance(match.get("knowledge"), dict) else match
            return str(record.get("knowledge_id") or record.get("id") or match.get("knowledge_id") or match.get("id") or "")
        return str(getattr(match, "knowledge_id", "") or getattr(match, "memory_id", "") or getattr(match, "id", "") or "")

    def _extract_score(self, match: Any) -> Any:
        if isinstance(match, dict):
            return match.get("score")
        return getattr(match, "score", None)

    def _extract_reason(self, match: Any) -> Any:
        if isinstance(match, dict):
            return match.get("reason")
        return getattr(match, "reason", None)

    def _emit_event(self, event_type: str, **payload: Any) -> None:
        self.events.append({"event_type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), **payload})

    def _find(self, knowledge_id: str) -> KnowledgeRecord | None:
        if knowledge_id in self._records:
            return self._records[knowledge_id]
        return None

    def _to_dict(self, record: KnowledgeRecord) -> Dict[str, Any]:
        return {
            "knowledge_id": record.knowledge_id,
            "concept": record.concept,
            "statement": record.statement,
            "knowledge_type": record.knowledge_type,
            "confidence": record.confidence,
            "confidence_source": record.confidence_source,
            "importance": record.importance,
            "importance_source": record.importance_source,
            "importance_reason": record.importance_reason,
            "status": record.status.value,
            "revision": record.revision,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "last_accessed": record.last_accessed.isoformat(),
            "retrieval_count": record.retrieval_count,
            "supporting_episode_ids": record.supporting_episode_ids,
            "related_knowledge_ids": record.related_knowledge_ids,
            "metadata": record.metadata,
        }

    @staticmethod
    def _datetime(value: Any, fallback: datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return fallback
