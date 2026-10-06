# 17.13A: Production Integration Design & Safety Specification

## Executive Summary

This document specifies the production integration contract for Motivation + Goals (MG) representation, validated by 17.11A and 17.12A, **without modifying production behavior**.

**Critical Invariant:**
```
MG disabled (default)
    ⇒
production behavior == pre-17.13 behavior (bit-for-bit identical)
```

**Scope:** Design and safety gate specification only. No production code changes.

**Next Phase:** 17.13B will implement this design within the safety boundaries defined here.

---

## 1. Production Architecture

### Current State (Pre-17.13)
```
SimulationEngine
       ↓
Legacy prediction
       ↓
Objective
```

### Post-17.13 State (With MG Disabled — Default)
```
SimulationEngine
       ↓
Legacy prediction
       ↓
[MG Compatibility Layer — DISABLED]
       ↓
Objective
       ↓
(identical to current state)
```

### Optional State (MG Enabled — Requires Explicit Configuration)
```
SimulationEngine
       ↓
Legacy prediction
       ↓
MG Compatibility Layer [ENABLED]
       ├── Motivation signal
       ├── Goals signal
       └── MG coefficients
              ↓
       Corrected prediction
       ↓
Objective
```

### Architectural Principle

**`SimulationEngine` remains responsible for simulation semantics, not correction.**

MG correction belongs behind the compatibility boundary—separated from the core simulation logic.

```
┌─────────────────────────────┐
│  SimulationEngine           │  ← Responsible for: state transitions, calibration
│                             │    simulation logic, empirical prediction
└──────────────┬──────────────┘
               │
               ▼ (legacy_prediction)
┌─────────────────────────────┐
│ MG Compatibility Layer      │  ← Responsible for: dimension mapping,
│                             │    correction computation, fallback logic
│ [Disabled by default]       │
└──────────────┬──────────────┘
               │
               ▼ (corrected_prediction or fallback)
        Objective
```

---

## 2. Default Behavior Contract

### Invariant

When MG is disabled (default configuration):

```python
assert corrected_prediction == legacy_prediction  # numerically identical
```

This is the safety boundary. If this invariant is violated, rollback immediately.

### Configuration Default

```python
MG_COMPATIBILITY_CONFIG = {
    "enabled": False,
    "use_motivation": False,
    "use_goals": False,
    "fallback_enabled": True,
}
```

### Verification

The first gate (G1) must verify this invariant on every run:

```
MG disabled
    ↓
assert legacy_prediction == corrected_prediction
    ↓
if assertion fails:
    rollback
    alert
    log incident
```

---

## 3. MG Configuration Contract

### Configuration Object

All MG behavior is controlled by a single configuration object. Do not scatter flags throughout the engine.

```python
@dataclass
class MGCompatibilityConfig:
    """Production MG compatibility configuration.
    
    This object encapsulates ALL MG-related settings.
    It should be externally configured and loadable from:
    - Environment variables
    - Configuration files
    - Feature flags
    - Runtime management endpoints
    
    Default: MG disabled, zero correction.
    """
    
    # Activation
    enabled: bool = False
    
    # Feature usage
    use_motivation: bool = False
    use_goals: bool = False
    
    # Coefficients (externally configured, not hardcoded)
    motivation_coefficient: float = 0.0
    goals_coefficient: float = 0.0
    intercept_coefficient: float = 0.0
    
    # Fallback behavior
    fallback_enabled: bool = True
    fallback_on_invalid_signals: bool = True
    fallback_on_computation_error: bool = True
    fallback_on_coefficient_drift: bool = True
    
    # Observability
    emit_diagnostic_metadata: bool = True
    log_fallback_events: bool = True
    
    def is_active(self) -> bool:
        """Check if MG correction would actually be applied."""
        return self.enabled and (self.use_motivation or self.use_goals)
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration consistency.
        
        Returns: (is_valid, error_message)
        """
        if self.enabled and self.fallback_enabled is False:
            return False, "Cannot enable MG without fallback"
        
        if self.use_motivation and abs(self.motivation_coefficient) < 1e-9:
            return False, "Motivation enabled but coefficient is zero"
        
        if self.use_goals and abs(self.goals_coefficient) < 1e-9:
            return False, "Goals enabled but coefficient is zero"
        
        return True, ""
```

