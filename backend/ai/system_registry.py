from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class SystemRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "system_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def update_active_versions(self, **versions: str) -> Dict[str, Any]:
        payload = self.get_active_versions()
        payload.update(versions)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def get_active_versions(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
