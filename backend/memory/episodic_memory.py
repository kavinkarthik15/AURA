from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.ai.experience_retriever import ExperienceRetriever
from backend.memory.experience_index import ExperienceIndex
from backend.memory.memory_interfaces import MemoryStore
from backend.memory.memory_models import MemoryRecord, MemoryStatus

ACTIVE = MemoryStatus.ACTIVE.value
ARCHIVED = MemoryStatus.ARCHIVED.value
MERGED = MemoryStatus.MERGED.value
DEPRECATED = MemoryStatus.DEPRECATED.value


class EpisodicMemory(MemoryStore):
    memory_type = "episodic"

    def __init__(
        self,
        retriever: ExperienceRetriever | None = None,
        index: ExperienceIndex | None = None,
    ) -> None:
        self.retriever = retriever or ExperienceRetriever()
        self.index = index or ExperienceIndex(self.retriever.index_path)
        self.retriever.index = self.index
        self._records: Dict[str, MemoryRecord] = {}
        self.events: List[Dict[str, Any]] = []
        for experience in self.retriever.experiences:
            self._add_canonical(experience)
        if self._records:
            self._sync_index()

    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        canonical = self._add_canonical(record)
        self._sync_index()
        self._emit_event("MemoryCreated", memory_id=canonical.memory_id, status=canonical.status.value)
        return self._to_dict(canonical)

    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        query = query or {}
        result = self.retriever.retrieve(
            query.get("state", {}), query.get("goal", ""), query.get("actions", []), top_k=top_k
        )
        self._touch_matches(result["matches"])
        self._emit_event(
            "MemoryRetrieved",
            memory_ids=[self._extract_memory_id(match) for match in result["matches"]],
            top_k=top_k,
        )
        return result["matches"]

    def retrieve_experiences(self, state: Dict[str, float], goal: str, actions: List[str] | None = None, top_k: int = 10, diversity_threshold: float | None = None) -> Dict[str, Any]:
        if top_k == 10 and diversity_threshold is None:
            result = self.retriever.retrieve(state, goal, actions)
        else:
            kwargs: Dict[str, Any] = {"top_k": top_k}
            if diversity_threshold is not None:
                kwargs["diversity_threshold"] = diversity_threshold
            result = self.retriever.retrieve(state, goal, actions, **kwargs)
        self._touch_matches(result["matches"])
        self._emit_event(
            "MemoryRetrieved",
            memory_ids=[self._extract_memory_id(match) for match in result["matches"]],
            top_k=top_k,
            goal=goal,
        )
        return result

    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        record = self._find(memory_id)
        if record is None or record.status != MemoryStatus.ACTIVE:
            return None
        record.data.update(updates)
        if "status" in updates:
            record.status = MemoryStatus.coerce(updates["status"])
        if "related_memories" in updates:
            record.related_memories = list(updates["related_memories"])
        if "derived_from" in updates:
            record.derived_from = list(updates["derived_from"])
        if "confidence_source" in updates:
            record.confidence_source = updates["confidence_source"]
        if "importance_reason" in updates:
            record.importance_reason = updates["importance_reason"]
        if "importance_source" in updates:
            record.importance_source = updates["importance_source"]
        record.importance = float(updates.get("importance", record.importance))
        record.confidence = float(updates.get("confidence", record.confidence))
        record.updated_at = datetime.now(timezone.utc)
        record.data["status"] = record.status.value
        record.data["confidence_source"] = record.confidence_source
        record.data["importance_reason"] = record.importance_reason
        record.data["importance_source"] = record.importance_source
        self._sync_index()
        self._emit_event("MemoryUpdated", memory_id=record.memory_id, status=record.status.value)
        return self._to_dict(record)

    def delete(self, memory_id: str) -> bool:
        record = self._find(memory_id)
        if record is None:
            return False
        record.status = MemoryStatus.DEPRECATED
        record.updated_at = datetime.now(timezone.utc)
        record.data["status"] = record.status.value
        self._sync_index()
        self._emit_event("MemoryDeleted", memory_id=record.memory_id)
        return True

    def revise(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        previous = self._find(memory_id)
        if previous is None:
            return None
        revised = dict(previous.data)
        revised.update(updates)
        revised.update(
            {
                "memory_id": f"EXP-{uuid4().hex[:12].upper()}",
                "experience_id": previous.experience_id,
                "parent_memory_id": previous.memory_id,
                "revision": previous.revision + 1,
            }
        )
        previous.status = MemoryStatus.DEPRECATED
        previous.data["status"] = previous.status.value
        result = self._add_canonical(revised)
        self._sync_index()
        self._emit_event("MemoryUpdated", memory_id=result.memory_id, parent_memory_id=previous.memory_id)
        return self._to_dict(result)

    def merge(self, memory_ids: List[str], updates: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        records = [self._find(memory_id) for memory_id in memory_ids]
        records = [record for record in records if record is not None and record.status == MemoryStatus.ACTIVE]
        if len(records) < 2:
            return None
        merged_data = dict(records[0].data)
        for record in records[1:]:
            for key, value in record.data.items():
                if key not in merged_data or merged_data[key] in (None, "", [], {}):
                    merged_data[key] = value
        merged_data.update(updates or {})
        merged_data["memory_id"] = f"EXP-{uuid4().hex[:12].upper()}"
        merged_data["related_memories"] = [record.memory_id for record in records]
        merged = self._add_canonical(merged_data)
        for record in records:
            record.status = MemoryStatus.MERGED
            record.merged_into.append(merged.memory_id)
            record.data["status"] = record.status.value
        self._sync_index()
        self._emit_event("MemoryMerged", memory_id=merged.memory_id, source_memory_ids=[record.memory_id for record in records])
        return self._to_dict(merged)

    def archive(self, memory_id: str) -> bool:
        record = self._find(memory_id)
        if record is None:
            return False
        record.status = MemoryStatus.ARCHIVED
        record.data["status"] = record.status.value
        self._sync_index()
        self._emit_event("MemoryArchived", memory_id=record.memory_id)
        return True

    def relate(self, memory_id: str, related_memory_id: str) -> bool:
        record = self._find(memory_id)
        related = self._find(related_memory_id)
        if record is None or related is None:
            return False
        if related.memory_id not in record.related_memories:
            record.related_memories.append(related.memory_id)
        self._sync_index()
        return True

    def compute_adaptive_weight(self, *args: Any, **kwargs: Any) -> float:
        return self.retriever.compute_adaptive_weight(*args, **kwargs)

    def get_analytics_summary(self) -> Dict[str, Any]:
        return self.retriever.get_analytics_summary()

    def statistics(self) -> Dict[str, Any]:
        return {
            "count": self.count(),
            "active_count": sum(record.status == MemoryStatus.ACTIVE for record in self._records.values()),
            "archived_count": sum(record.status == MemoryStatus.ARCHIVED for record in self._records.values()),
            "revision_distribution": self.revision_distribution(),
            "status_distribution": self.status_distribution(),
            "index": self.index.statistics(),
            "retrieval": self.get_analytics_summary(),
        }

    def count(self) -> int:
        return len(self._records)

    def average_importance(self) -> float:
        return round(sum(record.importance for record in self._records.values()) / max(1, self.count()), 4)

    def revision_distribution(self) -> Dict[str, int]:
        return dict(Counter(str(record.revision) for record in self._records.values()))

    def status_distribution(self) -> Dict[str, int]:
        return dict(Counter(record.status.value for record in self._records.values()))

    def _add_canonical(self, record: Dict[str, Any]) -> MemoryRecord:
        raw = dict(record)
        experience_id = str(raw.get("experience_id") or f"exp_{uuid4().hex[:8]}")
        memory_id = str(raw.get("memory_id") or f"EXP-{uuid4().hex[:12].upper()}")
        now = datetime.now(timezone.utc)
        canonical = MemoryRecord(
            memory_id=memory_id,
            memory_type=self.memory_type,
            importance=float(raw.get("importance", 0.5)),
            confidence=float(raw.get("confidence", raw.get("experience_confidence", 0.5))),
            created_at=self._datetime(raw.get("created_at"), now),
            updated_at=self._datetime(raw.get("updated_at"), now),
            last_accessed=self._datetime(raw.get("last_accessed"), now),
            data=raw,
            experience_id=experience_id,
            revision=int(raw.get("revision", 1)),
            parent_memory_id=raw.get("parent_memory_id"),
            related_memories=list(raw.get("related_memories", [])),
            derived_from=list(raw.get("derived_from", [])),
            merged_into=list(raw.get("merged_into", [])),
            status=MemoryStatus.coerce(raw.get("status", ACTIVE)),
            confidence_source=raw.get("confidence_source"),
            importance_reason=raw.get("importance_reason"),
            importance_source=raw.get("importance_source"),
        )
        canonical.data.update({"memory_id": memory_id, "experience_id": experience_id, "status": canonical.status.value, "confidence_source": canonical.confidence_source, "importance_reason": canonical.importance_reason, "importance_source": canonical.importance_source})
        self._records[memory_id] = canonical
        return canonical

    def _sync_index(self) -> None:
        experiences = []
        for record in self._records.values():
            record.data.update(
                {
                    "memory_id": record.memory_id,
                    "experience_id": record.experience_id,
                    "importance": record.importance,
                    "confidence": record.confidence,
                    "revision": record.revision,
                    "status": record.status.value,
                    "confidence_source": record.confidence_source,
                    "importance_reason": record.importance_reason,
                    "importance_source": record.importance_source,
                }
            )
            experiences.append(record.data)
        self.retriever.experiences = experiences
        self.retriever.build_index(self.retriever.experiences)

    def _touch_matches(self, matches: List[Any]) -> None:
        for match in matches:
            record_id = self._extract_memory_id(match)
            record = self._find(record_id)
            if record is not None:
                record.touch()

    def _extract_memory_id(self, match: Any) -> str:
        if isinstance(match, dict):
            return str(match.get("memory_id") or match.get("experience_id") or match.get("id") or "")
        return str(getattr(match, "memory_id", "") or getattr(match, "experience_id", "") or getattr(match, "id", "") or "")

    def _emit_event(self, event_type: str, **payload: Any) -> None:
        self.events.append({"event_type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), **payload})

    def _find(self, memory_id: str) -> MemoryRecord | None:
        if memory_id in self._records:
            return self._records[memory_id]
        return next((record for record in self._records.values() if record.experience_id == memory_id), None)

    def _to_dict(self, record: MemoryRecord) -> Dict[str, Any]:
        result = dict(record.data)
        result.update(
            {
                "memory_id": record.memory_id,
                "experience_id": record.experience_id,
                "importance": record.importance,
                "confidence": record.confidence,
                "retrieval_count": record.retrieval_count,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "last_accessed": record.last_accessed.isoformat(),
                "revision": record.revision,
                "parent_memory_id": record.parent_memory_id,
                "related_memories": record.related_memories,
                "derived_from": record.derived_from,
                "merged_into": record.merged_into,
                "status": record.status.value,
                "confidence_source": record.confidence_source,
                "importance_reason": record.importance_reason,
                "importance_source": record.importance_source,
            }
        )
        return result

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
