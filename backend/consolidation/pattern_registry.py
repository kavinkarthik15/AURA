from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json


class PatternRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "pattern_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def record(self, pattern_type: str, confidence: float, support_count: int, execution_time_ms: float) -> Dict[str, Any]:
        payload = {
            "pattern_type": pattern_type,
            "confidence": confidence,
            "support_count": support_count,
            "execution_time_ms": execution_time_ms,
        }
        records = self._load()
        records.append(payload)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return payload

    def statistics(self) -> Dict[str, Any]:
        records = self._load()
        if not records:
            return {
                "patterns_generated": 0,
                "pattern_types": [],
                "average_confidence": 0.0,
                "average_support": 0.0,
                "execution_time_ms": 0.0,
            }

        type_names = sorted({record["pattern_type"] for record in records})
        average_confidence = sum(record["confidence"] for record in records) / len(records)
        average_support = sum(record["support_count"] for record in records) / len(records)
        execution_time_ms = sum(record["execution_time_ms"] for record in records) / len(records)
        return {
            "patterns_generated": len(records),
            "pattern_types": type_names,
            "average_confidence": average_confidence,
            "average_support": average_support,
            "execution_time_ms": execution_time_ms,
        }

    def _load(self) -> List[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
