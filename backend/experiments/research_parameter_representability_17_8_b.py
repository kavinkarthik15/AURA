"""
17.8B: Parameter Representability Analysis

Observational study answering:

    Can the current CalibrationParameters abstraction represent the predictive
    information identified in 17.8A?

This phase does not modify production architecture. It measures representability
using controlled dimension perturbations against the existing simulation path.
"""

from __future__ import annotations

import itertools
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine

FEATURES = ["python", "dsa", "machine_learning", "projects"]
PARAMETERS = [
    "expected_state_bias",
    "transition_probability_bias",
    "risk_bias",
    "uncertainty",
    "confidence",
]
PREDICTIVE_DIMENSIONS = ["motivation", "goals", "behavior"]

ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}

PARAMETER_GRID = {
    "expected_state_bias": [-5.0, 0.0, 5.0],
    "transition_probability_bias": [-1.0, 0.0, 1.0],
    "risk_bias": [-1.0, 0.0, 1.0],
    "uncertainty": [0.0, 0.5, 1.0],
    "confidence": [0.0, 0.5, 1.0],
}

CLASSIFICATION_REPRESENTED = "represented"
CLASSIFICATION_DISCONNECTED = "representable_but_disconnected"
CLASSIFICATION_NOT_REPRESENTABLE = "not_representable"
CLASSIFICATION_INDIRECT = "indirectly_representable"


