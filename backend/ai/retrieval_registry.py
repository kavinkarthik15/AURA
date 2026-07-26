from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_RETRIEVAL_REGISTRY_PATH = Path(__file__).resolve().parent / "retrieval_registry.json"


class RetrievalRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or DEFAULT_RETRIEVAL_REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, version: str, metric: str, retrieval_weight: float, dataset_version: str, benchmark: Dict[str, Any]) -> Dict[str, Any]:
        record = {"version": version, "similarity_metric": metric, "retrieval_weight": retrieval_weight, "dataset_version": dataset_version, "benchmark": benchmark, "timestamp": datetime.now(timezone.utc).isoformat()}
        records = self.list_records()
        records.append(record)
        self.registry_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return record

    def list_records(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def latest(self) -> Dict[str, Any] | None:
        records = self.list_records()
        return records[-1] if records else None
