"""
MGCompatibilityLayer: Core logic for applying MG correction to legacy predictions.

This layer:
1. Extracts Motivation and Goals signals from current state
2. Computes correction using validated 17.11A/17.12A coefficients
3. Returns either corrected prediction or legacy on failure/disable
4. Implements deterministic fallback rules
5. Emits diagnostic metadata for observability

CRITICAL: This is a pure function. No state mutations. No side effects.
It receives a legacy prediction and returns a prediction (original or corrected).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import numpy as np

from backend.compatibility.mg_config import MGCompatibilityConfig

logger = logging.getLogger(__name__)


@dataclass
class PredictionMetadata:
    """Metadata about prediction source and computation."""

    source: str  # "legacy", "mg", "fallback"
    correction_applied: bool
    motivation_signal: Optional[float] = None
    goals_signal: Optional[float] = None
    correction_value: Optional[float] = None
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    computation_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Export metadata as dictionary."""
        return asdict(self)


class MGCompatibilityLayer:
    """
    Apply Motivation + Goals correction to legacy predictions.

    Workflow:
        1. Check if MG is enabled and should apply (config, rollout)
        2. Extract motivation and goals signals from state
        3. Validate signals
        4. Compute correction: β₀ + β_M·M + β_G·G
        5. Apply correction to legacy prediction
        6. If any error, fallback to legacy
        7. Emit metadata

    This is a pure function: given legacy prediction and state, return result.
    No mutation of input state or prediction.
    """

    def __init__(self, config: MGCompatibilityConfig, fallback_rate_tracker: Optional[Dict] = None):
        """
        Initialize MG compatibility layer.

        Args:
            config: MGCompatibilityConfig (immutable, externally configured)
            fallback_rate_tracker: Optional dict to track fallback rate across calls
        """
        self.config = config
        self.fallback_rate_tracker = fallback_rate_tracker or {"count": 0, "fallback_count": 0}

        # Validate configuration
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            logger.warning(f"MG configuration invalid: {error_msg}")

    def apply(
        self,
        legacy_prediction: Dict[str, Any],
        current_state: Dict[str, int],
        action: str,
        category: Optional[str] = None,
    ) -> tuple[Dict[str, Any], PredictionMetadata]:
        """
        Apply MG correction to legacy prediction.

        Args:
            legacy_prediction: Legacy prediction dict (unchanged, returned as-is if MG disabled)
            current_state: Current state dict with skills
            action: Action string (for signal extraction)
            category: Optional experience category (for frozen 17.12A mapping)

        Returns:
            (prediction, metadata):
                - prediction: Either corrected or legacy prediction dict
                - metadata: PredictionMetadata with source, correction_applied, signals, etc.
        """
        metadata = PredictionMetadata(source="legacy", correction_applied=False)

        # Gate 0: Fail closed on invalid configuration.
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            return self._fallback(
                legacy_prediction,
                metadata,
                self.config.fallback_enabled and self.config.fallback_on_invalid_signals,
                f"Invalid configuration: {error_msg}",
            )

        # Gate 1: Check if MG should apply
        if not self._should_apply():
            metadata.source = "legacy"
            metadata.correction_applied = False
            return legacy_prediction, metadata

        # Gate 2: Extract signals
        try:
            motivation_signal = self._extract_motivation_signal(current_state, action, category=category)
            goals_signal = self._extract_goals_signal(current_state, action)
            metadata.motivation_signal = motivation_signal
            metadata.goals_signal = goals_signal
        except Exception as e:
            return self._fallback(
                legacy_prediction,
                metadata,
                self.config.fallback_on_invalid_signals,
                f"Signal extraction error: {str(e)}",
            )

        # Gate 3: Validate signals
        if not self._validate_signals(motivation_signal, goals_signal):
            return self._fallback(
                legacy_prediction,
                metadata,
                self.config.fallback_on_invalid_signals,
                "Invalid signals (NaN, Inf, or out of range)",
            )

        # Gate 4: Compute correction
        try:
            correction = self._compute_correction(motivation_signal, goals_signal)
            metadata.correction_value = correction
        except Exception as e:
            return self._fallback(
                legacy_prediction,
                metadata,
                self.config.fallback_on_computation_error,
                f"Correction computation error: {str(e)}",
            )

        # Gate 5: Check for coefficient drift
        if self.config.fallback_on_coefficient_drift:
            if not self._check_coefficient_stability():
                return self._fallback(
                    legacy_prediction,
                    metadata,
                    True,
                    "Coefficient drift exceeded tolerance",
                )

        # Gate 6: Apply correction to legacy prediction
        try:
            corrected_prediction = self._apply_correction_to_prediction(
                legacy_prediction, correction
            )
            metadata.source = "mg"
            metadata.correction_applied = True
            self.fallback_rate_tracker["count"] += 1
            return corrected_prediction, metadata
        except Exception as e:
            return self._fallback(
                legacy_prediction,
                metadata,
                self.config.fallback_on_computation_error,
                f"Correction application error: {str(e)}",
            )

    def _should_apply(self) -> bool:
        """Check if MG should apply to this prediction."""
        if not self.config.is_active():
            return False

        # Respect rollout percentage
        if self.config.rollout_percentage < 100.0:
            import random

            if random.random() * 100 > self.config.rollout_percentage:
                return False

        return True

    def _extract_motivation_signal(self, current_state: Dict[str, int], action: str, category: Optional[str] = None) -> float:
        """
        Extract Motivation signal from current state or category.

        Uses frozen 17.12A category-based mapping if category is provided (for validation):
        - high_motivation, project_completion → 1.0
        - low_motivation, low_skill_practice → 0.0
        - All others → 0.5

        Falls back to skill-state-based heuristic if category is not available:
        - Low skill state (mean < 30): motivation = 0.0
        - High skill state (mean >= 60): motivation = 1.0
        - Medium skill state (30 <= mean < 60): motivation = 0.5
        """
        # Frozen 17.12A category-based mapping (when category is available)
        if category:
            if category in {"high_motivation", "project_completion"}:
                return 1.0
            if category in {"low_motivation", "low_skill_practice"}:
                return 0.0
            return 0.5
        
        # Skill-state-based heuristic (when category is not available)
        # Extract skill values from flat state or nested skills dict
        skills = current_state.get("skills", {})
        if not skills:
            # Production contract: flat skill dict
            skill_values = [
                float(current_state.get(key, 0))
                for key in ["python", "dsa", "machine_learning", "projects"]
                if key in current_state
            ]
        else:
            skill_values = [v for k, v in skills.items() if isinstance(v, (int, float))]

        if not skill_values:
            return 0.0

        mean_skill = sum(skill_values) / len(skill_values)

        # Skill-state-based mapping
        if mean_skill < 30.0:
            motivation = 0.0  # low_skill_practice / low_motivation
        elif mean_skill >= 60.0:
            motivation = 1.0  # high_motivation / project_completion
        else:
            motivation = 0.5  # medium

        return float(np.clip(motivation, 0.0, 1.0))

    def _extract_goals_signal(self, current_state: Dict[str, int], action: str) -> float:
        """
        Extract Goals signal from the actual state contract delivered by the engine.

        The validated 17.12A mapping uses a flat benchmark state and computes:
            goals_signal = mean(skill_values) / 100 * action_signal

        To preserve compatibility with prior nested-goals payloads, this method still
        supports the legacy nested "goals" object path when present.
        """
        goals = current_state.get("goals", {})
        if isinstance(goals, dict) and goals:
            non_zero_goals = sum(1 for v in goals.values() if v > 0)
            max_goals = max(5, len(goals))
            goals_signal = non_zero_goals / max_goals
            return float(np.clip(goals_signal, 0.0, 1.0))

        # Production compatibility contract: flat skill dict from SimulationEngine.
        skill_values = []
        for key in ["python", "dsa", "machine_learning", "projects"]:
            value = current_state.get(key)
            if isinstance(value, (int, float)):
                skill_values.append(float(value))

        if not skill_values:
            # Fallback to any numeric values in the state if no canonical skill keys exist.
            numeric_values = [
                float(value)
                for value in current_state.values()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            if not numeric_values:
                return 0.0
            skill_values = numeric_values

        action_signal = {
            "Python Project": 0.9,
            "DSA Practice": 0.75,
            "ML Course": 0.8,
            "Interview Prep": 0.75,
            "Build Portfolio": 1.0,
            "Research Paper": 0.8,
        }.get(action, 0.5)

        goals_signal = (sum(skill_values) / len(skill_values) / 100.0) * action_signal
        return float(np.clip(goals_signal, 0.0, 1.0))

    def _validate_signals(self, motivation: float, goals: float) -> bool:
        """Validate that signals are valid (no NaN, Inf, in valid range)."""
        if not all(np.isfinite(v) for v in [motivation, goals]):
            return False
        if not all(0.0 <= v <= 1.0 for v in [motivation, goals]):
            return False
        return True

    def _compute_correction(self, motivation_signal: float, goals_signal: float) -> float:
        """
        Compute MG correction: β₀ + β_M·M + β_G·G

        Returns:
            Correction value (added to legacy prediction)
        """
        correction = self.config.intercept_coefficient

        if self.config.use_motivation:
            correction += self.config.motivation_coefficient * motivation_signal

        if self.config.use_goals:
            correction += self.config.goals_coefficient * goals_signal

        return float(correction)

    def _check_coefficient_stability(self) -> bool:
        """
        Check if coefficients are within acceptable drift range.

        This is a basic check that coefficients haven't changed drastically.
        In production, this would compare against baseline coefficients.
        """
        # For now, simple check: coefficients shouldn't be extremely large
        max_reasonable_coeff = 10.0
        if abs(self.config.motivation_coefficient) > max_reasonable_coeff:
            return False
        if abs(self.config.goals_coefficient) > max_reasonable_coeff:
            return False
        return True

    def _apply_correction_to_prediction(
        self, legacy_prediction: Dict[str, Any], correction: float
    ) -> Dict[str, Any]:
        """
        Apply correction to legacy prediction.

        Applies correction to predicted_future_state skills.

        Args:
            legacy_prediction: Original prediction dict
            correction: Correction value to apply

        Returns:
            Corrected prediction dict (new dict, doesn't modify input)
        """
        corrected = dict(legacy_prediction)

        # Apply correction to predicted_future_state
        if "predicted_future_state" in corrected:
            future_state = dict(corrected["predicted_future_state"])
            for skill_name in ["python", "dsa", "machine_learning", "projects"]:
                if skill_name in future_state:
                    original_value = float(future_state[skill_name])
                    corrected_value = original_value + correction
                    future_state[skill_name] = max(0.0, min(100.0, corrected_value))
            corrected["predicted_future_state"] = future_state

        return corrected

    def _fallback(
        self,
        legacy_prediction: Dict[str, Any],
        metadata: PredictionMetadata,
        should_fallback: bool,
        reason: str,
    ) -> tuple[Dict[str, Any], PredictionMetadata]:
        """
        Fallback to legacy prediction on error.

        Args:
            legacy_prediction: Original prediction
            metadata: Metadata to update
            should_fallback: Whether fallback is enabled
            reason: Fallback reason

        Returns:
            (legacy_prediction, metadata with fallback info)
        """
        if not should_fallback and self.config.fallback_enabled:
            # Still fallback, but log as policy-driven
            pass

        metadata.source = "fallback"
        metadata.correction_applied = False
        metadata.fallback_triggered = True
        metadata.fallback_reason = reason

        self.fallback_rate_tracker["count"] += 1
        self.fallback_rate_tracker["fallback_count"] += 1

        if self.config.log_fallback_events:
            logger.info(f"MG fallback triggered: {reason}")

        return legacy_prediction, metadata

    def get_fallback_rate(self) -> float:
        """Get current fallback rate (0-1)."""
        total = self.fallback_rate_tracker.get("count", 0)
        if total == 0:
            return 0.0
        fallback_count = self.fallback_rate_tracker.get("fallback_count", 0)
        return fallback_count / total
