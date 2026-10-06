"""
Test suite for Phase 17.5B: Error Distribution & Sequence Dynamics Analysis

Tests cover:
- Data model validation (ErrorBalanceMetrics, ErrorMagnitudeMetrics, etc.)
- Analyzer initialization and core computation methods
- Single-seed analysis end-to-end
- Orchestrator execution
- Result persistence and structure
"""

import pytest
import statistics
from pathlib import Path
from datetime import datetime

from backend.experiments.research_error_distribution_sequence_17_5_b import (
    ErrorBalanceMetrics,
    ErrorMagnitudeMetrics,
    TemporalSequenceMetrics,
    CumulativeErrorMetrics,
    CategoryErrorStats,
    SeedDistributionResult,
    DistributionSequenceAnalysisResult,
    ErrorDistributionSequenceAnalyzer,
    ResearchPhase17_5_B,
)


# ============================================================================
# Data Model Tests
# ============================================================================


class TestErrorBalanceMetrics:
    """Test ErrorBalanceMetrics data model."""

    def test_creation(self):
        """Test basic creation."""
        metrics = ErrorBalanceMetrics(
            positive_error_count=50,
            negative_error_count=45,
            zero_error_count=5,
            positive_error_ratio=0.5,
            negative_error_ratio=0.45,
            mean_signed_error=0.002,
            median_signed_error=0.001,
            std_signed_error=0.05,
        )
        assert metrics.positive_error_count == 50
        assert metrics.positive_error_ratio == 0.5

    def test_defaults(self):
        """Test default values."""
        metrics = ErrorBalanceMetrics()
        assert metrics.positive_error_count == 0
        assert metrics.mean_signed_error == 0.0


class TestErrorMagnitudeMetrics:
    """Test ErrorMagnitudeMetrics data model."""

    def test_creation(self):
        """Test basic creation."""
        metrics = ErrorMagnitudeMetrics(
            mean_abs_error=0.042,
            median_abs_error=0.035,
            max_abs_error=0.15,
            percentile_95_abs_error=0.12,
        )
        assert metrics.mean_abs_error == 0.042

    def test_percentile_95(self):
        """Test 95th percentile tracking."""
        metrics = ErrorMagnitudeMetrics(percentile_95_abs_error=0.10)
        assert metrics.percentile_95_abs_error == 0.10


class TestTemporalSequenceMetrics:
    """Test TemporalSequenceMetrics data model."""

    def test_creation(self):
        """Test basic creation."""
        metrics = TemporalSequenceMetrics(
            longest_positive_streak=12,
            longest_negative_streak=8,
            positive_to_negative_transitions=5,
            negative_to_positive_transitions=5,
            early_mean_signed_error=0.01,
            late_mean_signed_error=-0.01,
        )
        assert metrics.longest_positive_streak == 12
        assert metrics.positive_to_negative_transitions == 5

    def test_temporal_segments(self):
        """Test that all 5 temporal segments are tracked."""
        metrics = TemporalSequenceMetrics(
            early_mean_signed_error=0.01,
            early_mid_mean_signed_error=0.005,
            mid_mean_signed_error=0.0,
            mid_late_mean_signed_error=-0.005,
            late_mean_signed_error=-0.01,
        )
        assert abs(metrics.early_mean_signed_error - metrics.late_mean_signed_error) == 0.02


class TestCumulativeErrorMetrics:
    """Test CumulativeErrorMetrics data model."""

    def test_creation_with_trajectory(self):
        """Test creation with trajectory lists."""
        trajectory = [0.01, 0.02, 0.01, 0.03, 0.05]
        abs_trajectory = [0.01, 0.02, 0.01, 0.03, 0.05]
        metrics = CumulativeErrorMetrics(
            final_cumulative_error=0.05,
            final_cumulative_abs_error=0.12,
            cumulative_error_trajectory=trajectory,
            cumulative_abs_error_trajectory=abs_trajectory,
        )
        assert len(metrics.cumulative_error_trajectory) == 5
        assert metrics.final_cumulative_error == 0.05