### Configuration Loading

The configuration should be **externally configured**, not hardcoded in SimulationEngine:

```python
# ✅ Correct: Load from external source
mg_config = MGCompatibilityConfig(
    enabled=os.getenv("MG_ENABLED", "false").lower() == "true",
    use_motivation=os.getenv("MG_USE_MOTIVATION", "false").lower() == "true",
    use_goals=os.getenv("MG_USE_GOALS", "false").lower() == "true",
    motivation_coefficient=float(os.getenv("MG_MOTIVATION_COEFF", "0.0")),
    goals_coefficient=float(os.getenv("MG_GOALS_COEFF", "0.0")),
    intercept_coefficient=float(os.getenv("MG_INTERCEPT_COEFF", "0.0")),
)

# ❌ Incorrect: Hardcoded values in engine
simulation_engine = SimulationEngine(
    mg_motivation_coeff=0.0234,  # ← Don't do this
)
```

### Coefficients from Research

Coefficients should come from validated research results, **not** from tuning:

```python
# Load from 17.11A / 17.12A validated results
VALIDATED_MG_COEFFICIENTS = {
    42: {"motivation": 0.0234, "goals": 0.0567, "intercept": -0.0123},
    123: {"motivation": 0.0189, "goals": 0.0612, "intercept": -0.0087},
    456: {"motivation": 0.0301, "goals": 0.0489, "intercept": -0.0145},
    # ... etc
}

# Or use average from all seeds
PRODUCTION_COEFFICIENTS = {
    "motivation": mean([c["motivation"] for c in VALIDATED_MG_COEFFICIENTS.values()]),
    "goals": mean([c["goals"] for c in VALIDATED_MG_COEFFICIENTS.values()]),
    "intercept": mean([c["intercept"] for c in VALIDATED_MG_COEFFICIENTS.values()]),
}
```

---

## 4. Compatibility Layer Contract

### Responsibility Scope

The MG compatibility layer **SHOULD**:

- ✅ Map Motivation and Goals signals from simulation state
- ✅ Compute correction based on coefficients
- ✅ Apply correction to legacy prediction
- ✅ Detect invalid states and trigger fallback
- ✅ Emit diagnostic metadata (prediction_source, fallback_triggered, etc.)
- ✅ Return both corrected prediction and source attribution

The MG compatibility layer **SHOULD NOT**:

- ❌ Modify simulation state
- ❌ Modify experience history or dataset
- ❌ Modify calibration parameters
- ❌ Modify benchmark generation or splits
- ❌ Modify underlying simulation equations
- ❌ Modify objective definitions
- ❌ Feed MG corrections back into the simulation loop
- ❌ Change behavior when disabled

### Interface Contract

