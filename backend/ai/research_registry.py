from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class ResearchRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "research_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def register_experiment(
        self,
        experiment_id: str,
        planner_version: str,
        policy_version: str,
        retrieval_version: str,
        reasoner_version: str,
        twin_version: str,
        dataset_version: str,
        benchmark_version: str,
    ) -> Dict[str, Any]:
        payload = {
            "research_version": f"research_{len(self._load()) + 1}",
            "experiment_id": experiment_id,
            "planner_version": planner_version,
            "policy_version": policy_version,
            "retrieval_version": retrieval_version,
            "reasoner_version": reasoner_version,
            "twin_version": twin_version,
            "dataset_version": dataset_version,
            "benchmark_version": benchmark_version,
            "lineage": {
                "experiment": experiment_id,
                "planner": planner_version,
                "policy": policy_version,
                "retriever": retrieval_version,
                "reasoner": reasoner_version,
                "twin": twin_version,
                "dataset": dataset_version,
                "benchmark": benchmark_version,
            },
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
