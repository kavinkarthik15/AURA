"""
Unit tests for Phase 17.4C: Clipped and Confidence-Gated Signed Updates

Tests the result models, variant runner, and experiment infrastructure.
"""

import pytest
from datetime import datetime
from backend.experiments.research_sign_aware_clipping_confidence_gating_17_4_c import (
    CalibrationVariantMetrics,
    SeedComparisonResult17_4_C,
    VariantAggregateStatistics,
    ResearchPhase17_4_CResult,
    ResearchPhase17_4_C,
)
from backend.experiments.variant_runner_17_4_c import VariantRunner, VariantResult


# ============================================================================
# TESTS FOR RESULT MODELS
# ============================================================================

class TestCalibrationVariantMetrics:
    """Tests for CalibrationVariantMetrics model."""
    
    def test_create_metrics(self):
        """Test creating a metrics object."""
        metrics = CalibrationVariantMetrics(
            variant_name="test-variant",
            seed=42,
            held_out_mae=5.0,
            improvement_vs_baseline=-0.5,
            beats_baseline=False,
            overall_direction_accuracy=0.75,
            positive_bias_direction_accuracy=0.80,
            negative_bias_direction_accuracy=0.70,
            max_absolute_parameter_drift=0.08,
            final_expected_state_bias={"dsa": 0.05, "python": -0.03},
            per_category_mae={"dsa": 5.2, "python": 4.8},
            per_category_direction_accuracy={"dsa": 0.80, "python": 0.70},
        )
        
        assert metrics.variant_name == "test-variant"
        assert metrics.seed == 42
        assert metrics.held_out_mae == 5.0
        assert not metrics.beats_baseline
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CalibrationVariantMetrics(
            variant_name="original",
            seed=123,
            held_out_mae=5.7875,
            improvement_vs_baseline=0.0,
            beats_baseline=False,
            overall_direction_accuracy=0.70,
            positive_bias_direction_accuracy=0.75,
            negative_bias_direction_accuracy=0.65,
            max_absolute_parameter_drift=0.0,
            final_expected_state_bias={},
        )
        
        result_dict = metrics.to_dict()
        assert result_dict["variant_name"] == "original"
        assert result_dict["held_out_mae"] == 5.7875
        assert result_dict["beats_baseline"] is False


class TestSeedComparisonResult17_4_C:
    """Tests for SeedComparisonResult17_4_C model."""
    
    def test_create_seed_result(self):
        """Test creating seed comparison result."""
        result = SeedComparisonResult17_4_C(seed=42)
        assert result.seed == 42
        assert len(result.variants) == 0
    
    def test_add_variants(self):
        """Test adding variants to seed result."""
        result = SeedComparisonResult17_4_C(seed=42)
        
        metrics1 = CalibrationVariantMetrics(
            variant_name="original",
            seed=42,
            held_out_mae=5.7875,
            improvement_vs_baseline=0.0,
            beats_baseline=False,
            overall_direction_accuracy=0.70,
            positive_bias_direction_accuracy=0.75,
            negative_bias_direction_accuracy=0.65,
            max_absolute_parameter_drift=0.0,
            final_expected_state_bias={},
        )
        
        metrics2 = CalibrationVariantMetrics(
            variant_name="clipped",
            seed=42,
            held_out_mae=5.5,
            improvement_vs_baseline=0.2875,
            beats_baseline=True,
            overall_direction_accuracy=0.80,
            positive_bias_direction_accuracy=0.85,
            negative_bias_direction_accuracy=0.75,
            max_absolute_parameter_drift=0.06,
            final_expected_state_bias={"dsa": 0.04},
        )
        
        result.variants["original"] = metrics1
        result.variants["clipped"] = metrics2
        
        assert len(result.variants) == 2
        result.win_count = sum(1 for m in result.variants.values() if m.beats_baseline)
        assert result.win_count == 1


