from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_POLICY_REGISTRY_PATH = Path(__file__).resolve().parent / "policy_registry.json"


class PolicyRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or DEFAULT_POLICY_REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def register(
        self,
        policy_version: str,
        dataset_hash: str,
        sample_count: int,
        benchmark: Dict[str, Any],
        parent_policy: str | None = None,
        accepted: bool | None = None,
        reason: str | None = None,
    ) -> Dict[str, Any]:
        record = {
            "policy_version": policy_version,
            "dataset_hash": dataset_hash,
            "sample_count": sample_count,
            "benchmark": benchmark,
            "parent_policy": parent_policy,
            "accepted": accepted,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        records = self._load()
        if accepted:
            for existing in records:
                existing["active"] = False
            record["active"] = True
        records.append(record)
        self.registry_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return record

    def rollback(self, policy_version: str) -> Dict[str, Any]:
        records = self._load()
        target = next((record for record in records if record.get("policy_version") == policy_version), None)
        if target is None:
            raise ValueError(f"Policy {policy_version} is not registered")
        for record in records:
            record["active"] = record.get("policy_version") == policy_version
        target["accepted"] = True
        target["reason"] = "restored by automatic rollback"
        self.registry_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return target

    def list_policies(self) -> List[Dict[str, Any]]:
        return self._load()

    def latest(self) -> Dict[str, Any] | None:
        records = self._load()
        active = [record for record in records if record.get("active")]
        if active:
            return active[-1]
        accepted = [record for record in records if record.get("accepted")]
        return accepted[-1] if accepted else (records[-1] if records else None)
