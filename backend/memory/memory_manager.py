from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.ai.reflection_memory import ReflectionMemory
from backend.memory.context_memory import ContextMemory
from backend.memory.episodic_memory import EpisodicMemory
from backend.memory.memory_registry import MemoryRegistry
from backend.memory.memory_interfaces import MemoryStore
from backend.memory.memory_policies import MemoryPolicies
from backend.memory.placeholder_store import PlaceholderMemoryStore
from backend.memory.reflection_memory_store import ReflectionMemoryStore
from backend.memory.semantic_memory import SemanticMemory
from backend.memory.working_memory import WorkingMemory
from backend.memory.knowledge_retriever import KnowledgeRetriever


class MemoryManager:
    """Single gateway that routes memory operations to specialized stores."""

    version = "memory_manager_v1"

    def __init__(
        self,
        episodic_store: EpisodicMemory | None = None,
        reflection_store: ReflectionMemoryStore | None = None,
        registry: MemoryRegistry | None = None,
        reflection_memory: ReflectionMemory | None = None,
        registry_path: Path | None = None,
        policies: MemoryPolicies | None = None,
    ) -> None:
        self.stores: Dict[str, MemoryStore] = {
            "working": WorkingMemory(),
            "episodic": episodic_store or EpisodicMemory(),
            "semantic": SemanticMemory(),
            "procedural": PlaceholderMemoryStore("procedural"),
            "reflection": reflection_store or ReflectionMemoryStore(reflection_memory),
            "context": ContextMemory(),
        }
        self.knowledge_retriever = KnowledgeRetriever(index=self.stores["semantic"].index)
        self.registry = registry or MemoryRegistry(registry_path)
        self.policies = policies or MemoryPolicies()
        self.registry.register(
            self.stores.keys(),
            {
                "episodic": "ExperienceRetriever",
                "mode": "foundation",
                "episodic_version": "episodic_memory_v1",
                "episodic_status": "active",
                "benchmark_status": "available",
                "policies": ["retrieval", "importance", "consolidation", "forgetting"],
            },
        )
        self.metrics: Dict[str, int] = {"retrieve": 0, "store": 0, "update": 0, "delete": 0}

    @property
    def episodic_memory(self) -> EpisodicMemory:
        return self.stores["episodic"]  # type: ignore[return-value]

    @property
    def working_memory(self) -> WorkingMemory:
        return self.stores["working"]  # type: ignore[return-value]

    def create_working_session(self) -> str:
        return self.working_memory.create_session()

    def end_working_session(self, session_id: str | None = None, retain: bool = False) -> Dict[str, Any] | None:
        return self.working_memory.end_session(session_id, retain)

    def set_working_goal(self, goal: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("goal", goal, session_id, importance=0.95)

    def add_working_experience(self, experience: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("experience", experience, session_id, importance=0.7)

    def add_candidate_plan(self, plan: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("candidate_plan", plan, session_id, importance=0.8)

    def set_working_strategy(self, strategy: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("strategy", strategy, session_id, importance=0.75)

    def add_working_constraint(self, constraint: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("constraint", constraint, session_id, importance=0.85)

    def set_working_confidence(self, confidence: float, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("confidence", confidence, session_id, importance=0.8)

    def store_working_reasoning(self, reasoning: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("reasoning", reasoning, session_id, importance=0.8)

    def store_working_reflection(self, reflection: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_working("reflection", reflection, session_id, importance=0.9)

    def working_snapshot(self, session_id: str | None = None) -> Dict[str, Any]:
        return self.working_memory.snapshot(session_id)

    def working_health(self) -> Dict[str, Any]:
        return self.working_memory.health()

    def retrieve_experiences(
        self,
        state: Dict[str, float],
        goal: str,
        actions: List[str] | None = None,
        top_k: int = 10,
        diversity_threshold: float | None = None,
    ) -> Dict[str, Any]:
        self.metrics["retrieve"] += 1
        return self.episodic_memory.retrieve_experiences(state, goal, actions, top_k, diversity_threshold)

    def compute_adaptive_weight(self, **kwargs: Any) -> float:
        return self.episodic_memory.compute_adaptive_weight(**kwargs)

    def get_analytics_summary(self) -> Dict[str, Any]:
        return self.episodic_memory.get_analytics_summary()

    def episodic_statistics(self) -> Dict[str, Any]:
        return self.episodic_memory.statistics()

    def revise_episodic(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        return self.episodic_memory.revise(memory_id, updates)

    def merge_episodic(self, memory_ids: List[str], updates: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        return self.episodic_memory.merge(memory_ids, updates)

    def archive_episodic(self, memory_id: str) -> bool:
        return self.episodic_memory.archive(memory_id)

    def relate_episodic(self, memory_id: str, related_memory_id: str) -> bool:
        return self.episodic_memory.relate(memory_id, related_memory_id)

    def store(self, memory_type: str, record: Dict[str, Any]) -> Dict[str, Any]:
        self.metrics["store"] += 1
        return self._get_store(memory_type).store(record)

    def store_knowledge(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.metrics["store"] += 1
        return self.store("semantic", record)

    def retrieve_knowledge(self, query: str, top_k: int = 10, filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        self.metrics["retrieve"] += 1
        if isinstance(self.stores["semantic"], SemanticMemory):
            result = self.knowledge_retriever.retrieve(query, top_k=top_k, filters=filters)
            matches: List[Dict[str, Any]] = []
            for item in result.get("matches", []):
                if isinstance(item, dict):
                    payload = dict(item.get("knowledge") or item)
                    for key, value in item.items():
                        if key != "knowledge" and key not in payload:
                            payload[key] = value
                    matches.append(payload)
                else:
                    payload = dict(getattr(item, "knowledge", {}) or {})
                    for key, value in vars(item).items():
                        if key != "knowledge" and key not in payload:
                            payload[key] = value
                    matches.append(payload)
            return matches
        return self.retrieve("semantic", {"query": query}, top_k)

    def update_knowledge(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        self.metrics["update"] += 1
        return self.update("semantic", memory_id, updates)

    def archive_knowledge(self, memory_id: str) -> bool:
        self.metrics["update"] += 1
        return self._get_store("semantic").archive(memory_id)

    def delete_knowledge(self, memory_id: str) -> bool:
        self.metrics["delete"] += 1
        return self.delete("semantic", memory_id)

    def knowledge_statistics(self) -> Dict[str, Any]:
        return self.episodic_memory.statistics() if False else self._get_store("semantic").statistics()  # type: ignore[attr-defined]

    def revise_knowledge(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        return self._get_store("semantic").revise(memory_id, updates)

    def relate_knowledge(self, memory_id: str, related_memory_id: str) -> bool:
        return self._get_store("semantic").relate(memory_id, related_memory_id)

    def retrieve(
        self,
        memory_type: str | None = None,
        query: Dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        self.metrics["retrieve"] += 1
        if memory_type is not None:
            return self._get_store(memory_type).retrieve(query, top_k)
        return self.retrieve_auto(query, top_k)

    def retrieve_auto(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        query = query or {}
        records: List[Dict[str, Any]] = []
        for memory_type in self.policies.retrieval.select_memory_types(query):
            records.extend(self._get_store(memory_type).retrieve(query, top_k))
        return self.policies.importance.rank(records)[:top_k]

    def update(self, memory_type: str, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        self.metrics["update"] += 1
        return self._get_store(memory_type).update(memory_id, updates)

    def delete(self, memory_type: str, memory_id: str) -> bool:
        self.metrics["delete"] += 1
        return self._get_store(memory_type).delete(memory_id)

    def store_reflection(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        return self.store("reflection", reflection)

    def retrieve_reflections(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        return self.retrieve("reflection", query, top_k)

    def consolidate(self) -> Dict[str, Any]:
        return {memory_type: store.consolidate() for memory_type, store in self.stores.items()}

    def forget(self) -> Dict[str, Any]:
        return {memory_type: store.forget() for memory_type, store in self.stores.items()}

    def health(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "stores": list(self.stores),
            "policies": ["retrieval", "importance", "consolidation", "forgetting"],
            "episodic": {
                "version": "episodic_memory_v1",
                "implementation_status": "active",
                "benchmark_status": "available",
                "metrics": self.episodic_memory.statistics(),
            },
            "metrics": dict(self.metrics),
            "healthy": True,
        }

    def _get_store(self, memory_type: str) -> MemoryStore:
        try:
            return self.stores[memory_type]
        except KeyError as exc:
            raise ValueError(f"Unknown memory type: {memory_type}") from exc

    def _store_working(
        self,
        record_type: str,
        value: Any,
        session_id: str | None,
        importance: float,
    ) -> Dict[str, Any]:
        record = {"type": record_type, "value": value, "importance": importance}
        if session_id is not None:
            record["working_memory_id"] = session_id
        return self.store("working", record)
