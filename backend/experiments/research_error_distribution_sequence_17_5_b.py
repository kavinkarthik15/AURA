"""
Phase 17.5B: Error Distribution & Sequence Dynamics Analysis

Research Question:
  If every individual calibration update has the correct direction,
  why do some random seeds still produce substantially worse final calibration?

Hypothesis:
  The sequence and distribution of errors (not individual error signs) cause
  parameter drift. Even with 100% directionally-correct updates, persistent
  error patterns in one direction can accumulate bias.

Metrics:
  1. Error Balance: positive/negative/zero counts and ratios
  2. Error Magnitude: mean, median, max, 95th percentile
  3. Temporal Sequence: streaks, transitions, early vs late training
  4. Cumulative Error: trajectory over time
  5. Category Breakdown: error stats per category per seed

Comparison:
  Successful seeds (42, 123) vs Problematic seeds (456, 789, 999)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path
from datetime import datetime
import statistics

from backend.services.simulation_engine import SimulationEngine
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ErrorBalanceMetrics:
    """Metrics for error balance across a seed's training."""
    positive_error_count: int = 0
    negative_error_count: int = 0
    zero_error_count: int = 0
    positive_error_ratio: float = 0.0
    negative_error_ratio: float = 0.0
    mean_signed_error: float = 0.0
    median_signed_error: float = 0.0
    std_signed_error: float = 0.0


@dataclass
class ErrorMagnitudeMetrics:
    """Metrics for error magnitude across a seed's training."""
    mean_abs_error: float = 0.0
    median_abs_error: float = 0.0
    max_abs_error: float = 0.0
    percentile_95_abs_error: float = 0.0


@dataclass
class TemporalSequenceMetrics:
    """Metrics for temporal/sequence characteristics."""
    longest_positive_streak: int = 0
    longest_negative_streak: int = 0
    positive_to_negative_transitions: int = 0
    negative_to_positive_transitions: int = 0
    # Early vs late training (5 segments)
    early_mean_signed_error: float = 0.0      # 0-20%
    early_mid_mean_signed_error: float = 0.0  # 20-40%
    mid_mean_signed_error: float = 0.0        # 40-60%
    mid_late_mean_signed_error: float = 0.0   # 60-80%
    late_mean_signed_error: float = 0.0       # 80-100%


@dataclass
class CumulativeErrorMetrics:
    """Metrics for cumulative error trajectory."""
    final_cumulative_error: float = 0.0
    final_cumulative_abs_error: float = 0.0
    cumulative_error_trajectory: List[float] = field(default_factory=list)
    cumulative_abs_error_trajectory: List[float] = field(default_factory=list)


@dataclass
class CategoryErrorStats:
    """Error statistics for a single category."""
    category_name: str
    positive_error_count: int = 0
    negative_error_count: int = 0
    zero_error_count: int = 0
    mean_signed_error: float = 0.0
    mean_abs_error: float = 0.0
    total_events: int = 0


@dataclass
class SeedDistributionResult:
    """Complete analysis results for a single seed."""
    seed: int
    total_events: int
    balance_metrics: ErrorBalanceMetrics = field(default_factory=ErrorBalanceMetrics)
    magnitude_metrics: ErrorMagnitudeMetrics = field(default_factory=ErrorMagnitudeMetrics)
    sequence_metrics: TemporalSequenceMetrics = field(default_factory=TemporalSequenceMetrics)
    cumulative_metrics: CumulativeErrorMetrics = field(default_factory=CumulativeErrorMetrics)
    category_stats: Dict[str, CategoryErrorStats] = field(default_factory=dict)
    final_mae: float = 0.0


