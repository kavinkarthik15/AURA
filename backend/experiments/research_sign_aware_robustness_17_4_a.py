"""Phase 17.4A: Multi-Seed Robustness Validation for Sign-Aware Calibration.

Validates that the 17.3 sign-aware calibration improvement generalizes
across independent random seeds (42, 123, 456, 789, 999).

Success criterion: Sign-aware outperforms original on ≥80% of seeds (4/5).
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from backend.experiments.research_sign_aware_calibration_17_3_a import (
    ResearchSignAwareCalibration17_3_A,
)


@dataclass
class SeedComparisonResult:
    """Results for a single seed."""

    seed: int
    baseline_mae: float
    original_mae: float
    sign_aware_mae: float
    original_improvement: float  # Original - Baseline
    sign_aware_improvement: float  # Sign-aware - Baseline
    original_direction_accuracy: float
    sign_aware_direction_accuracy: float
    original_negative_bias_accuracy: float
    sign_aware_negative_bias_accuracy: float
    sign_aware_wins: bool  # True if sign_aware_mae < original_mae


@dataclass
class RobustnessStatistics:
    """Aggregated statistics across all seeds."""

    mean_original_improvement: float
    mean_sign_aware_improvement: float
    mean_improvement_delta: float  # sign_aware - original
    median_improvement_delta: float
    min_improvement_delta: float
    max_improvement_delta: float
    std_dev_improvement_delta: float
    sign_aware_win_count: int
    sign_aware_win_rate: float
    all_seeds_no_regression: bool  # True if sign-aware never worse by >1% MAE


@dataclass
class ResearchSignAwareRobustness17_4_AResult:
    """Complete results for 17.4A robustness validation."""

    experiment_name: str = "17.4A: Multi-Seed Sign-Aware Calibration Robustness"
    timestamp: str = ""
    seeds: List[int] = None
    seed_results: Dict[int, SeedComparisonResult] = None
    statistics: RobustnessStatistics = None
    success_criterion_met: bool = False

    def __post_init__(self):
        if self.timestamp == "":
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.seeds is None:
            self.seeds = [42, 123, 456, 789, 999]
        if self.seed_results is None:
            self.seed_results = {}

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        result = {
            "experiment_name": self.experiment_name,
            "timestamp": self.timestamp,
            "seeds": self.seeds,
            "seed_results": {
                str(seed): asdict(result) for seed, result in self.seed_results.items()
            },
            "statistics": asdict(self.statistics) if self.statistics else None,
            "success_criterion_met": self.success_criterion_met,
        }
        return result


class ResearchSignAwareRobustness17_4_A:
    """Multi-seed robustness validation for sign-aware calibration."""

    def __init__(self, seeds: List[int] = None):
        """Initialize robustness experiment.

        Args:
            seeds: List of random seeds to test. Defaults to [42, 123, 456, 789, 999].
        """
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> ResearchSignAwareRobustness17_4_AResult:
        """Run robustness validation across all seeds.

        Returns:
            Complete robustness result with statistics and per-seed comparisons.
        """
        result = ResearchSignAwareRobustness17_4_AResult(seeds=self.seeds)
        seed_results: Dict[int, SeedComparisonResult] = {}

        # Negative-bias categories for per-category accuracy calculation
        negative_bias_categories = {"high_skill_practice", "high_motivation"}

        # Run comparison for each seed
        for seed in self.seeds:
            print(f"\n{'='*60}")
            print(f"Testing seed: {seed}")
            print(f"{'='*60}")

            comparison = ResearchSignAwareCalibration17_3_A(seed=seed)
            comparison_result = comparison.run()

            # Extract metrics
            baseline_mae = 5.7875  # From 17.1 baseline
            original_mae = comparison_result.existing_calibrator_result.held_out_mae
            sign_aware_mae = comparison_result.sign_aware_calibrator_result.held_out_mae

            original_improvement = baseline_mae - original_mae
            sign_aware_improvement = baseline_mae - sign_aware_mae

            original_accuracy = comparison_result.existing_calibrator_result.direction_accuracy
            sign_aware_accuracy = comparison_result.sign_aware_calibrator_result.direction_accuracy

            # Calculate negative-bias direction accuracy
            original_negative_bias_accuracy = self._compute_category_subset_accuracy(
                comparison_result.existing_calibrator_result.category_accuracies,
                negative_bias_categories,
            )
            sign_aware_negative_bias_accuracy = self._compute_category_subset_accuracy(
                comparison_result.sign_aware_calibrator_result.category_accuracies,
                negative_bias_categories,
            )

            sign_aware_wins = sign_aware_mae < original_mae

            # Store result
            seed_result = SeedComparisonResult(
                seed=seed,
                baseline_mae=baseline_mae,
                original_mae=original_mae,
                sign_aware_mae=sign_aware_mae,
                original_improvement=original_improvement,
                sign_aware_improvement=sign_aware_improvement,
                original_direction_accuracy=original_accuracy,
                sign_aware_direction_accuracy=sign_aware_accuracy,
                original_negative_bias_accuracy=original_negative_bias_accuracy,
                sign_aware_negative_bias_accuracy=sign_aware_negative_bias_accuracy,
                sign_aware_wins=sign_aware_wins,
            )
            seed_results[seed] = seed_result

            # Print result summary
            print(f"Seed {seed} Results:")
            print(f"  Baseline MAE:            {baseline_mae:.4f}")
            print(f"  Original MAE:            {original_mae:.4f} (Δ {original_improvement:+.4f})")
            print(f"  Sign-aware MAE:          {sign_aware_mae:.4f} (Δ {sign_aware_improvement:+.4f})")
            print(f"  Improvement delta:       {sign_aware_improvement - original_improvement:+.4f}")
            print(f"  Sign-aware wins:         {sign_aware_wins}")
            print(f"  Original direction acc:  {original_accuracy:.2%}")
            print(f"  Sign-aware direction acc:{sign_aware_accuracy:.2%}")
            print(f"  Neg-bias acc (orig):     {original_negative_bias_accuracy:.2%}")
            print(f"  Neg-bias acc (sign-aware):{sign_aware_negative_bias_accuracy:.2%}")

        # Calculate statistics
        result.seed_results = seed_results
        statistics = self._calculate_statistics(seed_results)
        result.statistics = statistics

        # Check success criterion
        result.success_criterion_met = (
            statistics.sign_aware_win_rate >= 0.80
            and statistics.all_seeds_no_regression
        )

        # Print summary
        self._print_summary(result)

        return result

    def _calculate_statistics(
        self, seed_results: Dict[int, SeedComparisonResult]
    ) -> RobustnessStatistics:
        """Calculate aggregate statistics across seeds."""
        results_list = list(seed_results.values())

        original_improvements = [r.original_improvement for r in results_list]
        sign_aware_improvements = [r.sign_aware_improvement for r in results_list]
        improvement_deltas = [
            r.sign_aware_improvement - r.original_improvement for r in results_list
        ]

        win_count = sum(1 for r in results_list if r.sign_aware_wins)
        win_rate = win_count / len(results_list)

        # Check if any seed shows regression > 1%
        no_regression = all(
            abs(delta) < 0.01 or delta >= -0.01 for delta in improvement_deltas
        )

        return RobustnessStatistics(
            mean_original_improvement=sum(original_improvements)
            / len(original_improvements),
            mean_sign_aware_improvement=sum(sign_aware_improvements)
            / len(sign_aware_improvements),
            mean_improvement_delta=sum(improvement_deltas) / len(improvement_deltas),
            median_improvement_delta=sorted(improvement_deltas)[len(improvement_deltas) // 2],
            min_improvement_delta=min(improvement_deltas),
            max_improvement_delta=max(improvement_deltas),
            std_dev_improvement_delta=self._std_dev(improvement_deltas),
            sign_aware_win_count=win_count,
            sign_aware_win_rate=win_rate,
            all_seeds_no_regression=no_regression,
        )

    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _compute_category_subset_accuracy(
        self, category_accuracies: Dict[str, float], target_categories: set
    ) -> float:
        """Compute accuracy for subset of categories."""
        subset_accuracies = [
            acc
            for cat, acc in category_accuracies.items()
            if cat in target_categories
        ]
        if not subset_accuracies:
            return 0.0
        return sum(subset_accuracies) / len(subset_accuracies)

    def _print_summary(self, result: ResearchSignAwareRobustness17_4_AResult) -> None:
        """Print comprehensive summary."""
        stats = result.statistics
        print(f"\n\n{'='*60}")
        print("ROBUSTNESS VALIDATION SUMMARY")
        print(f"{'='*60}")

        print(f"\nSeed Results:")
        for seed, seed_result in result.seed_results.items():
            win_indicator = "✓ WIN" if seed_result.sign_aware_wins else "✗ LOSS"
            delta = seed_result.sign_aware_improvement - seed_result.original_improvement
            print(
                f"  Seed {seed:3d}: {win_indicator}  "
                f"Improvement delta: {delta:+.4f}  "
                f"(orig={seed_result.original_improvement:.4f}, "
                f"sign-aware={seed_result.sign_aware_improvement:.4f})"
            )

        print(f"\nAggregate Statistics:")
        print(f"  Mean original improvement:       {stats.mean_original_improvement:.4f}")
        print(f"  Mean sign-aware improvement:     {stats.mean_sign_aware_improvement:.4f}")
        print(f"  Mean improvement delta (sign-aware - original): {stats.mean_improvement_delta:+.4f}")
        print(f"  Median improvement delta:        {stats.median_improvement_delta:+.4f}")
        print(f"  Min improvement delta:           {stats.min_improvement_delta:+.4f}")
        print(f"  Max improvement delta:           {stats.max_improvement_delta:+.4f}")
        print(f"  Std dev of delta:                {stats.std_dev_improvement_delta:.4f}")

        print(f"\nWin Statistics:")
        print(
            f"  Sign-aware wins: {stats.sign_aware_win_count}/{len(result.seeds)} "
            f"({stats.sign_aware_win_rate:.1%})"
        )
        print(f"  No regression on any seed: {stats.all_seeds_no_regression}")

        print(f"\nSuccess Criterion (≥80% win rate + no regression):")
        if result.success_criterion_met:
            print("  ✓ PASS - Sign-aware robustly outperforms across seeds")
        else:
            if stats.sign_aware_win_rate < 0.80:
                print(
                    f"  ✗ FAIL - Win rate {stats.sign_aware_win_rate:.1%} < 80% threshold"
                )
            if not stats.all_seeds_no_regression:
                print(f"  ✗ FAIL - Regression detected on one or more seeds")

        print(f"{'='*60}\n")


def run_research_sign_aware_robustness_17_4_a(
    seeds: List[int] = None,
) -> ResearchSignAwareRobustness17_4_AResult:
    """Convenience function to run 17.4A robustness validation.

    Args:
        seeds: List of seeds to test. Defaults to [42, 123, 456, 789, 999].

    Returns:
        Robustness validation result.
    """
    experiment = ResearchSignAwareRobustness17_4_A(seeds=seeds)
    return experiment.run()


def save_17_4_a_results(
    result: ResearchSignAwareRobustness17_4_AResult, output_path: str = None
) -> str:
    """Save 17.4A results to JSON file.

    Args:
        result: Robustness validation result.
        output_path: Path to save JSON. Defaults to results/research_17_4_a_sign_aware_robustness.json.

    Returns:
        Path to saved file.
    """
    if output_path is None:
        output_path = (
            Path(__file__).parent / "results" / "research_17_4_a_sign_aware_robustness.json"
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    # Run with default seeds [42, 123, 456, 789, 999]
    result = run_research_sign_aware_robustness_17_4_a()

    # Save results
    save_17_4_a_results(result)
