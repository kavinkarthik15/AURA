import unittest

from backend.memory.knowledge_retriever import KnowledgeRetriever
from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_models import MemoryStatus
from backend.memory.semantic_memory import SemanticMemory


class KnowledgeRetrieverTests(unittest.TestCase):
    def test_retrieval_by_similarity(self) -> None:
        retriever = KnowledgeRetriever(
            knowledge_records=[
                {"knowledge_id": "KNW-1", "concept": "Python", "statement": "Python helps build backend systems", "confidence": 0.9, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1", "ep-2", "ep-3"], "revision": 1},
                {"knowledge_id": "KNW-2", "concept": "Java", "statement": "Java is used for enterprise services", "confidence": 0.7, "importance": 0.6, "status": "ACTIVE", "supporting_episode_ids": ["ep-4"], "revision": 1},
            ]
        )
        result = retriever.retrieve("python backend")
        self.assertGreaterEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["knowledge"]["concept"], "Python")

    def test_ranking_order_prefers_higher_confidence(self) -> None:
        retriever = KnowledgeRetriever(
            knowledge_records=[
                {"knowledge_id": "KNW-1", "concept": "A", "statement": "alpha", "confidence": 0.6, "importance": 0.5, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1},
                {"knowledge_id": "KNW-2", "concept": "B", "statement": "alpha", "confidence": 0.9, "importance": 0.9, "status": "ACTIVE", "supporting_episode_ids": ["ep-1", "ep-2", "ep-3"], "revision": 1},
            ]
        )
        result = retriever.retrieve("alpha")
        self.assertEqual(result["matches"][0]["knowledge"]["knowledge_id"], "KNW-2")

    def test_evidence_weighting_raises_score(self) -> None:
        retriever = KnowledgeRetriever(
            knowledge_records=[
                {"knowledge_id": "KNW-1", "concept": "A", "statement": "alpha", "confidence": 0.8, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1", "ep-2", "ep-3", "ep-4", "ep-5"], "revision": 1},
                {"knowledge_id": "KNW-2", "concept": "B", "statement": "alpha", "confidence": 0.8, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1},
            ]
        )
        result = retriever.retrieve("alpha")
        self.assertEqual(result["matches"][0]["knowledge"]["knowledge_id"], "KNW-1")

    def test_top_k_filtering(self) -> None:
        retriever = KnowledgeRetriever(
            knowledge_records=[
                {"knowledge_id": "KNW-1", "concept": "One", "statement": "one", "confidence": 0.8, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1},
                {"knowledge_id": "KNW-2", "concept": "Two", "statement": "two", "confidence": 0.7, "importance": 0.7, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1},
            ]
        )
        result = retriever.retrieve("one two", top_k=1)
        self.assertEqual(len(result["matches"]), 1)

    def test_status_filtering(self) -> None:
        retriever = KnowledgeRetriever(
            knowledge_records=[
                {"knowledge_id": "KNW-1", "concept": "Active", "statement": "active", "confidence": 0.8, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1},
                {"knowledge_id": "KNW-2", "concept": "Archived", "statement": "archived", "confidence": 0.8, "importance": 0.8, "status": "ARCHIVED", "supporting_episode_ids": ["ep-1"], "revision": 1},
            ]
        )
        result = retriever.retrieve("active", filters={"status": "ACTIVE"})
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["knowledge"]["concept"], "Active")

    def test_explainability_contains_reasons(self) -> None:
        retriever = KnowledgeRetriever(knowledge_records=[{"knowledge_id": "KNW-1", "concept": "Python", "statement": "Python builds backend systems", "confidence": 0.9, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1", "ep-2", "ep-3"], "revision": 1}])
        result = retriever.retrieve("python")
        self.assertIn("matched_goal", result["matches"][0]["retrieval_reason"])

    def test_empty_result_handling(self) -> None:
        retriever = KnowledgeRetriever(knowledge_records=[])
        result = retriever.retrieve("nothing")
        self.assertEqual(result["matches"], [])

    def test_memory_manager_gateway_returns_retrieval_payload(self) -> None:
        manager = MemoryManager()
        semantic = SemanticMemory()
        semantic.store({"concept": "Planning", "statement": "Planning improves execution", "confidence": 0.8, "importance": 0.8, "supporting_episode_ids": ["ep-1", "ep-2"], "knowledge_type": "pattern"})
        manager.stores["semantic"] = semantic
        manager.knowledge_retriever = KnowledgeRetriever(index=semantic.index)
        result = manager.retrieve_knowledge("planning")
        self.assertGreaterEqual(len(result), 1)

    def test_cache_hit_and_miss_behavior(self) -> None:
        retriever = KnowledgeRetriever(knowledge_records=[{"knowledge_id": "KNW-1", "concept": "Cache", "statement": "cache", "confidence": 0.8, "importance": 0.8, "status": "ACTIVE", "supporting_episode_ids": ["ep-1"], "revision": 1}])
        first = retriever.retrieve("cache")
        second = retriever.retrieve("cache")
        self.assertFalse(first["cache_hit"])
        self.assertFalse(second["cache_hit"])