@dataclass
class DistributionSequenceAnalysisResult:
    """Aggregated results across all seeds."""
    analysis_date: str
    learning_rate: float
    total_seeds: int
    seed_results: Dict[int, SeedDistributionResult] = field(default_factory=dict)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "analysis_date": self.analysis_date,
            "learning_rate": self.learning_rate,
            "total_seeds": self.total_seeds,
            "seed_results": {
                str(seed): {
                    "seed": result.seed,
                    "total_events": result.total_events,
                    "balance_metrics": asdict(result.balance_metrics),
                    "magnitude_metrics": asdict(result.magnitude_metrics),
                    "sequence_metrics": asdict(result.sequence_metrics),
                    "cumulative_metrics": {
                        "final_cumulative_error": result.cumulative_metrics.final_cumulative_error,
                        "final_cumulative_abs_error": result.cumulative_metrics.final_cumulative_abs_error,
                        "cumulative_error_trajectory_length": len(result.cumulative_metrics.cumulative_error_trajectory),
                    },
                    "category_stats": {
                        cat: asdict(stats)
                        for cat, stats in result.category_stats.items()
                    },
                    "final_mae": result.final_mae,
                }
                for seed, result in self.seed_results.items()
            },
        }


# ============================================================================
# Analyzer
# ============================================================================


