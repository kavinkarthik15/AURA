"""
17.7A: Parameter Expressiveness & Sensitivity Mapping

Observational-only experiment designed to answer:

    Can expected_state_bias mathematically express the required correction
    for the benchmark, and how sensitive the system is to each calibration parameter?

This experiment does not modify production calibration logic. It merely sweeps
relevant parameter values and measures the actual mapping from parameter value
into state predictions and MAE.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine

FEATURES = ["python", "dsa", "machine_learning", "projects"]
PARAMETER_SPECS = {
    "expected_state_bias": {"values": list(range(-10, 11, 2)), "description": "state-bias sweep"},
    "transition_probability_bias": {"values": [round(x * 0.1, 2) for x in range(-10, 11, 2)], "description": "transition bias sweep"},
    "risk_bias": {"values": [round(x * 0.1, 2) for x in range(-10, 11, 2)], "description": "risk bias sweep"},
    "uncertainty": {"values": [round(x / 10.0, 2) for x in range(0, 11, 1)], "description": "uncertainty sweep"},
    "confidence": {"values": [round(x / 10.0, 2) for x in range(0, 11, 1)], "description": "confidence sweep"},
}


@dataclass
class SweepPoint:
    bias_value: float
    mean_prediction: float
    mean_actual: float
    mean_signed_error: float
    mean_abs_error: float
    max_abs_error: float


@dataclass
class SweepSummary:
    state_id: str
    category: str
    required_correction: float
    achievable_correction: float
    expressiveness_ratio: float
    monotonic_direction: float
    best_bias: float
    best_mae: float
    response_curve: List[SweepPoint] = field(default_factory=list)


@dataclass
class ParameterSensitivityEntry:
    parameter: str
    sweep_values: List[float]
    mean_prediction_delta: float
    mean_mae_delta: float
    mean_effect_size: float
    identifiable: bool
    description: str


@dataclass
class SeedExpressivenessResult:
    seed: int
    total_events: int
    expected_state_bias_mean_ratio: float
    expected_state_bias_median_ratio: float
    expected_state_bias_monotonic_rate: float
    overall_required_correction: float
    overall_achievable_correction: float
    sensitivity_matrix: List[ParameterSensitivityEntry]
    sweep_examples: List[SweepSummary]

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events": self.total_events,
            "expected_state_bias_mean_ratio": self.expected_state_bias_mean_ratio,
            "expected_state_bias_median_ratio": self.expected_state_bias_median_ratio,
            "expected_state_bias_monotonic_rate": self.expected_state_bias_monotonic_rate,
            "overall_required_correction": self.overall_required_correction,
            "overall_achievable_correction": self.overall_achievable_correction,
            "sensitivity_matrix": [asdict(entry) for entry in self.sensitivity_matrix],
            "sweep_examples": [asdict(entry) for entry in self.sweep_examples],
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    learning_rate: float
    seed_results: Dict[int, SeedExpressivenessResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "learning_rate": self.learning_rate,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class ParameterExpressivenessAnalyzer:
    """Measure whether each parameter can materially affect the benchmark mapping."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedExpressivenessResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)

        sweep_examples: List[SweepSummary] = []
        required_corrections: List[float] = []
        achievable_corrections: List[float] = []
        monotonic_rates: List[float] = []
        ratios: List[float] = []

        for idx, experience in enumerate(dataset.training_experiences[:12]):
            summary = self._sweep_expected_state_bias_for_experience(experience)
            sweep_examples.append(summary)
            required_corrections.append(summary.required_correction)
            achievable_corrections.append(summary.achievable_correction)
            monotonic_rates.append(summary.monotonic_direction)
            ratios.append(summary.expressiveness_ratio)

        sensitivity_matrix = self._parameter_sensitivity_matrix(dataset)

        return SeedExpressivenessResult(
            seed=self.seed,
            total_events=len(dataset.training_experiences),
            expected_state_bias_mean_ratio=mean(ratios) if ratios else 0.0,
            expected_state_bias_median_ratio=self._median(ratios) if ratios else 0.0,
            expected_state_bias_monotonic_rate=mean(monotonic_rates) if monotonic_rates else 0.0,
            overall_required_correction=mean(required_corrections) if required_corrections else 0.0,
            overall_achievable_correction=mean(achievable_corrections) if achievable_corrections else 0.0,
            sensitivity_matrix=sensitivity_matrix,
            sweep_examples=sweep_examples,
        )

    def _sweep_expected_state_bias_for_experience(self, experience) -> SweepSummary:
        state = {str(k): float(v) for k, v in experience.initial_state.items()}
        actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
        base_prediction = self._simulate_prediction(state, experience.selected_action, CalibrationParameters())
        required_correction = self._mean_signed_gap(actual, base_prediction)
        if required_correction == 0:
            required_correction = self._mean_abs_gap(actual, base_prediction)

        curve: List[SweepPoint] = []
        for bias in PARAMETER_SPECS["expected_state_bias"]["values"]:
            params = CalibrationParameters(
                expected_state_bias={feature: float(bias) for feature in FEATURES},
                transition_probability_bias=0.0,
                risk_bias=0.0,
                uncertainty=0.5,
                confidence=0.5,
            )
            prediction = self._simulate_prediction(state, experience.selected_action, params)
            mean_pred = mean(prediction.values()) if prediction else 0.0
            mean_actual = mean(actual.values()) if actual else 0.0
            signed_error = self._mean_signed_gap(actual, prediction)
            abs_error = self._mean_abs_gap(actual, prediction)
            max_abs_error = max(abs(actual.get(key, 0.0) - prediction.get(key, 0.0)) for key in set(actual) | set(prediction)) if (set(actual) | set(prediction)) else 0.0
            curve.append(
                SweepPoint(
                    bias_value=float(bias),
                    mean_prediction=mean_pred,
                    mean_actual=mean_actual,
                    mean_signed_error=signed_error,
                    mean_abs_error=abs_error,
                    max_abs_error=max_abs_error,
                )
            )

        achievable = self._max_prediction_shift(curve, baseline=mean(base_prediction.values()) if base_prediction else 0.0)
        expressiveness_ratio = self._expressiveness_ratio(required_correction, achievable)
        monotonic_direction = self._monotonic_direction_score(curve)
        best_bias = min(curve, key=lambda p: p.mean_abs_error).bias_value if curve else 0.0
        best_mae = min(curve, key=lambda p: p.mean_abs_error).mean_abs_error if curve else 0.0

        return SweepSummary(
            state_id=f"{experience.experience_id}",
            category=experience.category,
            required_correction=abs(required_correction),
            achievable_correction=achievable,
            expressiveness_ratio=expressiveness_ratio,
            monotonic_direction=monotonic_direction,
            best_bias=best_bias,
            best_mae=best_mae,
            response_curve=curve,
        )

    def _parameter_sensitivity_matrix(self, dataset) -> List[ParameterSensitivityEntry]:
        results: List[ParameterSensitivityEntry] = []

        for param_name, spec in PARAMETER_SPECS.items():
            values = spec["values"]
            deltas: List[float] = []
            mae_deltas: List[float] = []
            effect_sizes: List[float] = []

            for value in values:
                params = self._parameter_configuration(param_name, value)
                total_prediction = 0.0
                total_mae = 0.0
                count = 0
                for experience in dataset.training_experiences:
                    state = {str(k): float(v) for k, v in experience.initial_state.items()}
                    actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
                    prediction = self._simulate_prediction(state, experience.selected_action, params)
                    total_prediction += mean(prediction.values()) if prediction else 0.0
                    total_mae += self._mean_abs_gap(actual, prediction)
                    count += 1
                deltas.append(total_prediction / max(1, count))
                mae_deltas.append(total_mae / max(1, count))

            baseline_prediction = sum(deltas[:1]) / max(1, len(deltas[:1])) if deltas else 0.0
            max_prediction = max(deltas) if deltas else 0.0
            min_prediction = min(deltas) if deltas else 0.0
            prediction_delta = abs(max_prediction - min_prediction)
            baseline_mae = sum(mae_deltas[:1]) / max(1, len(mae_deltas[:1])) if mae_deltas else 0.0
            max_mae = max(mae_deltas) if mae_deltas else 0.0
            min_mae = min(mae_deltas) if mae_deltas else 0.0
            mae_delta = abs(max_mae - min_mae)
            effect_sizes.append(prediction_delta)
            effect_sizes.append(mae_delta)

            results.append(
                ParameterSensitivityEntry(
                    parameter=param_name,
                    sweep_values=values,
                    mean_prediction_delta=prediction_delta,
                    mean_mae_delta=mae_delta,
                    mean_effect_size=mean(effect_sizes) if effect_sizes else 0.0,
                    identifiable=prediction_delta > 0.01 or mae_delta > 0.01,
                    description=spec["description"],
                )
            )

        return results

    def _parameter_configuration(self, param_name: str, value: float) -> CalibrationParameters:
        params = CalibrationParameters(
            expected_state_bias={feature: 0.0 for feature in FEATURES},
            transition_probability_bias=0.0,
            risk_bias=0.0,
            uncertainty=0.5,
            confidence=0.5,
        )

        if param_name == "expected_state_bias":
            params.expected_state_bias = {feature: float(value) for feature in FEATURES}
        elif param_name == "transition_probability_bias":
            params.transition_probability_bias = float(value)
        elif param_name == "risk_bias":
            params.risk_bias = float(value)
        elif param_name == "uncertainty":
            params.uncertainty = float(value)
        elif param_name == "confidence":
            params.confidence = float(value)

        return params

    @staticmethod
    def _simulate_prediction(state: Dict[str, float], action: str, params: CalibrationParameters):
        engine = SimulationEngine(calibration_parameters=params)
        result = engine.simulate_action(state, action)
        return {str(k): float(v) for k, v in result.get("predicted_future_state", {}).items()}

    @staticmethod
    def _mean_abs_gap(actual: Dict[str, float], predicted: Dict[str, float]) -> float:
        keys = sorted(set(actual) | set(predicted))
        if not keys:
            return 0.0
        return mean([abs(actual.get(key, 0.0) - predicted.get(key, 0.0)) for key in keys])

    @staticmethod
    def _mean_signed_gap(actual: Dict[str, float], predicted: Dict[str, float]) -> float:
        keys = sorted(set(actual) | set(predicted))
        if not keys:
            return 0.0
        return mean([float(actual.get(key, 0.0) - predicted.get(key, 0.0)) for key in keys])

    @staticmethod
    def _max_prediction_shift(curve: Iterable[SweepPoint], baseline: float) -> float:
        values = [abs(item.mean_prediction - baseline) for item in curve]
        return max(values) if values else 0.0

    @staticmethod
    def _expressiveness_ratio(required_correction: float, achievable_correction: float) -> float:
        if required_correction <= 0:
            return 1.0 if achievable_correction <= 0 else 1.0
        return min(1.0, achievable_correction / required_correction)

    @staticmethod
    def _monotonic_direction_score(curve: List[SweepPoint]) -> float:
        if len(curve) < 2:
            return 1.0
        values = [point.mean_prediction for point in curve]
        increasing = 0
        decreasing = 0
        for i in range(1, len(values)):
            if values[i] > values[i - 1]:
                increasing += 1
            elif values[i] < values[i - 1]:
                decreasing += 1
        if increasing == 0 and decreasing == 0:
            return 1.0
        return max(increasing, decreasing) / max(1, len(values) - 1)

    @staticmethod
    def _median(values: List[float]) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        mid = len(ordered) // 2
        if len(ordered) % 2 == 0:
            return (ordered[mid - 1] + ordered[mid]) / 2.0
        return ordered[mid]


