"""
17.10C: Behavior Discrepancy Diagnostic

This is a diagnostic experiment, not a production redesign. The purpose is to
explain why Behavior appears useful in the 17.9 observational correction model
but fails to provide consistent incremental improvement when routed through the
actual 17.10B compatibility boundary.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator

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
BEHAVIOR_VARIANTS = ["original", "normalized", "binary", "action_frequency", "state_transition_based"]
MODEL_CANDIDATES = ["Legacy", "M", "G", "B", "MG", "MB", "GB", "MGB"]


@dataclass
class ModelMetrics:
    model: str
    features: List[str]
    train_mae: float
    heldout_mae: float
    train_rmse: float
    heldout_rmse: float
    train_r2: float
    heldout_r2: float
    coefficients: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeedDiagnosticResult:
    seed: int
    legacy_mae: float
    model_metrics: Dict[str, ModelMetrics]
    mg_vs_mgb: Dict[str, float]
    marginal_contribution: Dict[str, float]
    by_category: Dict[str, Dict[str, float]]
    by_action: Dict[str, Dict[str, float]]
    by_skill: Dict[str, Dict[str, float]]
    behavior_redundancy: Dict[str, float]
    behavior_mapping_sensitivity: Dict[str, Dict[str, float]]
    mapping_semantics_comparison: Dict[str, Any]
    diagnosis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "legacy_mae": self.legacy_mae,
            "model_metrics": {name: metrics.to_dict() for name, metrics in self.model_metrics.items()},
            "mg_vs_mgb": self.mg_vs_mgb,
            "marginal_contribution": self.marginal_contribution,
            "by_category": self.by_category,
            "by_action": self.by_action,
            "by_skill": self.by_skill,
            "behavior_redundancy": self.behavior_redundancy,
            "behavior_mapping_sensitivity": self.behavior_mapping_sensitivity,
            "mapping_semantics_comparison": self.mapping_semantics_comparison,
            "diagnosis": self.diagnosis,
        }


class BehaviorDiagnosticExperiment:
    def __init__(self, seed: int):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedDiagnosticResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        train_rows = self._build_rows(dataset.training_experiences)
        heldout_rows = self._build_rows(dataset.held_out_experiences)

        model_metrics = {
            "Legacy": self._fit_and_score_model(train_rows, heldout_rows, [], "Legacy"),
            "M": self._fit_and_score_model(train_rows, heldout_rows, ["motivation"], "M"),
            "G": self._fit_and_score_model(train_rows, heldout_rows, ["goals"], "G"),
            "B": self._fit_and_score_model(train_rows, heldout_rows, ["behavior"], "B"),
            "MG": self._fit_and_score_model(train_rows, heldout_rows, ["motivation", "goals"], "MG"),
            "MB": self._fit_and_score_model(train_rows, heldout_rows, ["motivation", "behavior"], "MB"),
            "GB": self._fit_and_score_model(train_rows, heldout_rows, ["goals", "behavior"], "GB"),
            "MGB": self._fit_and_score_model(train_rows, heldout_rows, ["motivation", "goals", "behavior"], "MGB"),
        }

        mg_vs_mgb = {
            "mae_mg": model_metrics["MG"].heldout_mae,
            "mae_mgb": model_metrics["MGB"].heldout_mae,
            "mgb_minus_mg": model_metrics["MGB"].heldout_mae - model_metrics["MG"].heldout_mae,
            "legacy_mae": model_metrics["Legacy"].heldout_mae,
            "mgb_vs_legacy_delta": model_metrics["Legacy"].heldout_mae - model_metrics["MGB"].heldout_mae,
        }

        marginal_contribution = {
            "mg_vs_mgb_delta": mg_vs_mgb["mgb_minus_mg"],
            "classification_pass": mg_vs_mgb["mgb_minus_mg"] < 0.0,
            "behavior_helpful": mg_vs_mgb["mgb_minus_mg"] < 0.0,
        }

        by_category = self._summarize_by_category(train_rows, heldout_rows)
        by_action = self._summarize_by_action(train_rows, heldout_rows)
        by_skill = self._summarize_by_skill(train_rows, heldout_rows)
        behavior_redundancy = self._behavior_redundancy(train_rows, heldout_rows)
        behavior_mapping_sensitivity = self._behavior_mapping_sensitivity(train_rows, heldout_rows)
        mapping_semantics_comparison = self._compare_mapping_semantics(model_metrics)
        diagnosis = self._diagnose_seed(model_metrics, behavior_redundancy, behavior_mapping_sensitivity, mg_vs_mgb, by_action, by_category, by_skill, mapping_semantics_comparison)

        return SeedDiagnosticResult(
            seed=self.seed,
            legacy_mae=model_metrics["Legacy"].heldout_mae,
            model_metrics=model_metrics,
            mg_vs_mgb=mg_vs_mgb,
            marginal_contribution=marginal_contribution,
            by_category=by_category,
            by_action=by_action,
            by_skill=by_skill,
            behavior_redundancy=behavior_redundancy,
            behavior_mapping_sensitivity=behavior_mapping_sensitivity,
            mapping_semantics_comparison=mapping_semantics_comparison,
            diagnosis=diagnosis,
        )

    def _build_rows(self, experiences) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for exp in experiences:
            state = {str(k): int(v) for k, v in exp.initial_state.items()}
            action = str(exp.selected_action)
            actual = np.asarray([float(exp.actual_future_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)
            base_pred = np.asarray([float(exp.predicted_future_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)
            row = {
                "category": str(exp.category),
                "action": action,
                "state": state,
                "actual": actual,
                "base_pred": base_pred,
                "motivation": self._motivation_signal(str(exp.category)),
                "goals": self._goals_signal(state, action),
                "behavior": self._behavior_signal(action),
            }
            rows.append(row)
        return rows

    @staticmethod
    def _motivation_signal(category: str) -> float:
        if category in {"high_motivation", "project_completion"}:
            return 1.0
        if category in {"low_motivation", "low_skill_practice"}:
            return 0.0
        return 0.5

    @staticmethod
    def _goals_signal(state: Dict[str, int], action: str) -> float:
        return float(mean([float(state.get(skill, 0.0)) for skill in SKILLS]) / 100.0) * ACTION_SIGNAL.get(action, 0.5)

    @staticmethod
    def _behavior_signal(action: str) -> float:
        return float(ACTION_SIGNAL.get(action, 0.5))

    @staticmethod
    def _apply_behavior_variant(row: Dict[str, object], variant: str) -> float:
        base = float(row["behavior"])
        if variant == "normalized":
            return base / 1.0
        if variant == "binary":
            return 1.0 if base >= 0.8 else 0.0
        if variant == "action_frequency":
            return min(1.0, base * 1.2)
        if variant == "state_transition_based":
            state_mean = float(mean([float(v) for v in row["state"].values()])) / 100.0
            return max(0.0, min(1.0, base * 0.7 + state_mean * 0.3))
        return base

    def _fit_and_score_model(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
        features: List[str],
        model_name: str,
    ) -> ModelMetrics:
        X_train = self._design_matrix(train_rows, features)
        y_train = self._residual_target(train_rows)
        coeff, *_ = np.linalg.lstsq(X_train, y_train, rcond=None)

        train_pred = self._corrected_predictions(train_rows, features, coeff)
        heldout_pred = self._corrected_predictions(heldout_rows, features, coeff)
        train_actual = np.asarray([row["actual"] for row in train_rows], dtype=float)
        heldout_actual = np.asarray([row["actual"] for row in heldout_rows], dtype=float)

        coefficients = {"beta_0": float(coeff[0])}
        for idx, value in enumerate(coeff[1:], start=1):
            coefficients[f"beta_{idx}"] = float(value)

        return ModelMetrics(
            model=model_name,
            features=list(features),
            train_mae=float(self._mae_matrix(train_actual, train_pred)),
            heldout_mae=float(self._mae_matrix(heldout_actual, heldout_pred)),
            train_rmse=float(self._rmse_matrix(train_actual, train_pred)),
            heldout_rmse=float(self._rmse_matrix(heldout_actual, heldout_pred)),
            train_r2=float(self._r2_scalar(train_actual.mean(axis=1), train_pred.mean(axis=1))),
            heldout_r2=float(self._r2_scalar(heldout_actual.mean(axis=1), heldout_pred.mean(axis=1))),
            coefficients=coefficients,
        )

    @staticmethod
    def _design_matrix(rows: List[Dict[str, object]], features: List[str]) -> np.ndarray:
        cols = [np.ones(len(rows), dtype=float)]
        for feature in features:
            cols.append(np.asarray([float(row[feature]) for row in rows], dtype=float))
        return np.column_stack(cols)

    @staticmethod
    def _residual_target(rows: List[Dict[str, object]]) -> np.ndarray:
        residuals: List[float] = []
        for row in rows:
            residual = np.asarray(row["actual"], dtype=float) - np.asarray(row["base_pred"], dtype=float)
            residuals.append(float(np.mean(residual)))
        return np.asarray(residuals, dtype=float)

    @staticmethod
    def _corrected_predictions(rows: List[Dict[str, object]], features: List[str], coeff: np.ndarray) -> np.ndarray:
        X = BehaviorDiagnosticExperiment._design_matrix(rows, features)
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

    def _summarize_by_category(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> Dict[str, Dict[str, float]]:
        summaries: Dict[str, Dict[str, float]] = {}
        for rows in [train_rows, heldout_rows]:
            for row in rows:
                category = str(row["category"])
                if category not in summaries:
                    summaries[category] = {"count": 0.0, "mg_mae": 0.0, "mgb_mae": 0.0, "delta": 0.0}
                summaries[category]["count"] += 1.0
        for category, stats in summaries.items():
            category_rows = [row for row in train_rows + heldout_rows if str(row["category"]) == category]
            mg_mae = self._mae_for_feature_set(category_rows, ["motivation", "goals"])
            mgb_mae = self._mae_for_feature_set(category_rows, ["motivation", "goals", "behavior"])
            stats["mg_mae"] = mg_mae
            stats["mgb_mae"] = mgb_mae
            stats["delta"] = mgb_mae - mg_mae
        return summaries

    def _summarize_by_action(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> Dict[str, Dict[str, float]]:
        summaries: Dict[str, Dict[str, float]] = {}
        all_rows = train_rows + heldout_rows
        for action in sorted({str(row["action"]) for row in all_rows}):
            action_rows = [row for row in all_rows if str(row["action"]) == action]
            mg_mae = self._mae_for_feature_set(action_rows, ["motivation", "goals"])
            mgb_mae = self._mae_for_feature_set(action_rows, ["motivation", "goals", "behavior"])
            summaries[action] = {
                "count": float(len(action_rows)),
                "mg_mae": mg_mae,
                "mgb_mae": mgb_mae,
                "delta": mgb_mae - mg_mae,
            }
        return summaries

    def _summarize_by_skill(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> Dict[str, Dict[str, float]]:
        summaries: Dict[str, Dict[str, float]] = {}
        for idx, skill in enumerate(SKILLS):
            skill_rows = train_rows + heldout_rows
            mg_mae = self._mae_for_skill(skill_rows, idx, ["motivation", "goals"])
            mgb_mae = self._mae_for_skill(skill_rows, idx, ["motivation", "goals", "behavior"])
            summaries[skill] = {
                "mg_mae": mg_mae,
                "mgb_mae": mgb_mae,
                "delta": mgb_mae - mg_mae,
            }
        return summaries

    def _behavior_redundancy(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> Dict[str, float]:
        values = {
            "motivation": np.asarray([float(row["motivation"]) for row in train_rows + heldout_rows], dtype=float),
            "goals": np.asarray([float(row["goals"]) for row in train_rows + heldout_rows], dtype=float),
            "behavior": np.asarray([float(row["behavior"]) for row in train_rows + heldout_rows], dtype=float),
        }
        corr = {}
        for left_name, left in values.items():
            for right_name, right in values.items():
                if left_name >= right_name:
                    continue
                corr[f"{left_name}_vs_{right_name}"] = float(np.corrcoef(left, right)[0, 1])
        return corr

    def _behavior_mapping_sensitivity(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> Dict[str, Dict[str, float]]:
        sensitivity: Dict[str, Dict[str, float]] = {}
        for variant in BEHAVIOR_VARIANTS:
            variant_rows_train = []
            variant_rows_held = []
            for row in train_rows:
                row_copy = dict(row)
                row_copy["behavior"] = self._apply_behavior_variant(row, variant)
                variant_rows_train.append(row_copy)
            for row in heldout_rows:
                row_copy = dict(row)
                row_copy["behavior"] = self._apply_behavior_variant(row, variant)
                variant_rows_held.append(row_copy)

            mg = self._fit_and_score_model(variant_rows_train, variant_rows_held, ["motivation", "goals"], "MG")
            mgb = self._fit_and_score_model(variant_rows_train, variant_rows_held, ["motivation", "goals", "behavior"], "MGB")
            sensitivity[variant] = {
                "mg_mae": mg.heldout_mae,
                "mgb_mae": mgb.heldout_mae,
                "mgb_minus_mg": mgb.heldout_mae - mg.heldout_mae,
            }
        return sensitivity

    def _compare_mapping_semantics(self, model_metrics: Dict[str, ModelMetrics]) -> Dict[str, Any]:
        mg = model_metrics["MG"].coefficients
        mgb = model_metrics["MGB"].coefficients
        behavior_coef = float(mgb.get("beta_3", 0.0)) if "beta_3" in mgb else 0.0
        legacy_like = abs(behavior_coef) < 1e-9 or abs(behavior_coef - float(mg.get("beta_2", 0.0))) < 1e-6
        return {
            "mg_coefficients": mg,
            "mgb_coefficients": mgb,
            "behavior_sign": np.sign(behavior_coef),
            "behavior_coefficient": behavior_coef,
            "equivalent_to_17_9": bool(legacy_like),
            "same_mapping_family": bool(abs(behavior_coef) < 1e2 and len(mgb) >= 4),
            "mapping_equivalence_pass": bool(legacy_like),
            "model_difference_note": "17.10B differs from 17.9 when the behavior coefficient changes sign or magnitude, meaning the integrated semantic mapping is not equivalent.",
        }

    def _diagnose_seed(
        self,
        model_metrics: Dict[str, ModelMetrics],
        behavior_redundancy: Dict[str, float],
        behavior_mapping_sensitivity: Dict[str, Dict[str, float]],
        mg_vs_mgb: Dict[str, float],
        by_action: Dict[str, Dict[str, float]],
        by_category: Dict[str, Dict[str, float]],
        by_skill: Dict[str, Dict[str, float]],
        mapping_semantics_comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        mg_better = mg_vs_mgb["mgb_minus_mg"] > 0.0
        redundant = max(abs(v) for v in behavior_redundancy.values()) > 0.9
        sensitivity_flip = any(v["mgb_minus_mg"] > 0.0 for v in behavior_mapping_sensitivity.values())
        action_benefit = sum(1 for stats in by_action.values() if stats["delta"] < 0.0)
        category_benefit = sum(1 for stats in by_category.values() if stats["delta"] < 0.0)
        skill_benefit = sum(1 for stats in by_skill.values() if stats["delta"] < 0.0)
        mapping_equivalent = mapping_semantics_comparison.get("mapping_equivalence_pass", False)

        checks = {
            "redundancy_analysis": {"pass": bool(not redundant), "detail": "B is redundant" if redundant else "B is not strongly redundant with M/G"},
            "marginal_contribution": {"pass": bool(mg_vs_mgb["mgb_minus_mg"] < 0.0), "detail": "B improves MG" if mg_vs_mgb["mgb_minus_mg"] < 0.0 else "B fails to improve MG"},
            "action_utility": {"pass": bool(action_benefit > 0), "detail": f"{action_benefit} actions benefit from B"},
            "category_utility": {"pass": bool(category_benefit > 0), "detail": f"{category_benefit} categories benefit from B"},
            "skill_utility": {"pass": bool(skill_benefit > 0), "detail": f"{skill_benefit} skills benefit from B"},
            "mapping_semantics": {"pass": bool(mapping_equivalent), "detail": "17.10B matches 17.9 semantics" if mapping_equivalent else "17.10B mapping diverges from 17.9"},
        }

        if redundant:
            cause = "A. Redundant"
        elif mapping_equivalent is False and sensitivity_flip:
            cause = "C. Useful but incorrectly mapped"
        elif mg_better:
            cause = "D. Harmful / non-useful"
        elif action_benefit > 0 or category_benefit > 0 or skill_benefit > 0:
            cause = "B. Contextually useful"
        else:
            cause = "E. Evidence insufficient"

        return {
            "behavior_is_redundant": redundant,
            "overall_mgb_is_worse_than_mg": mg_better is False,
            "sensitivity_changes_direction": sensitivity_flip,
            "action_benefit_count": action_benefit,
            "category_benefit_count": category_benefit,
            "skill_benefit_count": skill_benefit,
            "mapping_equivalence_pass": mapping_equivalent,
            "required_checks": checks,
            "final_causal_classification": cause,
            "final_explanation": (
                "Behavior is not a robust global addition in the compatibility path because the marginal contribution is not stable across seeds, the action/category/skill utility is sparse, and the coefficient mapping is not equivalent to the 17.9 design."
                if cause == "C. Useful but incorrectly mapped"
                else (
                    "Behavior is largely redundant or non-useful under the actual compatibility boundary, so MG remains the more stable integrated candidate."
                    if cause in {"A. Redundant", "D. Harmful / non-useful"}
                    else "Behavior has isolated contextual benefit but not sufficient, stable evidence to justify production activation."
                )
            ),
            "likely_class": "redundant" if redundant else ("mapping_problem" if sensitivity_flip else "useful_but_contextual"),
        }

    def _mae_for_feature_set(self, rows: List[Dict[str, object]], features: List[str]) -> float:
        if not rows:
            return 0.0
        X = self._design_matrix(rows, features)
        y = self._residual_target(rows)
        coeff, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = self._corrected_predictions(rows, features, coeff)
        actual = np.asarray([row["actual"] for row in rows], dtype=float)
        return float(self._mae_matrix(actual, pred))

    def _mae_for_skill(self, rows: List[Dict[str, object]], skill_index: int, features: List[str]) -> float:
        if not rows:
            return 0.0
        X = self._design_matrix(rows, features)
        y = self._residual_target(rows)
        coeff, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = self._corrected_predictions(rows, features, coeff)
        actual = np.asarray([row["actual"][skill_index] for row in rows], dtype=float)
        return float(self._mae_matrix(actual, pred[:, skill_index]))


def run_behavior_diagnostics(
    seeds: Optional[Sequence[int]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    selected = list(seeds or SEEDS)
    results = {
        "analysis_date": datetime.now().isoformat(),
        "total_seeds": len(selected),
        "seed_results": {},
    }

    for seed in selected:
        result = BehaviorDiagnosticExperiment(seed=seed).analyze_seed()
        results["seed_results"][str(seed)] = result.to_dict()

    mg_values = [results["seed_results"][str(seed)]["mg_vs_mgb"]["mae_mg"] for seed in [str(s) for s in selected]]
    mgb_values = [results["seed_results"][str(seed)]["mg_vs_mgb"]["mae_mgb"] for seed in [str(s) for s in selected]]
    diff_values = [results["seed_results"][str(seed)]["mg_vs_mgb"]["mgb_minus_mg"] for seed in [str(s) for s in selected]]

    aggregate = {
        "mean_mg_mae": float(mean(mg_values)),
        "mean_mgb_mae": float(mean(mgb_values)),
        "mean_mgb_minus_mg": float(mean(diff_values)),
        "sensitivity_summary": {
            variant: float(
                mean([
                    results["seed_results"][str(seed)]["behavior_mapping_sensitivity"][variant]["mgb_minus_mg"]
                    for seed in [str(s) for s in selected]
                ])
            )
            for variant in BEHAVIOR_VARIANTS
        },
    }
    results["aggregate_summary"] = aggregate

    output_file = Path(output_path) if output_path is not None else Path("backend/experiments/results/research_17_10_c_behavior_diagnostics.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    return results


if __name__ == "__main__":
    run_behavior_diagnostics()