class TestVariantAggregateStatistics:
    """Tests for VariantAggregateStatistics model."""
    
    def test_create_stats(self):
        """Test creating aggregate statistics."""
        stats = VariantAggregateStatistics(
            variant_name="clipped",
            seed_results_count=5,
            win_count=4,
            mean_improvement=0.15,
            std_dev_improvement=0.05,
            mean_direction_accuracy=0.82,
            mean_positive_bias_direction_accuracy=0.85,
            mean_negative_bias_direction_accuracy=0.79,
            passes_primary_criterion=True,
            passes_ideal_criterion=False,
        )
        
        assert stats.variant_name == "clipped"
        assert stats.win_count == 4
        assert stats.passes_primary_criterion is True
    
    def test_stats_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = VariantAggregateStatistics(
            variant_name="sign-aware-17.3",
            seed_results_count=5,
            win_count=2,
            mean_improvement=0.05,
            std_dev_improvement=0.08,
            mean_direction_accuracy=0.75,
            mean_positive_bias_direction_accuracy=0.78,
            mean_negative_bias_direction_accuracy=0.72,
            passes_primary_criterion=False,
            passes_ideal_criterion=False,
        )
        
        result_dict = stats.to_dict()
        assert result_dict["variant_name"] == "sign-aware-17.3"
        assert result_dict["win_rate"] == 0.4
        assert result_dict["passes_primary_criterion"] is False


class TestResearchPhase17_4_CResult:
    """Tests for complete experiment result."""
    
    def test_create_result(self):
        """Test creating experiment result."""
        result = ResearchPhase17_4_CResult(
            timestamp=datetime.now().isoformat()
        )
        
        assert result.timestamp is not None
        assert len(result.seed_results) == 0
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ResearchPhase17_4_CResult(
            timestamp=datetime.now().isoformat(),
            recommended_variant="clipped",
            success_summary="Success: 4/5 seeds improved",
        )
        
        result_dict = result.to_dict()
        assert result_dict["recommended_variant"] == "clipped"
        assert "Success" in result_dict["success_summary"]


# ============================================================================
# TESTS FOR VARIANT RUNNER
# ============================================================================

class TestVariantResult:
    """Tests for VariantResult data class."""
    
    def test_create_variant_result(self):
        """Test creating a variant result."""
        result = VariantResult(
            variant_name="clipped",
            seed=42,
            held_out_mae=5.5,
            baseline_mae=5.7875,
            held_out_mae_improvement=0.2875,
            overall_direction_accuracy=0.80,
            positive_bias_direction_accuracy=0.85,
            negative_bias_direction_accuracy=0.75,
            max_parameter_drift=0.06,
            final_expected_state_bias={"dsa": 0.04},
            per_category_mae={"dsa": 5.2},
            per_category_direction_accuracy={"dsa": 0.80},
        )
        
        assert result.variant_name == "clipped"
        assert result.seed == 42
        assert result.held_out_mae_improvement == pytest.approx(0.2875, abs=0.001)


