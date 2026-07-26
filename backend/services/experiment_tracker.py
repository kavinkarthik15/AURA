from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


DEFAULT_EXPERIMENTS_PATH = Path(__file__).resolve().parents[2] / "experiments"


class ExperimentTracker:
    def __init__(self, root_path: Path | None = None) -> None:
        self.root_path = root_path or DEFAULT_EXPERIMENTS_PATH
        self.root_path.mkdir(parents=True, exist_ok=True)

    def record(self, experiment_id: str, metadata: Dict[str, Any]) -> Path:
        experiment_dir = self.root_path / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "experiment_id": experiment_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "planner_version": metadata.get("planner_version", "v2"),
            "policy_version": metadata.get("policy_version", "policy_v1"),
            "retrieval_version": metadata.get("retrieval_version", "retrieval_v1"),
            "model_version": metadata.get("model_version", "v2"),
            "random_seed": metadata.get("random_seed"),
            "retrieval_configuration": metadata.get("retrieval_configuration", {}),
            "planner_configuration": metadata.get("planner_configuration", {}),
            "beam_width": metadata.get("beam_width", 5),
            "objective_profile": metadata.get("objective_profile", "balanced_learning"),
            "benchmark_results": metadata.get("benchmark_results", {}),
            "execution_metrics": metadata.get("execution_metrics", {}),
            "performance_timings_ms": metadata.get("performance_timings_ms", {}),
            "confidence_breakdown": metadata.get("confidence_breakdown", {}),
            "research_version": metadata.get("research_version", "research_v1"),
            "system_registry": metadata.get("system_registry", {}),
        }
        output_path = experiment_dir / "experiment.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path
