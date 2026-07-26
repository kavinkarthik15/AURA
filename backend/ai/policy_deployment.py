from __future__ import annotations

from typing import Dict

from backend.ai.policy_registry import PolicyRegistry


class PolicyDeployment:
    def deploy(self, candidate: Dict, benchmark: Dict, registry: PolicyRegistry) -> Dict:
        baseline = registry.latest()
        baseline_accuracy = float((baseline or {}).get("benchmark", {}).get("top_action_accuracy", 0.0))
        candidate_accuracy = float(benchmark.get("top_action_accuracy", 0.0))
        accepted = baseline is None or candidate_accuracy >= baseline_accuracy
        reason = "candidate meets or exceeds the previous benchmark" if accepted else "candidate benchmark is below the previous policy"
        record = registry.register(
            policy_version=candidate.get("policy_version", "policy_v1"),
            dataset_hash=candidate.get("dataset_hash", ""),
            sample_count=int(candidate.get("sample_count", 0)),
            benchmark=benchmark,
            parent_policy=baseline.get("policy_version") if baseline else None,
            accepted=accepted,
            reason=reason,
        )
        if accepted:
            return {"deployed": True, "active_policy": record["policy_version"], "reason": reason, "record": record}
        restored = registry.rollback(baseline["policy_version"])
        return {"deployed": False, "active_policy": restored.get("policy_version"), "reason": reason, "rollback": restored, "record": record}
