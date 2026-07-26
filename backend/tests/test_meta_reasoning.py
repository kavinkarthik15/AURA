import tempfile
import unittest
from pathlib import Path

from backend.ai.assumption_detector import AssumptionDetector
from backend.ai.meta_learning import MetaLearningLog
from backend.ai.meta_reasoner import MetaReasoner
from backend.ai.reflection_dashboard import ReflectionDashboard
from backend.ai.reflection_memory import ReflectionMemory
from backend.ai.reflection_registry import ReflectionRegistry
from backend.ai.self_critique import SelfCritiqueEngine
from backend.ai.strategy_selector import StrategySelector
from backend.ai.meta_reasoning_metrics import MetaReasoningMetrics
from backend.services.system_benchmark import SystemBenchmark


class MetaReasoningTests(unittest.TestCase):
    def test_meta_reasoner_reflects_on_reasoning_trace(self) -> None:
        reasoner = MetaReasoner()
        result = reasoner.evaluate(
            reasoning_trace={"confidence": 0.62, "coverage": 0.4},
            reasoning_metadata={"consistency_status": {"consistent": False}},
            confidence_breakdown={"retrieval": 0.25, "policy": 0.5},
            retrieved_experiences=[],
            goal="Placement",
            assumptions=[{"assumption": "skill_level", "category": "Skill Assumptions", "value": 80, "supported": False}],
            contributors=["reasoner", "retrieval"],
        )
        self.assertIn("decision", result)
        self.assertEqual(result["contributors"], ["reasoner", "retrieval"])
        self.assertLess(result["confidence"], 1.0)
        self.assertGreaterEqual(result["reflection_score"], 0.0)

    def test_assumption_detector_and_self_critique(self) -> None:
        detector = AssumptionDetector()
        assumptions = detector.detect(
            goal="Placement",
            context={"time_available_hours": 3, "skill_level": 80, "internet_available": True},
            evidence={"skill_level": False, "time_available_hours": True},
        )
        self.assertTrue(any(item["assumption"] == "skill_level" for item in assumptions))

        critique = SelfCritiqueEngine().critique(
            confidence=0.6,
            consistency=False,
            evidence_count=1,
            counterfactuals=[]
        )
        self.assertIn("recommendation", critique)
        self.assertEqual(critique["status"], "needs_replanning")

    def test_strategy_selector_memory_dashboard_and_metrics(self) -> None:
        selector = StrategySelector()
        selection = selector.select(goal="Novel Goal", confidence=0.55, evidence_count=1, contradictions=True)
        self.assertIn("strategy", selection)

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ReflectionMemory(Path(tmpdir) / "reflections.json")
            memory.record_pre_execution(
                plan="A",
                prediction="uncertain",
                assumptions=[],
                evidence_sufficiency=0.3,
            )
            stored = memory.list_entries()
            self.assertEqual(len(stored), 1)

            dashboard = ReflectionDashboard()
            summary = dashboard.summarize([{"reflection_score": 0.7}, {"reflection_score": 0.8}])
            self.assertIn("average_reflection_score", summary)

            metrics = MetaReasoningMetrics().evaluate(
                reflection_accuracy=0.82,
                replanning_rate=0.15,
                assumption_precision=0.78,
                self_critique_accuracy=0.8,
                strategy_selection_accuracy=0.85,
                evidence_sufficiency_rate=0.83,
                reflection_agreement_rate=0.8,
                false_replan_rate=0.05,
                reflection_improvement_rate=0.12,
                calibration_error=0.1,
            )
            self.assertGreaterEqual(metrics["overall_meta_reasoning_score"], 0.68)

            benchmark = SystemBenchmark()
            score = benchmark.evaluate(
                goal_success=0.82,
                planning_accuracy=0.78,
                recommendation_accuracy=0.79,
                policy_accuracy=0.8,
                retrieval_accuracy=0.76,
                reasoning_consistency=0.74,
                counterfactual_quality=0.72,
                execution_success=0.81,
                learning_improvement=0.18,
                reflection_score=0.83,
                self_critique_score=0.8,
            )
            self.assertIn("overall_intelligence_score_v2", score)

    def test_meta_reasoner_handles_missing_assumptions(self) -> None:
        reasoner = MetaReasoner()
        result = reasoner.evaluate(
            reasoning_trace={"confidence": 0.55, "coverage": 0.3},
            reasoning_metadata={"consistency_status": {"consistent": True}},
            confidence_breakdown={"retrieval": 0.4, "policy": 0.6},
            retrieved_experiences=[],
            goal="Exploration",
            assumptions=[],
            contributors=["reasoner"],
        )
        self.assertEqual(result["decision"], "request_more_information")
        self.assertEqual(result["recommended_action"], "gather_additional_information")

    def test_meta_reasoner_rejects_contradictory_evidence(self) -> None:
        reasoner = MetaReasoner()
        result = reasoner.evaluate(
            reasoning_trace={"confidence": 0.85, "coverage": 0.9},
            reasoning_metadata={"consistency_status": {"consistent": False}},
            confidence_breakdown={"retrieval": 0.8, "policy": 0.7},
            retrieved_experiences=[{"experience_id": "exp1", "similarity": 0.9, "success": True}],
            goal="Conflict Goal",
            assumptions=[{"assumption": "internet_available", "category": "Environmental Assumptions", "value": True, "supported": True}],
            contributors=["reasoner", "retrieval", "policy"],
        )
        self.assertEqual(result["decision"], "reject")

    def test_meta_reasoner_accepts_high_confidence_strong_evidence(self) -> None:
        reasoner = MetaReasoner()
        result = reasoner.evaluate(
            reasoning_trace={"confidence": 0.95, "coverage": 0.95},
            reasoning_metadata={"consistency_status": {"consistent": True}},
            confidence_breakdown={"retrieval": 0.9, "policy": 0.85},
            retrieved_experiences=[{"experience_id": "exp2", "similarity": 0.94, "success": True}],
            goal="Stable Goal",
            assumptions=[{"assumption": "skill_level", "category": "Skill Assumptions", "value": 90, "supported": True}],
            contributors=["reasoner", "policy"],
        )
        self.assertEqual(result["decision"], "accept")

    def test_reflection_registry_records_reflection_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ReflectionRegistry(Path(tmpdir) / "reflection_registry.json")
            record = registry.register(
                reflection_version="reflection_v1",
                thresholds={"evidence_sufficiency": 0.6},
                metrics={"reflection_score": 0.82},
                benchmark_results={"overall_intelligence_score": 0.9},
                release_date="2026-07-26",
            )
            self.assertEqual(record["reflection_version"], "reflection_v1")
            self.assertEqual(registry.latest()["reflection_version"], "reflection_v1")

    def test_meta_learning_reinforces_successful_execution(self) -> None:
        logger = MetaLearningLog()
        record = logger.record(
            reasoning_strategy="beam_search_counterfactuals",
            reflection_score=0.88,
            execution_success=True,
            lesson="keep strategy",
            plan="A -> B",
        )
        self.assertEqual(record["reinforcement"], "reinforce")


if __name__ == "__main__":
    unittest.main()
