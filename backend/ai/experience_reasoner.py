from __future__ import annotations

from typing import Any, Dict, List

from backend.memory.memory_manager import MemoryManager
from backend.ai.reasoning_confidence import ReasoningConfidenceModel


class ExperienceReasoner:
    def __init__(self, memory_manager: MemoryManager | None = None, session_id: str | None = None) -> None:
        self.version = "reasoning_v1"
        self.memory_manager = memory_manager
        self.session_id = session_id

    def analyze(self, experiences: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        if experiences is None and self.memory_manager is not None:
            experiences = [
                record["value"]
                for record in self.memory_manager.retrieve(
                    "working", {"working_memory_id": self.session_id, "type": "experience"}
                )
            ]
        experiences = experiences or []
        successful_patterns: List[str] = []
        failure_patterns: List[str] = []
        repeated_mistakes: List[str] = []

        for experience in experiences:
            actions = experience.get("actions") or []
            completed = experience.get("completed_actions") or []
            if experience.get("success"):
                if actions:
                    successful_patterns.extend([str(action) for action in actions])
                if completed:
                    successful_patterns.extend([str(action) for action in completed])
            else:
                if actions:
                    failure_patterns.extend([str(action) for action in actions])
                if completed:
                    failure_patterns.extend([str(action) for action in completed])
                if completed and actions:
                    repeated_mistakes.extend([str(action) for action in completed if action in actions])

        unique_successes = sorted(set(successful_patterns))
        unique_failures = sorted(set(failure_patterns))
        unique_mistakes = sorted(set(repeated_mistakes))

        confidence = round(min(0.99, 0.5 + (len(experiences) * 0.03) + (0.05 if unique_successes and unique_failures else 0.0)), 2)
        reasoning_confidence = ReasoningConfidenceModel().score(len(experiences), len(unique_failures), 0.8, confidence)
        result = {
            "successful_patterns": unique_successes[:5],
            "failure_patterns": unique_failures[:5],
            "repeated_mistakes": unique_mistakes[:5],
            "confidence": confidence,
            "evidence_count": len(experiences),
            "reasoning_confidence": reasoning_confidence["reasoning_confidence"],
            "evidence_support": reasoning_confidence["evidence_support"],
            "contradictions": reasoning_confidence["contradictions"],
            "coverage": reasoning_confidence["coverage"],
        }
        if self.memory_manager is not None:
            self.memory_manager.store_working_reasoning(result, self.session_id)
        return result
