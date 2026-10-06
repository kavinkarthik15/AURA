from __future__ import annotations

from typing import List

from backend.consolidation.merge_models import MergeDecision
from backend.consolidation.validation_models import ValidatedKnowledgeCandidate
from backend.memory.memory_models import KnowledgeRecord


class KnowledgeMerger:
    def __init__(self, existing_knowledge: List[KnowledgeRecord] | None = None) -> None:
        self.existing_knowledge = existing_knowledge or []

    def decide(self, validated_candidates: List[ValidatedKnowledgeCandidate]) -> List[MergeDecision]:
        decisions: List[MergeDecision] = []
        for candidate in validated_candidates:
            decision = self._decide_for_candidate(candidate)
            decisions.append(decision)
        return decisions

    def _decide_for_candidate(self, candidate: ValidatedKnowledgeCandidate) -> MergeDecision:
        if candidate.decision != "ACCEPT":
            return MergeDecision(action="IGNORE", merge_reason="Candidate was not accepted for promotion", metadata={"candidate_id": candidate.candidate_id})

        for record in self.existing_knowledge:
            similarity = self._similarity(candidate, record)
            if similarity >= 0.8:
                return MergeDecision(
                    action="MERGE",
                    target_knowledge_id=record.knowledge_id,
                    similarity=round(similarity, 2),
                    merge_reason="Existing knowledge is highly similar",
                    confidence_change=0.1,
                    revision_increment=1,
                    updated_evidence=list(candidate.metadata.get("evidence", [])),
                    conflicts=[],
                    metadata={"candidate_id": candidate.candidate_id, "existing_knowledge_id": record.knowledge_id},
                )
            if similarity >= 0.5:
                return MergeDecision(
                    action="UPDATE",
                    target_knowledge_id=record.knowledge_id,
                    similarity=round(similarity, 2),
                    merge_reason="Existing knowledge overlaps and should be refreshed",
                    confidence_change=0.05,
                    revision_increment=1,
                    updated_evidence=list(candidate.metadata.get("evidence", [])),
                    conflicts=[],
                    metadata={"candidate_id": candidate.candidate_id, "existing_knowledge_id": record.knowledge_id},
                )

        return MergeDecision(
            action="CREATE",
            similarity=0.0,
            merge_reason="No sufficiently similar knowledge exists",
            confidence_change=0.0,
            revision_increment=1,
            updated_evidence=list(candidate.metadata.get("evidence", [])),
            conflicts=[],
            metadata={"candidate_id": candidate.candidate_id},
        )

    def _similarity(self, candidate: ValidatedKnowledgeCandidate, record: KnowledgeRecord) -> float:
        candidate_text = str(candidate.metadata.get("knowledge", "")).lower()
        record_text = str(record.statement).lower()
        if not candidate_text or not record_text:
            return 0.0
        if candidate_text == record_text:
            return 1.0
        common = len(set(candidate_text.split()) & set(record_text.split()))
        total = len(set(candidate_text.split()) | set(record_text.split()))
        return round(common / total if total else 0.0, 2)
