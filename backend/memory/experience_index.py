from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class ExperienceIndex:
    """Replaceable lookup projection owned by EpisodicMemory."""

    version = "experience_index_v1"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._entries: Dict[str, Dict[str, Any]] = {}

    def index(self, experience: Dict[str, Any]) -> None:
        memory_id = str(experience["memory_id"])
        self._entries[memory_id] = self._projection(experience)
        self._persist()

    def remove(self, memory_id: str) -> bool:
        removed = self._entries.pop(memory_id, None) is not None
        if removed:
            self._persist()
        return removed

    def update(self, experience: Dict[str, Any]) -> None:
        self.index(experience)

    def search(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        self._load()
        query = query or {}
        entries = list(self._entries.values())
        if not query.get("include_archived", False):
            entries = [entry for entry in entries if entry.get("status", "ACTIVE") == "ACTIVE"]
        if query.get("user_id") is not None:
            entries = [entry for entry in entries if entry.get("user_id") == query["user_id"]]
        return entries[:top_k]

    def rebuild(self, experiences: Iterable[Dict[str, Any]]) -> None:
        self._entries = {
            str(experience["memory_id"]): self._projection(experience)
            for experience in experiences
        }
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

    def _projection(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "memory_id": experience["memory_id"],
            "experience_id": experience.get("experience_id", experience["memory_id"]),
            "initial_state": experience.get("initial_state", experience.get("state_before", {})),
            "state": experience.get("state", experience.get("initial_state", experience.get("state_before", {}))),
            "goal_name": experience.get("goal_name", experience.get("goal", "")),
            "goal": experience.get("goal", experience.get("goal_name", "")),
            "actions": experience.get("actions", [experience.get("action", "")]),
            "completed_actions": experience.get("completed_actions", []),
            "success": bool(experience.get("success", experience.get("outcome_value", 0) > 0)),
            "goal_completion": float(experience.get("goal_completion", experience.get("outcome_value", 0.0) or 0.0)),
            "timestamp": experience.get("timestamp") or experience.get("occurred_at") or experience.get("created_at", ""),
            "importance": float(experience.get("importance", 0.5)),
            "confidence": float(experience.get("confidence", experience.get("experience_confidence", 0.5))),
            "status": experience.get("status", "ACTIVE"),
            "user_id": experience.get("user_id", "default_user"),
        }

    def _load(self) -> None:
        if self.path is not None and self.path.exists() and not self._entries:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = {}
            for entry in payload:
                memory_id = str(entry.get("memory_id") or entry.get("experience_id", ""))
                if not memory_id:
                    continue
                entry["memory_id"] = memory_id
                self._entries[memory_id] = entry

    def _persist(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(list(self._entries.values()), indent=2), encoding="utf-8")
