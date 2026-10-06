from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.models.batch_closed_loop_result import BatchClosedLoopResult
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.experiment_metrics import ExperimentMetrics


class ExperimentMetricsCalculator:
    """Derive experiment-level metrics from a completed BatchClosedLoopResult.

    This calculator is purely derived. It does not mutate the input batch result,
    its contained validation results, or any calibration parameters.
    """

    @classmethod
    def calculate(cls, batch_result: BatchClosedLoopResult) -> ExperimentMetrics:
        base_errors = cls._collect_errors(batch_result, "baseline_future_error")
        calibrated_errors = cls._collect_errors(batch_result, "calibrated_future_error")

        baseline_mae = cls._safe_mean(base_errors)
        calibrated_mae = cls._safe_mean(calibrated_errors)
        absolute_improvement = round(baseline_mae - calibrated_mae, 4)
        improvement_percent = cls._compute_improvement_percent(baseline_mae, absolute_improvement)

        total_steps = len(batch_result.steps)
        calibration_count = total_steps
        evaluation_count = total_steps
        accepted = batch_result.successful_calibrations
        rejected = batch_result.rejected_calibrations

        acceptance_rate = cls._safe_rate(accepted, calibration_count)
        rejection_rate = cls._safe_rate(rejected, calibration_count)
        parameter_drift = cls._compute_parameter_drift(batch_result)
        error_by_action = cls._derive_error_by_action(batch_result)
        error_by_dimension = cls._derive_error_by_dimension(batch_result)
        rolling_baseline_mae = cls._compute_rolling(batch_result, "baseline_future_error")
        rolling_calibrated_mae = cls._compute_rolling(batch_result, "calibrated_future_error")
        rolling_improvement = cls._compute_rolling(batch_result, "error_improvement")
        rolling_improvement_pct = cls._compute_rolling_improvement_pct(rolling_baseline_mae, rolling_calibrated_mae)
        parameter_drift_progression = cls._compute_parameter_drift_progression(batch_result)
        stability_metrics = cls._compute_stability_metrics(batch_result)

        return ExperimentMetrics(
            baseline_mae=baseline_mae,
            calibrated_mae=calibrated_mae,
            absolute_improvement=absolute_improvement,
            improvement_percent=improvement_percent,
            acceptance_rate=acceptance_rate,
            rejection_rate=rejection_rate,
            parameter_drift=parameter_drift,
            error_by_dimension=error_by_dimension,
            error_by_action=error_by_action,
            rolling_baseline_mae=rolling_baseline_mae,
            rolling_calibrated_mae=rolling_calibrated_mae,
            rolling_improvement_pct=rolling_improvement_pct,
            rolling_improvement=rolling_improvement,
            parameter_drift_progression=parameter_drift_progression,
            stability_metrics=stability_metrics,
            calibration_count=calibration_count,
            evaluation_count=evaluation_count,
        )

    @staticmethod
    def _collect_errors(batch_result: BatchClosedLoopResult, field_name: str) -> List[float]:
        errors: List[float] = []
        for step in batch_result.steps:
            error = getattr(step.validation, field_name)
            if error is not None:
                errors.append(float(error))
        return errors

    @staticmethod
    def _safe_mean(values: List[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)

    @staticmethod
    def _compute_improvement_percent(baseline_mae: float, improvement: float) -> float:
        if baseline_mae == 0.0:
            return 0.0
        return round((improvement / baseline_mae) * 100.0, 4)

    @staticmethod
    def _safe_rate(count: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(float(count) / total, 4)

    @classmethod
    def _compute_parameter_drift(cls, batch_result: BatchClosedLoopResult) -> float:
        initial_parameters = cls._initial_parameters_from_metadata(batch_result.metadata)
        if initial_parameters is None:
            return 0.0
        final_parameters = batch_result.final_learning_parameters
        return cls._calibration_parameter_distance(initial_parameters, final_parameters)

    @staticmethod
    def _initial_parameters_from_metadata(metadata: Dict[str, Any]) -> Optional[CalibrationParameters]:
        if not metadata:
            return None

        initial = metadata.get("initial_parameters") or metadata.get("baseline_parameters")
        if isinstance(initial, CalibrationParameters):
            return initial
        if isinstance(initial, dict):
            try:
                return CalibrationParameters(**initial)
            except Exception:
                return None
        return None

    @classmethod
    def _derive_error_by_action(cls, batch_result: BatchClosedLoopResult) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = {}
        for step in batch_result.steps:
            action = getattr(step.validation, "future_selected_action", None)
            error = getattr(step.validation, "calibrated_future_error", None)
            if action is None or error is None:
                continue
            grouped.setdefault(action, []).append(float(error))

        return {action: cls._safe_mean(errors) for action, errors in sorted(grouped.items())}

    @classmethod
    def _derive_error_by_dimension(cls, batch_result: BatchClosedLoopResult) -> Dict[str, float]:
        totals: Dict[str, List[float]] = {}
        for step in batch_result.steps:
            actual = getattr(step.validation, "future_actual_state", None)
            predicted = getattr(step.validation, "calibrated_future_prediction", None)
            if not isinstance(actual, dict) or not isinstance(predicted, dict):
                continue

            for key, actual_value in actual.items():
                if key not in predicted:
                    continue
                try:
                    predicted_value = float(predicted[key])
                    actual_value_f = float(actual_value)
                except (TypeError, ValueError):
                    continue
                totals.setdefault(key, []).append(abs(predicted_value - actual_value_f))

        return {dim: cls._safe_mean(errors) for dim, errors in sorted(totals.items())}

    @classmethod
    def _compute_rolling(cls, batch_result: BatchClosedLoopResult, field_name: str) -> List[float]:
        values: List[float] = []
        rolling: List[float] = []
        for step in batch_result.steps:
            item = getattr(step.validation, field_name, None)
            if item is not None:
                values.append(float(item))
            if values:
                rolling.append(cls._safe_mean(values))
            else:
                rolling.append(0.0)
        return rolling

    @classmethod
    def _compute_rolling_improvement_pct(cls, baseline_mae: List[float], calibrated_mae: List[float]) -> List[float]:
        pct: List[float] = []
        for base, calibrated in zip(baseline_mae, calibrated_mae):
            if base == 0.0:
                pct.append(0.0)
                continue
            improvement = round(base - calibrated, 4)
            pct.append(round((improvement / base) * 100.0, 4))
        return pct

    @classmethod
    def _compute_parameter_drift_progression(cls, batch_result: BatchClosedLoopResult) -> List[float]:
        initial_parameters = cls._initial_parameters_from_metadata(batch_result.metadata)
        if initial_parameters is None:
            return [0.0] * len(batch_result.steps)

        progression: List[float] = []
        current_parameters = initial_parameters
        for step in batch_result.steps:
            calibrated = getattr(step.validation, "calibrated_parameters", None)
            if isinstance(calibrated, CalibrationParameters):
                current_parameters = calibrated
            progression.append(cls._calibration_parameter_distance(initial_parameters, current_parameters))
        return progression

    @classmethod
    def _compute_stability_metrics(cls, batch_result: BatchClosedLoopResult) -> Dict[str, float]:
        baseline_changes = 0
        calibrated_changes = 0
        previous_baseline: Optional[float] = None
        previous_calibrated: Optional[float] = None
        for step in batch_result.steps:
            baseline_error = getattr(step.validation, "baseline_future_error", None)
            calibrated_error = getattr(step.validation, "calibrated_future_error", None)
            if baseline_error is not None and previous_baseline is not None and baseline_error != previous_baseline:
                baseline_changes += 1
            if calibrated_error is not None and previous_calibrated is not None and calibrated_error != previous_calibrated:
                calibrated_changes += 1
            previous_baseline = baseline_error if baseline_error is not None else previous_baseline
            previous_calibrated = calibrated_error if calibrated_error is not None else previous_calibrated

        total = len(batch_result.steps)
        return {
            "baseline_change_fraction": cls._safe_rate(baseline_changes, total),
            "calibrated_change_fraction": cls._safe_rate(calibrated_changes, total),
            "step_count": float(total),
        }

    @staticmethod
    def _calibration_parameter_distance(before: CalibrationParameters, after: CalibrationParameters) -> float:
        total = 0.0
        # expected_state_bias drift
        all_keys = set(before.expected_state_bias) | set(after.expected_state_bias)
        for key in all_keys:
            total += abs(before.expected_state_bias.get(key, 0.0) - after.expected_state_bias.get(key, 0.0))

        total += abs(before.transition_probability_bias - after.transition_probability_bias)
        total += abs(before.risk_bias - after.risk_bias)
        total += abs(before.uncertainty - after.uncertainty)
        total += abs(before.confidence - after.confidence)
        return round(total, 4)