@dataclass
class DimensionRepresentabilityEntry:
    dimension: str
    existing_parameter: str
    can_influence_prediction: bool
    directly_representable: bool
    classification: str
    prediction_sensitivity: float
    mae_sensitivity: float
    objective_delta: float
    jacobian_by_parameter: Dict[str, float]
    jacobian_delta_norm: float
    effect_distinguishable_from_expected_state_bias: bool
    expected_state_bias_equivalence_rmse: float
    equivalent_parameter_settings_count: int
    unique_prediction_signatures: int
    evidence: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SeedRepresentabilityResult:
    seed: int
    total_events: int
    matrix: Dict[str, DimensionRepresentabilityEntry]
    elapsed_seconds: float
    prediction_requests: int
    prediction_calls: int
    prediction_cache_hits: int
    prediction_cache_hit_rate: float

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events": self.total_events,
            "matrix": {k: v.to_dict() for k, v in self.matrix.items()},
            "elapsed_seconds": self.elapsed_seconds,
            "prediction_requests": self.prediction_requests,
            "prediction_calls": self.prediction_calls,
            "prediction_cache_hits": self.prediction_cache_hits,
            "prediction_cache_hit_rate": self.prediction_cache_hit_rate,
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    seed_results: Dict[int, SeedRepresentabilityResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class ParameterRepresentabilityAnalyzer:
    """Build a representability matrix for motivation/goals/behavior."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self._prediction_cache: Dict[Tuple, np.ndarray] = {}
        self._engine_cache: Dict[Tuple, SimulationEngine] = {}
        self.prediction_requests = 0
        self.prediction_calls = 0
        self.prediction_cache_hits = 0

    def analyze_seed(self) -> SeedRepresentabilityResult:
        start = time.perf_counter()
        self._prediction_cache.clear()
        self._engine_cache.clear()
        self.prediction_requests = 0
        self.prediction_calls = 0
        self.prediction_cache_hits = 0

        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        matrix: Dict[str, DimensionRepresentabilityEntry] = {}

        for dimension in PREDICTIVE_DIMENSIONS:
            matrix[dimension] = self._analyze_dimension(dataset, dimension)

        elapsed = time.perf_counter() - start
        hit_rate = (self.prediction_cache_hits / self.prediction_requests) if self.prediction_requests else 0.0
        return SeedRepresentabilityResult(
            seed=self.seed,
            total_events=len(dataset.training_experiences),
            matrix=matrix,
            elapsed_seconds=float(elapsed),
            prediction_requests=self.prediction_requests,
            prediction_calls=self.prediction_calls,
            prediction_cache_hits=self.prediction_cache_hits,
            prediction_cache_hit_rate=float(hit_rate),
        )

    def _analyze_dimension(self, dataset, dimension: str) -> DimensionRepresentabilityEntry:
        base_params = self._base_params()
        base_preds: List[np.ndarray] = []
        pert_preds: List[np.ndarray] = []
        base_maes: List[float] = []
        pert_maes: List[float] = []

        for experience in dataset.training_experiences:
            base_state = {str(k): float(v) for k, v in experience.initial_state.items()}
            base_action = str(experience.selected_action)
            base_actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}

            pert_state, pert_action = self._perturb_dimension(
                dimension=dimension,
                state=base_state,
                action=base_action,
                category=str(experience.category),
            )

            base_pred = self._predict_vector(base_state, base_action, base_params)
            pert_pred = self._predict_vector(pert_state, pert_action, base_params)

            base_preds.append(base_pred)
            pert_preds.append(pert_pred)

            base_maes.append(self._mae_from_vector(base_actual, base_pred))
            pert_maes.append(self._mae_from_vector(base_actual, pert_pred))

        prediction_sensitivity = float(np.mean([np.mean(np.abs(p - b)) for b, p in zip(base_preds, pert_preds)]))
        objective_deltas = [p - b for b, p in zip(base_maes, pert_maes)]
        mae_sensitivity = float(np.mean(np.abs(objective_deltas)))
        objective_delta = float(np.mean(objective_deltas))
        can_influence_prediction = prediction_sensitivity > 1e-9

        jac_base = self._parameter_jacobian(dataset, dimension, perturbed=False)
        jac_pert = self._parameter_jacobian(dataset, dimension, perturbed=True)
        jacobian_by_parameter = {name: float(jac_pert[name]) for name in PARAMETERS}
        jacobian_delta_norm = float(sum(abs(jac_pert[name] - jac_base[name]) for name in PARAMETERS))

        rmse_to_bias, fitted_bias = self._fit_expected_bias_equivalence(base_preds, pert_preds)
        distinguishable = rmse_to_bias > 1e-6

        eq_count, unique_signatures = self._equivalent_parameter_settings(dataset, dimension)

        directly_representable = self._directly_representable(jacobian_by_parameter)
        existing_parameter = self._existing_parameter_for_dimension(dimension)
        classification = self._classify(
            dimension=dimension,
            directly_representable=directly_representable,
            can_influence_prediction=can_influence_prediction,
            distinguishable=distinguishable,
        )
        evidence = self._evidence(
            dimension=dimension,
            prediction_sensitivity=prediction_sensitivity,
            mae_sensitivity=mae_sensitivity,
            objective_delta=objective_delta,
            jacobian_by_parameter=jacobian_by_parameter,
            rmse_to_bias=rmse_to_bias,
            fitted_bias=fitted_bias,
            eq_count=eq_count,
            unique_signatures=unique_signatures,
        )

        return DimensionRepresentabilityEntry(
            dimension=dimension,
            existing_parameter=existing_parameter,
            can_influence_prediction=can_influence_prediction,
            directly_representable=directly_representable,
            classification=classification,
            prediction_sensitivity=prediction_sensitivity,
            mae_sensitivity=mae_sensitivity,
            objective_delta=objective_delta,
            jacobian_by_parameter=jacobian_by_parameter,
            jacobian_delta_norm=jacobian_delta_norm,
            effect_distinguishable_from_expected_state_bias=distinguishable,
            expected_state_bias_equivalence_rmse=rmse_to_bias,
            equivalent_parameter_settings_count=eq_count,
            unique_prediction_signatures=unique_signatures,
            evidence=evidence,
        )

    def _perturb_dimension(self, dimension: str, state: Dict[str, float], action: str, category: str) -> Tuple[Dict[str, float], str]:
        # Motivation and goals are metadata-only in the current prediction path.
        if dimension in {"motivation", "goals"}:
            return dict(state), str(action)

        # Behavior perturbation: swap action signal while holding state fixed.
        if dimension == "behavior":
            if action != "Build Portfolio":
                return dict(state), "Build Portfolio"
            return dict(state), "DSA Practice"

        return dict(state), str(action)

    @staticmethod
    def _base_params() -> CalibrationParameters:
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

    def _parameter_jacobian(self, dataset, dimension: str, perturbed: bool) -> Dict[str, float]:
        jac: Dict[str, float] = {}
        base_params = self._base_params()
        eps = {
            "expected_state_bias": 1.0,
            "transition_probability_bias": 0.5,
            "risk_bias": 0.5,
            "uncertainty": 0.1,
            "confidence": 0.1,
        }

        for name in PARAMETERS:
            plus_params = self._parameter_override(name, eps[name])
            minus_params = self._parameter_override(name, -eps[name] if name in {"expected_state_bias", "transition_probability_bias", "risk_bias"} else max(0.0, 0.5 - eps[name]))

            baseline_values = []
            plus_values = []
            minus_values = []

            for experience in dataset.training_experiences:
                state = {str(k): float(v) for k, v in experience.initial_state.items()}
                action = str(experience.selected_action)
                if perturbed:
                    state, action = self._perturb_dimension(
                        dimension=dimension,
                        state=state,
                        action=action,
                        category=str(experience.category),
                    )

                baseline_values.append(float(np.mean(self._predict_vector(state, action, base_params))))
                plus_values.append(float(np.mean(self._predict_vector(state, action, plus_params))))
                minus_values.append(float(np.mean(self._predict_vector(state, action, minus_params))))

            numerator = mean(plus_values) - mean(minus_values)
            denom = (eps[name] * 2.0) if name in {"expected_state_bias", "transition_probability_bias", "risk_bias"} else eps[name]
            jac[name] = float(numerator / denom) if abs(denom) > 0 else 0.0

        return jac

    def _fit_expected_bias_equivalence(self, base_preds: List[np.ndarray], pert_preds: List[np.ndarray]) -> Tuple[float, Dict[str, float]]:
        if not base_preds:
            return 0.0, {feature: 0.0 for feature in FEATURES}

        deltas = np.asarray([p - b for b, p in zip(base_preds, pert_preds)], dtype=float)
        fitted = np.mean(deltas, axis=0)

        residuals = []
        for base, target in zip(base_preds, pert_preds):
            approx = base + fitted
            residuals.append(np.mean((approx - target) ** 2))
        rmse = float(np.sqrt(np.mean(residuals))) if residuals else 0.0

        fitted_bias = {feature: float(fitted[idx]) for idx, feature in enumerate(FEATURES)}
        return rmse, fitted_bias

    def _equivalent_parameter_settings(self, dataset, dimension: str) -> Tuple[int, int]:
        settings = list(itertools.product(*[PARAMETER_GRID[name] for name in PARAMETERS]))
        signatures: Dict[Tuple[float, ...], int] = {}

        baseline_sig = self._prediction_signature(dataset, self._base_params(), dimension)

        for combo in settings:
            params = self._params_from_combo(combo)
            signature = self._prediction_signature(dataset, params, dimension)
            signatures[signature] = signatures.get(signature, 0) + 1

        equivalent_count = signatures.get(baseline_sig, 0)
        return equivalent_count, len(signatures)

    def _prediction_signature(self, dataset, params: CalibrationParameters, dimension: str) -> Tuple[float, ...]:
        values: List[float] = []
        for experience in dataset.training_experiences:
            state = {str(k): float(v) for k, v in experience.initial_state.items()}
            action = str(experience.selected_action)
            state, action = self._perturb_dimension(
                dimension=dimension,
                state=state,
                action=action,
                category=str(experience.category),
            )
            pred = self._predict_vector(state, action, params)
            values.extend(float(v) for v in pred)
        return tuple(round(v, 6) for v in values)

    def _params_from_combo(self, combo: Tuple[float, ...]) -> CalibrationParameters:
        expected_state_bias, transition_probability_bias, risk_bias, uncertainty, confidence = combo
        return CalibrationParameters(
            expected_state_bias={feature: float(expected_state_bias) for feature in FEATURES},
            transition_probability_bias=float(transition_probability_bias),
            risk_bias=float(risk_bias),
            uncertainty=float(uncertainty),
            confidence=float(confidence),
        )

    @staticmethod
    def _directly_representable(jacobian_by_parameter: Dict[str, float]) -> bool:
        # Direct representation requires a non-bias parameter path into predicted future_state.
        return (
            abs(jacobian_by_parameter.get("transition_probability_bias", 0.0)) > 1e-9
            or abs(jacobian_by_parameter.get("risk_bias", 0.0)) > 1e-9
        )

    @staticmethod
    def _existing_parameter_for_dimension(dimension: str) -> str:
        if dimension == "motivation":
            return "expected_state_bias (indirect proxy only)"
        if dimension == "goals":
            return "expected_state_bias (indirect proxy only)"
        if dimension == "behavior":
            return "transition_probability_bias (conceptual), expected_state_bias (indirect)"
        return "none"

    @staticmethod
    def _classify(
        dimension: str,
        directly_representable: bool,
        can_influence_prediction: bool,
        distinguishable: bool,
    ) -> str:
        if directly_representable:
            return CLASSIFICATION_REPRESENTED

        if dimension in {"motivation", "goals"} and not can_influence_prediction:
            return CLASSIFICATION_NOT_REPRESENTABLE

        if dimension == "behavior" and can_influence_prediction and not distinguishable:
            return CLASSIFICATION_INDIRECT

        if dimension == "behavior" and can_influence_prediction and distinguishable:
            return CLASSIFICATION_DISCONNECTED

        return CLASSIFICATION_NOT_REPRESENTABLE

    @staticmethod
    def _evidence(
        dimension: str,
        prediction_sensitivity: float,
        mae_sensitivity: float,
        objective_delta: float,
        jacobian_by_parameter: Dict[str, float],
        rmse_to_bias: float,
        fitted_bias: Dict[str, float],
        eq_count: int,
        unique_signatures: int,
    ) -> str:
        return (
            f"{dimension}: pred_sens={prediction_sensitivity:.6f}, "
            f"mae_sens={mae_sensitivity:.6f}, objective_delta={objective_delta:.6f}; "
            f"jac_expected_state_bias={jacobian_by_parameter.get('expected_state_bias', 0.0):.6f}, "
            f"jac_transition_probability_bias={jacobian_by_parameter.get('transition_probability_bias', 0.0):.6f}, "
            f"jac_risk_bias={jacobian_by_parameter.get('risk_bias', 0.0):.6f}; "
            f"equivalence_rmse={rmse_to_bias:.6f}, fitted_bias={fitted_bias}; "
            f"equivalent_settings={eq_count}, unique_signatures={unique_signatures}."
        )

    @staticmethod
    def _params_key(params: CalibrationParameters) -> Tuple:
        return (
            tuple((feature, float(params.expected_state_bias.get(feature, 0.0))) for feature in FEATURES),
            float(params.transition_probability_bias),
            float(params.risk_bias),
            float(params.uncertainty),
            float(params.confidence),
        )

    @staticmethod
    def _state_key(state: Dict[str, float]) -> Tuple:
        return tuple(sorted((str(k), float(v)) for k, v in state.items()))

    def _predict_vector(self, state: Dict[str, float], action: str, params: CalibrationParameters) -> np.ndarray:
        self.prediction_requests += 1
        params_key = self._params_key(params)
        cache_key = (params_key, self._state_key(state), str(action))
        if cache_key in self._prediction_cache:
            self.prediction_cache_hits += 1
            return self._prediction_cache[cache_key]

        engine = self._engine_cache.get(params_key)
        if engine is None:
            engine = SimulationEngine(calibration_parameters=params)
            self._engine_cache[params_key] = engine

        self.prediction_calls += 1
        result = engine.simulate_action(state, action)
        pred = {str(k): float(v) for k, v in result.get("predicted_future_state", {}).items()}
        pred_vec = np.asarray([float(pred.get(feature, 0.0)) for feature in FEATURES], dtype=float)
        self._prediction_cache[cache_key] = pred_vec
        return pred_vec

    @staticmethod
    def _mae_from_vector(actual: Dict[str, float], pred_vec: np.ndarray) -> float:
        pred = {feature: float(pred_vec[idx]) for idx, feature in enumerate(FEATURES)}
        return float(np.mean([abs(float(actual.get(feature, 0.0)) - pred[feature]) for feature in FEATURES]))


class ResearchPhase17_8_B:
    """Run 17.8B representability analysis across seeds."""

    def __init__(self, seeds: List[int] | None = None):
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> AnalysisResult:
        result = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 120)
        print("Phase 17.8B: Parameter Representability Analysis")
        print("=" * 120)

        for seed in self.seeds:
            analyzer = ParameterRepresentabilityAnalyzer(seed=seed)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print(f"\nSeed {seed}:")
            for dimension, entry in seed_result.matrix.items():
                print(
                    f"  - {dimension:<12} "
                    f"can_influence={str(entry.can_influence_prediction):<5} "
                    f"direct={str(entry.directly_representable):<5} "
                    f"class={entry.classification:<30} "
                    f"pred_sens={entry.prediction_sensitivity:>8.4f} "
                    f"mae_sens={entry.mae_sensitivity:>8.4f} "
                    f"eq_bias_rmse={entry.expected_state_bias_equivalence_rmse:>8.4f}"
                )
            print(
                f"    runtime={seed_result.elapsed_seconds:.3f}s, "
                f"prediction_requests={seed_result.prediction_requests}, "
                f"prediction_calls={seed_result.prediction_calls}, "
                f"cache_hits={seed_result.prediction_cache_hits}, "
                f"cache_hit_rate={seed_result.prediction_cache_hit_rate:.2%}"
            )

        self._save_results(result)
        return result

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_8_b_parameter_representability.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_8_B().run()
