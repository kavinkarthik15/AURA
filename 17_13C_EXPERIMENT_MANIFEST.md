# 17.13C Experiment Manifest & Frozen Acceptance Criteria

**Date Created**: 2026-08-14  
**Status**: FROZEN (do not modify after creation)  
**Purpose**: Define exact acceptance criteria BEFORE 17.13C execution  
**Research Question**: Does the frozen 17.13B mechanism generalize safely beyond validated benchmark?

---

## Manifest Version & Hash

**Manifest ID**: 17.13C-MANIFEST-20260814-001  
**Content Hash**: [TO BE COMPUTED BY EXPERIMENT HARNESS]  
**Frozen At**: 2026-08-14 (before first 17.13C run)

---

## SECTION 1: FROZEN 17.13B BASELINE

### 1.1 Implementation Checkpoint

**Frozen Implementation State**:
```
Repository State:
  - backend/services/simulation_engine.py
    ├── Version: 17.13B
    ├── Key change: Line 38 added optional category parameter
    ├── Signature: def simulate_action(..., category: Optional[str] = None)
    └── Hash: [TO BE CAPTURED]
  
  - backend/compatibility/mg_compatibility.py
    ├── Version: 17.13B
    ├── Key changes: Lines 79-90, 194-245
    ├── Added: category parameter support in apply() and _extract_motivation_signal()
    └── Hash: [TO BE CAPTURED]

  - backend/experiments/ test harnesses (LOCKED, NO MODIFICATIONS)
    ├── test_mg_config_and_layer.py (Phase 1)
    ├── test_mg_safety_gates_17_13_b.py (Phase 2)
    ├── test_mg_disabled_equivalence_17_13_b.py (Phase 3)
    ├── test_mg_phase_4_reference_alignment_17_13_b.py (Phase 4A)
    └── test_mg_enabled_verification_17_13_b.py (Phase 4B)

Last Known Good State:
  - All Phase 1-4 tests passing (80/80)
  - Performance: 9.39% average improvement on validated benchmark
  - No outstanding failures or known issues
```

### 1.2 Frozen Coefficients (17.12A)

**These MUST NOT change for 17.13C**:

```python
FROZEN_COEFFICIENTS_17_13C = {
    42: {
        "motivation": -3.2807449219261597,
        "goals": -4.990929117526626,
        "intercept": 5.347402291610499,
    },
    123: {
        "motivation": -2.926512025045623,
        "goals": -5.966840681018364,
        "intercept": 5.4524982305536485,
    },
    456: {
        "motivation": -3.5430610773518003,
        "goals": -4.761399462830821,
        "intercept": 5.364756696601368,
    },
    789: {
        "motivation": -3.102887120621425,
        "goals": -5.896878903382189,
        "intercept": 5.595060650317936,
    },
    999: {
        "motivation": -3.4943725920572044,
        "goals": -5.102878916446432,
        "intercept": 5.383562400207635,
    },
}
```

**Verification**: [Will be checked at experiment start]
```
FOR each seed in {42, 123, 456, 789, 999}:
  ASSERT config.motivation_coefficient == FROZEN[seed].motivation
  ASSERT config.goals_coefficient == FROZEN[seed].goals
  ASSERT config.intercept_coefficient == FROZEN[seed].intercept
RESULT: PASS or FAIL (experiment halts on FAIL)
```

### 1.3 Integration Contract (Locked)

**MG Configuration (UNCHANGEABLE)**:
```python
mg_config = MGCompatibilityConfig.stage_2_controlled(
    enabled=True,
    rollout_percentage=100.0,
    use_motivation_signal=True,
    use_goals_signal=True,
    fallback_enabled=True,
    fallback_on_invalid_signals=True,
    emit_diagnostic_metadata=True,
    # DO NOT CHANGE coefficient_drift_tolerance, rollout_percentage, etc.
)
```

**Integration Boundary (UNCHANGEABLE)**:
```python
# Correct usage (must be used in 17.13C):
result = engine.simulate_action(state, action, category=category)

# Must pass category from experience dataset
# category in {low_skill_practice, medium_skill_practice, high_skill_practice, 
#              low_motivation, high_motivation, mixed_skills, 
#              project_completion, plateau}
```

**Simulation Engine (UNCHANGED FROM PRODUCTION)**:
- TransitionEngine: same semantics
- Calibration: same parameters
- State representations: same format
- Action semantics: unchanged

