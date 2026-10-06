# Research Plan: 17.13C Shadow Validation

**Status**: PLANNING (not yet executed)  
**Baseline**: 17.13B (frozen, validated)  
**Purpose**: Broader controlled shadow validation before production activation  
**Target Completion**: To be scheduled after plan approval  

---

## Executive Summary

17.13C extends the validation methodology established in 17.13B from a narrow research benchmark to a broader shadow validation setup, verifying that the frozen MG mechanism generalizes safely across real-world conditions without yet activating MG as the production default.

**Key Principle**: Reuse the exact frozen 17.13B implementation and coefficients. Do not tune, re-train, or modify the MG correction logic. The goal is to test whether the existing validated mechanism works reliably in new contexts, not to improve it.

---

## Research Progression Context

```
17.11A
  │ MG research / isolated validation
  ▼
17.12A
  │ frozen mapping + shadow integration  
  │ coefficients: validated and locked
  ▼
17.13B
  │ integration validation (Phase 1-4)
  │ • contract enhancement (category parameter)
  │ • 80/80 tests passing
  │ • 9.39% avg improvement on research benchmark
  │ • MG remains disabled by default
  ▼
17.13C ← YOU ARE HERE
  │ shadow validation (broader context)
  │ • reuse frozen 17.13B exactly
  │ • test generalization
  │ • define production deployment gate
  │ • MG still remains disabled by default
  ▼
Production Activation Decision
  │ (requires 17.13C acceptance criteria met)
  ▼
17.14A (or later)
  │ production rollout phase
```

---

## 1. Acceptance Criteria (DEFINED BEFORE EXECUTION)

### Must Pass: Safety & Consistency

These criteria must be satisfied to proceed to production:

#### A1. MG-Disabled Equivalence (Critical)
```
CRITERION: On any dataset with MG disabled, predictions must be 
           BITWISE IDENTICAL to original SimulationEngine.

MEASUREMENT: Compare 1000+ experiences (production-like dataset)
THRESHOLD: 100% equivalence (no tolerance)
FAILURE CONSEQUENCE: Do not proceed to production
```

**Rationale**: If MG-disabled breaks legacy behavior, the entire system is unsafe.

#### A2. Safety Gate Regression (Critical)
```
CRITERION: All Phase 2 safety gates (G1-G10) must still pass on 
           production-scale dataset.

MEASUREMENT: Run safety gate suite on broader dataset
THRESHOLD: 10/10 gates passing on representative sample
FAILURE CONSEQUENCE: Investigate root cause before production
```

**Rationale**: Safety gates define immutable contracts. Regression indicates systemic issue.

#### A3. Correction Magnitude Stability
```
CRITERION: MG correction magnitudes must remain within validated range.

MEASUREMENT: Capture all correction values on new dataset
THRESHOLD: 
  - 95th percentile correction < 3σ from 17.13B distribution
  - No systematic correction drift (correlation with experience type < 0.2)
FAILURE CONSEQUENCE: Investigate systemic bias before production
```

**Rationale**: Large unexpected corrections indicate the mechanism is encountering out-of-distribution cases.

#### A4. Fallback Rate (Tolerant)
```
CRITERION: Fallback triggering should remain rare and explainable.

MEASUREMENT: Count fallback triggers and categorize reasons
THRESHOLD: Fallback rate < 2% on new dataset
           All fallback reasons documented and acceptable
FAILURE CONSEQUENCE: If fallback rate > 5%, investigate cause
```

**Rationale**: Frequent fallbacks indicate the layer is encountering systematic issues.

### Should Pass: Generalization

These criteria should be satisfied but with some tolerance:

#### G1. Improvement Magnitude (Target)
```
CRITERION: Performance improvement should remain in validated range.

MEASUREMENT: Compute improvement % on new dataset (same metrics)
THRESHOLD: 
  - Median improvement: 6% - 15% (similar to 17.13B: 9.39%)
  - Not significantly worse (< 1% average)
ACCEPTABLE DEVIATION: ±3 percentage points from 17.13B
INFORMATION VALUE: If improvement is lower, understand why
```

**Rationale**: Validates that coefficients generalize to new data.

#### G2. Metric Consistency
```
CRITERION: Relative improvement should hold across metrics.

MEASUREMENT: Compute improvement on MAE, RMSE, R²
THRESHOLD: Improvement direction consistent across all metrics
           Rank order of seeds preserved (if seed-level testing done)
INFORMATION VALUE: Divergence indicates metric-specific issues
```

**Rationale**: Checks robustness to measurement perspective.

