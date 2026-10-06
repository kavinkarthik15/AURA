"""Tests for 17.6C: State Representation & Parameter Identifiability."""

from datetime import datetime
from pathlib import Path

import pytest

from backend.experiments.research_state_representation_identifiability_17_6_c import (
    ResearchPhase17_6_C,
    SeedRepresentationResult,
    StateCollisionGroup,
    StateRepresentationIdentifiabilityAnalyzer,
)


class TestStateCollisionGroup:
    def test_creation(self):
        group = StateCollisionGroup(
            state_key="python:50|dsa:30",
            group_size=2,
            mean_future_mae=3.0,
            max_future_mae=4.0,
            future_variance=1.2,
            distinct_actual_outcomes=2,
        )
        assert group.group_size == 2
        assert group.distinct_actual_outcomes == 2


class TestSeedRepresentationResult:
    def test_creation(self):
        result = SeedRepresentationResult(
            seed=42,
            total_events=80,
            state_collision_rate=0.3,
            mean_future_variance=2.0,
            max_state_group_size=4,
            bias_sensitivity_mean=0.4,
            bias_sensitivity_p95=1.2,
            identifiability_flatness=0.9,
            residual_mae=5.0,
            history_dependence_score=0.25,
        )
        assert result.seed == 42
        assert result.state_collision_rate == 0.3


class TestStateRepresentationIdentifiabilityAnalyzer:
    def test_initialization(self):
        analyzer = StateRepresentationIdentifiabilityAnalyzer(seed=42, learning_rate=0.007)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007

    def test_analyze_seed_returns_result(self):
        analyzer = StateRepresentationIdentifiabilityAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.analyze_seed()
        assert result.total_events > 0
        assert result.state_collision_rate >= 0.0
        assert result.residual_mae >= 0.0


@pytest.mark.slow
class TestPhase17_6_CIntegration:
    def test_orchestrator_run(self):
        orchestrator = ResearchPhase17_6_C(learning_rate=0.007)
        result = orchestrator.run()
        assert isinstance(result, object)
        assert result.total_seeds == 5
        assert len(result.seed_results) == 5

    def test_results_file_written(self):
        orchestrator = ResearchPhase17_6_C(learning_rate=0.007)
        orchestrator.run()
        path = Path("backend/experiments/results/research_17_6_c_state_representation_identifiability.json")
        assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
