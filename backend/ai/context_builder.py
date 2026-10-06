from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.memory.memory_manager import MemoryManager


@dataclass
class PlanningContext:
    goal: str
    current_state: Dict[str, Any]
    working_memory: List[Dict[str, Any]] = field(default_factory=list)
    relevant_experiences: List[Dict[str, Any]] = field(default_factory=list)
    relevant_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    relevant_reflections: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    habits: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)
    candidate_plans: List[Any] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    context_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "current_state": self.current_state,
            "working_memory": self.working_memory,
            "relevant_experiences": self.relevant_experiences,
            "relevant_knowledge": self.relevant_knowledge,
            "relevant_reflections": self.relevant_reflections,
            "constraints": self.constraints,
            "preferences": self.preferences,
            "habits": self.habits,
            "failure_patterns": self.failure_patterns,
            "success_patterns": self.success_patterns,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "context_summary": self.context_summary,
        }


class ContextBuilder:
    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        # Do not implicitly create a MemoryManager; allow explicit injection or None.
        # Tests and callers expect `ContextBuilder()` without args to produce an
        # empty context (no preloaded knowledge), so avoid auto-instantiation.
        self.memory_manager = memory_manager

    def build(self, goal: str, current_state: Dict[str, Any], session_id: str | None = None) -> PlanningContext:
        working_memory = []
        if self.memory_manager is not None:
            snapshot = self.memory_manager.working_snapshot(session_id)
            working_memory = list(snapshot.get("records", []))

        relevant_experiences = []
        if self.memory_manager is not None and goal:
            relevant_experiences = [
                item
                for item in self.memory_manager.retrieve_experiences(
                    state=current_state,
                    goal=goal,
                    top_k=3,
                ).get("matches", [])
            ]

        relevant_knowledge = []
        if self.memory_manager is not None and goal:
            relevant_knowledge = self.memory_manager.retrieve_knowledge(goal, top_k=3)
            if not relevant_knowledge:
                relevant_knowledge = self.memory_manager.retrieve_knowledge("", top_k=3)

        relevant_reflections = []
        if self.memory_manager is not None:
            relevant_reflections = self.memory_manager.retrieve_reflections({"goal": goal}, top_k=3)

        constraints = [item.get("value") for item in working_memory if item.get("type") == "constraint"]
        preferences = [item.get("value") for item in working_memory if item.get("type") == "preference"]
        habits = [item.get("value") for item in working_memory if item.get("type") == "habit"]
        failure_patterns = [item.get("value") for item in working_memory if item.get("type") == "failure_pattern"]
        success_patterns = [item.get("value") for item in working_memory if item.get("type") == "success_pattern"]
        candidate_plans = [item.get("value") for item in working_memory if item.get("type") == "candidate_plan"]
        patterns = list({*failure_patterns, *success_patterns})

        evidence = []
        evidence.extend([str(item.get("knowledge_id", "")) for item in relevant_knowledge if item.get("knowledge_id")])
        for item in relevant_experiences:
            if hasattr(item, "memory_id") and getattr(item, "memory_id"):
                evidence.append(str(getattr(item, "memory_id")))
            elif hasattr(item, "experience_id") and getattr(item, "experience_id"):
                evidence.append(str(getattr(item, "experience_id")))
        evidence.extend([str(item.get("goal", "")) for item in relevant_reflections if item.get("goal")])

        confidence = round(min(0.99, 0.35 + (0.15 if relevant_experiences else 0.0) + (0.15 if relevant_knowledge else 0.0) + (0.1 if relevant_reflections else 0.0)), 4)
        summary_parts = [goal, str(current_state)]
        if relevant_knowledge:
            summary_parts.append("knowledge")
        if relevant_experiences:
            summary_parts.append("experiences")
        if working_memory:
            summary_parts.append("working-memory")
        context_summary = " | ".join(summary_parts)

        return PlanningContext(
            goal=goal,
            current_state=current_state,
            working_memory=working_memory,
            relevant_experiences=relevant_experiences,
            relevant_knowledge=relevant_knowledge,
            relevant_reflections=relevant_reflections,
            constraints=[str(item) for item in constraints if item is not None],
            preferences=[str(item) for item in preferences if item is not None],
            habits=[str(item) for item in habits if item is not None],
            failure_patterns=[str(item) for item in failure_patterns if item is not None],
            success_patterns=[str(item) for item in success_patterns if item is not None],
            candidate_plans=[item for item in candidate_plans if item is not None],
            patterns=[str(item) for item in patterns if item is not None],
            confidence=confidence,
            evidence=evidence,
            context_summary=context_summary,
        )
