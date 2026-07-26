from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.ai.experience_embeddings import ExperienceEmbedder
from backend.ai.state_similarity import combined_similarity
from backend.config.retrieval_config import RETRIEVAL_ANALYTICS_ENABLED, RETRIEVAL_CACHE_ENABLED, RETRIEVAL_DECAY_HALF_LIFE_DAYS, RETRIEVAL_DIVERSITY_THRESHOLD, RETRIEVAL_EMBEDDING_ENABLED, RETRIEVAL_METRIC, RETRIEVAL_TOP_K


@dataclass
class RetrievedExperience:
    experience_id: str
    similarity: float
    state: Dict[str, Any]
    goal: str
    actions: List[str]
    completed_actions: List[str]
    success: bool
    goal_completion: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class ExperienceRetriever:
    def __init__(self, experiences: Iterable[Dict[str, Any]] | None = None, index_path: Path | None = None, metric: str = RETRIEVAL_METRIC, cache_enabled: bool = RETRIEVAL_CACHE_ENABLED) -> None:
        self.index_path = index_path or Path(__file__).resolve().parents[1] / "data" / "retrieval_index.json"
        self.metric = metric
        self.cache_enabled = cache_enabled
        self.experiences = list(experiences or [])
        self._cache: Dict[str, List[RetrievedExperience]] = {}
        self.embedder = ExperienceEmbedder()
        self.analytics_enabled = RETRIEVAL_ANALYTICS_ENABLED
        self.analytics: Dict[str, Dict[str, Any]] = {}

    def build_index(self, experiences: Iterable[Dict[str, Any]] | None = None) -> Path:
        records = list(experiences or self.experiences)
        self.experiences = records
        index = []
        for record in records:
            index.append({
                "experience_id": record.get("experience_id", ""),
                "state": record.get("initial_state", record.get("state_before", {})),
                "goal": record.get("goal_name", record.get("goal", "")),
                "actions": record.get("actions", [record.get("action", "")]),
                "completed_actions": record.get("completed_actions", []),
                "success": bool(record.get("success", record.get("outcome_value", 0) > 0)),
                "goal_completion": float(record.get("goal_completion", record.get("outcome_value", 0.0) or 0.0)),
                "timestamp": record.get("timestamp") or record.get("created_at") or record.get("created") or "",
            })
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        self.embedder.fit(index)
        return self.index_path

    def load_index(self) -> List[Dict[str, Any]]:
        if not self.index_path.exists():
            self.build_index()
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def retrieve(self, state: Dict[str, float], goal: str, actions: List[str] | None = None, top_k: int = RETRIEVAL_TOP_K, diversity_threshold: float = RETRIEVAL_DIVERSITY_THRESHOLD) -> Dict[str, Any]:
        started = time.perf_counter()
        actions = actions or []
        cache_key = json.dumps([state, goal, actions, top_k, self.metric], sort_keys=True)
        if self.cache_enabled and cache_key in self._cache:
            matches = self._cache[cache_key]
            return {"matches": matches, "retrieval_time_ms": 0.0, "cache_hit": True}
        scored: List[RetrievedExperience] = []
        for record in self.load_index():
            similarity = self._compute_similarity(state, goal, actions, record)
            freshness = self._freshness_score(record.get("timestamp", ""))
            effective_similarity = round(similarity * (1.0 if record.get("success", False) else 0.8) * freshness, 4)
            scored.append(RetrievedExperience(
                experience_id=record.get("experience_id", ""),
                similarity=effective_similarity,
                state=record.get("state", {}),
                goal=record.get("goal", ""),
                actions=record.get("actions", []),
                completed_actions=record.get("completed_actions", []),
                success=record.get("success", False),
                goal_completion=record.get("goal_completion", 0.0),
                reason="A similar previous execution succeeded." if record.get("success", False) else "A similar previous execution was retrieved for comparison.",
            ))
        scored.sort(key=lambda item: (item.similarity, item.success, item.goal_completion), reverse=True)
        selected: List[RetrievedExperience] = []
        for candidate in scored:
            if len(selected) >= top_k:
                break
            if any(self._diversity_overlap(candidate, item) >= diversity_threshold for item in selected):
                continue
            selected.append(candidate)
        if self.cache_enabled:
            self._cache[cache_key] = selected
        retrieval_time_ms = round((time.perf_counter() - started) * 1000, 4)
        if self.analytics_enabled:
            for item in selected:
                self.record_analytics(item.experience_id, item.similarity, retrieval_time_ms, 1.0 if item.success else 0.0, float(item.goal_completion))
        return {"matches": selected, "retrieval_time_ms": retrieval_time_ms, "cache_hit": False}

    def compute_adaptive_weight(self, policy_confidence: float, retrieval_confidence: float, goal_type: str = "default") -> float:
        goal_bias = {"exploration": 0.35, "optimization": 0.55, "stability": 0.25}.get(goal_type.lower(), 0.4)
        confidence_gap = max(0.0, retrieval_confidence - policy_confidence)
        return round(max(0.0, min(1.0, goal_bias + 0.3 * confidence_gap)), 4)

    def record_analytics(self, experience_id: str, similarity: float, latency_ms: float, success: float, goal_completion: float) -> None:
        if not self.analytics_enabled:
            return
        entry = self.analytics.setdefault(experience_id, {"retrieval_count": 0, "total_similarity": 0.0, "total_latency_ms": 0.0, "success_count": 0.0, "total_goal_completion": 0.0})
        entry["retrieval_count"] += 1
        entry["total_similarity"] += similarity
        entry["total_latency_ms"] += latency_ms
        entry["success_count"] += success
        entry["total_goal_completion"] += goal_completion

    def get_analytics_summary(self) -> Dict[str, Any]:
        if not self.analytics:
            return {"retrieval_count": 0, "average_similarity": 0.0, "average_latency_ms": 0.0, "success_rate": 0.0, "average_goal_completion": 0.0}
        total_retrievals = sum(entry["retrieval_count"] for entry in self.analytics.values())
        return {
            "retrieval_count": total_retrievals,
            "average_similarity": round(sum(entry["total_similarity"] for entry in self.analytics.values()) / total_retrievals, 4),
            "average_latency_ms": round(sum(entry["total_latency_ms"] for entry in self.analytics.values()) / total_retrievals, 4),
            "success_rate": round(sum(entry["success_count"] for entry in self.analytics.values()) / total_retrievals, 4),
            "average_goal_completion": round(sum(entry["total_goal_completion"] for entry in self.analytics.values()) / total_retrievals, 4),
        }

    def _compute_similarity(self, state: Dict[str, float], goal: str, actions: List[str], record: Dict[str, Any]) -> float:
        base_similarity = combined_similarity(state, goal, actions, record.get("state", {}), record.get("goal", ""), record.get("actions", []), metric=self.metric)
        if RETRIEVAL_EMBEDDING_ENABLED:
            embedding_similarity = self.embedder.similarity({"goal": goal, "actions": actions, "state": state}, {"goal": record.get("goal", ""), "actions": record.get("actions", []), "state": record.get("state", {})})
            return round((0.7 * base_similarity) + (0.3 * embedding_similarity), 4)
        return base_similarity

    def _freshness_score(self, timestamp: str) -> float:
        if not timestamp:
            return 1.0
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return 1.0
        age_days = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400.0)
        if age_days <= 0:
            return 1.0
        half_life = max(1.0, RETRIEVAL_DECAY_HALF_LIFE_DAYS)
        return round(math.pow(0.5, age_days / half_life), 4)

    def _diversity_overlap(self, left: RetrievedExperience, right: RetrievedExperience) -> float:
        return combined_similarity(left.state, "", left.actions, right.state, "", right.actions, metric="cosine")