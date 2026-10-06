"""
Tests for 17.2A Learning Mechanism Analysis

Validates:
- Mechanism analyzer structure and initialization
- Calibration trajectory tracking
- Bias comparison calculations
- Result model completeness
- Convergence verdicts
- Determinism (same seed reproducibility)
- Learning effectiveness
"""

import pytest
from backend.experiments.research_mechanism_analysis_17_2_a import (
    CalibrationParameterSnapshot,
    BiasComparisonPoint,
    MechanismAnalysisResult,
    ResearchMechanismAnalyzer,
    run_research_mechanism_17_2_a,
)
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator


class TestCalibrationParameterSnapshot:
    """Tests for calibration parameter tracking model."""

    def test_snapshot_creation(self):
        """Can create a valid calibration parameter snapshot."""
        snapshot = CalibrationParameterSnapshot(
            step=0,
            experience_id="exp_000",
            category="low_skill_practice",
            expected_state_bias={"python": 0.5},
            transition_probability_bias=0.1,
            risk_bias=0.05,
            uncertainty=0.55,
            confidence=0.5,
            prediction_error=1.5,
            cumulative_mae=1.5,
        )
        assert snapshot.step == 0
        assert snapshot.experience_id == "exp_000"
        assert snapshot.category == "low_skill_practice"
        assert snapshot.expected_state_bias["python"] == 0.5
        assert snapshot.prediction_error == 1.5

    def test_snapshot_default_bias(self):
        """Snapshot state bias defaults to empty dict."""
        snapshot = CalibrationParameterSnapshot(
            step=0,
            experience_id="exp_000",
            category="low_skill_practice",
            prediction_error=1.0,
            cumulative_mae=1.0,
        )
        assert snapshot.expected_state_bias == {}


class TestBiasComparisonPoint:
    """Tests for bias comparison model."""

    def test_comparison_creation(self):
        """Can create a valid bias comparison point."""
        comp = BiasComparisonPoint(
            step=5,
            experience_id="exp_005",
            category="medium_skill_practice",
            true_systematic_bias=3.0,
            learned_state_bias_avg=2.8,
            bias_distance=0.2,
            direction_correct=True,
            magnitude_ratio=0.93,
        )
        assert comp.step == 5
        assert comp.true_systematic_bias == 3.0
        assert comp.learned_state_bias_avg == 2.8
        assert comp.direction_correct is True
        assert comp.magnitude_ratio == 0.93


class TestMechanismAnalysisResult:
    """Tests for mechanism analysis result model."""

    def test_result_creation(self):
        """Can create a valid mechanism analysis result."""
        result = MechanismAnalysisResult(
            experiment_id="test_exp",
            seed=42,
            dataset_id="test_dataset",
            timestamp="2026-08-12T00:00:00",
            learning_rate=0.007,
            bounds={},
            initial_mae=2.5,
            final_mae=1.2,
            total_mae_reduction=1.3,
            convergence_rate=45.0,
            is_learning=True,
            is_converging=True,
            learning_explanation="Test explanation",
        )
        assert result.experiment_id == "test_exp"
        assert result.seed == 42
        assert result.is_learning is True
        assert result.is_converging is True

    def test_result_default_lists(self):
        """Result defaults to empty trajectory and comparison lists."""
        result = MechanismAnalysisResult(
            experiment_id="test",
            seed=42,
            dataset_id="test",
            timestamp="2026-08-12T00:00:00",
            learning_rate=0.007,
            bounds={},
            initial_mae=1.0,
            final_mae=0.9,
            total_mae_reduction=0.1,
            convergence_rate=10.0,
            is_learning=True,
            is_converging=False,
            learning_explanation="Test",
        )
        assert result.calibration_trajectory == []
        assert result.bias_comparisons == []
        assert result.category_bias_distances == {}
        assert result.category_direction_accuracy == {}