### 1.4 Benchmark Generation (Frozen)

**ResearchBenchmarkGenerator (UNCHANGED)**:
```python
generator = ResearchBenchmarkGenerator(seed=seed)
dataset = generator.generate_dataset(training_size=80, held_out_size=20)

# Properties:
#   - 100 experiences per seed (80 training, 20 held-out)
#   - Deterministic (seed-based)
#   - Skills: python, dsa, machine_learning, projects (0-100)
#   - Actions: 20 distinct types
#   - Categories: 8 types (low_skill_practice, medium_skill_practice, ...)
#   - No modifications to generation logic
```

---

## SECTION 2: FROZEN ACCEPTANCE CRITERIA

### 2.1 Critical Safety Criteria (A1-A4)

**ALL MUST PASS to proceed beyond 17.13C shadow validation**

#### A1: MG-Disabled Equivalence (CRITICAL)

```
CRITERION: MG-disabled predictions ≡ legacy predictions

MEASUREMENT:
  FOR each experience in shadow dataset:
    legacy_pred = engine_disabled.simulate_action(state, action)
    actual = experience.actual_future_state
    
  COMPARISON: byte-wise equality check
    assert legacy_pred["predicted_future_state"] == legacy_pred_original
    (where legacy_pred_original is from identical run on 17.13B)

THRESHOLD: 100% equivalence (zero tolerance)

RESULT CODES:
  PASS: 100% equivalence ✓
  FAIL: ANY divergence ✗ → STOP (critical safety violation)

INTERPRETATION:
  If A1 fails, the entire system is unsafe.
  Do not proceed to any other checks.
  Investigate root cause immediately.
```

#### A2: Safety Gate Regression (CRITICAL)

```
CRITERION: Phase 2 safety gates (G1-G10) pass on shadow dataset

GATES TO VERIFY (from test_mg_safety_gates_17_13_b.py):
  G1:  Isolation (layer operates independently)
  G2:  Disabled Identity (disabled ≡ legacy)
  G3:  Config Contract (explicit changes only)
  G4:  External Coefficients (no drift)
  G5:  Fallback Rules (deterministic behavior)
  G6:  No State Mutation (immutable state)
  G7:  Observable Source (metadata accurate)
  G8:  Shadow Isolation (no cross-seed leakage)
  G9:  Rollback Config-Only (rollback sufficient)
  G10: Default Disabled (default state safe)

MEASUREMENT:
  Run safety gate suite on shadow dataset
  Aggregate: num_seeds × num_gates = total_gate_tests
  (e.g., 5 seeds × 10 gates = 50 gate tests)

THRESHOLD: 10/10 gates passing per seed (100% pass rate required)

RESULT CODES:
  PASS: ALL gates passing ✓
  FAIL: ANY gate failing ✗ → STOP (contract violation)

INTERPRETATION:
  Safety gates define immutable system contracts.
  Regression indicates systemic problem.
  Do not proceed if any gate fails.
```

#### A3: Correction Magnitude Stability (CRITICAL)

```
CRITERION: MG corrections remain within validated distribution

MEASUREMENT:
  FOR each experience in shadow dataset with MG enabled:
    correction = mg_pred - legacy_pred
    
  Compute per-seed statistics:
    mean_correction_17_13b = 1.036 (example, actual from Phase 4B)
    std_correction_17_13b = σ_17_13b
    
  For shadow dataset:
    correction_values = [all corrections]
    percentile_95 = np.percentile(correction_values, 95)
    percentile_5 = np.percentile(correction_values, 5)
    drift_metric = correlation(correction, experience_properties)

THRESHOLD:
  ✓ 95th percentile < mean + 3σ  (upper bound)
  ✓ 5th percentile > mean - 3σ   (lower bound)
  ✓ |drift_metric| < 0.2         (no systematic bias)
  
  EXCEPTIONS (acceptable):
    - Correction = 0 (no signal, fallback to legacy)
    - Correction ∈ (mean ± 2σ) for < 5% of experiences

RESULT CODES:
  PASS: Within bounds ✓
  WARN: 2-3σ violations in <5% of experiences → log, continue
  FAIL: > 3σ violations OR drift > 0.2 ✗ → STOP

INTERPRETATION:
  Large corrections indicate out-of-distribution encounters.
  If this fails, mechanism is pathological on new data.
  Systematic bias (drift > 0.2) indicates coefficients don't generalize.
```

