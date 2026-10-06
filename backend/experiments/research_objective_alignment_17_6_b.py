"""
17.6B: Calibration Objective & State Representation Analysis

Observational-only diagnostic that compares the actual calibration update direction
against the locally optimal direction of the objective itself.

This does not change production calibration logic.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine


FEATURES = ["python", "dsa", "machine_learning", "projects"]


@dataclass
class ObjectiveAlignmentEvent:
    seed: int
    category: str
    step: int
    feature: str
    bias_before: float
    bias_delta: float
    bias_after: float
    signed_error: float
    prediction_before: float
    prediction_after: float
    mae_before: float
    mae_after: float
    objective_best_direction: int
    actual_update_direction: int
    objective_aligned: bool


@dataclass
class SeedObjectiveAlignmentResult:
    seed: int
    total_events: int
    objective_direction_accuracy: float
    mean_mae_before: float
    mean_mae_after: float
    mean_improvement: float
    mean_signed_error: float
    mean_bias_delta: float
    alignment_by_category: Dict[str, float] = field(default_factory=dict)


@dataclass
class ObjectiveAlignmentResult:
    analysis_date: str
    learning_rate: float
    total_seeds: int
    seed_results: Dict[int, SeedObjectiveAlignmentResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "learning_rate": self.learning_rate,
            "total_seeds": self.total_seeds,
            "seed_results": {
                str(seed): {
                    "seed": result.seed,
                    "total_events": result.total_events,
                    "objective_direction_accuracy": result.objective_direction_accuracy,
                    "mean_mae_before": result.mean_mae_before,
                    "mean_mae_after": result.mean_mae_after,
                    "mean_improvement": result.mean_improvement,
                    "mean_signed_error": result.mean_signed_error,
                    "mean_bias_delta": result.mean_bias_delta,
                    "alignment_by_category": result.alignment_by_category,
                }
                for seed, result in self.seed_results.items()
            },
        }


class ObjectiveAlignmentAnalyzer:
    """Compare actual calibration updates to locally optimal objective direction."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.simulator = SimulationEngine()

    def analyze_seed(self) -> SeedObjectiveAlignmentResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        training = dataset.training_experiences

        current_bias: Dict[str, float] = {}
        events: List[ObjectiveAlignmentEvent] = []
        category_scores: Dict[str, List[bool]] = {}

        for step, experience in enumerate(training):
            state_before = {str(k): float(v) for k, v in experience.initial_state.items()}
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            all_features = sorted(set(state_before) | set(actual))

            params_before = CalibrationParameters(expected_state_bias=current_bias.copy())
            self.simulator.calibration_parameters = params_before
            predicted_before = self.simulator.simulate_action(
                current_state=state_before,
                action=experience.selected_action,
            ).get("predicted_future_state", {})
            predicted_before = {str(k): float(v) for k, v in predicted_before.items()}
            mae_before = self._mae(actual, predicted_before)

            for feature in all_features:
                signed_error = actual.get(feature, 0.0) - predicted_before.get(feature, 0.0)
                bias_before = current_bias.get(feature, 0.0)
                bias_delta = self.learning_rate * signed_error
                bias_after = bias_before + bias_delta
                current_bias[feature] = bias_after
                params_after = CalibrationParameters(expected_state_bias=current_bias.copy())
                self.simulator.calibration_parameters = params_after
                predicted_after = self.simulator.simulate_action(
                    current_state=state_before,
                    action=experience.selected_action,
                ).get("predicted_future_state", {})
                predicted_after = {str(k): float(v) for k, v in predicted_after.items()}
                mae_after = self._mae(actual, predicted_after)

                objective_best_direction = self._local_objective_direction(
                    current_state=state_before,
                    action=experience.selected_action,
                    actual=actual,
                    feature=feature,
                    current_bias=current_bias.copy(),
                    base_bias=bias_before,
                    epsilon=max(0.05, abs(bias_before) * 0.1 + 0.05),
                )
                actual_update_direction = self._direction_from_value(bias_delta)
                objective_aligned = objective_best_direction == actual_update_direction

                events.append(
                    ObjectiveAlignmentEvent(
                        seed=self.seed,
                        category=experience.category,
                        step=step,
                        feature=feature,
                        bias_before=bias_before,
                        bias_delta=bias_delta,
                        bias_after=bias_after,
                        signed_error=signed_error,
                        prediction_before=predicted_before.get(feature, 0.0),
                        prediction_after=predicted_after.get(feature, 0.0),
                        mae_before=mae_before,
                        mae_after=mae_after,
                        objective_best_direction=objective_best_direction,
                        actual_update_direction=actual_update_direction,
                        objective_aligned=objective_aligned,
                    )
                )
                category_scores.setdefault(experience.category, []).append(objective_aligned)

            # Reset bias state for next experience based on the actual update path.
            # This keeps the experiment aligned with the real calibration trajectory.
            current_bias = {k: v for k, v in current_bias.items()}

        if not events:
            return SeedObjectiveAlignmentResult(
                seed=self.seed,
                total_events=0,
                objective_direction_accuracy=0.0,
                mean_mae_before=0.0,
                mean_mae_after=0.0,
                mean_improvement=0.0,
                mean_signed_error=0.0,
                mean_bias_delta=0.0,
                alignment_by_category={},
            )

        objective_direction_accuracy = (
            sum(1 for event in events if event.objective_aligned) / len(events)
        )
        mean_mae_before = statistics.mean(event.mae_before for event in events)
        mean_mae_after = statistics.mean(event.mae_after for event in events)
        mean_improvement = mean_mae_before - mean_mae_after
        mean_signed_error = statistics.mean(event.signed_error for event in events)
        mean_bias_delta = statistics.mean(abs(event.bias_delta) for event in events)

        alignment_by_category = {
            category: (sum(1 for v in values if v) / len(values)) if values else 0.0
            for category, values in category_scores.items()
        }

        return SeedObjectiveAlignmentResult(
            seed=self.seed,
            total_events=len(events),
            objective_direction_accuracy=objective_direction_accuracy,
            mean_mae_before=mean_mae_before,
            mean_mae_after=mean_mae_after,
            mean_improvement=mean_improvement,
            mean_signed_error=mean_signed_error,
            mean_bias_delta=mean_bias_delta,
            alignment_by_category=alignment_by_category,
        )

    @staticmethod
    def _mae(actual: Dict[str, float], predicted: Dict[str, float]) -> float:
        all_features = sorted(set(actual) | set(predicted))
        if not all_features:
            return 0.0
        errors = [abs(actual.get(feature, 0.0) - predicted.get(feature, 0.0)) for feature in all_features]
        return statistics.mean(errors) if errors else 0.0

    def _local_objective_direction(
        self,
        current_state: Dict[str, float],
        action: str,
        actual: Dict[str, float],
        feature: str,
        current_bias: Dict[str, float],
        base_bias: float,
        epsilon: float,
    ) -> int:
        base_error = self._state_mae_for_bias(current_state, action, actual, feature, current_bias, base_bias)
        minus_bias = {k: v for k, v in current_bias.items()}
        plus_bias = {k: v for k, v in current_bias.items()}
        minus_bias[feature] = base_bias - epsilon
        plus_bias[feature] = base_bias + epsilon

        minus_error = self._state_mae_for_bias(current_state, action, actual, feature, minus_bias, base_bias - epsilon)
        plus_error = self._state_mae_for_bias(current_state, action, actual, feature, plus_bias, base_bias + epsilon)

        if minus_error < base_error and minus_error <= plus_error:
            return -1
        if plus_error < base_error and plus_error <= minus_error:
            return 1
        return 0

    def _state_mae_for_bias(
        self,
        current_state: Dict[str, float],
        action: str,
        actual: Dict[str, float],
        feature: str,
        bias_state: Dict[str, float],
        candidate_bias: float,
    ) -> float:
        params = CalibrationParameters(expected_state_bias=bias_state.copy())
        self.simulator.calibration_parameters = params
        predicted = self.simulator.simulate_action(
            current_state=current_state,
            action=action,
        ).get("predicted_future_state", {})
        predicted = {str(k): float(v) for k, v in predicted.items()}
        return self._mae(actual, predicted)

    @staticmethod
    def _direction_from_value(value: float) -> int:
        if abs(value) < 1e-9:
            return 0
        return 1 if value > 0 else -1


