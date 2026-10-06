"""
17.6A: State Transition × Calibration Interaction

Observational-only diagnostic for whether large state transitions produce
systematically worse calibration behavior than small transitions.

This does not modify production calibration logic.
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


FEATURES = ["python", "dsa", "machine_learning", "projects"]


@dataclass
class StateTransitionEvent:
    seed: int
    category: str
    step: int
    state_before: Dict[str, float]
    state_after: Dict[str, float]
    feature_delta: Dict[str, float]
    prediction: Dict[str, float]
    actual: Dict[str, float]
    signed_error: Dict[str, float]
    bias_before: Dict[str, float]
    bias_delta: Dict[str, float]
    bias_after: Dict[str, float]
    transition_magnitude: float
    number_of_features_changed: int
    largest_feature_change: str
    direction_of_state_change: str


@dataclass
class TransitionBucketSummary:
    bucket_name: str
    event_count: int
    mean_signed_error: float
    mean_abs_error: float
    mean_bias_delta: float
    mean_abs_bias_drift: float
    direction_accuracy: float
    final_prediction_error: float


@dataclass
class CategoryTransitionPattern:
    category: str
    stable_event_count: int = 0
    large_event_count: int = 0
    mean_transition_magnitude_stable: float = 0.0
    mean_transition_magnitude_large: float = 0.0
    large_negative_error_rate: float = 0.0
    large_positive_error_rate: float = 0.0
    high_bias_large_transition_count: int = 0


@dataclass
class TransitionInteractionResult:
    analysis_date: str
    learning_rate: float
    total_seeds: int
    seed_results: Dict[int, Dict[str, TransitionBucketSummary]] = field(default_factory=dict)
    category_patterns: Dict[int, Dict[str, CategoryTransitionPattern]] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "learning_rate": self.learning_rate,
            "total_seeds": self.total_seeds,
            "seed_results": {
                str(seed): {
                    bucket: asdict(summary)
                    for bucket, summary in bucket_map.items()
                }
                for seed, bucket_map in self.seed_results.items()
            },
            "category_patterns": {
                str(seed): {
                    category: asdict(pattern)
                    for category, pattern in patterns.items()
                }
                for seed, patterns in self.category_patterns.items()
            },
        }


class StateTransitionCalibrationAnalyzer:
    """Compute transition-based calibration diagnostics for a single seed."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.simulator = SimulationEngine()

    def analyze_seed(self) -> Dict[str, TransitionBucketSummary]:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        training = dataset.training_experiences

        events: List[StateTransitionEvent] = []
        category_patterns: Dict[str, CategoryTransitionPattern] = {}

        for step, experience in enumerate(training):
            state_before = {str(k): float(v) for k, v in experience.initial_state.items()}
            predicted = self.simulator.simulate_action(
                current_state=state_before,
                action=experience.selected_action,
            ).get("predicted_future_state", {})
            predicted = {str(k): float(v) for k, v in predicted.items()}
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            state_after = actual.copy()

            feature_delta = {}
            for feature in sorted(set(state_before) | set(actual)):
                before = state_before.get(feature, 0.0)
                after = actual.get(feature, 0.0)
                feature_delta[feature] = after - before

            signed_error = {}
            for feature in sorted(set(predicted) | set(actual)):
                signed_error[feature] = actual.get(feature, 0.0) - predicted.get(feature, 0.0)

            bias_before = {}
            bias_after = {}
            bias_delta = {}
            current_bias = {}
            for feature in sorted(set(feature_delta) | set(signed_error)):
                bias_before[feature] = current_bias.get(feature, 0.0)
                delta = self.learning_rate * signed_error.get(feature, 0.0)
                new_bias = bias_before[feature] + delta
                current_bias[feature] = new_bias
                bias_after[feature] = new_bias
                bias_delta[feature] = delta

            transition_magnitude = self._mean_abs_values(feature_delta)
            number_of_features_changed = sum(1 for v in feature_delta.values() if abs(v) > 1e-9)
            largest_feature_change = max(feature_delta, key=lambda k: abs(feature_delta.get(k, 0.0)), default="python")
            direction_of_state_change = self._direction_of_state_change(feature_delta)

            event = StateTransitionEvent(
                seed=self.seed,
                category=experience.category,
                step=step,
                state_before=state_before,
                state_after=state_after,
                feature_delta=feature_delta,
                prediction=predicted,
                actual=actual,
                signed_error=signed_error,
                bias_before=bias_before,
                bias_delta=bias_delta,
                bias_after=bias_after,
                transition_magnitude=transition_magnitude,
                number_of_features_changed=number_of_features_changed,
                largest_feature_change=largest_feature_change,
                direction_of_state_change=direction_of_state_change,
            )
            events.append(event)

            pattern = category_patterns.setdefault(
                experience.category,
                CategoryTransitionPattern(category=experience.category),
            )
            pattern.stable_event_count += 1
            pattern.large_event_count += 1

        if not events:
            return {
                "stable": self._empty_bucket_summary("stable"),
                "large": self._empty_bucket_summary("large"),
            }

        transition_threshold = statistics.median([e.transition_magnitude for e in events])
        buckets = {"stable": [], "large": []}
        for event in events:
            bucket = "large" if event.transition_magnitude >= transition_threshold else "stable"
            buckets[bucket].append(event)

        for category_name in sorted({e.category for e in events}):
            category_events = [e for e in events if e.category == category_name]
            category_patterns[category_name] = CategoryTransitionPattern(
                category=category_name,
                stable_event_count=sum(1 for e in category_events if e.transition_magnitude < transition_threshold),
                large_event_count=sum(1 for e in category_events if e.transition_magnitude >= transition_threshold),
                mean_transition_magnitude_stable=statistics.mean([e.transition_magnitude for e in category_events if e.transition_magnitude < transition_threshold]) if any(e.transition_magnitude < transition_threshold for e in category_events) else 0.0,
                mean_transition_magnitude_large=statistics.mean([e.transition_magnitude for e in category_events if e.transition_magnitude >= transition_threshold]) if any(e.transition_magnitude >= transition_threshold for e in category_events) else 0.0,
                large_negative_error_rate=sum(1 for e in category_events if e.transition_magnitude >= transition_threshold and any(v < 0 for v in e.signed_error.values())) / max(1, sum(1 for e in category_events if e.transition_magnitude >= transition_threshold)),
                large_positive_error_rate=sum(1 for e in category_events if e.transition_magnitude >= transition_threshold and any(v > 0 for v in e.signed_error.values())) / max(1, sum(1 for e in category_events if e.transition_magnitude >= transition_threshold)),
                high_bias_large_transition_count=sum(1 for e in category_events if e.transition_magnitude >= transition_threshold and abs(sum(e.bias_delta.values())) > 0.5),
            )

        summary: Dict[str, TransitionBucketSummary] = {}
        for bucket_name, bucket_events in buckets.items():
            if not bucket_events:
                summary[bucket_name] = self._empty_bucket_summary(bucket_name)
                continue
            signed_values = [value for event in bucket_events for value in event.signed_error.values()]
            abs_values = [abs(value) for event in bucket_events for value in event.signed_error.values()]
            bias_delta_values = [abs(value) for event in bucket_events for value in event.bias_delta.values()]
            bias_drift_values = [
                abs(event.bias_after.get(feature, 0.0) - event.bias_before.get(feature, 0.0))
                for event in bucket_events
                for feature in event.bias_after
            ]
            direction_hits = 0
            total_checks = 0
            for event in bucket_events:
                for feature, signed in event.signed_error.items():
                    total_checks += 1
                    error_sign = 1 if signed > 0 else (-1 if signed < 0 else 0)
                    bias_sign = 1 if event.bias_delta.get(feature, 0.0) > 0 else (-1 if event.bias_delta.get(feature, 0.0) < 0 else 0)
                    if error_sign == bias_sign:
                        direction_hits += 1
            direction_accuracy = direction_hits / total_checks if total_checks else 1.0
            summary[bucket_name] = TransitionBucketSummary(
                bucket_name=bucket_name,
                event_count=len(bucket_events),
                mean_signed_error=statistics.mean(signed_values) if signed_values else 0.0,
                mean_abs_error=statistics.mean(abs_values) if abs_values else 0.0,
                mean_bias_delta=statistics.mean(bias_delta_values) if bias_delta_values else 0.0,
                mean_abs_bias_drift=statistics.mean(bias_drift_values) if bias_drift_values else 0.0,
                direction_accuracy=direction_accuracy,
                final_prediction_error=statistics.mean(abs_values) if abs_values else 0.0,
            )

        return summary

    @staticmethod
    def _mean_abs_values(mapping: Dict[str, float]) -> float:
        vals = [abs(v) for v in mapping.values()]
        return statistics.mean(vals) if vals else 0.0

    @staticmethod
    def _direction_of_state_change(feature_delta: Dict[str, float]) -> str:
        total = sum(feature_delta.values())
        if abs(total) < 1e-9:
            return "neutral"
        return "positive" if total > 0 else "negative"

    @staticmethod
    def _empty_bucket_summary(bucket_name: str) -> TransitionBucketSummary:
        return TransitionBucketSummary(
            bucket_name=bucket_name,
            event_count=0,
            mean_signed_error=0.0,
            mean_abs_error=0.0,
            mean_bias_delta=0.0,
            mean_abs_bias_drift=0.0,
            direction_accuracy=1.0,
            final_prediction_error=0.0,
        )