```python
@dataclass
class MGCompatibilityResult:
    """Result of MG compatibility processing."""
    
    # Prediction
    prediction: Dict[str, float]          # Final prediction (legacy or MG)
    
    # Attribution
    source: Literal["legacy", "mg", "fallback"]
    
    # Diagnostic metadata
    motivation_signal: Optional[float] = None
    goals_signal: Optional[float] = None
    motivation_correction: Optional[float] = None
    goals_correction: Optional[float] = None
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/monitoring."""
        return asdict(self)


class MGCompatibilityLayer:
    """Apply MG correction to SimulationEngine predictions.
    
    Key invariant:
        MG disabled ⇒ result.source == "legacy" and result.prediction == legacy_prediction
    """
    
    def __init__(self, config: MGCompatibilityConfig):
        self.config = config
    
    def apply(
        self,
        legacy_prediction: Dict[str, float],
        simulation_state: Dict[str, Any],
        action: str,
    ) -> MGCompatibilityResult:
        """Apply MG correction to legacy prediction.
        
        Args:
            legacy_prediction: Output from SimulationEngine
            simulation_state: Current user state from simulation
            action: Action taken (for context)
        
        Returns:
            MGCompatibilityResult with final prediction and metadata
        """
        # If disabled, return legacy prediction unchanged
        if not self.config.is_active():
            return MGCompatibilityResult(
                prediction=legacy_prediction,
                source="legacy",
                motivation_signal=None,
                goals_signal=None,
                fallback_triggered=False,
            )
        
        # Extract signals (TBD: implementation)
        try:
            motivation_signal = self._extract_motivation_signal(simulation_state, action)
            goals_signal = self._extract_goals_signal(simulation_state, action)
        except Exception as e:
            if self.config.fallback_on_invalid_signals:
                return self._fallback_to_legacy(legacy_prediction, f"Signal extraction failed: {e}")
            raise
        
        # Compute corrections (TBD: implementation)
        try:
            motivation_correction = self._compute_motivation_correction(motivation_signal)
            goals_correction = self._compute_goals_correction(goals_signal)
            total_correction = motivation_correction + goals_correction
        except Exception as e:
            if self.config.fallback_on_computation_error:
                return self._fallback_to_legacy(legacy_prediction, f"Correction computation failed: {e}")
            raise
        
        # Apply correction
        corrected_prediction = self._apply_correction(legacy_prediction, total_correction)
        
        # Validate result
        if not self._validate_prediction(corrected_prediction):
            if self.config.fallback_enabled:
                return self._fallback_to_legacy(legacy_prediction, "Corrected prediction validation failed")
            raise ValueError("Corrected prediction is invalid")
        
        return MGCompatibilityResult(
            prediction=corrected_prediction,
            source="mg",
            motivation_signal=float(motivation_signal),
            goals_signal=float(goals_signal),
            motivation_correction=float(motivation_correction),
            goals_correction=float(goals_correction),
            fallback_triggered=False,
        )
    
    def _fallback_to_legacy(
        self, legacy_prediction: Dict[str, float], reason: str
    ) -> MGCompatibilityResult:
        """Fallback to legacy prediction."""
        if self.config.log_fallback_events:
            print(f"[MG Fallback] {reason}")
        
        return MGCompatibilityResult(
            prediction=legacy_prediction,
            source="legacy",
            fallback_triggered=True,
            fallback_reason=reason,
        )
    
    # TBD: Implementation methods
    # - _extract_motivation_signal
    # - _extract_goals_signal
    # - _compute_motivation_correction
    # - _compute_goals_correction
    # - _apply_correction
    # - _validate_prediction
```

---

## 5. Fallback Design

### Fallback Triggers

MG automatically falls back to Legacy in these conditions:

1. **Configuration Disabled**
   ```python
   if not config.enabled:
       return legacy_prediction
   ```

2. **Invalid Signals**
   ```python
   if motivation_signal is None or math.isnan(motivation_signal):
       if config.fallback_on_invalid_signals:
           return legacy_prediction
   ```

3. **Computation Error**
   ```python
   try:
       correction = compute_mg_correction(signals, coefficients)
   except Exception as e:
       if config.fallback_on_computation_error:
           return legacy_prediction
   ```

4. **NaN/Inf Correction**
   ```python
   if not math.isfinite(correction):
       return legacy_prediction
   ```

5. **Prediction Shape Mismatch**
   ```python
   if corrected_prediction.shape != legacy_prediction.shape:
       return legacy_prediction
   ```

6. **Coefficient Drift**
   ```python
   if abs(current_coefficient - expected_coefficient) > tolerance:
       if config.fallback_on_coefficient_drift:
           return legacy_prediction
   ```

