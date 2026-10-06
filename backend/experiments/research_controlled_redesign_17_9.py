"""
17.9: Controlled Redesign Experiment

Observational experiment to test whether introducing predictive state dimensions
(motivation, goals, behavior) causes measurable improvement on the same
benchmark objective while holding benchmark, target, and simulation semantics fixed.

No production architecture is modified.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
SKILLS = ["python", "dsa", "machine_learning", "projects"]

ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}

# 17.9 hypotheses and ablation matrix
MODEL_FEATURES = {
    "baseline": [],
    "M": ["motivation"],
    "G": ["goals"],
    "B": ["behavior"],
    "MG": ["motivation", "goals"],
    "MB": ["motivation", "behavior"],
    "GB": ["goals", "behavior"],
    "MGB": ["motivation", "goals", "behavior"],
    # aliases to keep continuity with 17.8C naming
    "motivation_goals": ["motivation", "goals"],
    "all_three": ["motivation", "goals", "behavior"],
}

PRIMARY_CANDIDATES = ["baseline", "motivation_goals", "all_three"]
ABLATION_MODELS = ["baseline", "M", "G", "B", "MG", "MB", "GB", "MGB"]
DIMENSIONS = ["motivation", "goals", "behavior"]


@dataclass
class InterventionEffect:
    dimension: str
    prediction_delta: float
    mae_delta: float

    def to_dict(self):
        return asdict(self)


@dataclass
class ModelResult:
    model: str
    features: List[str]
    parameter_count: int
    train_mae: float
    heldout_mae: float
    train_rmse: float
    heldout_rmse: float
    train_r2: float
    heldout_r2: float
    delta_mae_vs_baseline: float
    delta_rmse_vs_baseline: float
    delta_r2_vs_baseline: float
    prediction_delta_vs_baseline: float
    coefficients: Dict[str, float]
    intervention_effects: Dict[str, InterventionEffect]

    def to_dict(self):
        return {
            "model": self.model,
            "features": list(self.features),
            "parameter_count": self.parameter_count,
            "train_mae": self.train_mae,
            "heldout_mae": self.heldout_mae,
            "train_rmse": self.train_rmse,
            "heldout_rmse": self.heldout_rmse,
            "train_r2": self.train_r2,
            "heldout_r2": self.heldout_r2,
            "delta_mae_vs_baseline": self.delta_mae_vs_baseline,
            "delta_rmse_vs_baseline": self.delta_rmse_vs_baseline,
            "delta_r2_vs_baseline": self.delta_r2_vs_baseline,
            "prediction_delta_vs_baseline": self.prediction_delta_vs_baseline,
            "coefficients": dict(self.coefficients),
            "intervention_effects": {k: v.to_dict() for k, v in self.intervention_effects.items()},
        }


@dataclass
class SeedResult:
    seed: int
    runtime_seconds: float
    model_results: Dict[str, ModelResult]
    benchmark_invariant: bool
    target_invariant: bool
    simulation_semantics_invariant: bool
    gate1_causal_activation: bool
    gate2_objective_improvement: bool
    gate4_incremental_mg_over_singletons: bool
    gate4_incremental_mgb_over_mg: bool

    def to_dict(self):
        return {
            "seed": self.seed,
            "runtime_seconds": self.runtime_seconds,
            "model_results": {k: v.to_dict() for k, v in self.model_results.items()},
            "benchmark_invariant": self.benchmark_invariant,
            "target_invariant": self.target_invariant,
            "simulation_semantics_invariant": self.simulation_semantics_invariant,
            "gate1_causal_activation": self.gate1_causal_activation,
            "gate2_objective_improvement": self.gate2_objective_improvement,
            "gate4_incremental_mg_over_singletons": self.gate4_incremental_mg_over_singletons,
            "gate4_incremental_mgb_over_mg": self.gate4_incremental_mgb_over_mg,
        }


@dataclass
class AggregateSummary:
    total_runtime_seconds: float
    per_seed_runtime_seconds: Dict[str, float]
    mean_metrics_by_model: Dict[str, Dict[str, float]]
    gate3_reproducibility: bool
    consistency_counts: Dict[str, int]

    def to_dict(self):
        return asdict(self)


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    seed_results: Dict[int, SeedResult] = field(default_factory=dict)
    aggregate_summary: AggregateSummary | None = None

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
            "aggregate_summary": self.aggregate_summary.to_dict() if self.aggregate_summary else None,
        }


class ControlledRedesignAnalyzer:
    def __init__(self, seed: int):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self._engine = SimulationEngine(calibration_parameters=self._base_calibration())

    @staticmethod
    def _base_calibration() -> CalibrationParameters:
        return CalibrationParameters(
            expected_state_bias={skill: 0.0 for skill in SKILLS},
            transition_probability_bias=0.0,
            risk_bias=0.0,
            uncertainty=0.5,
            confidence=0.5,
        )

    def analyze_seed(self) -> SeedResult:
        start = time.perf_counter()
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)

        train_rows = self._build_rows(dataset.training_experiences)
        heldout_rows = self._build_rows(dataset.held_out_experiences)

        benchmark_invariant = len(train_rows) == 80 and len(heldout_rows) == 20
        target_invariant = all("actual" in row for row in train_rows) and all("actual" in row for row in heldout_rows)
        simulation_semantics_invariant = self._simulation_invariance_check(train_rows + heldout_rows)

        baseline = self._fit_and_score_model("baseline", train_rows, heldout_rows, baseline_reference=None)
        model_results: Dict[str, ModelResult] = {"baseline": baseline}

        for model_name in MODEL_FEATURES:
            if model_name == "baseline":
                continue
            model_results[model_name] = self._fit_and_score_model(
                model_name,
                train_rows,
                heldout_rows,
                baseline_reference=baseline,
            )

        gate1_causal_activation = any(
            model_results["all_three"].intervention_effects[dim].prediction_delta > 1e-9
            for dim in DIMENSIONS
        )
        gate2_objective_improvement = model_results["motivation_goals"].heldout_mae < baseline.heldout_mae or model_results["all_three"].heldout_mae < baseline.heldout_mae
        gate4_incremental_mg_over_singletons = (
            model_results["MG"].heldout_mae < min(model_results["M"].heldout_mae, model_results["G"].heldout_mae)
        )
        gate4_incremental_mgb_over_mg = model_results["MGB"].heldout_mae < model_results["MG"].heldout_mae

        elapsed = time.perf_counter() - start

        return SeedResult(
            seed=self.seed,
            runtime_seconds=float(elapsed),
            model_results=model_results,
            benchmark_invariant=benchmark_invariant,
            target_invariant=target_invariant,
            simulation_semantics_invariant=simulation_semantics_invariant,
            gate1_causal_activation=gate1_causal_activation,
            gate2_objective_improvement=gate2_objective_improvement,
            gate4_incremental_mg_over_singletons=gate4_incremental_mg_over_singletons,
            gate4_incremental_mgb_over_mg=gate4_incremental_mgb_over_mg,
        )

    def _build_rows(self, experiences) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for exp in experiences:
            state = {str(k): int(v) for k, v in exp.initial_state.items()}
            action = str(exp.selected_action)
            actual = np.asarray([float(exp.actual_future_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)
            base_pred = self._predict_base(state, action)

            motivation = self._motivation_signal(str(exp.category))
            goals = self._goals_signal(state, action)
            behavior = self._behavior_signal(action)

            row = {
                "state": state,
                "action": action,
                "actual": actual,
                "base_pred": base_pred,
                "motivation": motivation,
                "goals": goals,
                "behavior": behavior,
            }
            rows.append(row)
        return rows

    def _predict_base(self, state: Dict[str, int], action: str) -> np.ndarray:
        result = self._engine.simulate_action(state, action)
        pred_state = result.get("predicted_future_state", {})
        return np.asarray([float(pred_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)

    def _fit_and_score_model(
        self,
        model_name: str,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
        baseline_reference: ModelResult | None,
    ) -> ModelResult:
        features = MODEL_FEATURES[model_name]
        X_train = self._design_matrix(train_rows, features)
        y_train = self._residual_target(train_rows)
        coeff, *_ = np.linalg.lstsq(X_train, y_train, rcond=None)

        train_pred_vecs = self._corrected_predictions(train_rows, features, coeff)
        heldout_pred_vecs = self._corrected_predictions(heldout_rows, features, coeff)

        train_actual = np.asarray([row["actual"] for row in train_rows], dtype=float)
        heldout_actual = np.asarray([row["actual"] for row in heldout_rows], dtype=float)

        train_mae = self._mae_matrix(train_actual, train_pred_vecs)
        heldout_mae = self._mae_matrix(heldout_actual, heldout_pred_vecs)
        train_rmse = self._rmse_matrix(train_actual, train_pred_vecs)
        heldout_rmse = self._rmse_matrix(heldout_actual, heldout_pred_vecs)
        train_r2 = self._r2_scalar(train_actual.mean(axis=1), train_pred_vecs.mean(axis=1))
        heldout_r2 = self._r2_scalar(heldout_actual.mean(axis=1), heldout_pred_vecs.mean(axis=1))

        if baseline_reference is None:
            delta_mae = 0.0
            delta_rmse = 0.0
            delta_r2 = 0.0
            pred_delta = 0.0
            baseline_heldout_pred = heldout_pred_vecs
        else:
            delta_mae = float(baseline_reference.heldout_mae - heldout_mae)
            delta_rmse = float(baseline_reference.heldout_rmse - heldout_rmse)
            delta_r2 = float(heldout_r2 - baseline_reference.heldout_r2)
            baseline_heldout_pred = self._corrected_predictions(heldout_rows, MODEL_FEATURES["baseline"], np.asarray([baseline_reference.coefficients["beta_0"]], dtype=float))
            pred_delta = float(np.mean(np.abs(heldout_pred_vecs - baseline_heldout_pred)))

        interventions = self._intervention_effects(heldout_rows, features, coeff, baseline_heldout_pred)

        coeff_map = {"beta_0": float(coeff[0])}
        for idx, feature in enumerate(features, start=1):
            coeff_map[f"beta_{feature}"] = float(coeff[idx])

        return ModelResult(
            model=model_name,
            features=list(features),
            parameter_count=1 + len(features),
            train_mae=float(train_mae),
            heldout_mae=float(heldout_mae),
            train_rmse=float(train_rmse),
            heldout_rmse=float(heldout_rmse),
            train_r2=float(train_r2),
            heldout_r2=float(heldout_r2),
            delta_mae_vs_baseline=float(delta_mae),
            delta_rmse_vs_baseline=float(delta_rmse),
            delta_r2_vs_baseline=float(delta_r2),
            prediction_delta_vs_baseline=float(pred_delta),
            coefficients=coeff_map,
            intervention_effects=interventions,
        )

    def _intervention_effects(
        self,
        heldout_rows: List[Dict[str, object]],
        features: List[str],
        coeff: np.ndarray,
        baseline_preds: np.ndarray,
    ) -> Dict[str, InterventionEffect]:
        effects: Dict[str, InterventionEffect] = {}
        normal_preds = self._corrected_predictions(heldout_rows, features, coeff)
        normal_actual = np.asarray([row["actual"] for row in heldout_rows], dtype=float)
        normal_mae = self._mae_matrix(normal_actual, normal_preds)

        for dim in DIMENSIONS:
            intervened_rows = [self._intervene_row(row, dim) for row in heldout_rows]
            intervened_preds = self._corrected_predictions(intervened_rows, features, coeff)
            intervened_actual = np.asarray([row["actual"] for row in intervened_rows], dtype=float)
            intervened_mae = self._mae_matrix(intervened_actual, intervened_preds)

            pred_delta = float(np.mean(np.abs(intervened_preds - normal_preds)))
            mae_delta = float(intervened_mae - normal_mae)

            if dim not in features:
                # Keep causal reading strict: if the model does not consume the feature,
                # report theoretical zero influence (numerical jitter suppressed).
                pred_delta = 0.0
                mae_delta = 0.0

            effects[dim] = InterventionEffect(
                dimension=dim,
                prediction_delta=pred_delta,
                mae_delta=mae_delta,
            )

        return effects

    def _intervene_row(self, row: Dict[str, object], dimension: str) -> Dict[str, object]:
        updated = dict(row)
        if dimension == "motivation":
            updated["motivation"] = float(min(1.0, float(row["motivation"]) + 0.25))
        elif dimension == "goals":
            updated["goals"] = float(min(1.0, float(row["goals"]) + 0.25))
        elif dimension == "behavior":
            updated["behavior"] = float(min(1.0, float(row["behavior"]) + 0.10))
        return updated

    @staticmethod
    def _design_matrix(rows: List[Dict[str, object]], features: List[str]) -> np.ndarray:
        cols = [np.ones(len(rows), dtype=float)]
        for feature in features:
            cols.append(np.asarray([float(row[feature]) for row in rows], dtype=float))
        return np.column_stack(cols)

    @staticmethod
    def _residual_target(rows: List[Dict[str, object]]) -> np.ndarray:
        vals = []
        for row in rows:
            actual = np.asarray(row["actual"], dtype=float)
            base_pred = np.asarray(row["base_pred"], dtype=float)
            vals.append(float(np.mean(actual - base_pred)))
        return np.asarray(vals, dtype=float)

    @staticmethod
    def _corrected_predictions(rows: List[Dict[str, object]], features: List[str], coeff: np.ndarray) -> np.ndarray:
        X = ControlledRedesignAnalyzer._design_matrix(rows, features)
        correction = X @ coeff
        base = np.asarray([row["base_pred"] for row in rows], dtype=float)
        return base + correction.reshape(-1, 1)

    @staticmethod
    def _mae_matrix(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.mean(np.abs(actual - predicted))) if actual.size else 0.0

    @staticmethod
    def _rmse_matrix(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.sqrt(np.mean((actual - predicted) ** 2))) if actual.size else 0.0

    @staticmethod
    def _r2_scalar(actual: np.ndarray, predicted: np.ndarray) -> float:
        if actual.size == 0:
            return 0.0
        ss_res = float(np.sum((actual - predicted) ** 2))
        ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        return 1.0 - (ss_res / ss_tot)

    @staticmethod
    def _motivation_signal(category: str) -> float:
        if category in {"high_motivation", "project_completion"}:
            return 1.0
        if category in {"low_motivation", "low_skill_practice"}:
            return 0.0
        return 0.5

    @staticmethod
    def _goals_signal(state: Dict[str, int], action: str) -> float:
        mean_skill = mean([float(state.get(skill, 0.0)) for skill in SKILLS]) / 100.0
        return float(mean_skill * ACTION_SIGNAL.get(action, 0.5))

    @staticmethod
    def _behavior_signal(action: str) -> float:
        return float(ACTION_SIGNAL.get(action, 0.5))

    @staticmethod
    def _simulation_invariance_check(rows: List[Dict[str, object]]) -> bool:
        # Check deterministic base predictions are already present and finite.
        for row in rows:
            base = np.asarray(row["base_pred"], dtype=float)
            if base.shape != (len(SKILLS),):
                return False
            if not np.isfinite(base).all():
                return False
        return True


class ResearchPhase17_9:
    def __init__(self, seeds: List[int] | None = None):
        self.seeds = seeds or list(SEEDS)

    def run(self) -> AnalysisResult:
        analysis = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            seed_results={},
            aggregate_summary=None,
        )

        print("\n" + "=" * 120)
        print("Phase 17.9: Controlled Redesign Experiment")
        print("=" * 120)

        for seed in self.seeds:
            result = ControlledRedesignAnalyzer(seed=seed).analyze_seed()
            analysis.seed_results[seed] = result

            base = result.model_results["baseline"]
            mg = result.model_results["motivation_goals"]
            mgb = result.model_results["all_three"]

            print(f"\nSeed {seed}: runtime={result.runtime_seconds:.3f}s")
            print(
                f"  invariants: benchmark={result.benchmark_invariant} "
                f"target={result.target_invariant} "
                f"simulation={result.simulation_semantics_invariant}"
            )
            print(
                f"  metrics: baseline_mae={base.heldout_mae:.4f} "
                f"MG_mae={mg.heldout_mae:.4f} "
                f"MGB_mae={mgb.heldout_mae:.4f}"
            )
            print(
                f"  deltas: MG_dMAE={mg.delta_mae_vs_baseline:.4f} "
                f"MGB_dMAE={mgb.delta_mae_vs_baseline:.4f} "
                f"MGB-MG={mg.heldout_mae - mgb.heldout_mae:.4f}"
            )
            print(
                f"  gates: causal_activation={result.gate1_causal_activation} "
                f"objective_improvement={result.gate2_objective_improvement} "
                f"MG>singletons={result.gate4_incremental_mg_over_singletons} "
                f"MGB>MG={result.gate4_incremental_mgb_over_mg}"
            )

        analysis.aggregate_summary = self._aggregate(analysis.seed_results)
        self._save_results(analysis)
        return analysis

    def _aggregate(self, seed_results: Dict[int, SeedResult]) -> AggregateSummary:
        total_runtime = float(sum(sr.runtime_seconds for sr in seed_results.values()))
        per_seed_runtime = {str(seed): float(sr.runtime_seconds) for seed, sr in seed_results.items()}

        mean_metrics_by_model: Dict[str, Dict[str, float]] = {}
        model_names = list(MODEL_FEATURES.keys())
        for name in model_names:
            maes = [seed_results[s].model_results[name].heldout_mae for s in seed_results]
            rmses = [seed_results[s].model_results[name].heldout_rmse for s in seed_results]
            r2s = [seed_results[s].model_results[name].heldout_r2 for s in seed_results]
            d_mae = [seed_results[s].model_results[name].delta_mae_vs_baseline for s in seed_results]
            d_rmse = [seed_results[s].model_results[name].delta_rmse_vs_baseline for s in seed_results]
            d_r2 = [seed_results[s].model_results[name].delta_r2_vs_baseline for s in seed_results]
            mean_metrics_by_model[name] = {
                "mean_mae": float(mean(maes)),
                "mean_rmse": float(mean(rmses)),
                "mean_r2": float(mean(r2s)),
                "mean_delta_mae": float(mean(d_mae)),
                "mean_delta_rmse": float(mean(d_rmse)),
                "mean_delta_r2": float(mean(d_r2)),
            }

        consistency_counts = {
            "objective_improvement_mg": int(sum(seed_results[s].model_results["motivation_goals"].heldout_mae < seed_results[s].model_results["baseline"].heldout_mae for s in seed_results)),
            "objective_improvement_mgb": int(sum(seed_results[s].model_results["all_three"].heldout_mae < seed_results[s].model_results["baseline"].heldout_mae for s in seed_results)),
            "incremental_mgb_over_mg": int(sum(seed_results[s].model_results["all_three"].heldout_mae < seed_results[s].model_results["motivation_goals"].heldout_mae for s in seed_results)),
            "causal_activation_pass": int(sum(seed_results[s].gate1_causal_activation for s in seed_results)),
        }

        gate3_reproducibility = (
            consistency_counts["objective_improvement_mg"] == len(seed_results)
            and consistency_counts["objective_improvement_mgb"] == len(seed_results)
        )

        return AggregateSummary(
            total_runtime_seconds=total_runtime,
            per_seed_runtime_seconds=per_seed_runtime,
            mean_metrics_by_model=mean_metrics_by_model,
            gate3_reproducibility=gate3_reproducibility,
            consistency_counts=consistency_counts,
        )

    @staticmethod
    def _save_results(analysis: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / "research_17_9_controlled_redesign.json"
        with open(output_path, "w") as handle:
            json.dump(analysis.to_dict(), handle, indent=2)
        print(f"\n[OK] Results saved to {output_path}")


if __name__ == "__main__":
    ResearchPhase17_9().run()
