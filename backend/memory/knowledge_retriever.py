from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.memory.knowledge_index import KnowledgeIndex


class RetrievedKnowledge:
    def __init__(
        self,
        knowledge: Dict[str, Any],
        similarity: float,
        confidence: float,
        evidence_strength: float,
        retrieval_reason: List[str],
        retrieval_strategy: str,
        matched_terms: List[str],
        score: float,
    ) -> None:
        self.knowledge = knowledge
        self.similarity = similarity
        self.confidence = confidence
        self.evidence_strength = evidence_strength
        self.retrieval_reason = retrieval_reason
        self.retrieval_strategy = retrieval_strategy
        self.matched_terms = matched_terms
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge": self.knowledge,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "evidence_strength": self.evidence_strength,
            "retrieval_reason": self.retrieval_reason,
            "retrieval_strategy": self.retrieval_strategy,
            "matched_terms": self.matched_terms,
            "score": self.score,
        }


class KnowledgeRetriever:
    def __init__(self, knowledge_records: Iterable[Dict[str, Any]] | None = None, index_path: Path | None = None, index: KnowledgeIndex | None = None) -> None:
        self.index_path = index_path or Path(__file__).resolve().parent / "knowledge_index.json"
        # Track whether the caller explicitly provided a knowledge_records iterable.
        # If they did (even if empty), treat it as authoritative and do not load
        # the repository index file.
        self._records_provided = knowledge_records is not None
        self.knowledge_records = list(knowledge_records or [])
        self.index = index
        self._cache: Dict[str, Dict[str, Any]] = {}

    def build_index(self, knowledge_records: Iterable[Dict[str, Any]] | None = None) -> Path:
        records = list(knowledge_records or self.knowledge_records)
        self.knowledge_records = records
        if self.index is not None:
            self.index.rebuild(records)
            self._cache.clear()
            return self.index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return self.index_path

    def retrieve(self, query: str, top_k: int = 10, filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        filters = filters or {}
        cache_key = json.dumps([query, top_k, filters], sort_keys=True)
        if cache_key in self._cache:
            return self._cache[cache_key]

        records = self.load_index()
        if not records and self.knowledge_records:
            records = self.knowledge_records
        scored: List[RetrievedKnowledge] = []
        for record in records:
            if self._filter_record(record, filters) is False:
                continue
            if record.get("status", "ACTIVE") != "ACTIVE":
                continue
            similarity = self._similarity(query, record)
            if similarity <= 0.0:
                continue
            confidence = float(record.get("confidence", 0.5))
            evidence_strength = self._evidence_strength(record)
            retrieval_frequency = float(record.get("metadata", {}).get("retrieval_count", 0)) / 10.0
            score = round((0.45 * similarity) + (0.30 * confidence) + (0.20 * evidence_strength) + (0.05 * retrieval_frequency), 4)
            matched_terms = self._matched_terms(query, record)
            retrieval_reason = self._build_reason(record, similarity, confidence, evidence_strength, matched_terms)
            scored.append(
                RetrievedKnowledge(
                    knowledge=record,
                    similarity=round(similarity, 4),
                    confidence=round(confidence, 4),
                    evidence_strength=round(evidence_strength, 4),
                    retrieval_reason=retrieval_reason,
                    retrieval_strategy="semantic",
                    matched_terms=matched_terms,
                    score=score,
                )
            )

        if not scored and query.strip():
            for record in records:
                if self._filter_record(record, filters) is False:
                    continue
                if record.get("status", "ACTIVE") != "ACTIVE":
                    continue
                confidence = float(record.get("confidence", 0.5))
                evidence_strength = self._evidence_strength(record)
                retrieval_frequency = float(record.get("metadata", {}).get("retrieval_count", 0)) / 10.0
                score = round((0.30 * confidence) + (0.45 * evidence_strength) + (0.25 * retrieval_frequency), 4)
                matched_terms = self._matched_terms(query, record)
                retrieval_reason = ["fallback_retrieval"]
                scored.append(
                    RetrievedKnowledge(
                        knowledge=record,
                        similarity=0.0,
                        confidence=round(confidence, 4),
                        evidence_strength=round(evidence_strength, 4),
                        retrieval_reason=retrieval_reason,
                        retrieval_strategy="fallback",
                        matched_terms=matched_terms,
                        score=score,
                    )
                )

        scored.sort(key=lambda item: (item.score, item.confidence, item.similarity), reverse=True)
        selected = scored[:top_k]
        result = {
            "matches": [item.to_dict() for item in selected],
            "retrieval_time_ms": 0.0,
            "cache_hit": False,
        }
        self._cache[cache_key] = result
        return result

    def load_index(self) -> List[Dict[str, Any]]:
        # If the caller explicitly provided knowledge_records (even empty),
        # prefer that and do not read the on-disk index.
        if self._records_provided:
            return list(self.knowledge_records)
        if self.index is not None:
            return self.index.records()
        if not self.index_path.exists():
            self.build_index()
            return list(self.knowledge_records)
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except json.JSONDecodeError:
            self.build_index()
            return list(self.knowledge_records)

    def _similarity(self, query: str, record: Dict[str, Any]) -> float:
        text = f"{record.get('concept', '')} {record.get('statement', '')} {record.get('knowledge_type', '')}".lower()
        query_terms = re.findall(r"\w+", query.lower())
        if not query_terms:
            return 0.0
        overlap = sum(1 for term in query_terms if term in text)
        base = overlap / max(1, len(query_terms))
        if overlap == 0 and query_terms:
            return 0.0
        return round(min(1.0, base + 0.2), 4)

    def _evidence_strength(self, record: Dict[str, Any]) -> float:
        supporting_ids = record.get("supporting_episode_ids", []) or []
        if not supporting_ids:
            return 0.0
        return round(min(1.0, len(supporting_ids) / 10.0), 4)

    def _matched_terms(self, query: str, record: Dict[str, Any]) -> List[str]:
        text = f"{record.get('concept', '')} {record.get('statement', '')}".lower()
        query_terms = re.findall(r"\w+", query.lower())
        return [term for term in query_terms if term in text]

    def _build_reason(self, record: Dict[str, Any], similarity: float, confidence: float, evidence_strength: float, matched_terms: List[str]) -> List[str]:
        reasons: List[str] = []
        if matched_terms:
            reasons.append("matched_goal")
        if similarity >= 0.5:
            reasons.append("high_similarity")
        if confidence >= 0.7:
            reasons.append("high_confidence")
        if evidence_strength >= 0.3:
            reasons.append("supported_by_multiple_experiences")
        return reasons or ["weak_match"]

    def _filter_record(self, record: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        if filters.get("confidence") is not None and float(record.get("confidence", 0.0)) < float(filters["confidence"]):
            return False
        if filters.get("knowledge_type") and str(record.get("knowledge_type", "")).lower() != str(filters["knowledge_type"]).lower():
            return False
        if filters.get("status") and str(record.get("status", "ACTIVE")).upper() != str(filters["status"]).upper():
            return False
        if filters.get("revision") is not None and int(record.get("revision", 1)) < int(filters["revision"]):
            return False
        if filters.get("created_after") is not None:
            created_at = record.get("created_at")
            if isinstance(created_at, str) and created_at < filters["created_after"]:
                return False
        if filters.get("updated_after") is not None:
            updated_at = record.get("updated_at")
            if isinstance(updated_at, str) and updated_at < filters["updated_after"]:
                return False
        return True