#### G3. Experience Type Coverage
```
CRITERION: MG should not systematically favor/disfavor categories.

MEASUREMENT: Compute per-category improvement breakdown
THRESHOLD: No category with > 2x average improvement or < 0.5x
           improvement across all categories
INFORMATION VALUE: Identifies if MG works better for certain types
```

**Rationale**: If MG only helps on specific experience types, production rollout must account for this.

---

## 2. Experimental Design

### 2.1 Dataset Scope

**17.13B**: Narrow research benchmark (5 seeds × 20 held-out, 100 total experiences)

**17.13C**: Broader shadow context (options):

#### Option A: Extended Research Benchmark
```
Configuration:
  - Generate new seeds: 1001, 1002, 1003, 1004, 1005 (or similar)
  - Same ResearchBenchmarkGenerator (deterministic)
  - Same 80/20 train/held-out split
  - Total: 5 new seeds × 100 experiences = 500 experiences

Advantage: Isolates to methodology, not data
Disadvantage: Still narrow (research benchmark)

Verdict: MINIMUM for 17.13C
```

#### Option B: Production-Like Dataset Simulation
```
Configuration:
  - Create 2-3 simulated "student cohorts" 
  - Broader range of skill distributions
  - More diverse action sequences
  - Real-world-like temporal patterns
  - Total: 1000+ experiences

Advantage: More representative of production
Disadvantage: Simulation still has limits

Verdict: RECOMMENDED for 17.13C
```

#### Option C: Hybrid Approach
```
Configuration:
  - Extended research benchmark (Option A) as baseline
  - + Production-like simulation (Option B) for generalization
  - Total: 500 + 1000+ = 1500+ experiences

Advantage: Both rigor and representativeness
Disadvantage: More computation

Verdict: IDEAL (if resources permit)
```

**Recommended**: Option B or C

### 2.2 Baseline Specification

**Critical**: 17.13C must use the EXACT SAME baseline as 17.13B for fair comparison

```python
# Do NOT retrain or re-tune baseline
# Use frozen 17.13B SimulationEngine with MG-disabled
baseline_engine = SimulationEngine(
    mg_config=MGCompatibilityConfig.stage_0_disabled()
)

# Do NOT change benchmark generation
# Use identical ResearchBenchmarkGenerator logic
# (only different seeds)

# Do NOT modify any simulation semantics
# transition_engine, calibration, all unchanged
```

**Verification**: Compare 17.13B held-out baseline predictions (same experiences) on both runs → must be byte-identical

### 2.3 Experimental Protocol

#### Step 1: Generate Dataset
```python
# Generate new shadow dataset using same benchmark logic
# Document:
#   - Seeds used
#   - Experience category distribution
#   - Skill distribution statistics
#   - Action distribution
#   - Any anomalies detected
```

#### Step 2: Compute Baselines
```python
# For each experience:
baseline_pred = legacy_engine.simulate_action(state, action)
legacy_prediction = baseline_pred["predicted_future_state"]
actual_future_state = experience.actual_future_state

# Compute legacy error metrics (MAE, RMSE, R²)
# This is the baseline performance
```

#### Step 3: Apply MG Correction
```python
# For same experience (reuse frozen 17.13B coefficients):
mg_result = mg_engine.simulate_action(
    state, 
    action, 
    category=experience.category  # use available category
)
mg_prediction = mg_result["predicted_future_state"]
mg_metadata = mg_result.get("_mg_metadata", {})

# Capture:
#   - motivation_signal
#   - goals_signal
#   - correction_applied (bool)
#   - correction_value (float)
#   - source (should be "mg")
#   - fallback_triggered (should be False)
```

#### Step 4: Compute Metrics
```python
# For each experience:
legacy_error = abs(legacy_prediction - actual_future_state)
mg_error = abs(mg_prediction - actual_future_state)
improvement = (legacy_error - mg_error) / legacy_error * 100

# Aggregate by experience type, skill level, action category
```

#### Step 5: Evaluate Against Criteria
```
Compare against A1-A4 (critical) and G1-G3 (target):
  ✓ All critical criteria met?
  ✓ Most target criteria met?
  ✓ Any systematic issues identified?
  
If all A1-A4 pass → READY for production consideration
If A1-A4 fail → RETURN to 17.13B investigation
If G1-G3 lower than expected → DOCUMENT for deployment notes
```

---

## 3. MG Configuration for 17.13C

### Configuration Lock

