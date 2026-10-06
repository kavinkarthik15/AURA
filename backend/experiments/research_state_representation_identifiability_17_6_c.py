"""
17.6C: State Representation & Parameter Identifiability

Observational-only diagnostic for whether the current represented state,
combined with a scalar expected_state_bias parameter, is sufficient to explain
future-state prediction error.

This does not modify production calibration logic.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine


FEATURES = ["python", "dsa", "machine_learning", "projects"]


@dataclass
class StateCollisionGroup:
    state_key: str
    group_size: int
    mean_future_mae: float
    max_future_mae: float
    future_variance: float
    distinct_actual_outcomes: int


@dataclass
class ParameterIdentifiabilitySummary:
    bias_sensitivity_mean: float
    bias_sensitivity_p95: float
    flatness_ratio: float
    low_sensitivity_events: int
    weak_identifiability_rate: float


@dataclass
class SeedRepresentationResult:
    seed: int
    total_events: int
    state_collision_rate: float
    mean_future_variance: float
    max_state_group_size: int
    bias_sensitivity_mean: float
    bias_sensitivity_p95: float
    identifiability_flatness: float
    residual_mae: float
    history_dependence_score: float
    collision_groups: List[StateCollisionGroup] = field(default_factory=list)


@dataclass
class RepresentationAnalysisResult:
    analysis_date: str
    learning_rate: float
    total_seeds: int
    seed_results: Dict[int, SeedRepresentationResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "learning_rate": self.learning_rate,
            "total_seeds": self.total_seeds,
            "seed_results": {
                str(seed): {
                    "seed": result.seed,
                    "total_events": result.total_events,
                    "state_collision_rate": result.state_collision_rate,
                    "mean_future_variance": result.mean_future_variance,
                    "max_state_group_size": result.max_state_group_size,
                    "bias_sensitivity_mean": result.bias_sensitivity_mean,
                    "bias_sensitivity_p95": result.bias_sensitivity_p95,
                    "identifiability_flatness": result.identifiability_flatness,
                    "residual_mae": result.residual_mae,
                    "history_dependence_score": result.history_dependence_score,
                    "collision_groups": [asdict(group) for group in result.collision_groups],
                }
                for seed, result in self.seed_results.items()
            },
        }


class StateRepresentationIdentifiabilityAnalyzer:
    """Measure whether the current state representation suffices for calibration."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.simulator = SimulationEngine()

    def analyze_seed(self) -> SeedRepresentationResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        training = dataset.training_experiences

        state_to_events: Dict[Tuple[Tuple[str, float], ...], List[dict]] = defaultdict(list)
        previous_category_by_state: Dict[Tuple[Tuple[str, float], ...], List[str]] = defaultdict(list)
        previous_state_by_event: Dict[int, Tuple[Tuple[str, float], ...]] = {}
        event_count = 0
        last_category = None

        for experience in training:
            state_key = self._state_key(experience.initial_state)
            state_to_events[state_key].append({
                "experience": experience,
                "predicted": None,
                "actual": experience.actual_future_state,
                "category": experience.category,
                "previous_category": last_category,
            })
            if last_category is not None:
                previous_category_by_state[state_key].append(last_category)
            previous_state_by_event[event_count] = state_key
            event_count += 1
            last_category = experience.category

        collision_groups: List[StateCollisionGroup] = []
        group_sizes: List[int] = []
        future_variances: List[float] = []
        for state_key, events in state_to_events.items():
            if len(events) < 2:
                continue
            group_sizes.append(len(events))
            future_maes = []
            actual_outcomes = []
            for event in events:
                experience = event["experience"]
                actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
                future_maes.append(self._mae(actual, actual))
                actual_outcomes.append(tuple(sorted(actual.items())))
            future_maes = [self._mae(actual, actual) for actual in [dict(ev["experience"].actual_future_state) for ev in events]]
            distinct_actual_outcomes = len(set(tuple(sorted(dict(ev["experience"].actual_future_state).items())) for ev in events))
            future_variance = statistics.pstdev(future_maes) if len(future_maes) > 1 else 0.0
            future_variances.append(future_variance)
            collision_groups.append(
                StateCollisionGroup(
                    state_key=str(state_key),
                    group_size=len(events),
                    mean_future_mae=statistics.mean(future_maes) if future_maes else 0.0,
                    max_future_mae=max(future_maes) if future_maes else 0.0,
                    future_variance=future_variance,
                    distinct_actual_outcomes=distinct_actual_outcomes,
                )
            )

        residual_mae_values: List[float] = []
        sensitivity_values: List[float] = []
        identifiability_values: List[float] = []
        history_deviation_values: List[float] = []

        for experience in training:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            base_prediction = self.simulator.simulate_action(
                current_state=state,
                action=experience.selected_action,
            ).get("predicted_future_state", {})
            base_prediction = {str(k): float(v) for k, v in base_prediction.items()}
            residual_mae_values.append(self._mae(actual, base_prediction))

            sensitivity_value = self._predictive_sensitivity(state, experience.selected_action, actual)
            sensitivity_values.append(sensitivity_value)

            identifiability = self._identifiability_flatness(state, experience.selected_action, actual)
            identifiability_values.append(identifiability)

            same_state_events = [ev for ev in state_to_events.get(self._state_key(state), []) if ev["experience"].experience_id != experience.experience_id]
            if same_state_events:
                same_state_residuals = [
                    self._mae(
                        {str(k): float(v) for k, v in ev["experience"].actual_future_state.items()},
                        {str(k): float(v) for k, v in self.simulator.simulate_action(
                            current_state={str(k): float(v) for k, v in ev["experience"].initial_state.items()},
                            action=ev["experience"].selected_action,
                        ).get("predicted_future_state", {}).items()}
                    )
                    for ev in same_state_events
                ]
                if same_state_residuals:
                    residual_mean = statistics.mean(same_state_residuals)
                    if residual_mean > 0:
                        history_deviation_values.append(residual_mean)

        state_collision_rate = (
            sum(len(events) for events in state_to_events.values() if len(events) > 1) / max(1, len(training))
        )
        max_state_group_size = max(group_sizes) if group_sizes else 0
        mean_future_variance = statistics.mean(future_variances) if future_variances else 0.0
        bias_sensitivity_mean = statistics.mean(sensitivity_values) if sensitivity_values else 0.0
        bias_sensitivity_p95 = self._percentile(sensitivity_values, 95.0) if sensitivity_values else 0.0
        identifiability_flatness = statistics.mean(identifiability_values) if identifiability_values else 0.0
        residual_mae = statistics.mean(residual_mae_values) if residual_mae_values else 0.0
        history_dependence_score = statistics.mean(history_deviation_values) if history_deviation_values else 0.0

        return SeedRepresentationResult(
            seed=self.seed,
            total_events=len(training),
            state_collision_rate=state_collision_rate,
            mean_future_variance=mean_future_variance,
            max_state_group_size=max_state_group_size,
            bias_sensitivity_mean=bias_sensitivity_mean,
            bias_sensitivity_p95=bias_sensitivity_p95,
            identifiability_flatness=identifiability_flatness,
            residual_mae=residual_mae,
            history_dependence_score=history_dependence_score,
            collision_groups=collision_groups,
        )

    @staticmethod
    def _state_key(state: Dict[str, float]) -> Tuple[Tuple[str, float], ...]:
        return tuple(sorted((str(k), float(v)) for k, v in state.items()))

    @staticmethod
    def _mae(actual: Dict[str, float], predicted: Dict[str, float]) -> float:
        keys = sorted(set(actual) | set(predicted))
        if not keys:
            return 0.0
        errors = [abs(actual.get(k, 0.0) - predicted.get(k, 0.0)) for k in keys]
        return statistics.mean(errors) if errors else 0.0

    def _predictive_sensitivity(self, state: Dict[str, float], action: str, actual: Dict[str, float]) -> float:
        base_params = CalibrationParameters(expected_state_bias={})
        base_prediction = self.simulator.simulate_action(current_state=state, action=action).get("predicted_future_state", {})
        base_prediction = {str(k): float(v) for k, v in base_prediction.items()}
        base_mae = self._mae(actual, base_prediction)

        deltas = [0.25, 1.0, 2.0]
        values = []
        for delta in deltas:
            params_plus = CalibrationParameters(expected_state_bias={target: delta for target in FEATURES})
            self.simulator.calibration_parameters = params_plus
            pred_plus = self.simulator.simulate_action(current_state=state, action=action).get("predicted_future_state", {})
            pred_plus = {str(k): float(v) for k, v in pred_plus.items()}
            values.append(abs(self._mae(actual, pred_plus) - base_mae))
        return max(values) if values else 0.0

    def _identifiability_flatness(self, state: Dict[str, float], action: str, actual: Dict[str, float]) -> float:
        bias_values = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
        maes = []
        for bias in bias_values:
            params = CalibrationParameters(expected_state_bias={feature: bias for feature in FEATURES})
            self.simulator.calibration_parameters = params
            pred = self.simulator.simulate_action(current_state=state, action=action).get("predicted_future_state", {})
            pred = {str(k): float(v) for k, v in pred.items()}
            maes.append(self._mae(actual, pred))
        if not maes:
            return 0.0
        best = min(maes)
        near_best = sum(1 for value in maes if abs(value - best) <= 0.05)
        return near_best / len(maes)

    @staticmethod
    def _percentile(values: Iterable[float], percentile: float) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        if len(ordered) == 1:
            return ordered[0]
        rank = max(0, min(len(ordered) - 1, int((percentile / 100.0) * (len(ordered) - 1))))
        return ordered[rank]


