from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json


class KnowledgeRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "knowledge_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def record(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        records = self._load()
        records.append(candidate)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return candidate

    def statistics(self) -> Dict[str, Any]:
        records = self._load()
        if not records:
            return {"knowledge_candidates_generated": 0, "average_confidence": 0.0}
        average_confidence = sum(record.get("confidence", 0.0) for record in records) / len(records)
        return {"knowledge_candidates_generated": len(records), "average_confidence": average_confidence}

    def _load(self) -> List[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