```python
# 17.13C uses EXACT SAME configuration as 17.13B Phase 4B:

mg_config = MGCompatibilityConfig.stage_2_controlled(
    enabled=True,
    rollout_percentage=100.0,  # Full application for validation
    
    # DO NOT MODIFY THESE COEFFICIENTS
    motivation_coefficient=-3.28,  # Use seed-specific values
    goals_coefficient=-4.99,       # from 17.12A frozen set
    intercept_coefficient=5.35,    # (shown here for seed 42)
    
    # Preserve safety settings
    use_motivation_signal=True,
    use_goals_signal=True,
    fallback_enabled=True,
    fallback_on_invalid_signals=True,
    emit_diagnostic_metadata=True,
)

# REASON: Any change to config would confound results
```

### Integration Boundary Lock

```python
# 17.13C must use updated integration boundary from 17.13B:

# Correct usage:
result = engine.simulate_action(state, action, category=category)

# Do NOT revert to:
# result = engine.simulate_action(state, action)  # ← Wrong!
```

---

## 4. Measurement Plan

### 4.1 Per-Experience Capture

For each experience in shadow dataset:

```json
{
  "experience_id": "shadow_001_high_skill_practice",
  "category": "high_skill_practice",
  "initial_state": {...},
  "selected_action": "Interview Prep",
  "actual_future_state": {...},
  "legacy_prediction": {...},
  "legacy_error_mae": 2.5,
  "legacy_error_rmse": 3.1,
  "mg_prediction": {...},
  "mg_error_mae": 2.3,
  "mg_error_rmse": 2.9,
  "improvement_pct": 8.0,
  "mg_metadata": {
    "motivation_signal": 0.5,
    "goals_signal": 0.35,
    "correction_applied": true,
    "correction_value": 0.8,
    "source": "mg",
    "fallback_triggered": false,
    "fallback_reason": null
  }
}
```

### 4.2 Aggregations

```python
# Per-seed aggregation
result_per_seed = {
    "seed": 1001,
    "num_experiences": 100,
    "legacy_mae_mean": 5.8,
    "mg_mae_mean": 5.3,
    "improvement_pct_mean": 8.6,
    "improvement_pct_std": 3.2,
    "fallback_rate": 0.0,
    "safety_gates_passed": "10/10",
}

# Per-category aggregation
result_per_category = {
    "low_skill_practice": {
        "legacy_mae": 6.2,
        "mg_mae": 5.8,
        "improvement_pct": 6.5,
        "count": 20,
    },
    "high_skill_practice": {
        "legacy_mae": 5.4,
        "mg_mae": 5.1,
        "improvement_pct": 5.6,
        "count": 18,
    },
    # ... others ...
}

# Overall summary
summary = {
    "total_experiences": 500,
    "seeds_tested": 5,
    "legacy_mae_mean": 5.75,
    "mg_mae_mean": 5.25,
    "improvement_pct_mean": 8.7,
    "acceptance_criteria_met": True,
    "fallback_rate": 0.2,
    "safety_gates_passed": "50/50",
}
```

---

## 5. Deployment Decision Gate

### If 17.13C Accepts

```
Outcome: READY FOR PRODUCTION ACTIVATION

Next Step: 17.14A Production Rollout
  ├── Stage 1: Shadow rollout (1% traffic, MG enabled but observed)
  ├── Stage 2: Validation rollout (10% traffic, real production data)
  ├── Stage 3: Full rollout (100% traffic)
  └── Rollback plan: Revert to MG-disabled in < 5 minutes

Documentation:
  - 17.13C results artifact
  - Deployment runbook
  - Monitoring dashboard setup
  - Incident response procedures
```

### If 17.13C Rejects (Critical Failure)

```
Outcome: DO NOT ACTIVATE PRODUCTION

Investigation:
  ├── Root cause analysis
  ├── Compare against 17.13B results
  ├── Identify systematic issue
  └── Decision on next steps:
      ├── 17.13D: Narrow refinement
      ├── OR 17.13B: Revert to research baseline
      ├── OR Hold: Wait for new approach

Timeline: 2-3 weeks for investigation + decision
```

### If 17.13C Partial Acceptance (Mixed Results)

```
Outcome: CONDITIONAL ACTIVATION

Example: "Improvement lower than expected but all safety gates pass"

Decision Path:
  ├── Document the limitation
  ├── Define monitoring thresholds
  ├── Establish rollback criteria
  ├── Proceed to 17.14A with caveats
  └── Close monitoring for first 30 days
```

---

## 6. Timeline & Resource Plan

### Phase 6a: Design & Review (1 week)
```
- Finalize 17.13C design
- Get approval on acceptance criteria
- Prepare dataset generation code
- Document measurement plan
```

