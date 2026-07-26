from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_REFLECTION_REGISTRY_PATH = Path(__file__).resolve().parent / "reflection_registry.json"


class ReflectionRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_REFLECTION_REGISTRY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def register(
        self,
        reflection_version: str,
        thresholds: Dict[str, Any],
        metrics: Dict[str, Any],
        benchmark_results: Dict[str, Any],
        release_date: str,
        deployment_status: str = "draft",
        description: str | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "reflection_version": reflection_version,
            "thresholds": thresholds,
            "metrics": metrics,
            "benchmark_results": benchmark_results,
            "release_date": release_date,
            "deployment_status": deployment_status,
            "description": description,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "active": deployment_status == "active",
        }
        records = self._load()
        if deployment_status == "active":
            for record in records:
                record["active"] = False
        records.append(payload)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return payload

    def latest(self) -> Dict[str, Any]:
        records = self._load()
        return records[-1] if records else {}

    def list_records(self) -> List[Dict[str, Any]]:
        return self._load()

    def _load(self) -> List[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
