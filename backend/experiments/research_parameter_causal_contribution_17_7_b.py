"""
17.7B: Parameter Causal Contribution

Controlled intervention study that answers:

    Does changing a parameter causally affect the benchmark objective,
    and does it add anything beyond expected_state_bias?

This is observational only. It never changes the production calibrator.
It only sweeps parameter values and measures the induced change in predictions
and MAE against the benchmark.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine

FEATURES = ["python", "dsa", "machine_learning", "projects"]
PARAMETER_VALUES = {
    "expected_state_bias": [-10.0, -5.0, 0.0, 5.0, 10.0],
    "transition_probability_bias": [-1.0, -0.5, 0.0, 0.5, 1.0],
    "risk_bias": [-1.0, -0.5, 0.0, 0.5, 1.0],
    "uncertainty": [0.0, 0.25, 0.5, 0.75, 1.0],
    "confidence": [0.0, 0.25, 0.5, 0.75, 1.0],
}
PAIRWISE_INTERVENTIONS = [
    ("expected_state_bias", "transition_probability_bias"),
    ("expected_state_bias", "risk_bias"),
    ("expected_state_bias", "uncertainty"),
    ("expected_state_bias", "confidence"),
]


@dataclass
class InterventionResult:
    intervention_name: str
    parameter_names: List[str]
    baseline_prediction_mean: float
    modified_prediction_mean: float
    mean_prediction_delta: float
    max_prediction_delta: float
    baseline_mae: float
    modified_mae: float
    mae_delta: float
    improvement: float
    causally_effective: bool
    effective_range: float


@dataclass
class SeedCausalResult:
    seed: int
    total_events: int
    single_parameter_results: List[InterventionResult]
    pairwise_results: List[InterventionResult]
    causally_inert_parameters: List[str]
    causally_active_parameters: List[str]
    total_effective_interventions: int

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events": self.total_events,
            "single_parameter_results": [asdict(entry) for entry in self.single_parameter_results],
            "pairwise_results": [asdict(entry) for entry in self.pairwise_results],
            "causally_inert_parameters": self.causally_inert_parameters,
            "causally_active_parameters": self.causally_active_parameters,
            "total_effective_interventions": self.total_effective_interventions,
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    learning_rate: float
    seed_results: Dict[int, SeedCausalResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "learning_rate": self.learning_rate,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class ParameterCausalContributionAnalyzer:
    """Measure whether parameter changes cause a measurable effect on the benchmark objective."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.evaluator = PredictionErrorEvaluator()

    def analyze_seed(self) -> SeedCausalResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)

        single_results: List[InterventionResult] = []
        for parameter_name, values in PARAMETER_VALUES.items():
            baseline_params = self._base_params()
            baseline_prod = self._mean_dataset_mae(dataset, baseline_params)
            value_results: List[Tuple[float, float, float, float]] = []
            for value in values:
                params = self._parameter_override(parameter_name, value)
                modified_prod = self._mean_dataset_mae(dataset, params)
                prediction_delta = self._prediction_delta_mean(dataset, baseline_params, params)
                value_results.append((value, prediction_delta, modified_prod, baseline_prod))

            mean_prediction_delta = mean([v[1] for v in value_results]) if value_results else 0.0
            max_prediction_delta = max([v[1] for v in value_results]) if value_results else 0.0
            best_candidate = min(
                value_results,
                key=lambda item: item[2],
            ) if value_results else (0.0, 0.0, baseline_prod, baseline_prod)
            modified_mae = best_candidate[2]
            mae_delta = baseline_prod - modified_mae
            improvement = max(0.0, mae_delta)
            causally_effective = abs(mean_prediction_delta) > 1e-9 or abs(mae_delta) > 1e-9
            effective_range = max_prediction_delta
            best_params = self._parameter_override(parameter_name, best_candidate[0])

            single_results.append(
                InterventionResult(
                    intervention_name=parameter_name,
                    parameter_names=[parameter_name],
                    baseline_prediction_mean=self._mean_prediction(dataset, baseline_params),
                    modified_prediction_mean=self._mean_prediction(dataset, best_params),
                    mean_prediction_delta=mean_prediction_delta,
                    max_prediction_delta=max_prediction_delta,
                    baseline_mae=baseline_prod,
                    modified_mae=modified_mae,
                    mae_delta=mae_delta,
                    improvement=improvement,
                    causally_effective=causally_effective,
                    effective_range=effective_range,
                )
            )

        pairwise_results: List[InterventionResult] = []
        bias_only_params = self._parameter_override("expected_state_bias", 5.0)
        bias_only_mae = self._mean_dataset_mae(dataset, bias_only_params)
        for first_name, second_name in PAIRWISE_INTERVENTIONS:
            params = self._pairwise_intervention(first_name, second_name, bias_value=5.0)
            modified_mae = self._mean_dataset_mae(dataset, params)
            prediction_delta = self._prediction_delta_mean(dataset, bias_only_params, params)
            mae_delta = bias_only_mae - modified_mae
            improvement = max(0.0, mae_delta)
            causally_effective = abs(prediction_delta) > 1e-9 or abs(mae_delta) > 1e-9
            pairwise_results.append(
                InterventionResult(
                    intervention_name=f"{first_name}+{second_name}",
                    parameter_names=[first_name, second_name],
                    baseline_prediction_mean=self._mean_prediction(dataset, bias_only_params),
                    modified_prediction_mean=self._mean_prediction(dataset, params),
                    mean_prediction_delta=prediction_delta,
                    max_prediction_delta=max(abs(self._event_prediction_delta(base_params=bias_only_params, test_params=params, experience=experience)) for experience in dataset.training_experiences),
                    baseline_mae=bias_only_mae,
                    modified_mae=modified_mae,
                    mae_delta=mae_delta,
                    improvement=improvement,
                    causally_effective=causally_effective,
                    effective_range=abs(prediction_delta),
                )
            )

        inert = [
            result.intervention_name for result in single_results
            if not result.causally_effective
        ]
        active = [
            result.intervention_name for result in single_results
            if result.causally_effective
        ]

        return SeedCausalResult(
            seed=self.seed,
            total_events=len(dataset.training_experiences),
            single_parameter_results=single_results,
            pairwise_results=pairwise_results,
            causally_inert_parameters=inert,
            causally_active_parameters=active,
            total_effective_interventions=sum(1 for result in single_results if result.causally_effective),
        )

    def _base_params(self) -> CalibrationParameters:
        return CalibrationParameters(
            expected_state_bias={feature: 0.0 for feature in FEATURES},
            transition_probability_bias=0.0,
            risk_bias=0.0,
            uncertainty=0.5,
            confidence=0.5,
        )

    def _parameter_override(self, parameter_name: str, value: float) -> CalibrationParameters:
        params = self._base_params()
        if parameter_name == "expected_state_bias":
            params.expected_state_bias = {feature: float(value) for feature in FEATURES}
        elif parameter_name == "transition_probability_bias":
            params.transition_probability_bias = float(value)
        elif parameter_name == "risk_bias":
            params.risk_bias = float(value)
        elif parameter_name == "uncertainty":
            params.uncertainty = float(value)
        elif parameter_name == "confidence":
            params.confidence = float(value)
        return params

    def _pairwise_intervention(self, first_name: str, second_name: str, bias_value: float = 5.0) -> CalibrationParameters:
        params = self._base_params()
        params.expected_state_bias = {feature: float(bias_value) for feature in FEATURES}

        second_value_map = {
            "transition_probability_bias": 1.0,
            "risk_bias": 1.0,
            "uncertainty": 1.0,
            "confidence": 1.0,
        }

        if first_name != "expected_state_bias":
            setattr(params, first_name, float(second_value_map.get(first_name, 1.0)))
        if second_name != "expected_state_bias":
            setattr(params, second_name, float(second_value_map.get(second_name, 1.0)))
        return params

    def _event_prediction_delta(self, base_params: CalibrationParameters, test_params: CalibrationParameters, experience) -> float:
        state = {str(k): float(v) for k, v in experience.initial_state.items()}
        actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
        baseline_pred = self._simulate_prediction(state, experience.selected_action, base_params)
        modified_pred = self._simulate_prediction(state, experience.selected_action, test_params)
        keys = sorted(set(actual) | set(baseline_pred) | set(modified_pred))
        if not keys:
            return 0.0
        return mean(
            [abs(modified_pred.get(key, 0.0) - baseline_pred.get(key, 0.0)) for key in keys]
        )

    def _prediction_delta_mean(self, dataset, base_params: CalibrationParameters, test_params: CalibrationParameters) -> float:
        values = [
            self._event_prediction_delta(base_params, test_params, experience)
            for experience in dataset.training_experiences
        ]
        return mean(values) if values else 0.0

    def _mean_prediction(self, dataset, params: CalibrationParameters) -> float:
        values: List[float] = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            pred = self._simulate_prediction(state, experience.selected_action, params)
            if pred:
                values.append(mean(pred.values()))
        return mean(values) if values else 0.0

    def _mean_dataset_mae(self, dataset, params: CalibrationParameters) -> float:
        maes: List[float] = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            pred = self._simulate_prediction(state, experience.selected_action, params)
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            maes.append(self._mae(actual, pred))
        return mean(maes) if maes else 0.0

    @staticmethod
    def _mae(actual: Dict[str, float], predicted: Dict[str, float]) -> float:
        keys = sorted(set(actual) | set(predicted))
        if not keys:
            return 0.0
        return mean([abs(actual.get(key, 0.0) - predicted.get(key, 0.0)) for key in keys])

    @staticmethod
    def _simulate_prediction(state: Dict[str, float], action: str, params: CalibrationParameters):
        engine = SimulationEngine(calibration_parameters=params)
        result = engine.simulate_action(state, action)
        return {str(k): float(v) for k, v in result.get("predicted_future_state", {}).items()}


