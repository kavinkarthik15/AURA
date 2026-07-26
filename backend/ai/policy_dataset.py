from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.ai.planning_policy import PolicySample
from backend.models.experience_log import ExperienceLog


class PolicyDatasetBuilder:
    def build_samples(self, experiences: Iterable[ExperienceLog | Dict[str, Any]]) -> List[PolicySample]:
        samples: List[PolicySample] = []
        for item in experiences:
            record = item.to_dict() if isinstance(item, ExperienceLog) else item
            actions = record.get("actions", [])
            completed = set(record.get("completed_actions", []))
            success = bool(record.get("success", False))
            for action in actions:
                samples.append(PolicySample(
                    state={key: float(value) for key, value in record.get("initial_state", {}).items() if isinstance(value, (int, float))},
                    goal=str(record.get("goal_name", "")),
                    action=str(action),
                    action_history=list(record.get("completed_actions", [])),
                    success=success and action in completed,
                    weight=1.0 if action in completed else 0.5,
                ))
        return samples

    def build_from_json(self, path: Path) -> List[PolicySample]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        records = payload.get("records", payload) if isinstance(payload, dict) else payload
        return self.build_samples(records)