#### A4: Fallback Rate (CRITICAL)

```
CRITERION: Fallback triggering remains rare and explainable

MEASUREMENT:
  FOR each experience in shadow dataset:
    fallback_triggered = mg_metadata.get("fallback_triggered", False)
    fallback_reason = mg_metadata.get("fallback_reason", None)
    
  Aggregate:
    total_fallbacks = count(fallback_triggered == True)
    fallback_rate = total_fallbacks / num_experiences * 100
    
  Categorize reasons:
    - "Invalid configuration": should be 0
    - "Signal extraction error": should be rare
    - "Invalid signals (NaN, Inf)": should be 0 (indicates bug)
    - "Coefficient drift": should be 0 (coefficients frozen)

THRESHOLD:
  ✓ Fallback rate < 2%
  ✓ Zero "Invalid signals" or "Invalid configuration" failures
  ✓ All fallback reasons documented and acceptable
  
  WARNING thresholds:
    - 2-5% fallback rate: acceptable but investigate
    - > 5% fallback rate: potential systematic issue

RESULT CODES:
  PASS: < 2% fallback rate, all reasons acceptable ✓
  WARN: 2-5% fallback, inspect reasons → continue
  FAIL: > 5% fallback OR invalid reason ✗ → STOP

INTERPRETATION:
  High fallback rate indicates the mechanism is encountering
  systematic issues on new data.
  If > 5%, coefficients don't generalize to shadow domain.
```

---

### 2.2 Generalization Criteria (G1-G3)

**Target criteria (should pass, but with tolerance)**

#### G1: Improvement Magnitude (TARGET)

```
CRITERION: Performance improvement generalizes across datasets

BASELINE (17.13B on validated benchmark):
  Seed 42: 7.92%
  Seed 123: 10.37%
  Seed 456: 9.00%
  Seed 789: 12.78%
  Seed 999: 6.91%
  Mean: 9.39% (locked reference)
  Std: 2.19%
  Range: [6.91%, 12.78%]

MEASUREMENT on shadow dataset:
  FOR each seed in shadow:
    legacy_mae = mean absolute error (legacy predictions)
    mg_mae = mean absolute error (MG predictions)
    improvement_pct = (legacy_mae - mg_mae) / legacy_mae * 100
    
  Per-seed improvement: [seed_improvement_1, ..., seed_improvement_n]
  Mean improvement (shadow): shadow_mean_pct
  Std improvement (shadow): shadow_std_pct

THRESHOLD:
  ✓ PASS: shadow_mean_pct ∈ [6%, 15%]
    (similar range to 17.13B, ±3 percentage points from mean)
  ✓ ACCEPTABLE: shadow_mean_pct ∈ [4%, 18%]
    (broader range, indicates generalization possible but weaker)
  ? CONCERN: shadow_mean_pct < 4% or > 18%
    (significant deviation from validated range)
  ? DEGRADATION: shadow_mean_pct ≤ 0% or negative on any seed
    (MG makes things worse)

RESULT CODES:
  PASS: 6-15% ✓ (strong generalization)
  ACCEPTABLE: 4-18% (acceptable with monitoring)
  CONCERN: < 4% or > 18% (document caveat)
  FAIL: negative avg improvement (MG actively hurts)

INTERPRETATION:
  Lower improvement doesn't mean FAIL, just weaker generalization.
  If improvement is 4-6%, it's within acceptable deviation.
  If any individual seed has negative improvement, investigate that seed.
```

#### G2: Metric Consistency (TARGET)

```
CRITERION: Improvement direction consistent across metrics

MEASUREMENT:
  Compute per-seed improvement on three metrics:
    - MAE: mean absolute error
    - RMSE: root mean square error
    - R²: coefficient of determination
  
  Direction vectors:
    direction_mae = sign(improvement_pct_mae)
    direction_rmse = sign(improvement_pct_rmse)
    direction_r2 = sign(improvement_pct_r2)

THRESHOLD:
  ✓ PASS: All three directions same (all positive or all negative)
  ? WARN: Two out of three same direction (1 outlier metric)
  ? FAIL: Conflicting directions (MG improves one metric while degrading another)

RESULT CODES:
  PASS: Consistent direction across MAE, RMSE, R² ✓
  WARN: One metric diverges (acceptable with note)
  FAIL: Conflicting results (mechanism unstable)

INTERPRETATION:
  If MG improves MAE but worsens RMSE, it's optimizing for
  specific error patterns, not general robustness.
  This might indicate overfitting to 17.13B benchmark.
```

