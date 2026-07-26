from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class IntegrationCoverageTracker:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parents[1] / "ai" / "integration_coverage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"covered_paths": [], "paths": [
                "planner",
                "retriever",
                "reasoner",
                "execution",
                "continual_learning",
                "policy_update",
            ]}), encoding="utf-8")

    def mark_covered(self, path_name: str) -> None:
        payload = self._load()
        covered = payload.get("covered_paths", [])
        if path_name not in covered:
            covered.append(path_name)
            payload["covered_paths"] = covered
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def summary(self) -> Dict[str, Any]:
        payload = self._load()
        covered = payload.get("covered_paths", [])
        total_paths = len(payload.get("paths", []))
        return {
            "covered_paths": covered,
            "total_paths": total_paths,
            "coverage_ratio": round(len(covered) / max(1, total_paths), 4),
        }

    def _load(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