class ErrorDistributionSequenceAnalyzer:
    """
    Analyzes error distribution and sequence dynamics for a single seed.
    Measures how error patterns differ between seeds.
    """

    def __init__(
        self,
        seed: int,
        learning_rate: float = 0.007,
        state_adjustment_bounds: Tuple[float, float] = (-0.12, 0.12),
    ):
        self.seed = seed
        self.learning_rate = learning_rate
        self.state_adjustment_bounds = state_adjustment_bounds

    def analyze_seed(self) -> SeedDistributionResult:
        """
        Analyze a single seed's error distribution and sequence.
        Returns complete metrics for the seed.
        """
        # Generate dataset
        generator = ResearchBenchmarkGenerator(seed=self.seed)
        dataset = generator.generate_dataset(training_size=80, held_out_size=20)
        training_experiences = dataset.training_experiences

        # Initialize simulator
        sim = SimulationEngine()

        # Track all signed errors
        all_signed_errors: List[float] = []
        category_errors: Dict[str, List[float]] = {}
        cumulative_signed_error = 0.0
        cumulative_abs_error = 0.0
        cumulative_error_trajectory: List[float] = []
        cumulative_abs_error_trajectory: List[float] = []

        # Track streaks and transitions
        current_streak_sign: Optional[int] = None  # -1, 0, or +1
        current_streak_length = 0
        longest_positive_streak = 0
        longest_negative_streak = 0
        positive_to_negative_transitions = 0
        negative_to_positive_transitions = 0

        # Track by training segment
        segment_errors: Dict[int, List[float]] = {0: [], 1: [], 2: [], 3: [], 4: []}

        # Process each experience
        for idx, experience in enumerate(training_experiences):
            # Determine segment (0-4)
            segment = min(4, int((idx / len(training_experiences)) * 5))

            # Get predicted state
            prediction_result = sim.simulate_action(
                current_state=experience.initial_state,
                action=experience.selected_action,
            )
            predicted = prediction_result.get("predicted_future_state", {})

            # Compute signed error
            actual = experience.actual_future_state
            signed_error = self._compute_signed_error(actual, predicted)

            # Track error
            all_signed_errors.append(signed_error)
            segment_errors[segment].append(signed_error)
            cumulative_signed_error += signed_error
            cumulative_abs_error += abs(signed_error)
            cumulative_error_trajectory.append(cumulative_signed_error)
            cumulative_abs_error_trajectory.append(cumulative_abs_error)

            # Track category
            category = experience.category
            if category not in category_errors:
                category_errors[category] = []
            category_errors[category].append(signed_error)

            # Track streaks and transitions
            error_sign = self._sign(signed_error)
            if error_sign != 0:
                if error_sign == current_streak_sign:
                    current_streak_length += 1
                else:
                    # Transition occurred
                    if current_streak_sign == 1:
                        longest_positive_streak = max(longest_positive_streak, current_streak_length)
                        if error_sign == -1:
                            positive_to_negative_transitions += 1
                    elif current_streak_sign == -1:
                        longest_negative_streak = max(longest_negative_streak, current_streak_length)
                        if error_sign == 1:
                            negative_to_positive_transitions += 1
                    current_streak_sign = error_sign
                    current_streak_length = 1

        # Finalize streaks
        if current_streak_sign == 1:
            longest_positive_streak = max(longest_positive_streak, current_streak_length)
        elif current_streak_sign == -1:
            longest_negative_streak = max(longest_negative_streak, current_streak_length)

        # Compute balance metrics
        positive_errors = [e for e in all_signed_errors if e > 0]
        negative_errors = [e for e in all_signed_errors if e < 0]
        zero_errors = [e for e in all_signed_errors if e == 0]

        balance_metrics = ErrorBalanceMetrics(
            positive_error_count=len(positive_errors),
            negative_error_count=len(negative_errors),
            zero_error_count=len(zero_errors),
            positive_error_ratio=len(positive_errors) / len(all_signed_errors) if all_signed_errors else 0.0,
            negative_error_ratio=len(negative_errors) / len(all_signed_errors) if all_signed_errors else 0.0,
            mean_signed_error=statistics.mean(all_signed_errors) if all_signed_errors else 0.0,
            median_signed_error=statistics.median(all_signed_errors) if all_signed_errors else 0.0,
            std_signed_error=statistics.stdev(all_signed_errors) if len(all_signed_errors) > 1 else 0.0,
        )

        # Compute magnitude metrics
        abs_errors = [abs(e) for e in all_signed_errors]
        magnitude_metrics = ErrorMagnitudeMetrics(
            mean_abs_error=statistics.mean(abs_errors) if abs_errors else 0.0,
            median_abs_error=statistics.median(abs_errors) if abs_errors else 0.0,
            max_abs_error=max(abs_errors) if abs_errors else 0.0,
            percentile_95_abs_error=self._percentile(abs_errors, 0.95) if abs_errors else 0.0,
        )

        # Compute temporal sequence metrics
        sequence_metrics = TemporalSequenceMetrics(
            longest_positive_streak=longest_positive_streak,
            longest_negative_streak=longest_negative_streak,
            positive_to_negative_transitions=positive_to_negative_transitions,
            negative_to_positive_transitions=negative_to_positive_transitions,
            early_mean_signed_error=statistics.mean(segment_errors[0]) if segment_errors[0] else 0.0,
            early_mid_mean_signed_error=statistics.mean(segment_errors[1]) if segment_errors[1] else 0.0,
            mid_mean_signed_error=statistics.mean(segment_errors[2]) if segment_errors[2] else 0.0,
            mid_late_mean_signed_error=statistics.mean(segment_errors[3]) if segment_errors[3] else 0.0,
            late_mean_signed_error=statistics.mean(segment_errors[4]) if segment_errors[4] else 0.0,
        )

        # Compute cumulative error metrics
        cumulative_metrics = CumulativeErrorMetrics(
            final_cumulative_error=cumulative_signed_error,
            final_cumulative_abs_error=cumulative_abs_error,
            cumulative_error_trajectory=cumulative_error_trajectory,
            cumulative_abs_error_trajectory=cumulative_abs_error_trajectory,
        )

        # Compute category stats
        category_stats = {}
        for category, errors in category_errors.items():
            pos = len([e for e in errors if e > 0])
            neg = len([e for e in errors if e < 0])
            zero = len([e for e in errors if e == 0])
            category_stats[category] = CategoryErrorStats(
                category_name=category,
                positive_error_count=pos,
                negative_error_count=neg,
                zero_error_count=zero,
                mean_signed_error=statistics.mean(errors) if errors else 0.0,
                mean_abs_error=statistics.mean([abs(e) for e in errors]) if errors else 0.0,
                total_events=len(errors),
            )

        # Compute final MAE for comparison with 17.4A
        final_mae = statistics.mean(abs_errors) if abs_errors else 0.0

        return SeedDistributionResult(
            seed=self.seed,
            total_events=len(all_signed_errors),
            balance_metrics=balance_metrics,
            magnitude_metrics=magnitude_metrics,
            sequence_metrics=sequence_metrics,
            cumulative_metrics=cumulative_metrics,
            category_stats=category_stats,
            final_mae=final_mae,
        )

    def _compute_signed_error(self, actual: Dict, predicted: Dict) -> float:
        """
        Compute signed error across all state fields.
        Returns the mean signed error across all fields.
        """
        errors = []
        for key in actual.keys():
            if key in predicted:
                actual_val = actual.get(key, 0.0)
                predicted_val = predicted.get(key, 0.0)
                if isinstance(actual_val, (int, float)) and isinstance(predicted_val, (int, float)):
                    errors.append(float(actual_val) - float(predicted_val))
        return statistics.mean(errors) if errors else 0.0

    @staticmethod
    def _sign(value: float) -> int:
        """Return -1, 0, or +1 for a value's sign."""
        if value > 0:
            return 1
        elif value < 0:
            return -1
        else:
            return 0

    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        """Compute p-th percentile of data (0-1)."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = (p * (len(sorted_data) - 1))
        lower = int(idx)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[lower]
        fraction = idx - lower
        return sorted_data[lower] * (1 - fraction) + sorted_data[upper] * fraction


# ============================================================================
# Orchestrator
# ============================================================================


class ResearchPhase17_5_B:
    """
    Orchestrates Phase 17.5B analysis across all 5 seeds.
    Identifies statistical properties distinguishing successful from problematic seeds.
    """

    def __init__(self, learning_rate: float = 0.007):
        self.learning_rate = learning_rate
        self.seeds = [42, 123, 456, 789, 999]

    def run(self) -> DistributionSequenceAnalysisResult:
        """Execute analysis for all seeds and generate results."""
        print("\n" + "=" * 80)
        print("Phase 17.5B: Error Distribution & Sequence Dynamics Analysis")
        print("=" * 80)

        seed_results = {}
        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = ErrorDistributionSequenceAnalyzer(seed=seed, learning_rate=self.learning_rate)
            result = analyzer.analyze_seed()
            seed_results[seed] = result
            print("[DONE]")

        # Create aggregated result
        analysis_result = DistributionSequenceAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            total_seeds=len(self.seeds),
            seed_results=seed_results,
        )

        # Print diagnostic tables
        self._print_comparison_table(analysis_result)
        self._print_temporal_table(analysis_result)
        self._print_category_table(analysis_result)
        self._print_cumulative_error_summary(analysis_result)

        # Save results
        self._save_results(analysis_result)

        return analysis_result

    def _print_comparison_table(self, result: DistributionSequenceAnalysisResult):
        """Print main comparison table of key metrics."""
        print("\n" + "=" * 120)
        print("COMPARISON TABLE: Error Distribution Metrics")
        print("=" * 120)
        print(
            f"{'Metric':<30} {'Seed 42':<15} {'Seed 123':<15} {'Seed 456':<15} {'Seed 789':<15} {'Seed 999':<15}"
        )
        print("-" * 120)

        def fmt(v):
            if isinstance(v, float):
                return f"{v:.4f}"
            return str(v)

        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]

        # Positive errors %
        row = "Positive errors %"
        row += "".join(
            [
                f"{result.seed_results[seed].balance_metrics.positive_error_ratio * 100:<15.2f}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Negative errors %
        row = "Negative errors %"
        row += "".join(
            [
                f"{result.seed_results[seed].balance_metrics.negative_error_ratio * 100:<15.2f}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Mean signed error
        row = "Mean signed error"
        row += "".join(
            [
                f"{result.seed_results[seed].balance_metrics.mean_signed_error:<15.4f}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Mean absolute error
        row = "Mean absolute error"
        row += "".join(
            [f"{result.seed_results[seed].magnitude_metrics.mean_abs_error:<15.4f}" for seed in [42, 123, 456, 789, 999]]
        )
        print(f"{row}")

        # Max absolute error
        row = "Max absolute error"
        row += "".join(
            [f"{result.seed_results[seed].magnitude_metrics.max_abs_error:<15.4f}" for seed in [42, 123, 456, 789, 999]]
        )
        print(f"{row}")

        # Longest positive streak
        row = "Longest positive streak"
        row += "".join(
            [
                f"{result.seed_results[seed].sequence_metrics.longest_positive_streak:<15}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Longest negative streak
        row = "Longest negative streak"
        row += "".join(
            [
                f"{result.seed_results[seed].sequence_metrics.longest_negative_streak:<15}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Transitions
        row = "Pos→Neg transitions"
        row += "".join(
            [
                f"{result.seed_results[seed].sequence_metrics.positive_to_negative_transitions:<15}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        row = "Neg→Pos transitions"
        row += "".join(
            [
                f"{result.seed_results[seed].sequence_metrics.negative_to_positive_transitions:<15}"
                for seed in [42, 123, 456, 789, 999]
            ]
        )
        print(f"{row}")

        # Final cumulative error
        row = "Final cumulative error"
        row += "".join(
            [f"{result.seed_results[seed].cumulative_metrics.final_cumulative_error:<15.4f}" for seed in [42, 123, 456, 789, 999]]
        )
        print(f"{row}")

        # Final MAE
        row = "Final MAE"
        row += "".join([f"{result.seed_results[seed].final_mae:<15.4f}" for seed in [42, 123, 456, 789, 999]])
        print(f"{row}")

    def _print_temporal_table(self, result: DistributionSequenceAnalysisResult):
        """Print temporal segment analysis table."""
        print("\n" + "=" * 120)
        print("TEMPORAL SEGMENTS: Mean Signed Error by Training Phase")
        print("=" * 120)
        print(
            f"{'Phase':<15} {'Seed 42':<15} {'Seed 123':<15} {'Seed 456':<15} {'Seed 789':<15} {'Seed 999':<15}"
        )
        print("-" * 120)

        phases = ["Early (0-20%)", "Early-Mid (20-40%)", "Mid (40-60%)", "Mid-Late (60-80%)", "Late (80-100%)"]
        metrics_keys = [
            "early_mean_signed_error",
            "early_mid_mean_signed_error",
            "mid_mean_signed_error",
            "mid_late_mean_signed_error",
            "late_mean_signed_error",
        ]

        for phase, metric_key in zip(phases, metrics_keys):
            row = f"{phase:<15}"
            for seed in [42, 123, 456, 789, 999]:
                value = getattr(result.seed_results[seed].sequence_metrics, metric_key)
                row += f"{value:<15.4f}"
            print(row)

    def _print_category_table(self, result: DistributionSequenceAnalysisResult):
        """Print category-level error analysis."""
        print("\n" + "=" * 120)
        print("CATEGORY BREAKDOWN: Mean Signed Error by Category and Seed")
        print("=" * 120)

        # Get all categories
        all_categories = set()
        for seed_result in result.seed_results.values():
            all_categories.update(seed_result.category_stats.keys())

        print(f"{'Category':<30} {'Seed 42':<15} {'Seed 123':<15} {'Seed 456':<15} {'Seed 789':<15} {'Seed 999':<15}")
        print("-" * 120)

        for category in sorted(all_categories):
            row = f"{category:<30}"
            for seed in [42, 123, 456, 789, 999]:
                if category in result.seed_results[seed].category_stats:
                    value = result.seed_results[seed].category_stats[category].mean_signed_error
                    row += f"{value:<15.4f}"
                else:
                    row += f"{'N/A':<15}"
            print(row)

    def _print_cumulative_error_summary(self, result: DistributionSequenceAnalysisResult):
        """Print summary of cumulative error trajectories."""
        print("\n" + "=" * 80)
        print("CUMULATIVE ERROR ANALYSIS")
        print("=" * 80)

        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            cum_metrics = sr.cumulative_metrics
            print(
                f"Seed {seed}: Final cumulative error = {cum_metrics.final_cumulative_error:8.4f}, "
                f"Final cumulative abs error = {cum_metrics.final_cumulative_abs_error:8.4f}"
            )

    def _save_results(self, result: DistributionSequenceAnalysisResult):
        """Save results to JSON file."""
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        results_file = results_dir / "research_17_5_b_error_distribution_sequence.json"

        with open(results_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"\n✓ Results saved to {results_file}")


# ============================================================================
# Main Entry Point
# ============================================================================


if __name__ == "__main__":
    orchestrator = ResearchPhase17_5_B(learning_rate=0.007)
    analysis_result = orchestrator.run()
    print("\n✓ Phase 17.5B analysis complete")