#### G3: Experience Type Coverage (TARGET)

```
CRITERION: MG doesn't systematically favor/disfavor categories

MEASUREMENT:
  Categorize all experiences by type:
    - low_skill_practice
    - medium_skill_practice
    - high_skill_practice
    - low_motivation
    - high_motivation
    - mixed_skills
    - project_completion
    - plateau
  
  Per-category improvement:
    improvement_by_category = {
        "low_skill_practice": 7.2%,
        "high_skill_practice": 11.5%,
        ...
    }
  
  Compute ratio statistics:
    max_improvement / min_improvement = ratio
    std_improvement_across_categories = std

THRESHOLD:
  ✓ PASS: ratio < 1.5 (< 50% variation between categories)
           std < 3 percentage points
  ? WARN: ratio ∈ [1.5, 2.0] (up to 2x variation, acceptable)
  ? FAIL: ratio > 2.0 (MG heavily favors certain types)

RESULT CODES:
  PASS: Balanced improvement across categories ✓
  WARN: Slight category bias (document and monitor)
  FAIL: Heavy category bias (mechanism non-generalizable)

INTERPRETATION:
  If MG only helps high_skill_practice (ratio > 2.0),
  it's not a general improvement mechanism.
  Production deployment must account for category-specific behavior.
```

---

## SECTION 3: FROZEN SHADOW DATASET SPECIFICATION

### 3.1 Dataset Generation

```
Shadow Dataset Scope (MUST BE BROADER THAN 17.13B):

17.13B Validated Set:
  Seeds: 42, 123, 456, 789, 999
  Experiences: 5 × 100 = 500 total
  Scope: Narrow research benchmark

17.13C Shadow Set (NEW):
  Seeds: 2001, 2002, 2003, 2004, 2005 (or similar; deterministic)
  Experiences: 5+ × 100 ≥ 500 new experiences
  
  Option A (Recommended): Extended research benchmark
    - Same ResearchBenchmarkGenerator
    - Different seeds
    - Total: 500-1000 experiences
    
  Option B (Recommended+): Production-like simulation
    - Broader skill distributions
    - More diverse action patterns
    - Real-world-like temporal sequences
    - Total: 1000+ experiences
    
  CHOICE FOR 17.13C: [TO BE DECIDED BEFORE EXECUTION]
```

### 3.2 Dataset Properties (Frozen)

```
Frozen Dataset Properties:

Generator Logic:
  UNCHANGED: ResearchBenchmarkGenerator deterministic generation
  UNCHANGED: 80/20 train/held-out split per seed
  UNCHANGED: Skill range [0, 100] per skill
  UNCHANGED: Action types (same 20 types as 17.13B)
  UNCHANGED: Experience categories (same 8 types)

Verification Before Execution:
  1. Confirm generator produces deterministic results
     (same seed → identical experiences)
  2. Verify category distribution covers all 8 types
  3. Verify skill distributions reasonable (no extreme outliers)
  4. Check action type coverage (all 20 types present)
  5. Verify no data contamination (no overlap with 17.13B held-out)
```

### 3.3 Dataset Separation (Locked)

```
CRITICAL: No data leakage between 17.13B and 17.13C

17.13B Validated:
  Seeds: 42, 123, 456, 789, 999
  Status: DO NOT RE-RUN (results already captured)

17.13C Shadow:
  Seeds: 2001, 2002, 2003, 2004, 2005 (NEW SEEDS)
  Status: Will be generated fresh for this experiment
  
Verification:
  ASSERT seed_17_13c not in {42, 123, 456, 789, 999}
  RESULT: PASS or FAIL (experiment halts on FAIL)
```

---

## SECTION 4: DECISION RULES (FROZEN)

### 4.1 Execution Order (Immutable)