class ResearchPhase17_7_A:
    """Run the 17.7A parameter expressiveness analysis across all seeds."""

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
        print("Phase 17.7A: Parameter Expressiveness & Sensitivity Mapping")
        print("=" * 120)

        for seed in self.seeds:
            print(f"\nAnalyzing seed {seed}...", end=" ", flush=True)
            analyzer = ParameterExpressivenessAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print("[DONE]")

        self._print_summary(result)
        self._save_results(result)
        return result

    def _print_summary(self, result: AnalysisResult):
        print("\n" + "=" * 120)
        print("PARAMETER EXPRESSIVENESS SUMMARY")
        print("=" * 120)
        print(f"{'Seed':<8} {'Exp ratio':>12} {'Monotonic':>10} {'Req corr':>10} {'Ach corr':>10}")
        print("-" * 120)
        for seed in self.seeds:
            sr = result.seed_results[seed]
            print(
                f"{seed:<8} {sr.expected_state_bias_mean_ratio:>12.3f} {sr.expected_state_bias_monotonic_rate:>10.3f} "
                f"{sr.overall_required_correction:>10.3f} {sr.overall_achievable_correction:>10.3f}"
            )

        for seed in self.seeds:
            print(f"\nSeed {seed} sensitivity matrix:")
            for entry in result.seed_results[seed].sensitivity_matrix:
                print(
                    f"  - {entry.parameter:<26} "
                    f"pred_delta={entry.mean_prediction_delta:>7.4f}  "
                    f"mae_delta={entry.mean_mae_delta:>7.4f}  "
                    f"identifiable={str(entry.identifiable):<5}"
                )

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_7_a_parameter_expressiveness.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_7_A().run()
