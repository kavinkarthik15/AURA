"""
17.5C: Feature-Coupling / Temporal Interaction Analysis

This experiment is observational only. It does not modify the calibrator.
It measures whether specific feature combinations or temporal drift patterns
explain the seed-dependent calibration instability seen in 17.4A and 17.5B.

Goals:
  1. Feature -> error relationship
  2. Feature-pair interaction analysis
  3. Temporal feature drift analysis
  4. Compare successful vs failing seeds
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.services.simulation_engine import SimulationEngine


FEATURE_PAIRS = [
    ("python", "dsa"),
    ("python", "machine_learning"),
    ("python", "projects"),
    ("dsa", "machine_learning"),
    ("dsa", "projects"),
    ("machine_learning", "projects"),
]


@dataclass
class FeatureErrorStat:
    feature: str
    mean_signed_error: float = 0.0
    mean_abs_error: float = 0.0
    correlation_with_feature_value: float = 0.0
    feature_value_std: float = 0.0


@dataclass
class PairInteractionStat:
    pair: str
    high_high_mean_signed_error: float = 0.0
    low_low_mean_signed_error: float = 0.0
    interaction_gap: float = 0.0
    mean_pair_signed_error: float = 0.0
    correlation_with_pair_value: float = 0.0


@dataclass
class TemporalDriftStat:
    mean_feature_drift: float = 0.0
    high_drift_mean_signed_error: float = 0.0
    low_drift_mean_signed_error: float = 0.0
    drift_abs_error_correlation: float = 0.0
    mean_abs_error_high_drift: float = 0.0
    mean_abs_error_low_drift: float = 0.0


@dataclass
class FeatureTraceEvent:
    seed: int
    category: str
    step: int
    state_features: Dict[str, float]
    predicted_state: Dict[str, float]
    actual_state: Dict[str, float]
    signed_error_by_feature: Dict[str, float]
    expected_state_bias_before: Dict[str, float] = field(default_factory=dict)
    expected_state_bias_after: Dict[str, float] = field(default_factory=dict)
    bias_delta: Dict[str, float] = field(default_factory=dict)


@dataclass
class SeedFeatureCouplingResult:
    seed: int
    total_events: int
    feature_stats: Dict[str, FeatureErrorStat] = field(default_factory=dict)
    pair_interactions: Dict[str, PairInteractionStat] = field(default_factory=dict)
    temporal_metrics: TemporalDriftStat = field(default_factory=TemporalDriftStat)
    strongest_feature: str = ""
    strongest_pair: str = ""
    strongest_feature_correlation: float = 0.0
    strongest_pair_gap: float = 0.0
    high_drift_error_gap: float = 0.0


@dataclass
class FeatureCouplingAnalysisResult:
    analysis_date: str
    learning_rate: float
    total_seeds: int
    seed_results: Dict[int, SeedFeatureCouplingResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "learning_rate": self.learning_rate,
            "total_seeds": self.total_seeds,
            "seed_results": {
                str(seed): {
                    "seed": result.seed,
                    "total_events": result.total_events,
                    "strongest_feature": result.strongest_feature,
                    "strongest_feature_correlation": result.strongest_feature_correlation,
                    "strongest_pair": result.strongest_pair,
                    "strongest_pair_gap": result.strongest_pair_gap,
                    "high_drift_error_gap": result.high_drift_error_gap,
                    "feature_stats": {
                        name: asdict(stat)
                        for name, stat in result.feature_stats.items()
                    },
                    "pair_interactions": {
                        name: asdict(stat)
                        for name, stat in result.pair_interactions.items()
                    },
                    "temporal_metrics": asdict(result.temporal_metrics),
                }
                for seed, result in self.seed_results.items()
            },
        }


class FeatureCouplingTemporalAnalyzer:
    """Diagnostic analyzer for feature coupling and temporal interaction effects."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.simulator = SimulationEngine()

    def analyze_seed(self) -> SeedFeatureCouplingResult:
        """Compute all feature-coupling and temporal metrics for a single seed."""
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        training_experiences = dataset.training_experiences

        feature_value_history: Dict[str, List[float]] = {}
        feature_error_history: Dict[str, List[float]] = {}
        feature_abs_error_history: Dict[str, List[float]] = {}
        events: List[FeatureTraceEvent] = []

        bias_state: Dict[str, float] = {}
        previous_state: Dict[str, float] = {}
        drift_scores: List[float] = []
        drift_error_pairs: List[Tuple[float, float]] = []

        for step, experience in enumerate(training_experiences):
            current_state = {str(k): float(v) for k, v in experience.initial_state.items()}
            predicted = self.simulator.simulate_action(
                current_state=current_state,
                action=experience.selected_action,
            ).get("predicted_future_state", {})
            predicted = {str(k): float(v) for k, v in predicted.items()}
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            feature_names = sorted(set(current_state) | set(predicted) | set(actual))

            signed_errors = {}
            bias_before = {}
            bias_after = {}
            bias_delta = {}

            for feature in feature_names:
                actual_val = actual.get(feature, 0.0)
                predicted_val = predicted.get(feature, 0.0)
                signed_error = actual_val - predicted_val
                signed_errors[feature] = signed_error

                feature_value_history.setdefault(feature, []).append(current_state.get(feature, 0.0))
                feature_error_history.setdefault(feature, []).append(signed_error)
                feature_abs_error_history.setdefault(feature, []).append(abs(signed_error))

                prior_bias = bias_state.get(feature, 0.0)
                bias_before[feature] = prior_bias
                update = self.learning_rate * signed_error
                bias_after[feature] = prior_bias + update
                bias_delta[feature] = update
                bias_state[feature] = bias_after[feature]

            if previous_state:
                drift = []
                for feature in feature_names:
                    prev_val = previous_state.get(feature, 0.0)
                    curr_val = current_state.get(feature, 0.0)
                    drift.append(abs(curr_val - prev_val))
                drift_score = statistics.mean(drift) if drift else 0.0
                drift_scores.append(drift_score)
                abs_error_mean = statistics.mean([abs(v) for v in signed_errors.values()]) if signed_errors else 0.0
                drift_error_pairs.append((drift_score, abs_error_mean))

            previous_state = current_state

            events.append(
                FeatureTraceEvent(
                    seed=self.seed,
                    category=experience.category,
                    step=step,
                    state_features=current_state,
                    predicted_state=predicted,
                    actual_state=actual,
                    signed_error_by_feature=signed_errors,
                    expected_state_bias_before=bias_before,
                    expected_state_bias_after=bias_after,
                    bias_delta=bias_delta,
                )
            )

        # Feature stats
        feature_stats: Dict[str, FeatureErrorStat] = {}
        for feature in sorted(feature_value_history):
            values = feature_value_history[feature]
            errors = feature_error_history[feature]
            abs_errors = feature_abs_error_history[feature]
            corr = self._pearson(values, errors)
            feature_stats[feature] = FeatureErrorStat(
                feature=feature,
                mean_signed_error=statistics.mean(errors) if errors else 0.0,
                mean_abs_error=statistics.mean(abs_errors) if abs_errors else 0.0,
                correlation_with_feature_value=corr,
                feature_value_std=statistics.pstdev(values) if len(values) > 1 else 0.0,
            )

        strongest_feature = ""
        strongest_feature_correlation = 0.0
        for feature, stat in feature_stats.items():
            if abs(stat.correlation_with_feature_value) > abs(strongest_feature_correlation):
                strongest_feature = feature
                strongest_feature_correlation = stat.correlation_with_feature_value

        # Pair interactions
        pair_interactions: Dict[str, PairInteractionStat] = {}
        for pair in self._pair_candidates(feature_names=sorted(feature_value_history.keys())):
            left, right = pair
            values_left = feature_value_history.get(left, [])
            values_right = feature_value_history.get(right, [])
            if not values_left or not values_right:
                continue
            if len(values_left) != len(values_right):
                pair_len = min(len(values_left), len(values_right))
                values_left = values_left[:pair_len]
                values_right = values_right[:pair_len]

            pair_errors = []
            for idx in range(len(values_left)):
                left_err = feature_error_history.get(left, [0.0])[idx] if idx < len(feature_error_history.get(left, [0.0])) else 0.0
                right_err = feature_error_history.get(right, [0.0])[idx] if idx < len(feature_error_history.get(right, [0.0])) else 0.0
                pair_errors.append((left_err + right_err) / 2.0)

            if not pair_errors:
                continue

            left_med = statistics.median(values_left)
            right_med = statistics.median(values_right)
            high_high = [pair_errors[i] for i in range(len(values_left)) if values_left[i] >= left_med and values_right[i] >= right_med]
            low_low = [pair_errors[i] for i in range(len(values_left)) if values_left[i] <= left_med and values_right[i] <= right_med]

            high_high_mean = statistics.mean(high_high) if high_high else 0.0
            low_low_mean = statistics.mean(low_low) if low_low else 0.0
            interaction_gap = high_high_mean - low_low_mean
            pair_value_signal = [
                (values_left[i] + values_right[i]) / 2.0 for i in range(len(values_left))
            ]
            pair_corr = self._pearson(pair_value_signal, pair_errors)
            pair_interactions[f"{left}×{right}"] = PairInteractionStat(
                pair=f"{left}×{right}",
                high_high_mean_signed_error=high_high_mean,
                low_low_mean_signed_error=low_low_mean,
                interaction_gap=interaction_gap,
                mean_pair_signed_error=statistics.mean(pair_errors) if pair_errors else 0.0,
                correlation_with_pair_value=pair_corr,
            )

        strongest_pair = ""
        strongest_pair_gap = 0.0
        for pair_name, stat in pair_interactions.items():
            if abs(stat.interaction_gap) > abs(strongest_pair_gap):
                strongest_pair = pair_name
                strongest_pair_gap = stat.interaction_gap

        # Temporal drift
        if drift_error_pairs:
            drift_values = [d for d, _ in drift_error_pairs]
            abs_error_values = [e for _, e in drift_error_pairs]
            drift_corr = self._pearson(drift_values, abs_error_values)
            median_drift = statistics.median(drift_values) if drift_values else 0.0
            high_drift = [e for d, e in drift_error_pairs if d >= median_drift]
            low_drift = [e for d, e in drift_error_pairs if d < median_drift]
            high_drift_mean = statistics.mean(high_drift) if high_drift else 0.0
            low_drift_mean = statistics.mean(low_drift) if low_drift else 0.0
            mean_feature_drift = statistics.mean(drift_values) if drift_values else 0.0
            high_abs = [e for d, e in drift_error_pairs if d >= median_drift]
            low_abs = [e for d, e in drift_error_pairs if d < median_drift]
            mean_abs_high = statistics.mean(high_abs) if high_abs else 0.0
            mean_abs_low = statistics.mean(low_abs) if low_abs else 0.0
            drift_stat = TemporalDriftStat(
                mean_feature_drift=mean_feature_drift,
                high_drift_mean_signed_error=high_drift_mean,
                low_drift_mean_signed_error=low_drift_mean,
                drift_abs_error_correlation=drift_corr,
                mean_abs_error_high_drift=mean_abs_high,
                mean_abs_error_low_drift=mean_abs_low,
            )
        else:
            drift_stat = TemporalDriftStat()

        high_drift_error_gap = drift_stat.high_drift_mean_signed_error - drift_stat.low_drift_mean_signed_error

        return SeedFeatureCouplingResult(
            seed=self.seed,
            total_events=len(events),
            feature_stats=feature_stats,
            pair_interactions=pair_interactions,
            temporal_metrics=drift_stat,
            strongest_feature=strongest_feature,
            strongest_pair=strongest_pair,
            strongest_feature_correlation=strongest_feature_correlation,
            strongest_pair_gap=strongest_pair_gap,
            high_drift_error_gap=high_drift_error_gap,
        )

    @staticmethod
    def _pearson(xs: List[float], ys: List[float]) -> float:
        if len(xs) != len(ys) or len(xs) < 2:
            return 0.0
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        x_var = sum((x - x_mean) ** 2 for x in xs)
        y_var = sum((y - y_mean) ** 2 for y in ys)
        if x_var == 0 or y_var == 0:
            return 0.0
        return num / math.sqrt(x_var * y_var)

    @staticmethod
    def _pair_candidates(feature_names: Iterable[str]) -> List[Tuple[str, str]]:
        ordered = list(feature_names)
        pairs: List[Tuple[str, str]] = []
        for idx, left in enumerate(ordered):
            for right in ordered[idx + 1 :]:
                if (left, right) in FEATURE_PAIRS or (right, left) in FEATURE_PAIRS:
                    pairs.append((left, right))
        if not pairs:
            for idx, left in enumerate(ordered):
                for right in ordered[idx + 1 :]:
                    pairs.append((left, right))
        return pairs[:10]