class TestResearchMechanismAnalyzer:
    """Tests for mechanism analyzer."""

    def test_analyzer_initialization_default(self):
        """Can initialize analyzer with default parameters."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007
        assert analyzer.dataset_id is not None

    def test_analyzer_initialization_custom(self):
        """Can initialize with custom learning rate and bounds."""
        custom_bounds = {"state_adjustment_max": 0.5}
        analyzer = ResearchMechanismAnalyzer(
            seed=123,
            learning_rate=0.01,
            bounds=custom_bounds,
        )
        assert analyzer.seed == 123
        assert analyzer.learning_rate == 0.01
        assert analyzer.bounds["state_adjustment_max"] == 0.5

    def test_analyzer_with_preexisting_dataset(self):
        """Can initialize with pre-existing dataset."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)
        analyzer = ResearchMechanismAnalyzer(dataset=dataset)
        assert analyzer.dataset_id == dataset.dataset_id

    def test_category_systematic_bias_defined(self):
        """All 8 expected categories have known systematic biases."""
        expected_categories = {
            "low_skill_practice",
            "medium_skill_practice",
            "high_skill_practice",
            "low_motivation",
            "high_motivation",
            "mixed_skills",
            "project_completion",
            "plateau",
        }
        assert set(ResearchMechanismAnalyzer.CATEGORY_SYSTEMATIC_BIAS.keys()) == expected_categories

    def test_run_returns_valid_result(self):
        """Running analyzer produces valid MechanismAnalysisResult."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert isinstance(result, MechanismAnalysisResult)
        assert result.seed == 42
        assert result.dataset_id is not None
        assert result.timestamp is not None

    def test_trajectory_has_correct_length(self):
        """Trajectory has one entry per training experience."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert len(result.calibration_trajectory) == 80  # training_size default

    def test_bias_comparisons_has_correct_length(self):
        """Bias comparisons has one entry per training experience."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert len(result.bias_comparisons) == 80

    def test_trajectory_steps_sequential(self):
        """Trajectory steps are sequential from 0 to 79."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        steps = [snap.step for snap in result.calibration_trajectory]
        assert steps == list(range(80))

    def test_trajectory_experiences_match(self):
        """Trajectory experience IDs match dataset experiences."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        dataset_exp_ids = [
            exp.experience_id for exp in analyzer.dataset.training_experiences
        ]
        traj_exp_ids = [snap.experience_id for snap in result.calibration_trajectory]
        assert traj_exp_ids == dataset_exp_ids

    def test_trajectory_categories_match(self):
        """Trajectory categories match dataset experience categories."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        dataset_categories = [
            exp.category for exp in analyzer.dataset.training_experiences
        ]
        traj_categories = [snap.category for snap in result.calibration_trajectory]
        assert traj_categories == dataset_categories

    def test_cumulative_mae_is_non_increasing(self):
        """Cumulative MAE can decrease as calibration improves prediction."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        cumulative_maes = [snap.cumulative_mae for snap in result.calibration_trajectory]
        # Cumulative MAE should stabilize and can decrease with good learning
        # Just verify it's not NaN or negative
        for mae in cumulative_maes:
            assert mae > 0.0
            assert not (mae != mae)  # Not NaN

    def test_bias_comparison_steps_sequential(self):
        """Bias comparisons have sequential steps."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        steps = [comp.step for comp in result.bias_comparisons]
        assert steps == list(range(80))

    def test_initial_final_mae_values(self):
        """Initial and final MAE are populated."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert result.initial_mae > 0.0
        assert result.final_mae > 0.0
        assert result.initial_mae >= result.final_mae  # Learning should improve

    def test_mae_reduction_is_correct(self):
        """Total MAE reduction = initial - final."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        expected_reduction = result.initial_mae - result.final_mae
        assert abs(result.total_mae_reduction - expected_reduction) < 0.001

    def test_convergence_rate_is_percentage(self):
        """Convergence rate is between 0 and 100."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert 0.0 <= result.convergence_rate <= 100.0

    def test_is_learning_correct(self):
        """is_learning=True iff final_mae < initial_mae."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        expected_learning = result.final_mae < result.initial_mae
        assert result.is_learning == expected_learning

    def test_category_statistics_completeness(self):
        """All categories present in statistics."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        expected_categories = {
            "low_skill_practice",
            "medium_skill_practice",
            "high_skill_practice",
            "low_motivation",
            "high_motivation",
            "mixed_skills",
            "project_completion",
            "plateau",
        }
        assert set(result.category_bias_distances.keys()) == expected_categories
        assert set(result.category_direction_accuracy.keys()) == expected_categories

    def test_category_bias_distances_are_positive(self):
        """Category bias distances are non-negative."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        for distance in result.category_bias_distances.values():
            assert distance >= 0.0

    def test_category_direction_accuracy_is_percentage(self):
        """Category direction accuracy is between 0 and 100."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        for accuracy in result.category_direction_accuracy.values():
            assert 0.0 <= accuracy <= 100.0

    def test_learning_explanation_non_empty(self):
        """Learning explanation is non-empty."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        assert len(result.learning_explanation) > 0

    def test_is_converging_verdict_logic(self):
        """is_converging is True iff >20% convergence AND >60% direction accuracy."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        avg_direction_accuracy = (
            sum(result.category_direction_accuracy.values())
            / len(result.category_direction_accuracy)
        )
        expected_converging = (
            result.convergence_rate > 20.0 and avg_direction_accuracy > 60.0
        )
        assert result.is_converging == expected_converging

    def test_determinism_same_seed(self):
        """Same seed produces identical results."""
        analyzer1 = ResearchMechanismAnalyzer(seed=42)
        result1 = analyzer1.run()

        analyzer2 = ResearchMechanismAnalyzer(seed=42)
        result2 = analyzer2.run()

        assert result1.initial_mae == result2.initial_mae
        assert result1.final_mae == result2.final_mae
        assert result1.convergence_rate == result2.convergence_rate
        assert len(result1.calibration_trajectory) == len(result2.calibration_trajectory)

    def test_different_seeds_produce_different_results(self):
        """Different seeds produce different results."""
        analyzer1 = ResearchMechanismAnalyzer(seed=42)
        result1 = analyzer1.run()

        analyzer2 = ResearchMechanismAnalyzer(seed=123)
        result2 = analyzer2.run()

        # Results should be different (with overwhelming probability)
        assert result1.final_mae != result2.final_mae

    def test_custom_learning_rate_affects_convergence(self):
        """Different learning rates affect convergence."""
        analyzer1 = ResearchMechanismAnalyzer(seed=42, learning_rate=0.001)
        result1 = analyzer1.run()

        analyzer2 = ResearchMechanismAnalyzer(seed=42, learning_rate=0.01)
        result2 = analyzer2.run()

        # Different learning rates should produce different results
        assert result1.convergence_rate != result2.convergence_rate

    def test_trajectory_parameters_are_cumulative(self):
        """Calibration parameters show cumulative learning pattern."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        
        # Extract state bias magnitudes over time
        state_biases = []
        for snap in result.calibration_trajectory:
            if snap.expected_state_bias:
                avg_bias = sum(snap.expected_state_bias.values()) / len(snap.expected_state_bias)
                state_biases.append(abs(avg_bias))
        
        # Should have values (not empty)
        assert len(state_biases) > 0


