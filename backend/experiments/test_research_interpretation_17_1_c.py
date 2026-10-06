"""
Tests for 17.1C Ablation Interpretation

Validates the analysis and interpretation of ablation study results.
"""

import unittest
from backend.experiments.research_interpretation_17_1_c import (
    AblationInterpreter17_1_C,
    ConsistencyAnalysis,
    MeaningfulnessAnalysis,
    CausalityAnalysis,
    ResearchConclusion17_1_C,
    interpret_ablation_17_1_c,
)


class TestConsistencyAnalysis(unittest.TestCase):
    """Test consistency analysis."""

    def test_consistency_all_seeds_win(self):
        """When all seeds show improvement, consistency should be 100%."""
        analysis = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=5,
            consistency_score=100.0,
            is_consistent=True,
            evidence="All 5 seeds show improvement.",
        )
        self.assertTrue(analysis.is_consistent)
        self.assertEqual(analysis.consistency_score, 100.0)

    def test_consistency_threshold(self):
        """Consistency is true if >= 80%."""
        # 4/5 = 80% (pass)
        analysis_pass = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=4,
            consistency_score=80.0,
            is_consistent=True,
            evidence="80% of seeds show improvement.",
        )
        self.assertTrue(analysis_pass.is_consistent)

        # 3/5 = 60% (fail)
        analysis_fail = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=3,
            consistency_score=60.0,
            is_consistent=False,
            evidence="60% of seeds show improvement.",
        )
        self.assertFalse(analysis_fail.is_consistent)


class TestMeaningfulnessAnalysis(unittest.TestCase):
    """Test meaningfulness analysis."""

    def test_meaningfulness_significant(self):
        """When average > 5%, improvement is meaningful."""
        analysis = MeaningfulnessAnalysis(
            average_improvement_percent=10.09,
            median_improvement_percent=9.48,
            min_improvement_percent=6.48,
            max_improvement_percent=14.05,
            std_dev=2.84,
            is_meaningful=True,
            evidence="Average improvement is +10.09%, which is clearly meaningful.",
        )
        self.assertTrue(analysis.is_meaningful)

    def test_meaningfulness_marginal(self):
        """When average <= 5%, improvement is not meaningful."""
        analysis = MeaningfulnessAnalysis(
            average_improvement_percent=3.2,
            median_improvement_percent=3.0,
            min_improvement_percent=1.5,
            max_improvement_percent=5.0,
            std_dev=1.2,
            is_meaningful=False,
            evidence="Average improvement is +3.2%, which is marginal.",
        )
        self.assertFalse(analysis.is_meaningful)


class TestCausalityAnalysis(unittest.TestCase):
    """Test causality analysis."""

    def test_causality_structure(self):
        """Verify causality analysis contains key causal reasoning."""
        analysis = CausalityAnalysis(
            ablation_design="Condition A (Baseline) vs Condition B (Learning)",
            only_difference="Presence/absence of calibration",
            baseline_is_stable=True,
            learning_is_stable=True,
            causal_conclusion="Calibration is the cause of improvement.",
        )
        self.assertTrue(analysis.baseline_is_stable)
        self.assertTrue(analysis.learning_is_stable)