class ResearchPhase17_6_B:
    """Run the 17.6B objective-alignment experiment across the benchmark seeds."""

    def __init__(self, learning_rate: float = 0.007, seeds: List[int] | None = None):
        self.learning_rate = learning_rate
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> ObjectiveAlignmentResult:
        result = ObjectiveAlignmentResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 110)
        print("Phase 17.6B: Calibration Objective & State Representation Analysis")
        print("=" * 110)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = ObjectiveAlignmentAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: ObjectiveAlignmentResult):
        print("\n" + "=" * 110)
        print("OBJECTIVE-ALIGNMENT SUMMARY")
        print("=" * 110)
        header = (
            f"{'Seed':<8} {'Events':>7} {'Obj align':>10} {'MAE before':>12} "
            f"{'MAE after':>12} {'ΔMAE':>10} {'Mean signed err':>16} {'Mean bias Δ':>12}"
        )
        print(header)
        print("-" * 110)
        for seed in self.seeds:
            sr = result.seed_results[seed]
            print(
                f"{seed:<8} {sr.total_events:>7} {sr.objective_direction_accuracy:>10.3f} "
                f"{sr.mean_mae_before:>12.3f} {sr.mean_mae_after:>12.3f} {sr.mean_improvement:>10.3f} "
                f"{sr.mean_signed_error:>16.3f} {sr.mean_bias_delta:>12.3f}"
            )

        print("\nCategory alignment:")
        for seed in self.seeds:
            print(f"  Seed {seed}: {result.seed_results[seed].alignment_by_category}")

    def _save_results(self, result: ObjectiveAlignmentResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_6_b_objective_alignment.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_6_B(learning_rate=0.007).run()