class TestVariantRunner:
    """Tests for VariantRunner configuration and initialization."""
    
    def test_runner_initialization_default(self):
        """Test VariantRunner with default parameters."""
        runner = VariantRunner(seed=42)
        
        assert runner.seed == 42
        assert runner.learning_rate == 0.007
        assert runner.max_signed_delta is None
        assert runner.error_threshold is None
    
    def test_runner_initialization_custom(self):
        """Test VariantRunner with custom parameters."""
        runner = VariantRunner(
            seed=123,
            learning_rate=0.005,
            max_signed_delta=0.05,
            error_threshold=0.7,
        )
        
        assert runner.seed == 123
        assert runner.learning_rate == 0.005
        assert runner.max_signed_delta == 0.05
        assert runner.error_threshold == 0.7
    
    def test_apply_filtering_confidence_gate_only(self):
        """Test confidence gating filter."""
        runner = VariantRunner(
            seed=42,
            error_threshold=0.5,
        )
        
        signed_errors = {
            "dsa": 0.3,  # Below threshold
            "python": 0.7,  # Above threshold
            "ml": -0.6,  # Above threshold (absolute)
        }
        
        filtered = runner._apply_filtering(signed_errors)
        
        assert filtered["dsa"] == 0.0  # Filtered out
        assert filtered["python"] == 0.7  # Kept
        assert filtered["ml"] == -0.6  # Kept
    
    def test_apply_filtering_clipping_only(self):
        """Test clipping filter."""
        runner = VariantRunner(
            seed=42,
            max_signed_delta=0.05,
        )
        
        signed_errors = {
            "dsa": 0.08,  # Above clipping bound
            "python": -0.1,  # Below clipping bound
            "ml": 0.03,  # Within bounds
        }
        
        filtered = runner._apply_filtering(signed_errors)
        
        assert filtered["dsa"] == 0.05  # Clipped
        assert filtered["python"] == -0.05  # Clipped
        assert filtered["ml"] == 0.03  # Unchanged
    
    def test_apply_filtering_both(self):
        """Test both confidence gating and clipping."""
        runner = VariantRunner(
            seed=42,
            max_signed_delta=0.05,
            error_threshold=0.05,  # Threshold of 0.05
        )
        
        signed_errors = {
            "dsa": 0.03,  # Below threshold, filtered out
            "python": 0.08,  # Above threshold, gets clipped
            "ml": -0.06,  # Above threshold (absolute), gets clipped
        }
        
        filtered = runner._apply_filtering(signed_errors)
        
        assert filtered["dsa"] == 0.0  # Filtered out
        assert filtered["python"] == 0.05  # Clipped
        assert filtered["ml"] == -0.05  # Clipped


# ============================================================================
# TESTS FOR EXPERIMENT RUNNER
# ============================================================================

class TestResearchPhase17_4_C:
    """Tests for ResearchPhase17_4_C experiment."""
    
    def test_experiment_initialization(self):
        """Test experiment initialization."""
        experiment = ResearchPhase17_4_C(
            seeds=[42, 123],
            learning_rate=0.007,
        )
        
        assert experiment.seeds == [42, 123]
        assert experiment.learning_rate == 0.007
        assert len(experiment.VARIANTS) == 5
    
    def test_variants_list(self):
        """Test that all expected variants are defined."""
        experiment = ResearchPhase17_4_C(seeds=[42])
        
        expected_variants = [
            'original',
            'sign-aware-17.3',
            'clipped',
            'confidence-gated',
            'clipped-confidence-gated',
        ]
        
        assert experiment.VARIANTS == expected_variants
    
    def test_clipping_bound_default(self):
        """Test default clipping bound."""
        experiment = ResearchPhase17_4_C(seeds=[42])
        assert experiment.clipping_bound == 0.06  # Half of 0.12
    
    def test_error_threshold_default(self):
        """Test default error threshold."""
        experiment = ResearchPhase17_4_C(seeds=[42])
        assert experiment.error_threshold == 0.5
    
    def test_custom_parameters(self):
        """Test experiment with custom filtering parameters."""
        experiment = ResearchPhase17_4_C(
            seeds=[42, 123],
            learning_rate=0.005,
            clipping_bound=0.04,
            error_threshold=0.6,
        )
        
        assert experiment.learning_rate == 0.005
        assert experiment.clipping_bound == 0.04
        assert experiment.error_threshold == 0.6


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestVariantRunnerIntegration:
    """Integration tests for VariantRunner with actual calibrators."""
    
    @pytest.mark.slow
    def test_run_original_variant(self):
        """Test running original calibrator variant."""
        runner = VariantRunner(seed=42, learning_rate=0.007)
        
        # This will run a real experiment, so it's slow
        result = runner.run_variant('original')
        
        assert result.variant_name == 'original'
        assert result.seed == 42
        assert result.baseline_mae > 0
        assert result.held_out_mae > 0
    
    @pytest.mark.slow
    def test_run_sign_aware_variant(self):
        """Test running sign-aware variant."""
        runner = VariantRunner(seed=42, learning_rate=0.007)
        
        result = runner.run_variant('sign-aware-17.3')
        
        assert result.variant_name == 'sign-aware-17.3'
        assert result.seed == 42


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