class ResearchPhase17_6_A:
    """Run 17.6A across the known seed set for comparison."""

    def __init__(self, learning_rate: float = 0.007, seeds: List[int] | None = None):
        self.learning_rate = learning_rate
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> TransitionInteractionResult:
        result = TransitionInteractionResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 110)
        print("Phase 17.6A: State-Transition × Calibration Interaction")
        print("=" * 110)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = StateTransitionCalibrationAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_summary = analyzer.analyze_seed()
            result.seed_results[seed] = seed_summary
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: TransitionInteractionResult):
        print("\n" + "=" * 100)
        print("TRANSITION-BUCKET SUMMARY")
        print("=" * 100)
        print(f"{'Seed':<8} {'Bucket':<16} {'Events':>7} {'Mean signed err':>16} {'Mean abs err':>16} {'Bias delta':>12} {'Dir acc':>9} {'Final pred err':>15}")
        print("-" * 100)
        for seed in self.seeds:
            for bucket in ["stable", "large"]:
                summary = result.seed_results[seed].get(bucket, self._empty_bucket_summary(bucket))
                print(
                    f"{seed:<8} {bucket:<16} {summary.event_count:>7} "
                    f"{summary.mean_signed_error:>16.3f} {summary.mean_abs_error:>16.3f} "
                    f"{summary.mean_bias_delta:>12.3f} {summary.direction_accuracy:>9.3f} {summary.final_prediction_error:>15.3f}"
                )

    def _save_results(self, result: TransitionInteractionResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_6_a_state_transition_calibration.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")

    @staticmethod
    def _empty_bucket_summary(bucket_name: str) -> TransitionBucketSummary:
        return TransitionBucketSummary(
            bucket_name=bucket_name,
            event_count=0,
            mean_signed_error=0.0,
            mean_abs_error=0.0,
            mean_bias_delta=0.0,
            mean_abs_bias_drift=0.0,
            direction_accuracy=1.0,
            final_prediction_error=0.0,
        )


if __name__ == "__main__":
    ResearchPhase17_6_A(learning_rate=0.007).run()