7. **Compatibility Layer Exception**
   ```python
   try:
       return apply_mg_correction(legacy_prediction)
   except:
       if config.fallback_enabled:
           return legacy_prediction
       else:
           raise
   ```

### Fallback is Deterministic

```python
# ✅ Correct: Fallback is deterministic and observable
result = compatibility_layer.apply(legacy_pred, state, action)
if result.source == "legacy" and result.fallback_triggered:
    # Observable: we can log, monitor, alert on fallback events
    log_fallback_event(result.fallback_reason)

# ❌ Incorrect: Silent fallback or non-deterministic behavior
if mg_correction_fails():
    silently_use_legacy()  # ← Can't observe or monitor
```

---

## 6. Observability

### Prediction Metadata

Every prediction must be able to expose diagnostic metadata **without changing the prediction itself**:

```python
@dataclass
class PredictionMetadata:
    """Diagnostic metadata about a prediction."""
    
    # Attribution
    source: Literal["legacy", "mg", "fallback"]
    mg_enabled: bool
    
    # Inputs to MG (if applicable)
    motivation_signal: Optional[float] = None
    goals_signal: Optional[float] = None
    
    # Corrections applied (if applicable)
    motivation_correction: Optional[float] = None
    goals_correction: Optional[float] = None
    total_correction: Optional[float] = None
    
    # Fallback information
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    
    # Prediction shape and range
    prediction_shape: tuple
    prediction_range: tuple[float, float]  # min, max
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

### Logging Contract

Every MG prediction event should be loggable (if requested):

```python
class PredictionLogger:
    """Structured logging for MG predictions."""
    
    def log_prediction(
        self,
        prediction: Dict[str, float],
        metadata: PredictionMetadata,
        actual_future_state: Optional[Dict[str, float]] = None,
    ):
        """Log prediction with metadata for later analysis.
        
        This should be used for:
        - Stage 1 (Shadow): Compare Legacy vs MG predictions
        - Stage 2 (Controlled): Track MG accuracy vs Legacy
        - Stage 3 (Full): Monitor production metrics
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "metadata": metadata.to_dict(),
            "actual": actual_future_state,
        }
        self.logger.info(json.dumps(entry))
```

---

## 7. Rollout Strategy

### Stage 0: Disabled (Default)

```
MG_ENABLED = false
MG_USE_MOTIVATION = false
MG_USE_GOALS = false

Result:
    All predictions use Legacy
    No MG metadata is computed
    System behaves exactly as pre-17.13
```

**Duration:** Until Stage 1 gates pass.

### Stage 1: Shadow Mode

```
MG_ENABLED = true (but not used)
MG_USE_MOTIVATION = false (signals computed but not applied)
MG_USE_GOALS = false (signals computed but not applied)

Result:
    Active predictions: Legacy (production unchanged)
    Shadow predictions: MG (computed but not used)
    Compare: legacy_prediction vs mg_prediction
    Analyze: prediction_delta, signal_behavior, fallback_rate
```

**Success Criteria:**
- MG shadow accuracy matches 17.12A results (±5% variance)
- Fallback rate < 1%
- Signal behavior is stable across all data
- No production-side side effects

**Duration:** 1 week minimum observation.

### Stage 2: Controlled Activation

```
MG_ENABLED = true
MG_USE_MOTIVATION = true
MG_USE_GOALS = true
MG_ROLLOUT_PERCENTAGE = 10%  # Enable for 10% of predictions

Result:
    90% of predictions use Legacy
    10% of predictions use MG (live, affects outcomes)
    Monitor: MAE, RMSE, prediction drift, fallback events
```

**Success Criteria:**
- MAE(MG) <= MAE(Legacy) + 1%
- RMSE(MG) <= RMSE(Legacy) + 1%
- Prediction drift < 5%
- Fallback rate < 0.5%
- No unexpected regressions in any prediction dimension

**Duration:** 2 weeks per 10% increment.

### Stage 3: Full Activation

```
MG_ENABLED = true
MG_USE_MOTIVATION = true
MG_USE_GOALS = true
MG_ROLLOUT_PERCENTAGE = 100%

Result:
    All predictions use MG (unless fallback triggered)
    Monitor: Same metrics as Stage 2
```

**Precondition:** All Stage 2 success criteria met on 100% sample.

**Duration:** Indefinite (production behavior).

---

## 8. Rollback Mechanism

### Rollback is Configuration-Only

Rollback should require **no code changes**, only configuration:

```python
# ✅ Correct: Configuration-based rollback
os.environ["MG_ENABLED"] = "false"
# OR
set_runtime_config({"mg_enabled": False})
# Then restart or hot-reload configuration

# Immediate effect:
# All predictions revert to Legacy
# No deployment, no code changes
```

### Rollback Triggers

Rollback should be automatic if:

```python
# Policy: If fallback rate > threshold, disable MG
if fallback_rate > 0.05:  # > 5%
    mg_config.enabled = False
    alert("MG disabled: fallback rate exceeded threshold")

# Policy: If accuracy regression detected
if mae(current_window) > mae(baseline) * 1.05:  # > 5% worse
    mg_config.enabled = False
    alert("MG disabled: accuracy regression detected")

# Policy: If coefficient drift detected
if coefficient_divergence > tolerance:
    mg_config.enabled = False
    alert("MG disabled: coefficient drift detected")
```

### Rollback Verification

After rollback:

```python
# Verify that Legacy behavior is restored
assert all_predictions_source == "legacy"
assert prediction_accuracy == baseline_accuracy
```

---

## 9. Safety Gates (17.13A)

These gates define the production integration contract. **All 10 must be formally verified before 17.13B implementation.**

### G1: Architecture Isolation

**Requirement:** MG is isolated from core simulation semantics.

**Test:**
```python
def test_g1_architecture_isolation():
    """MG changes should not affect SimulationEngine logic."""
    
    # Create engine with MG disabled
    engine = SimulationEngine()
    
    # Create engine with MG enabled
    engine_with_mg = SimulationEngine(mg_config=MGCompatibilityConfig(
        enabled=True,
        use_motivation=True,
        use_goals=True,
    ))
    
    # Both should call the same SimulationEngine.simulate_action
    # The only difference is the compatibility layer wrapping the result
    
    state = {"python": 50, "dsa": 50, "machine_learning": 50, "projects": 50}
    action = "Python Project"
    
    result_base = engine.simulate_action(state, action)
    result_mg = engine_with_mg.simulate_action(state, action)
    
    # The internal simulation results should be identical
    # Only the final return value differs (legacy vs MG)
    assert result_base["internal_simulation"] == result_mg["internal_simulation"]
```

**Gate Pass Criterion:** MG logic is applied post-simulation, not during.

---

### G2: Disabled Identity

**Requirement:** MG disabled produces identical behavior to pre-17.13.

**Test:**
```python
def test_g2_disabled_identity():
    """MG disabled must be bit-for-bit identical to pre-17.13 behavior."""
    
    # Pre-17.13 behavior (control)
    engine_legacy = LegacySimulationEngine()
    prediction_legacy = engine_legacy.simulate_action(state, action)
    
    # Post-17.13 with MG disabled (test)
    engine_17_13 = SimulationEngine(mg_config=MGCompatibilityConfig(enabled=False))
    prediction_17_13 = engine_17_13.simulate_action(state, action)
    
    # Must be numerically identical
    np.testing.assert_allclose(
        prediction_legacy,
        prediction_17_13,
        rtol=1e-15,
        atol=1e-15,
    )
```

**Gate Pass Criterion:** Numeric identity within floating-point tolerance.

---

### G3: Configuration Contract Explicit

**Requirement:** Configuration contract is formal and externally configurable.

**Test:**
```python
def test_g3_configuration_contract():
    """MG configuration must be explicit and externally configurable."""
    
    # All MG settings in single config object
    config = MGCompatibilityConfig()
    assert hasattr(config, "enabled")
    assert hasattr(config, "use_motivation")
    assert hasattr(config, "use_goals")
    assert hasattr(config, "motivation_coefficient")
    assert hasattr(config, "goals_coefficient")
    assert hasattr(config, "fallback_enabled")
    
    # Config must be externally loadable
    from_env = MGCompatibilityConfig(
        enabled=os.getenv("MG_ENABLED", "false").lower() == "true",
        use_motivation=os.getenv("MG_USE_MOTIVATION", "false").lower() == "true",
        use_goals=os.getenv("MG_USE_GOALS", "false").lower() == "true",
    )
    
    # Config must be validatable
    is_valid, error = from_env.validate()
    assert isinstance(is_valid, bool)
    assert isinstance(error, str)
```

**Gate Pass Criterion:** Config object exists, is externally loadable, validates.

---

### G4: Coefficients Externally Configurable

**Requirement:** Coefficients are NOT hardcoded in SimulationEngine.

**Test:**
```python
def test_g4_coefficients_external():
    """MG coefficients must be externally configured, not hardcoded."""
    
    # Coefficients should come from config
    config = MGCompatibilityConfig(
        motivation_coefficient=0.0234,
        goals_coefficient=0.0567,
        intercept_coefficient=-0.0123,
    )
    
    # Should be loadable from environment/file
    config_from_env = MGCompatibilityConfig(
        motivation_coefficient=float(os.getenv("MG_MOTIVATION_COEFF", "0.0")),
        goals_coefficient=float(os.getenv("MG_GOALS_COEFF", "0.0")),
    )
    
    # Inspect SimulationEngine: no hardcoded coefficient values
    engine_source = inspect.getsource(SimulationEngine)
    assert "0.0234" not in engine_source  # No hardcoded values
    assert "0.0567" not in engine_source
```

**Gate Pass Criterion:** No coefficient constants in production code.

---

### G5: Invalid MG State Triggers Fallback

**Requirement:** If MG cannot safely compute, fallback to Legacy.

**Test:**
```python
def test_g5_fallback_on_invalid_mg():
    """Invalid MG state must trigger fallback to Legacy."""
    
    config = MGCompatibilityConfig(
        enabled=True,
        use_motivation=True,
        use_goals=True,
        fallback_enabled=True,
    )
    
    layer = MGCompatibilityLayer(config)
    
    # Simulate invalid signals
    legacy_pred = {"python": 50, "dsa": 50, "machine_learning": 50, "projects": 50}
    invalid_state = {}  # Missing required fields
    
    result = layer.apply(legacy_pred, invalid_state, "test_action")
    
    # Must fallback
    assert result.fallback_triggered is True
    assert result.source == "legacy"
    assert result.prediction == legacy_pred  # Unchanged
```

**Gate Pass Criterion:** Fallback occurs for all invalid conditions.

---

### G6: No Simulation State Mutation

**Requirement:** MG does not modify simulation state, experience history, or calibration.

**Test:**
```python
def test_g6_no_simulation_mutation():
    """MG must not mutate simulation state."""
    
    config = MGCompatibilityConfig(
        enabled=True,
        use_motivation=True,
        use_goals=True,
    )
    
    engine = SimulationEngine(mg_config=config)
    
    # Capture initial state
    state_before = deepcopy(engine.state)
    experiences_before = deepcopy(engine.experience_history)
    calibration_before = deepcopy(engine.calibration_parameters)
    
    # Run simulation
    engine.simulate_action(state_before, "Python Project")
    
    # State must not change
    assert engine.state == state_before
    assert engine.experience_history == experiences_before
    assert engine.calibration_parameters == calibration_before
```

**Gate Pass Criterion:** State is unchanged after MG execution.

---

### G7: Prediction Source Observable

**Requirement:** Every prediction can report its source (legacy, mg, fallback).

**Test:**
```python
def test_g7_prediction_source_observable():
    """Prediction source must be observable."""
    
    config = MGCompatibilityConfig(enabled=True)
    layer = MGCompatibilityLayer(config)
    
    result = layer.apply(legacy_pred, state, action)
    
    # Must have source field
    assert hasattr(result, "source")
    assert result.source in ["legacy", "mg", "fallback"]
    
    # Must have diagnostic metadata
    assert hasattr(result, "fallback_triggered")
    assert hasattr(result, "fallback_reason")
    assert hasattr(result, "motivation_signal")
    assert hasattr(result, "goals_signal")
```

**Gate Pass Criterion:** Result has source and metadata fields.

---

### G8: Shadow Mode Cannot Affect Active Prediction

**Requirement:** Shadow MG execution does not influence active prediction.

**Test:**
```python
def test_g8_shadow_isolation():
    """Shadow MG must not affect active prediction."""
    
    # Stage 1: Shadow mode
    config_shadow = MGCompatibilityConfig(
        enabled=True,
        use_motivation=False,  # ← Signals computed but not used
        use_goals=False,
        fallback_enabled=True,
    )
    
    layer_shadow = MGCompatibilityLayer(config_shadow)
    
    # Should return legacy prediction
    result = layer_shadow.apply(legacy_pred, state, action)
    assert result.source == "legacy"
    assert result.prediction == legacy_pred
    
    # Shadow should not influence the active result
    # (Shadow computation happens separately)
```

**Gate Pass Criterion:** When features are disabled, active result is Legacy.

---

### G9: Rollback Requires Configuration Only

**Requirement:** Rollback to Legacy requires only configuration change, not code deployment.

**Test:**
```python
def test_g9_rollback_configuration_only():
    """Rollback must be configuration-only."""
    
    # MG enabled
    config_enabled = MGCompatibilityConfig(
        enabled=True,
        use_motivation=True,
        use_goals=True,
    )
    
    layer_enabled = MGCompatibilityLayer(config_enabled)
    result_mg = layer_enabled.apply(legacy_pred, state, action)
    
    # Configuration changed to disabled (no code change)
    config_disabled = dataclasses.replace(config_enabled, enabled=False)
    layer_disabled = MGCompatibilityLayer(config_disabled)
    result_legacy = layer_disabled.apply(legacy_pred, state, action)
    
    # Result should be identical to Legacy
    assert result_legacy.source == "legacy"
    assert result_legacy.prediction == legacy_pred
```

**Gate Pass Criterion:** Configuration-only change restores Legacy behavior.

---

### G10: Production Activation Disabled by Default

**Requirement:** Default configuration does NOT activate MG in production.

**Test:**
```python
def test_g10_default_disabled():
    """Default configuration must have MG disabled."""
    
    config_default = MGCompatibilityConfig()  # All defaults
    
    assert config_default.enabled is False
    assert config_default.use_motivation is False
    assert config_default.use_goals is False
    
    # If someone forgets to set config, MG should be inactive
    layer_default = MGCompatibilityLayer(config_default)
    result = layer_default.apply(legacy_pred, state, action)
    
    assert result.source == "legacy"
    assert result.prediction == legacy_pred
```

**Gate Pass Criterion:** Default config produces Legacy behavior.

---

## 10. Proposed File Structure

### New Files (Implementation in 17.13B)

```
backend/
├── compatibility/
│   ├── __init__.py
│   ├── mg_config.py                 # MGCompatibilityConfig dataclass
│   ├── mg_compatibility.py          # MGCompatibilityLayer class
│   └── mg_metadata.py               # PredictionMetadata, PredictionLogger
│
└── tests/
    ├── test_mg_config.py            # Config validation tests
    ├── test_mg_disabled_identity.py  # G2 test (bit-for-bit identity)
    ├── test_mg_fallback.py           # G5 test (fallback behavior)
    ├── test_mg_shadow_isolation.py   # G8 test (shadow mode isolation)
    ├── test_mg_safety_gates.py       # All 10 gates (G1-G10)
    └── test_mg_rollback.py           # G9 test (rollback mechanics)
```

### Modified Files (Minimal Integration in 17.13B)

```
backend/
└── services/
    └── simulation_engine.py
        # Changes:
        # - Add mg_config parameter (optional, default None)
        # - After simulate_action(), wrap result with MGCompatibilityLayer.apply()
        # - Return result with metadata
        # - Minimal 5-10 lines of code
```

### No Changes To

```
backend/models/          # Simulation semantics unchanged
backend/planning/        # Transition model unchanged
backend/services/
  ├── transition_engine.py
  ├── experience_service.py
  ├── state_service.py
  # ... (all unchanged)
```

---

## 11. Implementation Restriction

### 17.13A Constraint

**17.13A produces the design specification and safety gate framework ONLY.**

It does NOT:
- ❌ Modify production code
- ❌ Change any production behavior
- ❌ Implement MGCompatibilityLayer or MGCompatibilityConfig
- ❌ Add new dependencies
- ❌ Change SimulationEngine

It DOES:
- ✅ Define the safety gates (test specifications)
- ✅ Specify the architecture (this document)
- ✅ Document the configuration contract
- ✅ Define the fallback rules
- ✅ Outline the rollout strategy
- ✅ Specify rollback mechanism

### 17.13B Implementation

17.13B will:
- Implement MGCompatibilityConfig dataclass
- Implement MGCompatibilityLayer class
- Add minimal integration hook to SimulationEngine
- Implement all 10 safety gate tests
- Verify all gates pass
- Commit implementation

### Post-17.13B

After 17.13B implementation and verification:
- Activate Stage 0 (MG disabled by default)
- Proceed to Stage 1 (Shadow mode observation) once gates pass
- Monitor and validate before Stage 2+ activation

---

## 12. Decision Clarity

### Before 17.13B

```
Is MG production-ready?
    ├── Technical validation: YES (17.11A, 17.12A)
    ├── Integration design: YES (17.13A)
    └── Implementation: Pending (17.13B)
```

### After 17.13B

```
Is MG production-ready?
    ├── Technical validation: YES (17.11A, 17.12A)
    ├── Integration design: YES (17.13A)
    ├── Implementation: YES (17.13B)
    ├── Safety gates: PASS (All 10)
    └── Activation: Stage 0 (disabled by default)
        └── Proceed to Stage 1 (shadow) if gates sustained
```

---

## Research Chain Summary

```
17.9    ─── MGB representation hypothesis
17.10B  ─── Mixed integration results
17.10C  ─── Behavior discrepancy diagnosed
17.10D  ─── Behavior reproducibility fails
17.11A  ─── MG validation succeeds (7/7 gates, 5/5 seeds)
17.12A  ─── MG shadow integration succeeds (10/10 gates, 5/5 seeds, zero discrepancy)
17.13A  ─── Production integration specification (DESIGN ONLY, THIS PHASE)
17.13B  ─── Implementation of 17.13A design
17.13C  ─── Stage 0→1 transition (shadow mode validation)
17.14+  ─── Staged activation (Stages 1→2→3)
```

---

## Approval Gate

This specification is complete when:

1. ✅ All 10 safety gate requirements are formally documented
2. ✅ Test specifications for each gate are defined
3. ✅ Architecture is clear and separates concerns
4. ✅ Configuration contract is explicit
5. ✅ Fallback and rollback mechanisms are specified
6. ✅ Rollout strategy is defined
7. ✅ No production behavior changes in 17.13A
8. ✅ All documents and gates are approved

**Current Status:** Specification complete. Ready for 17.13B implementation review.