### Phase 6b: Data Generation & Setup (1 week)
```
- Generate shadow dataset
- Validate baseline reproducibility
- Set up experiment harness
- Pre-validate measurement code
```

### Phase 6c: Execution (1-2 weeks)
```
- Run Phase 1-4 on shadow dataset
- Compute all acceptance criteria
- Generate 17.13C artifacts
- Document results
```

### Phase 6d: Analysis & Decision (1 week)
```
- Present results to team
- Decision on production activation
- Plan next phase (17.14A or other)
```

**Total Estimated Duration**: 4-5 weeks

---

## 7. Constraints & Assumptions

### Constraints

1. **Do NOT modify 17.13B implementation**
   - No tuning of coefficients
   - No changes to MG layer logic
   - No changes to integration boundary
   - Only change: increase dataset scope

2. **Do NOT activate MG as production default**
   - 17.13C remains shadow validation
   - Production continues with MG disabled
   - 17.14A is the production rollout phase

3. **Do NOT skip acceptance criteria**
   - A1-A4 must be checked explicitly
   - All critical gates must pass
   - No waiving safety requirements

### Assumptions

1. **Frozen 17.13B is stable**: No changes to baseline between now and 17.13C execution
2. **Acceptance criteria are achievable**: Based on 17.13B results (9.39% improvement, all gates passing)
3. **Reproducibility holds**: 17.13B behavior repeatable on new seeds
4. **No systemic changes to benchmark**: ResearchBenchmarkGenerator logic unchanged

---

## 8. Success Criteria Summary

### Minimum Requirements (All Must Pass)
- [x] A1: MG-disabled equivalence (100%)
- [x] A2: Safety gates regression (10/10)
- [x] A3: Correction magnitude stability (< 3σ, no drift)
- [x] A4: Fallback rate acceptable (< 2%)

### Target Requirements (Most Should Pass)
- [ ] G1: Improvement magnitude (6-15%, similar to 17.13B)
- [ ] G2: Metric consistency (same direction, all metrics)
- [ ] G3: Experience type coverage (no category > 2x or < 0.5x)

### Go/No-Go Decision
```
IF A1 AND A2 AND A3 AND A4: GO (proceed to production planning)
IF NOT A1 OR A2 OR A3 OR A4: NO-GO (return to 17.13B analysis)
IF (A1-A4 pass) AND (most of G1-G3 pass): GO with monitoring
IF (A1-A4 pass) AND (some G1-G3 fail): CONDITIONAL GO + document caveat
```

---

## 9. Artifact Generation

Upon completion, 17.13C will produce:

```
backend/experiments/results/
├── research_17_13_c_shadow_setup.json          # Dataset config
├── research_17_13_c_shadow_baselines.json      # Legacy predictions
├── research_17_13_c_shadow_phase_1_tests.json  # Unit tests
├── research_17_13_c_shadow_phase_2_gates.json  # Safety gates
├── research_17_13_c_shadow_phase_3_equiv.json  # Disabled equivalence
├── research_17_13_c_shadow_phase_4a_align.json # Reference alignment
├── research_17_13_c_shadow_phase_4b_verify.json # Enabled verification
└── research_17_13_c_shadow_summary.json        # Acceptance decision

RESEARCH_CHECKPOINT_17_13C_SHADOW_VALIDATED.md  # Full results doc
```

---

## 10. Go/No-Go Checklist

Before execution approval:

- [ ] Acceptance criteria reviewed and agreed
- [ ] Dataset scope finalized (Option A, B, or C)
- [ ] Team consensus on deployment decision gate
- [ ] Resources allocated (compute, personnel)
- [ ] Timeline acceptable
- [ ] Rollback plan documented
- [ ] Monitoring dashboard design reviewed
- [ ] No modifications to 17.13B code

---

## Relationship to 17.13B

| Aspect | 17.13B | 17.13C |
|--------|--------|--------|
| **Purpose** | Integration validation | Shadow generalization validation |
| **Dataset** | 5 seeds × 100 (narrow) | 5+ seeds × 1000+ (broader) |
| **Coefficients** | Frozen from 17.12A | REUSE 17.13B exactly |
| **Implementation** | NEW (validation) | LOCK 17.13B (no changes) |
| **MG Status** | Enabled in testing | Enabled in testing |
| **Production Default** | Disabled | Still disabled |
| **Deployment** | Not applicable | Conditional (decision gate) |

**Key Principle**: 17.13C answers "DOES it work?" not "CAN we improve it?"

---

**Status**: READY FOR APPROVAL  
**Next Step**: Review and approve plan, then execute per timeline  
**Do Not Modify**: 17.13B implementation during planning phase
