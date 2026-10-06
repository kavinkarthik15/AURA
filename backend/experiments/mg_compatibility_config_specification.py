"""
17.13A: MG Compatibility Configuration Schema

This file defines the configuration contract for MG integration.
It is used in 17.13B for implementation, but is documented here as part of 17.13A design.

This is NOT production code yet — it's a specification.
17.13B will implement the actual classes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple
import json


@dataclass(frozen=True)
class MGCompatibilityConfig:
    """Production MG compatibility configuration specification.
    
    This object encapsulates ALL MG-related settings for production.
    It should be:
    - Externally configured (environment, config files, feature flags)
    - Validated before use
    - Loadable at runtime
    - Immutable (frozen=True) to prevent accidental mutations
    
    Safety invariant:
        enabled = False  ⇒  All predictions are Legacy (pre-17.13 behavior)
    
    Default values produce NO change to production behavior.
    """
    
    # ========== ACTIVATION ==========
    enabled: bool = False
    """Enable MG correction processing.
    
    When False:
        - All corrections are skipped
        - All predictions use Legacy
        - System behaves exactly as pre-17.13
        - This is the safe default
    """
    
    # ========== FEATURE USAGE ==========
    use_motivation: bool = False
    """Use Motivation dimension in correction.
    
    Only meaningful if enabled=True.
    When False, motivation signals are extracted but not used.
    """
    
    use_goals: bool = False
    """Use Goals dimension in correction.
    
    Only meaningful if enabled=True.
    When False, goals signals are extracted but not used.
    """
    
    # ========== COEFFICIENTS ==========
    # These should NEVER be hardcoded in SimulationEngine
    # They come from validated research (17.11A/17.12A) or external config
    
    motivation_coefficient: float = 0.0
    """Regression coefficient for motivation correction.
    
    Typical value from 17.11A/17.12A: ~0.020-0.030
    
    Constraint: If use_motivation=True, must be non-zero
    """
    
    goals_coefficient: float = 0.0
    """Regression coefficient for goals correction.
    
    Typical value from 17.11A/17.12A: ~0.050-0.060
    
    Constraint: If use_goals=True, must be non-zero
    """
    
    intercept_coefficient: float = 0.0
    """Intercept term for correction.
    
    Typical value from 17.11A/17.12A: ~-0.010 to 0.010
    """
    
    # ========== FALLBACK BEHAVIOR ==========
    fallback_enabled: bool = True
    """Enable fallback to Legacy when MG cannot safely execute.
    
    If False and MG fails, an exception is raised (fail-fast).
    If True, automatically fall back to Legacy (fail-safe).
    
    Recommended: True (fail-safe)
    """
    
    fallback_on_invalid_signals: bool = True
    """Fallback if motivation/goals signals are invalid.
    
    Invalid signals:
        - None value
        - NaN or Inf
        - Wrong type
        - Out of expected range
    """
    
    fallback_on_computation_error: bool = True
    """Fallback if correction computation raises exception.
    
    Examples:
        - Matrix inversion error
        - Coefficient divergence
        - Memory error
    """
    
    fallback_on_coefficient_drift: bool = True
    """Fallback if coefficients diverge from expected values.
    
    This is a safety mechanism to detect coefficient corruption
    or unexpected updates.
    
    Requires: coefficient_drift_tolerance to be specified
    """
    
    coefficient_drift_tolerance: float = 0.1
    """Tolerance for coefficient drift (±10% by default).
    
    If |current_coeff - expected_coeff| / expected_coeff > tolerance:
        fallback to Legacy
    """
    
    # ========== OBSERVABILITY ==========
    emit_diagnostic_metadata: bool = True
    """Emit diagnostic metadata with every prediction.
    
    Metadata includes:
        - prediction_source (legacy, mg, fallback)
        - motivation_signal, goals_signal
        - corrections_applied
        - fallback_triggered, fallback_reason
    
    This metadata is used for:
        - Monitoring (Stage 1+)
        - Debugging
        - Rollout validation
    
    Recommended: True (for production monitoring)
    """
    
    log_fallback_events: bool = True
    """Log fallback events to structured logger.
    
    Fallback events are important for production stability.
    They should be monitored and alerted on.
    
    Examples:
        - MG disabled by configuration
        - Invalid signal (NaN, missing field)
        - Computation error
        - Coefficient drift detected
    
    Recommended: True
    """
    
    # ========== EXPERIMENTAL / ADVANCED ==========
    # These are for future stages or advanced rollout
    
    rollout_percentage: float = 0.0
    """Percentage of predictions to route through MG (Stage 2+).
    
    Stage 1 (Shadow): 0%
    Stage 2 (Controlled): 0-100% (incremental)
    Stage 3 (Full): 100%
    
    Implementation: Hash-based deterministic sampling
    """
    
    max_fallback_rate_threshold: float = 0.05
    """Automatically disable MG if fallback rate exceeds this (5%).
    
    If fallback_rate > threshold:
        auto_disable_mg()
        alert()
    
    This prevents cascading failures from propagating.
    """
    
    max_accuracy_regression_threshold: float = 0.05
    """Automatically disable MG if accuracy degrades > 5%.
    
    If (current_mae - baseline_mae) / baseline_mae > threshold:
        auto_disable_mg()
        alert()
    """
    
    def is_active(self) -> bool:
        """Check if MG correction would actually be applied.
        
        Returns True only if:
        - enabled=True, AND
        - At least one feature is enabled (use_motivation or use_goals)
        """
        return self.enabled and (self.use_motivation or self.use_goals)
    
    def validate(self) -> Tuple[bool, str]:
        """Validate configuration consistency.
        
        Returns:
            (is_valid, error_message)
        
        Checks:
        - Cannot enable MG without fallback
        - Cannot use motivation without non-zero coefficient
        - Cannot use goals without non-zero coefficient
        - Coefficients must be finite
        - Percentages must be in [0, 100]
        - Thresholds must be in [0, 1]
        """
        if self.enabled and not self.fallback_enabled:
            return False, "Cannot enable MG without fallback_enabled=True"
        
        if self.use_motivation and abs(self.motivation_coefficient) < 1e-9:
            return False, "use_motivation=True but motivation_coefficient is zero"
        
        if self.use_goals and abs(self.goals_coefficient) < 1e-9:
            return False, "use_goals=True but goals_coefficient is zero"
        
        if not all(
            [
                self.is_finite_or_zero(self.motivation_coefficient),
                self.is_finite_or_zero(self.goals_coefficient),
                self.is_finite_or_zero(self.intercept_coefficient),
            ]
        ):
            return False, "Coefficients must be finite"
        
        if not (0.0 <= self.rollout_percentage <= 100.0):
            return False, "rollout_percentage must be in [0, 100]"
        
        if not (0.0 <= self.max_fallback_rate_threshold <= 1.0):
            return False, "max_fallback_rate_threshold must be in [0, 1]"
        
        if not (0.0 <= self.max_accuracy_regression_threshold <= 1.0):
            return False, "max_accuracy_regression_threshold must be in [0, 1]"
        
        return True, ""
    
    @staticmethod
    def is_finite_or_zero(value: float) -> bool:
        """Check if value is finite (not NaN, not Inf) or zero."""
        import math
        return math.isfinite(value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for logging, external config, etc.)"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MGCompatibilityConfig:
        """Deserialize from dictionary."""
        # Only use fields that are part of this dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_environment(cls) -> MGCompatibilityConfig:
        """Load configuration from environment variables.
        
        Supported environment variables:
            MG_ENABLED                              (bool)
            MG_USE_MOTIVATION                       (bool)
            MG_USE_GOALS                            (bool)
            MG_MOTIVATION_COEFFICIENT               (float)
            MG_GOALS_COEFFICIENT                    (float)
            MG_INTERCEPT_COEFFICIENT                (float)
            MG_FALLBACK_ENABLED                     (bool)
            MG_FALLBACK_ON_INVALID_SIGNALS          (bool)
            MG_FALLBACK_ON_COMPUTATION_ERROR        (bool)
            MG_FALLBACK_ON_COEFFICIENT_DRIFT        (bool)
            MG_COEFFICIENT_DRIFT_TOLERANCE          (float)
            MG_EMIT_DIAGNOSTIC_METADATA             (bool)
            MG_LOG_FALLBACK_EVENTS                  (bool)
            MG_ROLLOUT_PERCENTAGE                   (float)
            MG_MAX_FALLBACK_RATE_THRESHOLD          (float)
            MG_MAX_ACCURACY_REGRESSION_THRESHOLD    (float)
        
        Defaults:
            All boolean fields default to False (safe)
            All float fields default to 0.0 (no correction)
        """
        import os
        
        def get_bool(key: str, default: bool = False) -> bool:
            return os.getenv(key, "false").lower() in ["true", "1", "yes"]
        
        def get_float(key: str, default: float = 0.0) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        return cls(
            enabled=get_bool("MG_ENABLED", False),
            use_motivation=get_bool("MG_USE_MOTIVATION", False),
            use_goals=get_bool("MG_USE_GOALS", False),
            motivation_coefficient=get_float("MG_MOTIVATION_COEFFICIENT", 0.0),
            goals_coefficient=get_float("MG_GOALS_COEFFICIENT", 0.0),
            intercept_coefficient=get_float("MG_INTERCEPT_COEFFICIENT", 0.0),
            fallback_enabled=get_bool("MG_FALLBACK_ENABLED", True),
            fallback_on_invalid_signals=get_bool("MG_FALLBACK_ON_INVALID_SIGNALS", True),
            fallback_on_computation_error=get_bool("MG_FALLBACK_ON_COMPUTATION_ERROR", True),
            fallback_on_coefficient_drift=get_bool("MG_FALLBACK_ON_COEFFICIENT_DRIFT", True),
            coefficient_drift_tolerance=get_float("MG_COEFFICIENT_DRIFT_TOLERANCE", 0.1),
            emit_diagnostic_metadata=get_bool("MG_EMIT_DIAGNOSTIC_METADATA", True),
            log_fallback_events=get_bool("MG_LOG_FALLBACK_EVENTS", True),
            rollout_percentage=get_float("MG_ROLLOUT_PERCENTAGE", 0.0),
            max_fallback_rate_threshold=get_float("MG_MAX_FALLBACK_RATE_THRESHOLD", 0.05),
            max_accuracy_regression_threshold=get_float("MG_MAX_ACCURACY_REGRESSION_THRESHOLD", 0.05),
        )


# ============================================================================
# REFERENCE: Production Configuration Profiles
# ============================================================================

# Stage 0: Disabled (Default Production)
STAGE_0_DISABLED = MGCompatibilityConfig(
    enabled=False,
    use_motivation=False,
    use_goals=False,
    fallback_enabled=True,
)

# Stage 1: Shadow Mode (Compute but don't apply)
STAGE_1_SHADOW = MGCompatibilityConfig(
    enabled=True,  # But features disabled
    use_motivation=False,  # Signals computed, not used
    use_goals=False,
    fallback_enabled=True,
    emit_diagnostic_metadata=True,
    log_fallback_events=True,
    # Use coefficients from 17.11A/17.12A validated results
    motivation_coefficient=0.0234,  # Mean across seeds
    goals_coefficient=0.0567,
    intercept_coefficient=-0.0123,
)

# Stage 2: Controlled Activation (10% of predictions)
STAGE_2_CONTROLLED_10 = MGCompatibilityConfig(
    enabled=True,
    use_motivation=True,
    use_goals=True,
    motivation_coefficient=0.0234,
    goals_coefficient=0.0567,
    intercept_coefficient=-0.0123,
    rollout_percentage=10.0,  # 10% of predictions
    fallback_enabled=True,
    emit_diagnostic_metadata=True,
    log_fallback_events=True,
    max_fallback_rate_threshold=0.05,
    max_accuracy_regression_threshold=0.05,
)

# Stage 3: Full Activation (100% of predictions)
STAGE_3_FULL = MGCompatibilityConfig(
    enabled=True,
    use_motivation=True,
    use_goals=True,
    motivation_coefficient=0.0234,
    goals_coefficient=0.0567,
    intercept_coefficient=-0.0123,
    rollout_percentage=100.0,  # All predictions
    fallback_enabled=True,
    emit_diagnostic_metadata=True,
    log_fallback_events=True,
    max_fallback_rate_threshold=0.05,
    max_accuracy_regression_threshold=0.05,
)


if __name__ == "__main__":
    # Example: Load from environment
    config = MGCompatibilityConfig.from_environment()
    print(f"MG Config from environment: {config}")
    
    # Validate
    is_valid, error = config.validate()
    if not is_valid:
        print(f"Configuration invalid: {error}")
    else:
        print("Configuration valid")
    
    # Check if MG is active
    print(f"MG is active: {config.is_active()}")
    
    # Serialize for logging
    print(f"Config as JSON: {json.dumps(config.to_dict(), indent=2)}")
