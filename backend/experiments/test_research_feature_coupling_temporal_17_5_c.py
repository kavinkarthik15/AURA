"""
Tests for 17.5C: Feature-Coupling / Temporal Interaction Analysis.

Validates the observational framework and diagnostic metrics without changing
production calibration logic.
"""

from datetime import datetime
from pathlib import Path

import pytest

from backend.experiments.research_feature_coupling_temporal_17_5_c import (
    FeatureCouplingAnalysisResult,
    FeatureCouplingTemporalAnalyzer,
    FeatureErrorStat,
    PairInteractionStat,
    SeedFeatureCouplingResult,
    TemporalDriftStat,
    ResearchPhase17_5_C,
)


class TestFeatureErrorStat:
    def test_creation(self):
        stat = FeatureErrorStat(
            feature="python",
            mean_signed_error=0.5,
            mean_abs_error=1.5,
            correlation_with_feature_value=0.2,
            feature_value_std=3.0,
        )
        assert stat.feature == "python"
        assert stat.mean_signed_error == 0.5


class TestPairInteractionStat:
    def test_creation(self):
        stat = PairInteractionStat(
            pair="python×dsa",
            high_high_mean_signed_error=1.1,
            low_low_mean_signed_error=-0.7,
            interaction_gap=1.8,
            mean_pair_signed_error=0.2,
            correlation_with_pair_value=0.3,
        )
        assert stat.pair == "python×dsa"
        assert stat.interaction_gap == 1.8


class TestTemporalDriftStat:
    def test_creation(self):
        stat = TemporalDriftStat(
            mean_feature_drift=1.2,
            high_drift_mean_signed_error=2.0,
            low_drift_mean_signed_error=0.5,
            drift_abs_error_correlation=0.4,
            mean_abs_error_high_drift=1.5,
            mean_abs_error_low_drift=0.8,
        )
        assert stat.mean_feature_drift == 1.2


class TestSeedFeatureCouplingResult:
    def test_creation(self):
        result = SeedFeatureCouplingResult(
            seed=42,
            total_events=80,
            strongest_feature="python",
            strongest_pair="python×dsa",
            strongest_feature_correlation=0.4,
            strongest_pair_gap=1.2,
            high_drift_error_gap=0.5,
        )
        assert result.seed == 42
        assert result.strongest_feature == "python"


class TestFeatureCouplingAnalysisResult:
    def test_to_dict(self):
        result = FeatureCouplingAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=0.007,
            total_seeds=1,
            seed_results={42: SeedFeatureCouplingResult(seed=42, total_events=80)},
        )
        payload = result.to_dict()
        assert payload["total_seeds"] == 1
        assert "42" in payload["seed_results"]


class TestFeatureCouplingTemporalAnalyzer:
    def test_initialization(self):
        analyzer = FeatureCouplingTemporalAnalyzer(seed=42, learning_rate=0.007)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007

    def test_analyze_seed_returns_result(self):
        analyzer = FeatureCouplingTemporalAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.analyze_seed()
        assert isinstance(result, SeedFeatureCouplingResult)
        assert result.total_events > 0
        assert result.feature_stats

    def test_feature_statistics_fields(self):
        analyzer = FeatureCouplingTemporalAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.analyze_seed()
        stat = next(iter(result.feature_stats.values()))
        assert hasattr(stat, "mean_signed_error")
        assert hasattr(stat, "mean_abs_error")
        assert hasattr(stat, "correlation_with_feature_value")


@pytest.mark.slow
class TestPhase17_5CIntegration:
    def test_orchestrator_run(self):
        orchestrator = ResearchPhase17_5_C(learning_rate=0.007)
        result = orchestrator.run()
        assert isinstance(result, FeatureCouplingAnalysisResult)
        assert result.total_seeds == 5
        assert len(result.seed_results) == 5

    def test_results_file_written(self):
        orchestrator = ResearchPhase17_5_C(learning_rate=0.007)
        result = orchestrator.run()
        path = Path("backend/experiments/results/research_17_5_c_feature_coupling_temporal.json")
        assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