```
17.13C Execution Sequence (MUST RUN IN THIS ORDER):

Step 1: MANIFEST VERIFICATION
  └─ Verify 17.13B baseline frozen
  └─ Verify coefficients match FROZEN_COEFFICIENTS_17_13C
  └─ Verify integration contract in place
  └─ Result: PASS or STOP

Step 2: DATASET GENERATION
  └─ Generate shadow dataset (new seeds)
  └─ Verify no contamination with 17.13B
  └─ Verify category/skill/action distributions
  └─ Result: PASS or STOP

Step 3: LEGACY BASELINE
  └─ Run MG-disabled engine on shadow dataset
  └─ Compute MAE, RMSE, R² for all experiences
  └─ Verify equivalence with 17.13B baseline (spot check)
  └─ Result: PASS or STOP

Step 4: MG SHADOW CORRECTION
  └─ Run frozen 17.13B MG engine on shadow dataset
  └─ Apply frozen coefficients
  └─ Use category parameter for frozen mapping
  └─ Capture all metadata (signals, corrections, fallbacks)
  └─ Result: PASS or continue

Step 5: SAFETY GATE VERIFICATION (A1-A4)
  ├─ A1: Disabled equivalence → PASS or STOP
  ├─ A2: Safety gates G1-G10 → PASS or STOP
  ├─ A3: Correction magnitude → PASS/WARN or STOP
  └─ A4: Fallback rate → PASS/WARN or STOP
  
  After A1-A4:
    ALL PASS → Continue to G1-G3
    ANY FAIL → STOP (no production consideration)

Step 6: GENERALIZATION METRICS (G1-G3)
  ├─ G1: Improvement magnitude → measure and classify
  ├─ G2: Metric consistency → measure and classify
  └─ G3: Category coverage → measure and classify
  
  After G1-G3:
    Result: Document findings (PASS/WARN/CONCERN)

Step 7: STATISTICAL ANALYSIS
  └─ Compare G1-G3 against baseline (17.13B)
  └─ Identify failure modes
  └─ Check for seed-specific anomalies
  └─ Analyze fallback distribution
  └─ Document all deviations

Step 8: DECISION (A1-A4 + G1-G3 → GO/CONDITIONAL/NO-GO)
  (See Section 4.2)
```

### 4.2 Decision Matrix (Frozen)

```
DECISION RULE (DO NOT MODIFY AFTER MANIFEST FROZEN):

┌─────────────────────────────────────────────────────────────────────────┐
│ SAFETY GATES (A1-A4) OUTCOME                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ A1: Disabled equivalence     │ MUST BE: PASS   │ (critical, 0% tolerance)
│ A2: Safety gate regression  │ MUST BE: PASS   │ (critical, 0% tolerance)
│ A3: Correction magnitude    │ MUST BE: PASS   │ (critical, 0% tolerance)
│ A4: Fallback rate           │ MUST BE: PASS   │ (critical, 0% tolerance)
└─────────────────────────────────────────────────────────────────────────┘

IF A1 FAILS → STOP (CRITICAL SAFETY VIOLATION)
             Outcome: NO-GO (do not proceed)
             Action: Investigate root cause, return to 17.13B analysis

IF A1 PASS but A2 FAILS → STOP (GATE CONTRACT VIOLATION)
                          Outcome: NO-GO
                          Action: Investigate gate failure

IF A1-A2 PASS but A3 FAILS → STOP (OUT-OF-DISTRIBUTION)
                              Outcome: NO-GO
                              Action: Coefficients don't generalize

IF A1-A3 PASS but A4 FAILS → STOP (SYSTEMATIC FALLBACK)
                              Outcome: NO-GO
                              Action: Mechanism unstable on new data

IF A1-A4 ALL PASS → Continue to generalization analysis

┌─────────────────────────────────────────────────────────────────────────┐
│ GENERALIZATION CRITERIA (G1-G3) OUTCOME (Only if A1-A4 pass)           │
├─────────────────────────────────────────────────────────────────────────┤
│ G1: Improvement magnitude   │ Target: 6-15%  │ Range: 4-18% acceptable
│ G2: Metric consistency      │ Target: all 3  │ Up to 1 divergence ok
│ G3: Category coverage       │ Target: ratio  │ < 1.5 preferred
│                             │         < 1.5  │
└─────────────────────────────────────────────────────────────────────────┘

IF A1-A4 PASS AND G1-G3 ALL STRONG:
  Outcome: GO ✓
  Rationale: Mechanism generalizes, proceed to production planning
  Decision: Recommend 17.14A production rollout phase
  Monitoring: Standard production monitoring

IF A1-A4 PASS AND G1-G3 MOSTLY ACCEPTABLE:
  Outcome: CONDITIONAL ⚠
  Rationale: Mechanism generalizes but with caveats
  Decision: Proceed with production deployment + enhanced monitoring
  Caveats: Document which criteria slightly missed
           Implement category-specific thresholds if G3 weak
           Monitor improvement metrics closely if G1 lower

IF A1-A4 PASS BUT ANY OF G1-G3 FAILS SIGNIFICANTLY:
  Outcome: CONDITIONAL ⚠ (or NO-GO with justification)
  Rationale: Core safety proven but generalization questionable
  Decision: Proceed ONLY with extreme caution
  Monitoring: Very tight thresholds, auto-rollback on divergence

DECISION CODES:
  GO → Production activation approved
  CONDITIONAL → Production activation with specific conditions
  NO-GO → Return to analysis, do not activate
```