class ResearchPhase17_7_B:
    """Run the 17.7B causal contribution analysis across all seeds."""

    def __init__(self, learning_rate: float = 0.007, seeds: List[int] | None = None):
        self.learning_rate = learning_rate
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> AnalysisResult:
        result = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            learning_rate=self.learning_rate,
            seed_results={},
        )

        print("\n" + "=" * 120)
        print("Phase 17.7B: Parameter Causal Contribution")
        print("=" * 120)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = ParameterCausalContributionAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: AnalysisResult):
        print("\n" + "=" * 120)
        print("CAUSAL CONTRIBUTION SUMMARY")
        print("=" * 120)
        for seed in self.seeds:
            sr = result.seed_results[seed]
            print(f"\nSeed {seed}: inert = {sr.causally_inert_parameters}, active = {sr.causally_active_parameters}")
            for item in sr.single_parameter_results:
                print(
                    f"  - {item.intervention_name:<28} "
                    f"mean_delta={item.mean_prediction_delta:>8.4f}  "
                    f"mae_delta={item.mae_delta:>8.4f}  "
                    f"effective={str(item.causally_effective):<5}"
                )

            for item in sr.pairwise_results:
                print(
                    f"  - {item.intervention_name:<28} "
                    f"mean_delta={item.mean_prediction_delta:>8.4f}  "
                    f"mae_delta={item.mae_delta:>8.4f}  "
                    f"effective={str(item.causally_effective):<5}"
                )

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_7_b_parameter_causal_contribution.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_7_B().run()
