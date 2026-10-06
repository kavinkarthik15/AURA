"""
MGCompatibilityConfig: Configuration for MG compatibility layer.

This dataclass controls all MG behavior, including activation, coefficients,
fallback rules, and observability. All values are externally configurable,
never hardcoded in the production engine.

CRITICAL INVARIANT:
  enabled=False by default  →  production behavior == pre-17.13 behavior
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MGCompatibilityConfig:
    """
    Configuration for Motivation + Goals compatibility layer.
    
    Immutable (frozen=True) to prevent accidental runtime modifications.
    """

    # Activation control
    enabled: bool = False
    use_motivation: bool = False
    use_goals: bool = False

    # Coefficients (from validated 17.11A/17.12A research)
    # External configuration, never hardcoded in engine
    motivation_coefficient: float = 0.0
    goals_coefficient: float = 0.0
    intercept_coefficient: float = 0.0

    # Fallback configuration
    fallback_enabled: bool = True
    fallback_on_invalid_signals: bool = True
    fallback_on_computation_error: bool = True
    fallback_on_coefficient_drift: bool = True
    coefficient_drift_tolerance: float = 0.1

    # Observability
    emit_diagnostic_metadata: bool = True
    log_fallback_events: bool = True

    # Advanced: Rollout control
    rollout_percentage: float = 0.0  # 0-100: percentage of predictions using MG
    max_fallback_rate_threshold: float = 0.05  # 5% max fallback rate
    max_accuracy_regression_threshold: float = 0.05  # 5% max accuracy regression

    def is_active(self) -> bool:
        """Check if MG is enabled and fully configured."""
        return (
            self.enabled
            and self.use_motivation
            and self.use_goals
            and self.rollout_percentage > 0.0
        )

    def validate(self) -> tuple[bool, str]:
        """
        Validate configuration for consistency and safety.
        
        Returns:
            (is_valid, error_message)
        """
        # Check coefficient drift tolerance is reasonable
        if self.coefficient_drift_tolerance < 0 or self.coefficient_drift_tolerance > 1.0:
            return False, "coefficient_drift_tolerance must be in [0.0, 1.0]"

        # Check rollout percentage is in valid range
        if self.rollout_percentage < 0.0 or self.rollout_percentage > 100.0:
            return False, "rollout_percentage must be in [0.0, 100.0]"

        # Check thresholds are reasonable
        if self.max_fallback_rate_threshold < 0.0 or self.max_fallback_rate_threshold > 1.0:
            return False, "max_fallback_rate_threshold must be in [0.0, 1.0]"

        if (
            self.max_accuracy_regression_threshold < 0.0
            or self.max_accuracy_regression_threshold > 1.0
        ):
            return False, "max_accuracy_regression_threshold must be in [0.0, 1.0]"

        # If MG is disabled, no further validation needed
        if not self.enabled:
            return True, ""

        # If enabled, coefficients must be set (not zero)
        if self.use_motivation and self.motivation_coefficient == 0.0:
            return False, "use_motivation=True but motivation_coefficient is 0.0"

        if self.use_goals and self.goals_coefficient == 0.0:
            return False, "use_goals=True but goals_coefficient is 0.0"

        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "enabled": self.enabled,
            "use_motivation": self.use_motivation,
            "use_goals": self.use_goals,
            "motivation_coefficient": self.motivation_coefficient,
            "goals_coefficient": self.goals_coefficient,
            "intercept_coefficient": self.intercept_coefficient,
            "fallback_enabled": self.fallback_enabled,
            "fallback_on_invalid_signals": self.fallback_on_invalid_signals,
            "fallback_on_computation_error": self.fallback_on_computation_error,
            "fallback_on_coefficient_drift": self.fallback_on_coefficient_drift,
            "coefficient_drift_tolerance": self.coefficient_drift_tolerance,
            "emit_diagnostic_metadata": self.emit_diagnostic_metadata,
            "log_fallback_events": self.log_fallback_events,
            "rollout_percentage": self.rollout_percentage,
            "max_fallback_rate_threshold": self.max_fallback_rate_threshold,
            "max_accuracy_regression_threshold": self.max_accuracy_regression_threshold,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> MGCompatibilityConfig:
        """Create config from dictionary."""
        return MGCompatibilityConfig(
            enabled=data.get("enabled", False),
            use_motivation=data.get("use_motivation", False),
            use_goals=data.get("use_goals", False),
            motivation_coefficient=data.get("motivation_coefficient", 0.0),
            goals_coefficient=data.get("goals_coefficient", 0.0),
            intercept_coefficient=data.get("intercept_coefficient", 0.0),
            fallback_enabled=data.get("fallback_enabled", True),
            fallback_on_invalid_signals=data.get("fallback_on_invalid_signals", True),
            fallback_on_computation_error=data.get("fallback_on_computation_error", True),
            fallback_on_coefficient_drift=data.get("fallback_on_coefficient_drift", True),
            coefficient_drift_tolerance=data.get("coefficient_drift_tolerance", 0.1),
            emit_diagnostic_metadata=data.get("emit_diagnostic_metadata", True),
            log_fallback_events=data.get("log_fallback_events", True),
            rollout_percentage=data.get("rollout_percentage", 0.0),
            max_fallback_rate_threshold=data.get("max_fallback_rate_threshold", 0.05),
            max_accuracy_regression_threshold=data.get(
                "max_accuracy_regression_threshold", 0.05
            ),
        )

    @staticmethod
    def from_environment() -> MGCompatibilityConfig:
        """Create config from environment variables."""
        return MGCompatibilityConfig(
            enabled=os.getenv("MG_ENABLED", "false").lower() == "true",
            use_motivation=os.getenv("MG_USE_MOTIVATION", "false").lower() == "true",
            use_goals=os.getenv("MG_USE_GOALS", "false").lower() == "true",
            motivation_coefficient=float(os.getenv("MG_MOTIVATION_COEFFICIENT", "0.0")),
            goals_coefficient=float(os.getenv("MG_GOALS_COEFFICIENT", "0.0")),
            intercept_coefficient=float(os.getenv("MG_INTERCEPT_COEFFICIENT", "0.0")),
            fallback_enabled=os.getenv("MG_FALLBACK_ENABLED", "true").lower() == "true",
            fallback_on_invalid_signals=os.getenv("MG_FALLBACK_ON_INVALID_SIGNALS", "true").lower()
            == "true",
            fallback_on_computation_error=os.getenv(
                "MG_FALLBACK_ON_COMPUTATION_ERROR", "true"
            ).lower()
            == "true",
            fallback_on_coefficient_drift=os.getenv(
                "MG_FALLBACK_ON_COEFFICIENT_DRIFT", "true"
            ).lower()
            == "true",
            coefficient_drift_tolerance=float(
                os.getenv("MG_COEFFICIENT_DRIFT_TOLERANCE", "0.1")
            ),
            emit_diagnostic_metadata=os.getenv("MG_EMIT_DIAGNOSTIC_METADATA", "true").lower()
            == "true",
            log_fallback_events=os.getenv("MG_LOG_FALLBACK_EVENTS", "true").lower() == "true",
            rollout_percentage=float(os.getenv("MG_ROLLOUT_PERCENTAGE", "0.0")),
            max_fallback_rate_threshold=float(
                os.getenv("MG_MAX_FALLBACK_RATE_THRESHOLD", "0.05")
            ),
            max_accuracy_regression_threshold=float(
                os.getenv("MG_MAX_ACCURACY_REGRESSION_THRESHOLD", "0.05")
            ),
        )

    # Reference configurations for rollout stages
    @staticmethod
    def stage_0_disabled() -> MGCompatibilityConfig:
        """Stage 0: Disabled (default, safe)."""
        return MGCompatibilityConfig(
            enabled=False,
            use_motivation=False,
            use_goals=False,
            rollout_percentage=0.0,
        )

    @staticmethod
    def stage_1_shadow(
        motivation_coefficient: float = 0.0,
        goals_coefficient: float = 0.0,
        intercept_coefficient: float = 0.0,
    ) -> MGCompatibilityConfig:
        """Stage 1: Shadow mode (MG runs in parallel, not used in active predictions)."""
        return MGCompatibilityConfig(
            enabled=False,  # Still disabled in production
            use_motivation=True,
            use_goals=True,
            motivation_coefficient=motivation_coefficient,
            goals_coefficient=goals_coefficient,
            intercept_coefficient=intercept_coefficient,
            rollout_percentage=0.0,  # Shadow only, 0% active
            fallback_enabled=True,
            emit_diagnostic_metadata=True,
        )

    @staticmethod
    def stage_2_controlled(
        rollout_percentage: float = 10.0,
        motivation_coefficient: float = 0.0,
        goals_coefficient: float = 0.0,
        intercept_coefficient: float = 0.0,
    ) -> MGCompatibilityConfig:
        """Stage 2: Controlled activation (10-100% of predictions use MG)."""
        return MGCompatibilityConfig(
            enabled=True,
            use_motivation=True,
            use_goals=True,
            motivation_coefficient=motivation_coefficient,
            goals_coefficient=goals_coefficient,
            intercept_coefficient=intercept_coefficient,
            rollout_percentage=rollout_percentage,
            fallback_enabled=True,
            fallback_on_invalid_signals=True,
            fallback_on_computation_error=True,
            fallback_on_coefficient_drift=True,
            emit_diagnostic_metadata=True,
            log_fallback_events=True,
        )

    @staticmethod
    def stage_3_full(
        motivation_coefficient: float = 0.0,
        goals_coefficient: float = 0.0,
        intercept_coefficient: float = 0.0,
    ) -> MGCompatibilityConfig:
        """Stage 3: Full activation (100% of predictions use MG with fallback)."""
        return MGCompatibilityConfig(
            enabled=True,
            use_motivation=True,
            use_goals=True,
            motivation_coefficient=motivation_coefficient,
            goals_coefficient=goals_coefficient,
            intercept_coefficient=intercept_coefficient,
            rollout_percentage=100.0,
            fallback_enabled=True,
            fallback_on_invalid_signals=True,
            fallback_on_computation_error=True,
            fallback_on_coefficient_drift=True,
            emit_diagnostic_metadata=True,
            log_fallback_events=True,
        )
