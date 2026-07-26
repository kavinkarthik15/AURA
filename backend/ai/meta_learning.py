from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class MetaLearningLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "meta_learning.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def record(
        self,
        reasoning_strategy: str,
        reflection_score: float,
        execution_success: bool,
        lesson: str,
        plan: str,
    ) -> Dict[str, Any]:
        reinforcement = "reinforce" if execution_success and reflection_score >= 0.75 else "review_failure" if not execution_success else "review"
        entry = {
            "reasoning_strategy": reasoning_strategy,
            "reflection_score": round(reflection_score, 4),
            "execution_success": execution_success,
            "lesson": lesson,
            "plan": plan,
            "reinforcement": reinforcement,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        records = self.list_entries()
        records.append(entry)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return entry

    def list_entries(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))
