from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class ReasoningRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "reasoning_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def register(self, version: str, benchmark: Dict[str, Any], deployment_status: str = "draft") -> Dict[str, Any]:
        payload = {
            "version": version,
            "benchmark_score": benchmark.get("explanation_quality", 0.0),
            "explanation_quality": benchmark.get("explanation_quality", 0.0),
            "reasoning_coverage": benchmark.get("reasoning_coverage", 0.0),
            "deployment_status": deployment_status,
            "parent_version": "reasoning_v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        records = self._load()
        records.append(payload)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return payload

    def latest(self) -> Dict[str, Any]:
        records = self._load()
        return records[-1] if records else {}

    def _load(self) -> List[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
