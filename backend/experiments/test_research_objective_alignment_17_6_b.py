"""
Tests for 17.6B: Calibration Objective & State Representation Analysis.
"""

from datetime import datetime
from pathlib import Path

import pytest

from backend.experiments.research_objective_alignment_17_6_b import (
    ObjectiveAlignmentAnalyzer,
    ObjectiveAlignmentEvent,
    ObjectiveAlignmentResult,
    ResearchPhase17_6_B,
    SeedObjectiveAlignmentResult,
)


class TestObjectiveAlignmentEvent:
    def test_creation(self):
        event = ObjectiveAlignmentEvent(
            seed=42,
            category="high_skill_practice",
            step=3,
            feature="python",
            bias_before=0.1,
            bias_delta=0.02,
            bias_after=0.12,
            signed_error=1.5,
            prediction_before=65.0,
            prediction_after=66.5,
            mae_before=2.0,
            mae_after=1.8,
            objective_best_direction=1,
            actual_update_direction=1,
            objective_aligned=True,
        )
        assert event.seed == 42
        assert event.objective_aligned is True


class TestSeedObjectiveAlignmentResult:
    def test_creation(self):
        result = SeedObjectiveAlignmentResult(
            seed=42,
            total_events=10,
            objective_direction_accuracy=0.9,
            mean_mae_before=2.0,
            mean_mae_after=1.5,
            mean_improvement=0.5,
            mean_signed_error=0.1,
            mean_bias_delta=0.02,
            alignment_by_category={"high_skill_practice": 0.8},
        )
        assert result.seed == 42
        assert result.objective_direction_accuracy > 0.8


class TestObjectiveAlignmentResult:
    def test_to_dict(self):
        result = ObjectiveAlignmentResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=0.007,
            total_seeds=1,
            seed_results={42: SeedObjectiveAlignmentResult(seed=42, total_events=1, objective_direction_accuracy=1.0, mean_mae_before=1.0, mean_mae_after=0.5, mean_improvement=0.5, mean_signed_error=0.1, mean_bias_delta=0.02, alignment_by_category={"high_skill_practice": 1.0})},
        )
        payload = result.to_dict()
        assert payload["total_seeds"] == 1
        assert "42" in payload["seed_results"]


class TestObjectiveAlignmentAnalyzer:
    def test_initialization(self):
        analyzer = ObjectiveAlignmentAnalyzer(seed=42, learning_rate=0.007)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007

    def test_analyze_seed_returns_result(self):
        analyzer = ObjectiveAlignmentAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.analyze_seed()
        assert result.total_events > 0
        assert 0.0 <= result.objective_direction_accuracy <= 1.0


@pytest.mark.slow
class TestPhase17_6_BIntegration:
    def test_orchestrator_run(self):
        run = ResearchPhase17_6_B(learning_rate=0.007)
        result = run.run()
        assert isinstance(result, ObjectiveAlignmentResult)
        assert result.total_seeds == 5
        assert len(result.seed_results) == 5

    def test_results_file_written(self):
        run = ResearchPhase17_6_B(learning_rate=0.007)
        run.run()
        path = Path("backend/experiments/results/research_17_6_b_objective_alignment.json")
        assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
