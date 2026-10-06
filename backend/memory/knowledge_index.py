from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class KnowledgeIndex:
    version = "knowledge_index_v1"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._entries: Dict[str, Dict[str, Any]] = {}

    def index(self, knowledge: Dict[str, Any]) -> None:
        knowledge_id = str(knowledge["knowledge_id"])
        self._entries[knowledge_id] = self._projection(knowledge)
        self._persist()

    def update(self, knowledge: Dict[str, Any]) -> None:
        self.index(knowledge)

    def remove(self, knowledge_id: str) -> bool:
        removed = self._entries.pop(knowledge_id, None) is not None
        if removed:
            self._persist()
        return removed

    def search(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        self._load()
        query = query or {}
        entries = list(self._entries.values())
        if not query.get("include_archived", False):
            entries = [entry for entry in entries if entry.get("status", "ACTIVE") == "ACTIVE"]
        if query.get("concept") is not None:
            entries = [entry for entry in entries if str(entry.get("concept", "")).lower() == str(query["concept"]).lower()]
        return entries[:top_k]

    def rebuild(self, knowledge: Iterable[Dict[str, Any]]) -> None:
        self._entries = {str(item["knowledge_id"]): self._projection(item) for item in knowledge}
        self._persist()

    def statistics(self) -> Dict[str, Any]:
        self._load()
        return {
            "version": self.version,
            "entries": len(self._entries),
            "active_entries": sum(entry.get("status", "ACTIVE") == "ACTIVE" for entry in self._entries.values()),
        }

    def records(self) -> List[Dict[str, Any]]:
        self._load()
        return list(self._entries.values())

    def _projection(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "knowledge_id": knowledge["knowledge_id"],
            "concept": knowledge.get("concept", ""),
            "statement": knowledge.get("statement", ""),
            "knowledge_type": knowledge.get("knowledge_type", "general"),
            "confidence": float(knowledge.get("confidence", 0.5)),
            "confidence_source": knowledge.get("confidence_source"),
            "importance": float(knowledge.get("importance", 0.5)),
            "importance_source": knowledge.get("importance_source"),
            "importance_reason": knowledge.get("importance_reason"),
            "status": knowledge.get("status", "ACTIVE"),
            "revision": int(knowledge.get("revision", 1)),
            "supporting_episode_ids": knowledge.get("supporting_episode_ids", []),
            "related_knowledge_ids": knowledge.get("related_knowledge_ids", []),
            "metadata": knowledge.get("metadata", {}),
        }

    def _load(self) -> None:
        if self.path is not None and self.path.exists() and not self._entries:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = {}
            for entry in payload:
                knowledge_id = str(entry.get("knowledge_id") or entry.get("concept", ""))
                if not knowledge_id:
                    continue
                entry["knowledge_id"] = knowledge_id
                self._entries[knowledge_id] = entry

    def _persist(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(list(self._entries.values()), indent=2), encoding="utf-8")