class ResearchPhase17_5_C:
    """Orchestrates 17.5C across all 5 seeds."""

    def __init__(self, learning_rate: float = 0.007, seeds: List[int] | None = None):
        self.learning_rate = learning_rate
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> FeatureCouplingAnalysisResult:
        result = FeatureCouplingAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 100)
        print("Phase 17.5C: Feature-Coupling / Temporal Interaction Analysis")
        print("=" * 100)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = FeatureCouplingTemporalAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: FeatureCouplingAnalysisResult):
        print("\n" + "=" * 120)
        print("FEATURE-COUPLING SUMMARY")
        print("=" * 120)
        header = f"{'Metric':<28} {'Seed 42':<12} {'Seed 123':<12} {'Seed 456':<12} {'Seed 789':<12} {'Seed 999':<12}"
        print(header)
        print("-" * 120)

        strongest_feature_row = "Strongest feature"
        strongest_pair_row = "Strongest pair"
        strongest_corr_row = "Feature corr"
        pair_gap_row = "Pair gap"
        drift_gap_row = "High drift gap"

        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            strongest_feature_row += f"{sr.strongest_feature:<12}"
            strongest_pair_row += f"{sr.strongest_pair:<12}"
            strongest_corr_row += f"{sr.strongest_feature_correlation:<12.3f}"
            pair_gap_row += f"{sr.strongest_pair_gap:<12.3f}"
            drift_gap_row += f"{sr.high_drift_error_gap:<12.3f}"

        print(strongest_feature_row)
        print(strongest_pair_row)
        print(strongest_corr_row)
        print(pair_gap_row)
        print(drift_gap_row)

        print("\n" + "=" * 120)
        print("Top per-feature statistics")
        print("=" * 120)
        for seed in [42, 123, 456, 789, 999]:
            sr = result.seed_results[seed]
            print(f"\nSeed {seed}:")
            sorted_features = sorted(
                sr.feature_stats.items(),
                key=lambda item: abs(item[1].correlation_with_feature_value),
                reverse=True,
            )[:5]
            for feature, stat in sorted_features:
                print(
                    f"  {feature:>18}: corr={stat.correlation_with_feature_value:>7.3f}, "
                    f"mean_signed={stat.mean_signed_error:>7.3f}, mean_abs={stat.mean_abs_error:>7.3f}"
                )

    def _save_results(self, result: FeatureCouplingAnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_5_c_feature_coupling_temporal.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_5_C(learning_rate=0.007).run()