class TestCategoryErrorStats:
    """Test CategoryErrorStats data model."""

    def test_creation(self):
        """Test basic creation."""
        stats = CategoryErrorStats(
            category_name="low_skill_practice",
            positive_error_count=8,
            negative_error_count=7,
            zero_error_count=1,
            mean_signed_error=0.002,
            mean_abs_error=0.04,
            total_events=16,
        )
        assert stats.category_name == "low_skill_practice"
        assert stats.total_events == 16

    def test_category_error_distribution(self):
        """Test that counts sum to total."""
        stats = CategoryErrorStats(
            category_name="test",
            positive_error_count=30,
            negative_error_count=25,
            zero_error_count=5,
            total_events=60,
        )
        assert stats.positive_error_count + stats.negative_error_count + stats.zero_error_count == stats.total_events


class TestSeedDistributionResult:
    """Test SeedDistributionResult data model."""

    def test_creation_minimal(self):
        """Test creation with minimal data."""
        result = SeedDistributionResult(seed=42, total_events=100)
        assert result.seed == 42
        assert result.total_events == 100

    def test_creation_full(self):
        """Test creation with all metrics."""
        result = SeedDistributionResult(
            seed=123,
            total_events=300,
            balance_metrics=ErrorBalanceMetrics(positive_error_count=150),
            magnitude_metrics=ErrorMagnitudeMetrics(mean_abs_error=0.05),
            sequence_metrics=TemporalSequenceMetrics(longest_positive_streak=20),
            cumulative_metrics=CumulativeErrorMetrics(final_cumulative_error=0.1),
            final_mae=0.05,
        )
        assert result.seed == 123
        assert result.final_mae == 0.05


class TestDistributionSequenceAnalysisResult:
    """Test DistributionSequenceAnalysisResult data model."""

    def test_creation_empty(self):
        """Test creation with empty seed results."""
        result = DistributionSequenceAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=0.007,
            total_seeds=0,
        )
        assert result.total_seeds == 0
        assert result.learning_rate == 0.007

    def test_to_dict_serialization(self):
        """Test JSON serialization."""
        seed_result = SeedDistributionResult(
            seed=42,
            total_events=100,
            balance_metrics=ErrorBalanceMetrics(positive_error_count=50),
        )
        result = DistributionSequenceAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=0.007,
            total_seeds=1,
            seed_results={42: seed_result},
        )
        result_dict = result.to_dict()
        assert "seed_results" in result_dict
        assert "42" in result_dict["seed_results"]
        assert result_dict["seed_results"]["42"]["seed"] == 42


# ============================================================================
# Analyzer Tests
# ============================================================================