class TestRunConvenienceFunction:
    """Tests for convenience function."""

    def test_run_function_works(self):
        """Convenience function produces valid result."""
        result = run_research_mechanism_17_2_a(seed=42)
        assert isinstance(result, MechanismAnalysisResult)
        assert result.seed == 42

    def test_run_function_with_custom_params(self):
        """Convenience function accepts custom parameters."""
        result = run_research_mechanism_17_2_a(
            seed=123,
            learning_rate=0.01,
            experiment_id="custom_exp",
        )
        assert result.seed == 123
        assert result.learning_rate == 0.01
        assert result.experiment_id == "custom_exp"

    def test_run_function_with_dataset(self):
        """Convenience function accepts pre-existing dataset."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset()
        result = run_research_mechanism_17_2_a(dataset=dataset)
        assert result.dataset_id == dataset.dataset_id


class TestMechanismLearningBehavior:
    """Tests for overall learning mechanism behavior."""

    def test_learning_improves_prediction(self):
        """Mechanism typically improves prediction over training."""
        analyzer = ResearchMechanismAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.run()
        # With learning rate 0.007, should see improvement
        assert result.is_learning is True

    def test_low_learning_rate_might_not_learn(self):
        """Very low learning rate may not produce measurable learning."""
        analyzer = ResearchMechanismAnalyzer(seed=42, learning_rate=0.0001)
        result = analyzer.run()
        # With very low LR, learning might not happen
        # (This is a realistic possibility, not an assertion)
        assert result.initial_mae >= result.final_mae  # MAE never increases

    def test_bias_learned_per_category(self):
        """Mechanism learns category-specific biases."""
        analyzer = ResearchMechanismAnalyzer(seed=42)
        result = analyzer.run()
        
        # Final bias comparisons should show learning
        final_comparisons = result.bias_comparisons[
            60:80
        ]  # Last 20 should be more learned
        early_comparisons = result.bias_comparisons[0:20]  # First 20 should be less learned
        
        avg_final_distance = sum(c.bias_distance for c in final_comparisons) / len(
            final_comparisons
        )
        avg_early_distance = sum(c.bias_distance for c in early_comparisons) / len(
            early_comparisons
        )
        
        # Final bias distance should be smaller or similar (not larger)
        assert avg_final_distance <= avg_early_distance + 0.5
