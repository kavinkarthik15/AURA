from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.ai.planning_policy import PlanningPolicy, PolicySample


class PolicyTrainer:
    def train(self, samples: Iterable[PolicySample], output_path: Path | None = None) -> Dict[str, Any]:
        sample_list = list(samples)
        policy = PlanningPolicy().fit(sample_list)
        policy.training_date = datetime.now(timezone.utc).isoformat()
        artifact = {
            "policy_version": policy.policy_version,
            "model": policy.to_dict(),
            "dataset_hash": hashlib.sha256(json.dumps([sample.__dict__ for sample in sample_list], sort_keys=True).encode("utf-8")).hexdigest(),
            "sample_count": len(sample_list),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return {"policy": policy, **artifact}
