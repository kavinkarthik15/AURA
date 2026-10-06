"""Tests for 17.3B Per-Category Validation."""

import pytest
from backend.experiments.research_per_category_validation_17_3_b import (
    CategoryAnalysisResult,
    ResearchPerCategoryValidation17_3_BResult,
    ResearchPerCategoryValidation17_3_B,
    run_research_per_category_validation_17_3_b,
)


class TestCategoryAnalysisResult:
    """Tests for category analysis result."""

    def test_result_creation(self):
        """Can create valid analysis result."""
        result = CategoryAnalysisResult(
            category="test_cat",
            true_systematic_bias=-3.0,
            num_training_experiences=10,
            avg_signed_error=-5.0,
            num_negative_errors=10,
            num_positive_errors=0,
            existing_final_bias=2.0,
            existing_bias_direction_correct=False,
            existing_error_gap=5.0,
            sign_aware_final_bias=1.0,
            sign_aware_bias_direction_correct=False,
            sign_aware_error_gap=4.0,
        )
        assert result.category == "test_cat"
        assert result.true_systematic_bias == -3.0


class TestResearchPerCategoryValidation17_3_B:
    """Tests for per-category validation experiment."""

    def test_experiment_initialization(self):
        """Can initialize experiment."""
        experiment = ResearchPerCategoryValidation17_3_B(seed=42)
        assert experiment.seed == 42

    def test_run_produces_valid_result(self):
        """Running produces valid result."""
        experiment = ResearchPerCategoryValidation17_3_B(seed=42)
        result = experiment.run()
        
        assert isinstance(result, ResearchPerCategoryValidation17_3_BResult)
        assert result.seed == 42
        assert len(result.category_analyses) > 0

    def test_all_categories_analyzed(self):
        """All 8 categories are analyzed."""
        experiment = ResearchPerCategoryValidation17_3_B(seed=42)
        result = experiment.run()
        
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
        assert set(result.category_analyses.keys()) == expected_categories

    def test_each_category_has_error_signals(self):
        """Each category has error signal statistics."""
        experiment = ResearchPerCategoryValidation17_3_B(seed=42)
        result = experiment.run()
        
        for analysis in result.category_analyses.values():
            assert analysis.num_training_experiences > 0
            total_errors = analysis.num_negative_errors + analysis.num_positive_errors
            assert total_errors > 0

    def test_results_are_deterministic(self):
        """Same seed produces identical results."""
        result1 = run_research_per_category_validation_17_3_b(seed=42)
        result2 = run_research_per_category_validation_17_3_b(seed=42)
        
        for cat in result1.category_analyses:
            assert (
                result1.category_analyses[cat].sign_aware_final_bias
                == result2.category_analyses[cat].sign_aware_final_bias
            )

    def test_summary_generated(self):
        """Result includes summary."""
        experiment = ResearchPerCategoryValidation17_3_B(seed=42)
        result = experiment.run()
        
        assert len(result.summary) > 0
        assert "NEGATIVE-BIAS" in result.summary
        assert "POSITIVE-BIAS" in result.summary
