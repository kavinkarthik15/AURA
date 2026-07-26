from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class ReflectionMemory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "reflection_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def record_pre_execution(
        self,
        plan: str,
        prediction: str,
        assumptions: List[Dict[str, Any]],
        evidence_sufficiency: float,
    ) -> Dict[str, Any]:
        entry = {
            "phase": "pre_execution",
            "plan": plan,
            "prediction": prediction,
            "assumptions": assumptions,
            "evidence_sufficiency": evidence_sufficiency,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        records = self.list_entries()
        records.append(entry)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return entry

    def record_post_execution(
        self,
        plan: str,
        outcome: str,
        reflection: str,
        lesson_learned: str,
    ) -> Dict[str, Any]:
        entry = {
            "phase": "post_execution",
            "plan": plan,
            "outcome": outcome,
            "reflection": reflection,
            "lesson_learned": lesson_learned,
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
