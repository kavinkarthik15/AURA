from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


class MemoryRegistry:
    version = "memory_v1"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "memory_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def register(self, stores: Iterable[str], configuration: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "version": self.version,
            "active_stores": list(stores),
            "configuration": configuration or {},
            "metrics": {},
            "health": "healthy",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "semantic": {
                "version": "semantic_memory_v1",
                "implementation_status": "active",
                "index_version": "knowledge_index_v1",
                "retriever_version": "knowledge_retriever_v1",
                "retrieval_strategy": "similarity_confidence_evidence",
                "statistics": {},
            },
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def get(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))
