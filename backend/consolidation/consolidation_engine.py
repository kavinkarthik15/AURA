from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.consolidation.knowledge_generator import KnowledgeGenerator
from backend.consolidation.knowledge_merger import KnowledgeMerger
from backend.consolidation.knowledge_validator import KnowledgeValidator
from backend.consolidation.pattern_detector import PatternDetector
from backend.memory.memory_manager import MemoryManager
from backend.models.experience import Experience


class ConsolidationEngine:
    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        self.memory_manager = memory_manager or MemoryManager()
        self.pattern_detector = PatternDetector()
        self.knowledge_generator = KnowledgeGenerator()
        self.knowledge_validator = KnowledgeValidator()
        self.knowledge_merger = KnowledgeMerger()
        self.history: List[Dict[str, Any]] = []

    def run(self, experiences: List[Experience], threshold: int = 3) -> Dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        eligible_experiences = [experience for experience in experiences if self._eligible(experience)]
        patterns = self.pattern_detector.detect_patterns(eligible_experiences)

        candidates = self.knowledge_generator.generate(patterns)
        validations = self.knowledge_validator.validate(candidates)

        accepted = [candidate for candidate, validation in zip(candidates, validations) if validation.decision == "ACCEPT"]
        accepted_validations = [validation for validation in validations if validation.decision == "ACCEPT"]

        self.knowledge_merger.existing_knowledge = self._load_existing_knowledge()
        merge_decisions = self.knowledge_merger.decide(accepted_validations)

        semantic_changes: List[Dict[str, Any]] = []
        for candidate, validation, decision in zip(accepted, accepted_validations, merge_decisions):
            if decision.action == "CREATE":
                stored = self.memory_manager.store_knowledge(
                    {
                        "concept": candidate.generated_from,
                        "statement": candidate.knowledge,
                        "knowledge_type": "consolidated",
                        "confidence": candidate.confidence,
                        "importance": max(0.5, round(candidate.confidence, 2)),
                        "confidence_source": "ConsolidationEngine",
                        "importance_reason": candidate.generated_from,
                        "importance_source": "ConsolidationEngine",
                        "supporting_episode_ids": candidate.evidence,
                        "metadata": {
                            "pattern_type": candidate.generated_from,
                            "validation_score": validation.validation_score,
                            "decision": validation.decision,
                        },
                    }
                )
                semantic_changes.append({"action": "CREATE", "knowledge_id": stored["knowledge_id"]})
            elif decision.action in {"UPDATE", "MERGE"}:
                updated = self.memory_manager.update_knowledge(
                    decision.target_knowledge_id,
                    {
                        "statement": candidate.knowledge,
                        "confidence": candidate.confidence,
                        "supporting_episode_ids": candidate.evidence,
                        "metadata": {"updated_by": "ConsolidationEngine"},
                    },
                )
                semantic_changes.append({"action": decision.action, "knowledge_id": decision.target_knowledge_id, "result": updated})

        ended_at = datetime.now(timezone.utc)
        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        report = {
            "run_id": f"RUN-{uuid4().hex[:12].upper()}",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "experiences_processed": len(eligible_experiences),
            "patterns_detected": len(patterns),
            "candidates_generated": len(candidates),
            "accepted_candidates": len(accepted_validations),
            "rejected_candidates": len(validations) - len(accepted_validations),
            "semantic_changes": semantic_changes,
            "patterns": [pattern.pattern_type for pattern in patterns],
            "validation_decisions": [{"candidate_id": validation.candidate_id, "decision": validation.decision, "score": validation.validation_score} for validation in validations],
            "merge_decisions": [{"action": decision.action, "target_knowledge_id": decision.target_knowledge_id, "similarity": decision.similarity, "merge_reason": decision.merge_reason} for decision in merge_decisions],
            "metrics": {
                "patterns_analyzed": len(patterns),
                "candidates_generated": len(candidates),
                "accepted_count": len(accepted_validations),
                "rejected_count": len(validations) - len(accepted_validations),
                "created_count": sum(1 for change in semantic_changes if change["action"] == "CREATE"),
                "updated_count": sum(1 for change in semantic_changes if change["action"] == "UPDATE"),
                "merged_count": sum(1 for change in semantic_changes if change["action"] == "MERGE"),
                "ignored_count": len(merge_decisions) - sum(1 for change in semantic_changes if change["action"] != "IGNORE"),
                "execution_time_ms": execution_time_ms,
            },
            "errors": [],
        }
        self.history.append(report)
        return report

    def _eligible(self, experience: Experience) -> bool:
        context = experience.context or {}
        status = str(context.get("status", "")).upper()
        return status not in {"ARCHIVED", "DELETED", "DEPRECATED"}

    def _load_existing_knowledge(self) -> List[Any]:
        records = self.memory_manager.retrieve("semantic", {"query": ""}, top_k=50)
        return [
            type("RecordProxy", (), {"knowledge_id": record["knowledge_id"], "statement": record.get("statement", "")})()
            for record in records
        ]