---

## SECTION 5: EXPLICIT FAILURE MODES TO INVESTIGATE

**These are NOT separate tests, but patterns to actively look for in results:**

```
Failure Mode Analysis (look for these in G1-G3 results):

1. SEED-SPECIFIC DEGRADATION
   Question: Are any individual seeds worse than 17.13B?
   Investigation: If seed 789 improves only 2% vs 12.78% in 17.13B,
                  investigate what's different about that seed
   Action: Document seed-level analysis

2. CATEGORY IMBALANCE
   Question: Does MG help only high_skill_practice?
   Investigation: If improvement ratio > 2.0 between categories,
                  MG is not a general mechanism
   Action: If true, production deployment must use category-specific gates

3. METRIC DIVERGENCE
   Question: Does MG optimize for one metric while degrading another?
   Investigation: If MAE improves but R² degrades, indicates overfitting
   Action: Document which metrics respond differently

4. PATHOLOGICAL SIGNALS
   Question: Are motivation/goals signals extreme in new data?
   Investigation: Check percentile distributions; look for extreme values
   Action: If > 5% of corrections > 3σ, mechanism is encountering OOD cases

5. FALLBACK CLUSTERING
   Question: Do fallbacks cluster in specific conditions?
   Investigation: Analyze fallback_triggered by category/action/skill level
   Action: If fallbacks concentrate on certain types, investigate why

6. CORRECTION POLARITY FLIPS
   Question: Do corrections flip sign for similar experiences?
   Investigation: Find pairs of similar experiences with opposite corrections
   Action: Indicates instability or non-smooth correction surface

7. TEMPORAL PATTERN SENSITIVITY
   Question: Does MG struggle with sequences vs single actions?
   Investigation: Compare improvement on single vs multi-step sequences
   Action: If weak on sequences, note in deployment restrictions

8. SKILL DISTRIBUTION EDGE CASES
   Question: Are corrections extreme for edge skill distributions?
   Investigation: Look at experiences with very low (< 20) or high (> 90) mean skill
   Action: If corrections > 2σ on edges, mechanism is brittle

9. ACTION CATEGORY BIAS
   Question: Does MG favor certain actions over others?
   Investigation: Per-action improvement breakdown
   Action: If ratio between actions > 2.0, action-specific tuning needed

10. LEGACY-METADATA MUTATION CHECK
    Question: Does apply() accidentally mutate input state/prediction?
    Investigation: Verify inputs unchanged after apply()
    Action: If ANY mutation detected → CRITICAL FAILURE
```

---

## SECTION 6: STATISTICAL ANALYSIS (Frozen Template)

