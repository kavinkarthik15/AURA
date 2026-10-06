from __future__ import annotations

from typing import List

from backend.consolidation.knowledge_models import KnowledgeCandidate
from backend.consolidation.knowledge_registry import KnowledgeRegistry
from backend.consolidation.pattern_models import PatternCandidate


class KnowledgeGenerator:
    def __init__(self, registry: KnowledgeRegistry | None = None) -> None:
        self.registry = registry or KnowledgeRegistry()

    def generate(self, patterns: List[PatternCandidate]) -> List[KnowledgeCandidate]:
        candidates: List[KnowledgeCandidate] = []
        for pattern in patterns:
            candidate = self._from_pattern(pattern)
            if candidate is None:
                continue
            candidates.append(candidate)
            self.registry.record(
                {
                    "candidate_id": candidate.candidate_id,
                    "knowledge": candidate.knowledge,
                    "confidence": candidate.confidence,
                    "generated_from": candidate.generated_from,
                    "evidence": candidate.evidence,
                }
            )
        return candidates

    def _from_pattern(self, pattern: PatternCandidate) -> KnowledgeCandidate | None:
        if not pattern.episode_ids:
            return None

        mapping = {
            "Repeated Success": self._repeated_success_knowledge,
            "Repeated Failure": self._repeated_failure_knowledge,
            "Habit": self._habit_knowledge,
            "Preference": self._preference_knowledge,
            "Goal Progress": self._goal_progress_knowledge,
        }
        builder = mapping.get(pattern.pattern_type)
        if builder is None:
            return None
        return builder(pattern)

    def _repeated_success_knowledge(self, pattern: PatternCandidate) -> KnowledgeCandidate:
        return KnowledgeCandidate(
            knowledge="Successful outcomes have been repeatedly observed in this context.",
            confidence=round(min(0.65 + (pattern.confidence * 0.2), 0.95), 2),
            evidence=pattern.episode_ids,
            generated_from=pattern.pattern_type,
            summary=f"Generated from repeated success pattern with {pattern.support_count} episodes",
            metadata={"pattern_id": pattern.pattern_id, "support_count": pattern.support_count},
        )

    def _repeated_failure_knowledge(self, pattern: PatternCandidate) -> KnowledgeCandidate:
        return KnowledgeCandidate(
            knowledge="Repeated failures indicate a recurring challenge in this context.",
            confidence=round(min(0.6 + (pattern.confidence * 0.2), 0.95), 2),
            evidence=pattern.episode_ids,
            generated_from=pattern.pattern_type,
            summary=f"Generated from repeated failure pattern with {pattern.support_count} episodes",
            metadata={"pattern_id": pattern.pattern_id, "support_count": pattern.support_count},
        )

    def _habit_knowledge(self, pattern: PatternCandidate) -> KnowledgeCandidate:
        return KnowledgeCandidate(
            knowledge="A recurring habit has been identified in the observed experiences.",
            confidence=round(min(0.7 + (pattern.confidence * 0.15), 0.95), 2),
            evidence=pattern.episode_ids,
            generated_from=pattern.pattern_type,
            summary=f"Generated from habit pattern with {pattern.support_count} episodes",
            metadata={"pattern_id": pattern.pattern_id, "support_count": pattern.support_count},
        )

    def _preference_knowledge(self, pattern: PatternCandidate) -> KnowledgeCandidate:
        return KnowledgeCandidate(
            knowledge="A clear preference has been observed across the supporting experiences.",
            confidence=round(min(0.7 + (pattern.confidence * 0.15), 0.95), 2),
            evidence=pattern.episode_ids,
            generated_from=pattern.pattern_type,
            summary=f"Generated from preference pattern with {pattern.support_count} episodes",
            metadata={"pattern_id": pattern.pattern_id, "support_count": pattern.support_count},
        )

    def _goal_progress_knowledge(self, pattern: PatternCandidate) -> KnowledgeCandidate:
        return KnowledgeCandidate(
            knowledge="Goal progress is being made through the observed sequence of experiences.",
            confidence=round(min(0.72 + (pattern.confidence * 0.15), 0.95), 2),
            evidence=pattern.episode_ids,
            generated_from=pattern.pattern_type,
            summary=f"Generated from goal progress pattern with {pattern.support_count} episodes",
            metadata={"pattern_id": pattern.pattern_id, "support_count": pattern.support_count},
        )
