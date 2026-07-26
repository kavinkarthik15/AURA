import json
import tempfile
import unittest
from pathlib import Path

from backend.ai.research_benchmark import ResearchBenchmark
from backend.ai.research_registry import ResearchRegistry
from backend.ai.research_report import ResearchReportGenerator
from backend.ai.system_registry import SystemRegistry
from backend.services.integration_coverage import IntegrationCoverageTracker


class ResearchInfrastructureTests(unittest.TestCase):
    def test_research_registry_tracks_full_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ResearchRegistry(Path(tmpdir) / "research_registry.json")
            record = registry.register_experiment(
                experiment_id="exp-001",
                planner_version="planner_v2",
                policy_version="policy_v3",
                retrieval_version="retrieval_v2",
                reasoner_version="reasoning_v1",
                twin_version="twin_v4",
                dataset_version="dataset_v1",
                benchmark_version="benchmark_v1",
            )

            self.assertEqual(record["experiment_id"], "exp-001")
            self.assertEqual(record["planner_version"], "planner_v2")
            self.assertEqual(record["lineage"]["experiment"], "exp-001")
            self.assertIn("research_version", record)

    def test_system_registry_exposes_unified_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SystemRegistry(Path(tmpdir) / "system_registry.json")
            registry.update_active_versions(
                planner="planner_v2",
                policy="policy_v3",
                retrieval="retrieval_v2",
                reasoning="reasoning_v1",
                twin="twin_v4",
            )
            active_versions = registry.get_active_versions()
            self.assertEqual(active_versions["planner"], "planner_v2")
            self.assertEqual(active_versions["reasoning"], "reasoning_v1")

    def test_research_benchmark_returns_end_to_end_score(self) -> None:
        benchmark = ResearchBenchmark()
        metrics = benchmark.evaluate(
            {
                "goal_success": 0.82,
                "planning_accuracy": 0.78,
                "policy_accuracy": 0.74,
                "retrieval_accuracy": 0.8,
                "reasoning_score": 0.76,
                "execution_success": 0.84,
                "learning_improvement": 0.19,
            }
        )
        self.assertGreater(metrics["overall_intelligence_score"], 0.75)
        self.assertIn("goal_success", metrics)

    def test_report_generator_creates_structured_sections(self) -> None:
        generator = ResearchReportGenerator()
        report = generator.generate_report(
            title="Sprint 11 Report",
            architecture={"planner": "beam_search"},
            benchmarks={"overall_intelligence_score": 0.81},
            ablation={"hybrid": 0.82},
            performance={"search_time_ms": 12.5},
            improvements=["added research registry"],
            future_work=["expand benchmarks"],
        )
        self.assertIn("Sprint 11 Report", report)
        self.assertIn("Architecture", report)
        self.assertIn("Benchmarks", report)
        self.assertIn("Future Work", report)

    def test_integration_coverage_tracker_marks_and_summarizes_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = IntegrationCoverageTracker(Path(tmpdir) / "coverage.json")
            tracker.mark_covered("planner")
            tracker.mark_covered("retriever")
            tracker.mark_covered("reasoner")
            summary = tracker.summary()
            self.assertIn("planner", summary["covered_paths"])
            self.assertGreater(summary["coverage_ratio"], 0.0)
            self.assertEqual(summary["total_paths"], 6)


if __name__ == "__main__":
    unittest.main()