class TestResearchConclusion17_1_C(unittest.TestCase):
    """Test research conclusion model."""

    def test_conclusion_structure(self):
        """Verify conclusion has all required sections."""
        consistency = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=5,
            consistency_score=100.0,
            is_consistent=True,
            evidence="All 5 seeds show improvement.",
        )
        meaningfulness = MeaningfulnessAnalysis(
            average_improvement_percent=10.09,
            median_improvement_percent=9.48,
            min_improvement_percent=6.48,
            max_improvement_percent=14.05,
            std_dev=2.84,
            is_meaningful=True,
            evidence="Average improvement is +10.09%.",
        )
        causality = CausalityAnalysis(
            ablation_design="A vs B comparison",
            only_difference="Calibration presence",
            baseline_is_stable=True,
            learning_is_stable=True,
            causal_conclusion="Calibration causes improvement.",
        )
        conclusion = ResearchConclusion17_1_C(
            consistency=consistency,
            meaningfulness=meaningfulness,
            causality=causality,
            summary_statement="Test summary",
            interpretation="Test interpretation",
            conclusion="Test conclusion",
            next_steps="Test next steps",
        )
        self.assertIsNotNone(conclusion.consistency)
        self.assertIsNotNone(conclusion.meaningfulness)
        self.assertIsNotNone(conclusion.causality)

    def test_is_conclusive_when_both_pass(self):
        """Conclusive if both consistency and meaningfulness pass."""
        consistency = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=5,
            consistency_score=100.0,
            is_consistent=True,
            evidence="All seeds win.",
        )
        meaningfulness = MeaningfulnessAnalysis(
            average_improvement_percent=10.09,
            median_improvement_percent=9.48,
            min_improvement_percent=6.48,
            max_improvement_percent=14.05,
            std_dev=2.84,
            is_meaningful=True,
            evidence="Strong improvement.",
        )
        causality = CausalityAnalysis(
            ablation_design="A vs B",
            only_difference="Calibration",
            baseline_is_stable=True,
            learning_is_stable=True,
            causal_conclusion="Calibration causes improvement.",
        )
        conclusion = ResearchConclusion17_1_C(
            consistency=consistency,
            meaningfulness=meaningfulness,
            causality=causality,
            summary_statement="Conclusive",
            interpretation="Test",
            conclusion="Test",
            next_steps="Test",
        )
        self.assertTrue(conclusion.is_conclusive())

    def test_not_conclusive_when_inconsistent(self):
        """Not conclusive if consistency fails."""
        consistency = ConsistencyAnalysis(
            total_seeds=5,
            seeds_with_improvement=2,
            consistency_score=40.0,
            is_consistent=False,
            evidence="Only 40% of seeds win.",
        )
        meaningfulness = MeaningfulnessAnalysis(
            average_improvement_percent=10.09,
            median_improvement_percent=9.48,
            min_improvement_percent=6.48,
            max_improvement_percent=14.05,
            std_dev=2.84,
            is_meaningful=True,
            evidence="Strong improvement.",
        )
        causality = CausalityAnalysis(
            ablation_design="A vs B",
            only_difference="Calibration",
            baseline_is_stable=True,
            learning_is_stable=True,
            causal_conclusion="Unclear",
        )
        conclusion = ResearchConclusion17_1_C(
            consistency=consistency,
            meaningfulness=meaningfulness,
            causality=causality,
            summary_statement="Not conclusive",
            interpretation="Test",
            conclusion="Test",
            next_steps="Test",
        )
        self.assertFalse(conclusion.is_conclusive())


class TestAblationInterpreter17_1_C(unittest.TestCase):
    """Test the interpreter implementation."""

    def setUp(self):
        """Set up test fixtures with realistic ablation results."""
        self.result_a = {
            "condition_a": {"held_out_mae": 5.7875},
            "condition_b": {"held_out_mae": 5.4125},
            "improvement_percent": 6.48,
        }
        self.result_b = {
            "total_seeds": 5,
            "learning_wins_count": 5,
            "average_improvement": 10.09,
            "median_improvement": 9.48,
            "min_improvement": 6.48,
            "max_improvement": 14.05,
            "std_dev_improvement": 2.84,
        }

    def test_interpreter_produces_conclusion(self):
        """Interpreter should produce valid conclusion."""
        interpreter = AblationInterpreter17_1_C(self.result_a, self.result_b)
        conclusion = interpreter.interpret()

        self.assertIsInstance(conclusion, ResearchConclusion17_1_C)
        self.assertTrue(conclusion.is_conclusive())

    def test_consistency_analysis(self):
        """Consistency analysis should extract win rate."""
        interpreter = AblationInterpreter17_1_C(self.result_a, self.result_b)
        consistency = interpreter.analyze_consistency()

        self.assertEqual(consistency.total_seeds, 5)
        self.assertEqual(consistency.seeds_with_improvement, 5)
        self.assertEqual(consistency.consistency_score, 100.0)
        self.assertTrue(consistency.is_consistent)

    def test_meaningfulness_analysis(self):
        """Meaningfulness analysis should assess improvement magnitude."""
        interpreter = AblationInterpreter17_1_C(self.result_a, self.result_b)
        meaningfulness = interpreter.analyze_meaningfulness()

        self.assertEqual(meaningfulness.average_improvement_percent, 10.09)
        self.assertTrue(meaningfulness.is_meaningful)

    def test_causality_analysis(self):
        """Causality analysis should explain causal link."""
        interpreter = AblationInterpreter17_1_C(self.result_a, self.result_b)
        causality = interpreter.analyze_causality()

        self.assertIn("calibration", causality.causal_conclusion.lower())
        # Check for "sole difference" or "only difference"
        conclusion_lower = causality.causal_conclusion.lower()
        self.assertTrue(
            "sole difference" in conclusion_lower or "only difference" in conclusion_lower
        )

    def test_convenience_function(self):
        """Convenience function should work."""
        conclusion = interpret_ablation_17_1_c(self.result_a, self.result_b)

        self.assertIsInstance(conclusion, ResearchConclusion17_1_C)
        self.assertTrue(conclusion.is_conclusive())
        self.assertIn("calibration", conclusion.conclusion.lower())


if __name__ == "__main__":
    unittest.main()
