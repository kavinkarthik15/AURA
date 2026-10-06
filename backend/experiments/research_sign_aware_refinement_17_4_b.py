"""Phase 17.4B: Controlled Learning-Rate Refinement for Sign-Aware Calibration.

Tests different learning rates to find optimal balance between:
- Retaining benefit of signed errors (17.3 improvement)
- Preventing over-correction on diverse seeds (17.4A problem)

Primary criterion: ≥80% seed win rate with no severe degradation
Secondary criterion: Best average MAE improvement
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


class _ResearchSignAwareCalibrationWithLearningRate:
    """Wrapper for 17.3A experiment with custom learning rate."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        """Initialize with custom learning rate."""
        from backend.experiments.research_sign_aware_calibration_17_3_a import (
            ResearchSignAwareCalibration17_3_A,
        )

        self.base_experiment = ResearchSignAwareCalibration17_3_A(seed=seed, learning_rate=learning_rate)

    def run(self):
        """Run experiment and return results."""
        return self.base_experiment.run()


@dataclass
class LearningRateSeedResult:
    """Result for one learning rate on one seed."""

    learning_rate: float
    seed: int
    baseline_mae: float
    original_mae: float
    sign_aware_mae: float
    sign_aware_wins: bool
    original_improvement: float
    sign_aware_improvement: float
    improvement_delta: float
    original_direction_accuracy: float
    sign_aware_direction_accuracy: float
    direction_accuracy_delta: float
    original_negative_bias_accuracy: float
    sign_aware_negative_bias_accuracy: float
    max_bias_change: float
    any_bias_sign_flip: bool


@dataclass
class LearningRateComparisonResult:
    """Statistics for one learning rate across all seeds."""

    learning_rate: float
    seed_results: List[LearningRateSeedResult]
    mean_improvement_delta: float
    std_improvement_delta: float
    win_count: int
    win_rate: float
    seeds_with_degradation: int
    seeds_with_severe_dir_acc_loss: int  # > 10%
    max_direction_accuracy_loss: float
    meets_robustness_criterion: bool


@dataclass
class ResearchSignAwareRefinement17_4_BResult:
    """Complete results for 17.4B learning rate refinement."""

    experiment_name: str = "17.4B: Sign-Aware Learning Rate Refinement"
    timestamp: str = ""
    seeds: List[int] = None
    learning_rates: List[float] = None
    results_by_learning_rate: Dict[float, LearningRateComparisonResult] = None
    recommended_learning_rate: float = None
    analysis_summary: str = ""

    def __post_init__(self):
        if self.timestamp == "":
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.seeds is None:
            self.seeds = [42, 123, 456, 789, 999]
        if self.learning_rates is None:
            self.learning_rates = [0.007, 0.005, 0.003, 0.002, 0.001]
        if self.results_by_learning_rate is None:
            self.results_by_learning_rate = {}

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "experiment_name": self.experiment_name,
            "timestamp": self.timestamp,
            "seeds": self.seeds,
            "learning_rates": self.learning_rates,
            "results_by_learning_rate": {
                str(lr): {
                    "learning_rate": result.learning_rate,
                    "seed_results": [asdict(r) for r in result.seed_results],
                    "mean_improvement_delta": result.mean_improvement_delta,
                    "std_improvement_delta": result.std_improvement_delta,
                    "win_count": result.win_count,
                    "win_rate": result.win_rate,
                    "seeds_with_degradation": result.seeds_with_degradation,
                    "seeds_with_severe_dir_acc_loss": result.seeds_with_severe_dir_acc_loss,
                    "max_direction_accuracy_loss": result.max_direction_accuracy_loss,
                    "meets_robustness_criterion": result.meets_robustness_criterion,
                }
                for lr, result in self.results_by_learning_rate.items()
            },
            "recommended_learning_rate": self.recommended_learning_rate,
            "analysis_summary": self.analysis_summary,
        }


class ResearchSignAwareRefinement17_4_B:
    """Controlled learning-rate refinement for sign-aware calibrator."""

    def __init__(self, seeds: List[int] = None, learning_rates: List[float] = None):
        """Initialize refinement experiment.
        
        Args:
            seeds: Seeds to test. Defaults to [42, 123, 456, 789, 999].
            learning_rates: Learning rates to test. Defaults to [0.007, 0.005, 0.003, 0.002, 0.001].
        """
        self.seeds = seeds or [42, 123, 456, 789, 999]
        self.learning_rates = learning_rates or [0.007, 0.005, 0.003, 0.002, 0.001]
        self.baseline_mae = 5.7875  # From 17.1 baseline

    def run(self) -> ResearchSignAwareRefinement17_4_BResult:
        """Run learning rate refinement across all seeds.
        
        Returns:
            Complete refinement results with recommendations.
        """
        result = ResearchSignAwareRefinement17_4_BResult(
            seeds=self.seeds, learning_rates=self.learning_rates
        )

        print(f"\n{'='*70}")
        print("PHASE 17.4B: SIGN-AWARE LEARNING RATE REFINEMENT")
        print(f"{'='*70}")
        print(f"Testing {len(self.learning_rates)} learning rates across {len(self.seeds)} seeds")
        print(f"Learning rates: {self.learning_rates}")
        print(f"Seeds: {self.seeds}\n")

        # Test each learning rate
        for lr in self.learning_rates:
            print(f"\n{'='*70}")
            print(f"Testing Learning Rate: {lr}")
            print(f"{'='*70}")

            lr_results = self._test_learning_rate(lr)
            result.results_by_learning_rate[lr] = lr_results

            # Print summary for this learning rate
            self._print_learning_rate_summary(lr_results)

        # Determine recommended learning rate
        result.recommended_learning_rate = self._select_recommended_learning_rate(
            result.results_by_learning_rate
        )
        result.analysis_summary = self._generate_analysis_summary(
            result.results_by_learning_rate, result.recommended_learning_rate
        )

        # Print overall summary
        self._print_overall_summary(result)

        return result

    def _test_learning_rate(self, learning_rate: float) -> LearningRateComparisonResult:
        """Test sign-aware calibrator with specific learning rate across all seeds."""
        seed_results: List[LearningRateSeedResult] = []

        for seed in self.seeds:
            # Create custom comparison with this learning rate
            comparison = _ResearchSignAwareCalibrationWithLearningRate(
                seed=seed, learning_rate=learning_rate
            )
            comparison_result = comparison.run()

            # Extract metrics
            original_mae = comparison_result.existing_calibrator_result.held_out_mae
            sign_aware_mae = comparison_result.sign_aware_calibrator_result.held_out_mae

            original_improvement = self.baseline_mae - original_mae
            sign_aware_improvement = self.baseline_mae - sign_aware_mae
            improvement_delta = sign_aware_improvement - original_improvement

            original_acc = comparison_result.existing_calibrator_result.direction_accuracy
            sign_aware_acc = comparison_result.sign_aware_calibrator_result.direction_accuracy
            dir_acc_delta = sign_aware_acc - original_acc

            original_neg_bias_acc = self._compute_category_subset_accuracy(
                comparison_result.existing_calibrator_result.category_accuracies,
                {"high_skill_practice", "high_motivation"},
            )
            sign_aware_neg_bias_acc = self._compute_category_subset_accuracy(
                comparison_result.sign_aware_calibrator_result.category_accuracies,
                {"high_skill_practice", "high_motivation"},
            )

            # Compute max bias change
            orig_biases = comparison_result.existing_calibrator_result.final_expected_state_bias
            sa_biases = comparison_result.sign_aware_calibrator_result.final_expected_state_bias
            max_bias_change = max(
                abs(sa_biases.get(k, 0) - orig_biases.get(k, 0))
                for k in set(orig_biases.keys()) | set(sa_biases.keys())
            ) if orig_biases else 0.0

            # Check if any bias changes sign
            any_sign_flip = any(
                (orig_biases.get(k, 0) >= 0) != (sa_biases.get(k, 0) >= 0)
                for k in set(orig_biases.keys()) | set(sa_biases.keys())
            ) if orig_biases else False

            seed_result = LearningRateSeedResult(
                learning_rate=learning_rate,
                seed=seed,
                baseline_mae=self.baseline_mae,
                original_mae=original_mae,
                sign_aware_mae=sign_aware_mae,
                sign_aware_wins=sign_aware_mae < original_mae,
                original_improvement=original_improvement,
                sign_aware_improvement=sign_aware_improvement,
                improvement_delta=improvement_delta,
                original_direction_accuracy=original_acc,
                sign_aware_direction_accuracy=sign_aware_acc,
                direction_accuracy_delta=dir_acc_delta,
                original_negative_bias_accuracy=original_neg_bias_acc,
                sign_aware_negative_bias_accuracy=sign_aware_neg_bias_acc,
                max_bias_change=max_bias_change,
                any_bias_sign_flip=any_sign_flip,
            )
            seed_results.append(seed_result)

            print(f"  Seed {seed:3d}: MAE={sign_aware_mae:.4f} ({improvement_delta:+.4f}), "
                  f"Dir Acc={sign_aware_acc:.1%} ({dir_acc_delta:+.1%}), "
                  f"Win={'✓' if seed_result.sign_aware_wins else '✗'}")

        # Calculate statistics
        improvement_deltas = [r.improvement_delta for r in seed_results]
        win_count = sum(1 for r in seed_results if r.sign_aware_wins)
        degradation_count = sum(1 for r in seed_results if r.improvement_delta < -0.05)
        severe_dir_acc_loss = sum(
            1 for r in seed_results if r.direction_accuracy_delta < -0.10
        )
        max_dir_acc_loss = min([r.direction_accuracy_delta for r in seed_results], default=0)

        comparison = LearningRateComparisonResult(
            learning_rate=learning_rate,
            seed_results=seed_results,
            mean_improvement_delta=sum(improvement_deltas) / len(improvement_deltas),
            std_improvement_delta=self._std_dev(improvement_deltas),
            win_count=win_count,
            win_rate=win_count / len(seed_results),
            seeds_with_degradation=degradation_count,
            seeds_with_severe_dir_acc_loss=severe_dir_acc_loss,
            max_direction_accuracy_loss=max_dir_acc_loss,
            meets_robustness_criterion=(win_count >= 4 and degradation_count == 0),
        )

        return comparison

    def _compute_category_subset_accuracy(
        self, category_accuracies: Dict[str, float], target_categories: set
    ) -> float:
        """Compute accuracy for subset of categories."""
        subset_accuracies = [
            acc
            for cat, acc in category_accuracies.items()
            if cat in target_categories
        ]
        return sum(subset_accuracies) / len(subset_accuracies) if subset_accuracies else 0.0

    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _print_learning_rate_summary(self, result: LearningRateComparisonResult) -> None:
        """Print summary for single learning rate."""
        print(f"\nLearning Rate {result.learning_rate} Summary:")
        print(f"  Win rate: {result.win_count}/5 ({result.win_rate:.0%})")
        print(f"  Mean improvement delta: {result.mean_improvement_delta:+.4f}")
        print(f"  Std dev: {result.std_improvement_delta:.4f}")
        print(f"  Severe direction accuracy loss: {result.seeds_with_severe_dir_acc_loss}/5")
        print(f"  Max direction accuracy loss: {result.max_direction_accuracy_loss:+.1%}")
        print(f"  Robustness criterion met: {'✓ YES' if result.meets_robustness_criterion else '✗ NO'}")

    def _select_recommended_learning_rate(
        self, results: Dict[float, LearningRateComparisonResult]
    ) -> float:
        """Select recommended learning rate based on criteria."""
        # Primary criterion: robustness (≥80% win rate, no degradation)
        robust_rates = [
            lr for lr, result in results.items() if result.meets_robustness_criterion
        ]

        if robust_rates:
            # Among robust rates, pick one with best improvement delta
            return max(robust_rates, key=lambda lr: results[lr].mean_improvement_delta)

        # Secondary: pick learning rate with best win rate
        return max(results.keys(), key=lambda lr: (results[lr].win_rate, results[lr].mean_improvement_delta))

    def _generate_analysis_summary(
        self, results: Dict[float, LearningRateComparisonResult], recommended_lr: float
    ) -> str:
        """Generate text summary of analysis."""
        lines = []
        lines.append("LEARNING RATE ANALYSIS SUMMARY\n")

        # Find which rates meet robustness criterion
        robust_rates = [lr for lr, r in results.items() if r.meets_robustness_criterion]

        if robust_rates:
            lines.append(f"✓ {len(robust_rates)} learning rate(s) meet robustness criterion (≥80% win rate)")
            for lr in sorted(robust_rates):
                result = results[lr]
                lines.append(
                    f"  LR {lr}: {result.win_count}/5 wins, "
                    f"Δ {result.mean_improvement_delta:+.4f}, "
                    f"Dir Acc loss {result.max_direction_accuracy_loss:+.1%}"
                )
        else:
            lines.append("✗ No learning rate meets robustness criterion")
            best_lr = max(results.keys(), key=lambda lr: results[lr].win_rate)
            best_result = results[best_lr]
            lines.append(
                f"  Best alternative: LR {best_lr} with {best_result.win_rate:.0%} win rate"
            )

        lines.append(f"\nRECOMMENDED: Learning Rate {recommended_lr}")
        rec_result = results[recommended_lr]
        lines.append(f"  Win rate: {rec_result.win_count}/5 ({rec_result.win_rate:.0%})")
        lines.append(f"  Mean improvement delta: {rec_result.mean_improvement_delta:+.4f}")
        lines.append(f"  Robustness: {'✓ Meets criterion' if rec_result.meets_robustness_criterion else '✗ Needs refinement'}")

        return "\n".join(lines)

    def _print_overall_summary(self, result: ResearchSignAwareRefinement17_4_BResult) -> None:
        """Print comprehensive overall summary."""
        print(f"\n\n{'='*70}")
        print("PHASE 17.4B OVERALL SUMMARY")
        print(f"{'='*70}\n")

        # Print table of results
        print("Learning Rate Performance Summary:")
        print(f"{'LR':>8} {'Wins':>6} {'Rate':>8} {'Δ MAE':>10} {'σ':>8} {'Dir Acc':>10} {'Robust':>10}")
        print("-" * 70)
        
        for lr in sorted(result.learning_rates):
            res = result.results_by_learning_rate[lr]
            robust = "✓ YES" if res.meets_robustness_criterion else "✗ NO"
            print(
                f"{lr:>8.4f} {res.win_count:>2}/5    {res.win_rate:>7.0%}  "
                f"{res.mean_improvement_delta:>+9.4f}  {res.std_improvement_delta:>7.4f}  "
                f"{res.max_direction_accuracy_loss:>+9.1%}  {robust:>10}"
            )

        print(f"\n{result.analysis_summary}")
        print(f"{'='*70}\n")


def run_research_sign_aware_refinement_17_4_b(
    seeds: List[int] = None, learning_rates: List[float] = None
) -> ResearchSignAwareRefinement17_4_BResult:
    """Convenience function to run 17.4B learning rate refinement."""
    experiment = ResearchSignAwareRefinement17_4_B(seeds=seeds, learning_rates=learning_rates)
    return experiment.run()


def save_17_4_b_results(
    result: ResearchSignAwareRefinement17_4_BResult, output_path: str = None
) -> str:
    """Save 17.4B results to JSON file."""
    if output_path is None:
        output_path = (
            Path(__file__).parent / "results" / "research_17_4_b_sign_aware_refinement.json"
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    result = run_research_sign_aware_refinement_17_4_b()
    save_17_4_b_results(result)