```
Analysis Script Structure (to run AFTER Step 8 decision):

def analyze_17_13c_results(results):
    """
    Frozen analysis template for 17.13C results.
    Do not add new analysis steps after experiment starts.
    """
    
    # A1: Binary equivalence check
    a1_pass = verify_disabled_equivalence(results)
    
    # A2: Gate pass rate
    a2_pass = (results['safety_gates_passed'] == 50/50)  # 5 seeds × 10 gates
    
    # A3: Correction distribution
    a3_pass = verify_correction_bounds(
        results['corrections'],
        mean=results['baseline_correction_mean'],
        sigma_threshold=3.0,
        drift_threshold=0.2
    )
    
    # A4: Fallback rate
    a4_pass = (results['fallback_rate'] < 0.02)
    
    # G1: Improvement magnitude
    g1_improvement = results['mean_improvement_pct']
    g1_pass = (6.0 <= g1_improvement <= 15.0)
    g1_acceptable = (4.0 <= g1_improvement <= 18.0)
    
    # G2: Metric consistency
    g2_consistent = (results['mae_direction'] == results['rmse_direction'] == results['r2_direction'])
    
    # G3: Category balance
    g3_ratio = results['max_category_improvement'] / results['min_category_improvement']
    g3_pass = (g3_ratio < 1.5)
    
    # Decision
    if not (a1_pass and a2_pass and a3_pass and a4_pass):
        return "NO-GO"
    elif g1_pass and g2_consistent and g3_pass:
        return "GO"
    elif g1_acceptable and g2_consistent:
        return "CONDITIONAL"
    else:
        return "CONDITIONAL_WITH_CAVEATS"
```

---

## SECTION 7: PRE-EXECUTION CHECKLIST

**BEFORE running 17.13C, verify all of these:**

- [ ] 17.13B implementation frozen (no modifications)
- [ ] All coefficients match FROZEN_COEFFICIENTS_17_13C exactly
- [ ] Integration boundary (category parameter) in place
- [ ] Phase 1-4 test harnesses locked (not modified)
- [ ] A1-A4 numerical criteria reviewed and understood
- [ ] G1-G3 numerical criteria reviewed and understood
- [ ] Decision matrix (GO/CONDITIONAL/NO-GO) reviewed
- [ ] Shadow dataset generation procedure finalized
- [ ] Dataset seeds differ from 17.13B (2001, 2002, etc.)
- [ ] Execution order (8 steps) documented
- [ ] Failure modes checklist prepared
- [ ] Statistical analysis template ready
- [ ] Monitoring/rollback plan prepared for production
- [ ] Team alignment on acceptance criteria
- [ ] No modifications planned to MG implementation
- [ ] Coefficients will NOT be re-tuned
- [ ] Results interpretation guidelines clear

---

## SECTION 8: EXPERIMENTAL BOUNDARIES

```
Clean Experimental Boundary:

┌──────────────────────────────────────────────────────────────┐
│ 17.13B VALIDATED (FROZEN)                                    │
│ ├─ Phase 1-4: 80/80 PASS                                   │
│ ├─ Improvement: 9.39% average                              │
│ ├─ Status: IMPLEMENTATION LOCKED                           │
│ └─ Production activation: PENDING 17.13C acceptance         │
├──────────────────────────────────────────────────────────────┤
│ 17.13C MANIFEST SIGNED (THIS DOCUMENT)                      │
│ ├─ Acceptance criteria: FROZEN (A1-A4, G1-G3)              │
│ ├─ Dataset specification: FROZEN                            │
│ ├─ Decision rules: FROZEN                                   │
│ ├─ Status: READY FOR EXECUTION                              │
│ └─ Hash: [TO BE COMPUTED]                                   │
├──────────────────────────────────────────────────────────────┤
│ 17.13C EXECUTION (AFTER MANIFEST FROZEN)                    │
│ ├─ Dataset generation                                        │
│ ├─ Shadow MG application                                    │
│ ├─ Safety checks (A1-A4)                                   │
│ ├─ Generalization analysis (G1-G3)                         │
│ └─ Decision: GO / CONDITIONAL / NO-GO                      │
├──────────────────────────────────────────────────────────────┤
│ POST-17.13C DECISION                                         │
│ ├─ If GO: → 17.14A Production rollout                      │
│ ├─ If CONDITIONAL: → Production + enhanced monitoring      │
│ └─ If NO-GO: → Return to analysis                          │
└──────────────────────────────────────────────────────────────┘
```

---

## SIGN-OFF

**This manifest defines the complete 17.13C experiment specification.**

**Once execution begins, NO MODIFICATIONS to A1-A4 thresholds are permitted.**

**Results interpretation must follow the decision matrix exactly.**

**Failure mode investigation is observational only; it does NOT change pass/fail criteria.**

---

**Manifest Status**: FROZEN  
**Date**: 2026-08-14  
**Ready for Execution**: YES (pending team review)  
**Content Hash**: [WILL BE COMPUTED AT EXPERIMENT START]
