"""
17.7C: Parameter Activation / Model-Expressiveness Analysis

Observational-only diagnostic answering:

    Why are four calibration parameters present in the model but causally inert
    under the current prediction architecture?

This phase does not change the calibrator. It traces each parameter from
CalibrationParameters through the simulation path and measures whether it produces
any measurable delta in the predicted future state and the objective.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine

FEATURES = ["python", "dsa", "machine_learning", "projects"]
PARAMETER_ORDER = [
    "expected_state_bias",
    "transition_probability_bias",
    "risk_bias",
    "uncertainty",
    "confidence",
]


@dataclass
class InterventionProbe:
    value: float
    mean_prediction_delta: float
    mean_future_state_delta: float
    mean_mae_delta: float
    mean_calibration_delta: float


@dataclass
class ActivationEntry:
    parameter: str
    baseline_value: Any
    active_values: List[float]
    max_prediction_delta: float
    max_future_state_delta: float
    max_mae_delta: float
    mean_prediction_delta: float
    mean_future_state_delta: float
    mean_mae_delta: float
    is_activated: bool
    activation_stage: str
    dependency_path: str
    reason: str
    probes: List[InterventionProbe] = field(default_factory=list)

    def to_dict(self):
        return {
            "parameter": self.parameter,
            "baseline_value": self.baseline_value,
            "active_values": self.active_values,
            "max_prediction_delta": self.max_prediction_delta,
            "max_future_state_delta": self.max_future_state_delta,
            "max_mae_delta": self.max_mae_delta,
            "mean_prediction_delta": self.mean_prediction_delta,
            "mean_future_state_delta": self.mean_future_state_delta,
            "mean_mae_delta": self.mean_mae_delta,
            "is_activated": self.is_activated,
            "activation_stage": self.activation_stage,
            "dependency_path": self.dependency_path,
            "reason": self.reason,
            "probes": [asdict(p) for p in self.probes],
        }


@dataclass
class SeedActivationResult:
    seed: int
    total_events: int
    activation_map: Dict[str, ActivationEntry]

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events": self.total_events,
            "activation_map": {name: entry.to_dict() for name, entry in self.activation_map.items()},
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    seed_results: Dict[int, SeedActivationResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class ParameterActivationAnalyzer:
    """Trace whether each parameter affects the actual prediction pipeline or only metadata."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedActivationResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        activation_map: Dict[str, ActivationEntry] = {}

        for parameter_name in PARAMETER_ORDER:
            activation_map[parameter_name] = self._analyze_parameter(parameter_name, dataset)

        return SeedActivationResult(
            seed=self.seed,
            total_events=len(dataset.training_experiences),
            activation_map=activation_map,
        )

    def _analyze_parameter(self, parameter_name: str, dataset) -> ActivationEntry:
        baseline_params = self._base_params()
        baseline_mae = self._mean_dataset_mae(dataset, baseline_params)
        baseline_prediction = self._mean_prediction(dataset, baseline_params)

        probe_values = self._intervention_values(parameter_name)
        probes: List[InterventionProbe] = []
        prediction_deltas: List[float] = []
        future_state_deltas: List[float] = []
        mae_deltas: List[float] = []
        calibration_deltas: List[float] = []

        for value in probe_values:
            params = self._parameter_override(parameter_name, value)
            modified_mae = self._mean_dataset_mae(dataset, params)
            modified_prediction = self._mean_prediction(dataset, params)
            future_state_delta = self._mean_future_state_delta(dataset, baseline_params, params)
            prediction_delta = abs(modified_prediction - baseline_prediction)
            mae_delta = modified_mae - baseline_mae
            calibration_delta = self._mean_calibration_delta(dataset, baseline_params, params)

            probes.append(
                InterventionProbe(
                    value=float(value),
                    mean_prediction_delta=float(prediction_delta),
                    mean_future_state_delta=float(future_state_delta),
                    mean_mae_delta=float(mae_delta),
                    mean_calibration_delta=float(calibration_delta),
                )
            )
            prediction_deltas.append(abs(prediction_delta))
            future_state_deltas.append(abs(future_state_delta))
            mae_deltas.append(abs(mae_delta))
            calibration_deltas.append(abs(calibration_delta))

        max_prediction_delta = max(prediction_deltas) if prediction_deltas else 0.0
        max_future_state_delta = max(future_state_deltas) if future_state_deltas else 0.0
        max_mae_delta = max(mae_deltas) if mae_deltas else 0.0
        mean_prediction_delta = mean(prediction_deltas) if prediction_deltas else 0.0
        mean_future_state_delta = mean(future_state_deltas) if future_state_deltas else 0.0
        mean_mae_delta = mean(mae_deltas) if mae_deltas else 0.0

        is_activated = (
            max_prediction_delta > 1e-9
            or max_future_state_delta > 1e-9
            or max_mae_delta > 1e-9
        )

        activation_stage, dependency_path, reason = self._dependency_summary(parameter_name)

        return ActivationEntry(
            parameter=parameter_name,
            baseline_value=self._baseline_value(parameter_name),
            active_values=probe_values,
            max_prediction_delta=max_prediction_delta,
            max_future_state_delta=max_future_state_delta,
            max_mae_delta=max_mae_delta,
            mean_prediction_delta=mean_prediction_delta,
            mean_future_state_delta=mean_future_state_delta,
            mean_mae_delta=mean_mae_delta,
            is_activated=is_activated,
            activation_stage=activation_stage,
            dependency_path=dependency_path,
            reason=reason,
            probes=probes,
        )

    @staticmethod
    def _intervention_values(parameter_name: str) -> List[float]:
        if parameter_name == "expected_state_bias":
            return [0.0, 0.5, 2.0, 10.0, 50.0, -50.0]
        if parameter_name in {"transition_probability_bias", "risk_bias"}:
            return [0.0, 0.5, 2.0, 10.0, 1.0, -1.0]
        return [0.0, 0.25, 0.5, 0.75, 1.0, 0.0, 0.1, 0.9]

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

    @staticmethod
    def _base_params() -> CalibrationParameters:
        return CalibrationParameters(
            expected_state_bias={feature: 0.0 for feature in FEATURES},
            transition_probability_bias=0.0,
            risk_bias=0.0,
            uncertainty=0.5,
            confidence=0.5,
        )

    @staticmethod
    def _baseline_value(parameter_name: str):
        if parameter_name == "expected_state_bias":
            return {feature: 0.0 for feature in FEATURES}
        return 0.0

    def _mean_prediction(self, dataset, params: CalibrationParameters) -> float:
        values = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            pred = self._simulate_prediction(state, experience.selected_action, params)
            if pred:
                values.append(mean(pred.values()))
        return mean(values) if values else 0.0

    def _mean_dataset_mae(self, dataset, params: CalibrationParameters) -> float:
        maes = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            pred = self._simulate_prediction(state, experience.selected_action, params)
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            maes.append(self._mae(actual, pred))
        return mean(maes) if maes else 0.0

    def _mean_future_state_delta(self, dataset, baseline_params: CalibrationParameters, test_params: CalibrationParameters) -> float:
        deltas = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            base_pred = self._simulate_prediction(state, experience.selected_action, baseline_params)
            test_pred = self._simulate_prediction(state, experience.selected_action, test_params)
            deltas.append(self._mae(base_pred, test_pred))
        return mean(deltas) if deltas else 0.0

    @staticmethod
    def _mean_calibration_delta(dataset, baseline_params: CalibrationParameters, test_params: CalibrationParameters) -> float:
        deltas = []
        for experience in dataset.training_experiences:
            baseline_conf = SimulationEngine(calibration_parameters=baseline_params).simulate_action(
                {str(k): float(v) for k, v in experience.initial_state.items()},
                experience.selected_action,
            )['confidence']
            test_conf = SimulationEngine(calibration_parameters=test_params).simulate_action(
                {str(k): float(v) for k, v in experience.initial_state.items()},
                experience.selected_action,
            )['confidence']
            deltas.append(abs(float(test_conf) - float(baseline_conf)))
        return mean(deltas) if deltas else 0.0

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

    @staticmethod
    def _dependency_summary(parameter_name: str):
        if parameter_name == "expected_state_bias":
            return (
                "state_prediction",
                "CalibrationParameters.expected_state_bias -> SimulationEngine._apply_calibration_bias -> predicted_future_state -> objective/MAE",
                "This parameter directly modifies future_state values before the objective is computed.",
            )
        if parameter_name in {"transition_probability_bias", "risk_bias"}:
            return (
                "unused_parameter",
                "CalibrationParameters.<scalar> -> no read path in SimulationEngine / TransitionEngine / prediction equation -> no effect on predicted_future_state or MAE",
                "The current prediction architecture never consumes these fields; they are stored but disconnected from the actual state update path.",
            )
        if parameter_name == "uncertainty":
            return (
                "confidence_metadata_only",
                "CalibrationParameters.uncertainty -> SimulationEngine._apply_calibration_bias adjusts confidence only; it never changes future_state -> objective unchanged",
                "This parameter modulates confidence, not the predicted state itself, so it cannot affect MAE unless the scoring layer explicitly uses it.",
            )
        if parameter_name == "confidence":
            return (
                "confidence_metadata_only",
                "CalibrationParameters.confidence -> SimulationEngine._apply_calibration_bias adjusts confidence only; future_state unaffected -> objective unchanged",
                "This parameter only rescales the confidence reporting channel; it is not part of the state transition equation.",
            )
        return (
            "unknown",
            "CalibrationParameters -> unknown route",
            "Parameter path not recognized.",
        )


class ResearchPhase17_7_C:
    """Run the 17.7C activation analysis across a set of seeds."""

    def __init__(self, seeds: List[int] | None = None):
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> AnalysisResult:
        result = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 120)
        print("Phase 17.7C: Parameter Activation / Model-Expressiveness Analysis")
        print("=" * 120)

        for seed in self.seeds:
            analyzer = ParameterActivationAnalyzer(seed=seed)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print(f"\nSeed {seed}: active={[(name, entry.is_activated) for name, entry in seed_result.activation_map.items()]}")
            for name, entry in seed_result.activation_map.items():
                print(
                    f"  - {name:<28} active={str(entry.is_activated):<5} "
                    f"max_pred_delta={entry.max_prediction_delta:>8.4f} "
                    f"max_mae_delta={entry.max_mae_delta:>8.4f} "
                    f"stage={entry.activation_stage}"
                )

        self._save_results(result)
        return result

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_7_c_parameter_activation.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_7_C().run()