class TestErrorDistributionSequenceAnalyzer:
    """Test ErrorDistributionSequenceAnalyzer core methods."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42, learning_rate=0.007)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007

    def test_sign_function_positive(self):
        """Test sign function for positive values."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        assert analyzer._sign(0.5) == 1
        assert analyzer._sign(0.001) == 1

    def test_sign_function_negative(self):
        """Test sign function for negative values."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        assert analyzer._sign(-0.5) == -1
        assert analyzer._sign(-0.001) == -1

    def test_sign_function_zero(self):
        """Test sign function for zero."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        assert analyzer._sign(0.0) == 0

    def test_percentile_function(self):
        """Test percentile computation."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        p95 = analyzer._percentile(data, 0.95)
        assert 9 <= p95 <= 10

    def test_percentile_empty_list(self):
        """Test percentile with empty list."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        p95 = analyzer._percentile([], 0.95)
        assert p95 == 0.0

    def test_compute_signed_error_empty(self):
        """Test signed error computation with empty states."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        error = analyzer._compute_signed_error({}, {})
        assert error == 0.0

    def test_compute_signed_error_simple(self):
        """Test signed error computation with simple states."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        actual = {"skill": 0.5}
        predicted = {"skill": 0.3}
        error = analyzer._compute_signed_error(actual, predicted)
        assert error == 0.2

    def test_compute_signed_error_multiple_fields(self):
        """Test signed error computation with multiple fields."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        actual = {"skill": 0.5, "motivation": 0.6}
        predicted = {"skill": 0.3, "motivation": 0.4}
        error = analyzer._compute_signed_error(actual, predicted)
        expected = (0.2 + 0.2) / 2
        assert abs(error - expected) < 1e-6


# ============================================================================
# Integration Tests (marked slow)
# ============================================================================


@pytest.mark.slow
class TestSingleSeedAnalysis:
    """Integration tests for single-seed analysis."""

    def test_analyze_seed_returns_result(self):
        """Test that analyze_seed returns SeedDistributionResult."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        result = analyzer.analyze_seed()
        assert isinstance(result, SeedDistributionResult)

    def test_analyze_seed_has_metrics(self):
        """Test that result contains all required metrics."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        result = analyzer.analyze_seed()
        assert result.seed == 42
        assert result.total_events > 0
        assert isinstance(result.balance_metrics, ErrorBalanceMetrics)
        assert isinstance(result.magnitude_metrics, ErrorMagnitudeMetrics)
        assert isinstance(result.sequence_metrics, TemporalSequenceMetrics)
        assert isinstance(result.cumulative_metrics, CumulativeErrorMetrics)
        assert result.final_mae >= 0.0

    def test_analyze_seed_balance_metrics_valid(self):
        """Test that balance metrics are mathematically valid."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        result = analyzer.analyze_seed()
        bm = result.balance_metrics
        # Counts should sum to total events
        assert bm.positive_error_count + bm.negative_error_count + bm.zero_error_count == result.total_events
        # Ratios should be between 0 and 1
        assert 0 <= bm.positive_error_ratio <= 1
        assert 0 <= bm.negative_error_ratio <= 1

    def test_analyze_seed_cumulative_error_trajectory_increasing(self):
        """Test that cumulative absolute error trajectory is monotonically increasing."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        result = analyzer.analyze_seed()
        trajectory = result.cumulative_metrics.cumulative_abs_error_trajectory
        for i in range(1, len(trajectory)):
            assert trajectory[i] >= trajectory[i - 1]

    def test_analyze_seed_categories_populated(self):
        """Test that category stats are populated."""
        analyzer = ErrorDistributionSequenceAnalyzer(seed=42)
        result = analyzer.analyze_seed()
        assert len(result.category_stats) > 0
        for cat_name, cat_stats in result.category_stats.items():
            assert cat_stats.total_events > 0
            assert (
                cat_stats.positive_error_count
                + cat_stats.negative_error_count
                + cat_stats.zero_error_count
                == cat_stats.total_events
            )


@pytest.mark.slow
class TestOrchestrator:
    """Integration tests for ResearchPhase17_5_B orchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        assert orchestrator.learning_rate == 0.007
        assert len(orchestrator.seeds) == 5

    def test_orchestrator_run_returns_result(self):
        """Test that run() returns DistributionSequenceAnalysisResult."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()
        assert isinstance(result, DistributionSequenceAnalysisResult)

    def test_orchestrator_all_seeds_analyzed(self):
        """Test that all 5 seeds are analyzed."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()
        assert result.total_seeds == 5
        assert len(result.seed_results) == 5
        for seed in [42, 123, 456, 789, 999]:
            assert seed in result.seed_results

    def test_orchestrator_results_saved(self):
        """Test that results are saved to JSON file."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()
        results_file = Path("backend/experiments/results/research_17_5_b_error_distribution_sequence.json")
        assert results_file.exists()


# ============================================================================
# Diagnostic Tests
# ============================================================================


class TestDiagnosticProperties:
    """Tests to verify diagnostic properties that should distinguish seeds."""

    def test_seed_comparison_structure(self):
        """Verify that comparison tables can be generated for all seeds."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()

        # Verify all seeds have comparable metrics
        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            assert sr.balance_metrics.positive_error_ratio is not None
            assert sr.magnitude_metrics.mean_abs_error is not None
            assert sr.sequence_metrics.longest_positive_streak is not None

    def test_cumulative_error_is_measurable(self):
        """Verify that cumulative error can be measured and compared."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()

        cumulative_errors = [
            result.seed_results[seed].cumulative_metrics.final_cumulative_error for seed in [42, 123, 456, 789, 999]
        ]
        assert len(cumulative_errors) == 5

    def test_temporal_evolution_is_trackable(self):
        """Verify that temporal segments can be compared across seeds."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()

        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            # All 5 segments should have values
            segments = [
                sr.sequence_metrics.early_mean_signed_error,
                sr.sequence_metrics.early_mid_mean_signed_error,
                sr.sequence_metrics.mid_mean_signed_error,
                sr.sequence_metrics.mid_late_mean_signed_error,
                sr.sequence_metrics.late_mean_signed_error,
            ]
            assert len(segments) == 5

    def test_category_breakdown_is_complete(self):
        """Verify that all categories are analyzed for each seed."""
        orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
        result = orchestrator.run()

        # Collect all categories across seeds
        all_categories = set()
        for seed_result in result.seed_results.values():
            all_categories.update(seed_result.category_stats.keys())

        # Each seed should have category stats
        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            assert len(sr.category_stats) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