class ResearchPhase17_6_C:
    """Run the 17.6C representation-identifiability analysis across all seeds."""

    def __init__(self, learning_rate: float = 0.007, seeds: List[int] | None = None):
        self.learning_rate = learning_rate
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> RepresentationAnalysisResult:
        result = RepresentationAnalysisResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 110)
        print("Phase 17.6C: State Representation & Parameter Identifiability")
        print("=" * 110)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = StateRepresentationIdentifiabilityAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: RepresentationAnalysisResult):
        print("\n" + "=" * 110)
        print("STATE-REPRESENTATION SUMMARY")
        print("=" * 110)
        header = (
            f"{'Seed':<8} {'Collision':>10} {'Future var':>12} {'Bias sens':>12} {'Ident flat':>11} "
            f"{'Residual MAE':>13} {'Hist dep':>10}"
        )
        print(header)
        print("-" * 110)
        for seed in self.seeds:
            sr = result.seed_results[seed]
            print(
                f"{seed:<8} {sr.state_collision_rate:>10.3f} {sr.mean_future_variance:>12.3f} "
                f"{sr.bias_sensitivity_mean:>12.3f} {sr.identifiability_flatness:>11.3f} "
                f"{sr.residual_mae:>13.3f} {sr.history_dependence_score:>10.3f}"
            )

    def _save_results(self, result: RepresentationAnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_6_c_state_representation_identifiability.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_6_C(learning_rate=0.007).run()
