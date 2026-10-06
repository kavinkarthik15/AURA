# 17.16 Schema Analysis — Critical Finding

**Date**: 2026-08-14  
**Status**: Schema inspection complete

---

## Event Schema (2,400 Frozen Events)

Inspected sample events from `17_15_SHADOW_VALIDATION_EVENTS.json`.

Each event contains:

| Field | Type | Example | Purpose |
|-------|------|---------|---------|
| `experience_id` | null | null | Not used |
| `seed` | null | null | Not populated |
| `category` | string | "low_skill_practice" | State classification (4 categories) |
| `action` | string | "Complete Python Basics" | Action attempted |
| `legacy_prediction` | dict | `{predicted_future_state: {...}}` | Original prediction |
| `mg_shadow_prediction` | dict | `{predicted_future_state: {...}}` | MG-corrected prediction |
| `motivation_signal` | float | 0.0 / 1.0 | Signal extracted from state |
| `goals_signal` | float | 0.0875 | Signal extracted from state |
| `mg_correction.correction_value` | float | 4.910695993826919 | Correction magnitude |
| `mg_latency_ms` | float | 22.934900000109337 | Computation latency |
| `fallback_triggered` | boolean | false | Fallback activation |

---

## CRITICAL FINDING: Missing Outcome/Ground Truth

**The 2,400 events do NOT contain actual outcomes.**

```
Current structure:
┌─ legacy_prediction
│  └─ predicted_future_state (e.g., python: 27)
│
├─ mg_shadow_prediction  
│  └─ predicted_future_state (e.g., python: 31.91)
│
└─ mg_correction
   └─ correction_value (e.g., 4.91)

❌ MISSING:
   actual_future_state  ← Ground truth outcome
   real_skill_change    ← What actually happened
   experiment_result    ← Did the action succeed?
```

**Cannot Calculate**:
- Error_Legacy = |predicted_future_state - actual_future_state|
- Error_MG = |predicted_future_state - actual_future_state|
- ΔError = Error_MG - Error_Legacy
- Improvement = Error_Legacy > Error_MG

**Why this matters**: 
The user specified that outcome-based comparison is "much more important than the fact that all eight safety gates passed."

---

## What We CAN Analyze with Current 2,400 Events

### 1. Correction Mechanism Behavior ✅

```
motivation_signal + goals_signal  →  correction_value

Analysis:
- Does higher motivation → larger correction?
- Does higher goals → larger correction?
- Are relationships monotonic?
- Are relationships stable across seeds/categories?
```

**Example queries**:
- For events where motivation=1.0, what's the correction magnitude distribution?
- For events where motivation=0.0, what's the correction magnitude distribution?
- Are corrections consistent: (motivation=1.0, goals=0.25) always produces ~same correction?

### 2. Prediction Differences ✅

```
Prediction_delta = |MG_predicted - Legacy_predicted|

Analysis:
- How much does MG change predictions?
- Does delta vary by category?
- Does delta vary by seed?
- Are deltas within reasonable bounds?
```

**Example queries**:
- Mean delta for low_skill_practice category?
- Mean delta for high_motivation category?
- p95 delta (outlier detection)?

### 3. Category-Level Patterns ✅

```
Category comparison:
    low_skill_practice  →  correction distribution
    project_completion  →  correction distribution
    high_motivation     →  correction distribution
    edge_case           →  correction distribution

Analysis:
- Do different categories behave differently?
- Are corrections sensible for each category?
```

### 4. Seed Consistency ✅

```
Seed comparison:
    [1000, 2000, 3000, 4000, 5000, 6000]

Analysis:
- Are corrections consistent across seeds?
- Are there seed-specific anomalies?
```

### 5. Determinism Validation ✅

```
Input pair: (motivation_signal, goals_signal, category)
    → Always produces same correction_value?

Analysis:
- Full pipeline determinism (not just 2-signal pairs)
- State-to-correction reproducibility
```

---

## What We CANNOT Analyze

❌ **Prediction Accuracy**  
Cannot measure which predictor is correct without actual outcomes.

❌ **Behavioral Improvement**  
Cannot calculate ΔError or say "MG is better/worse."

❌ **Effectiveness vs Frozen Coefficients**  
Cannot validate whether 17.13B coefficients are optimal for seeds [1000-6000].

❌ **Production Readiness**  
Cannot say "MG improves real-world predictions."

---

## Three Options to Proceed

### Option A: Correction Pattern Analysis (Current 2,400 Events)

**Scope**: Analyze correction behavior, signals, patterns  
**Produces**:
- Signal-correction relationships
- Category-level behavior
- Correction distributions
- Consistency checks
- Mechanism validation

**Cannot Answer**: "Does MG improve accuracy?"

**Cost**: Low (analyze existing data)  
**Status**: Complete within 17.15 frozen artifact  
**Recommendation**: ✅ Start here

---

### Option B: New 17.16 Experiment with Outcome Capture

**Scope**: Execute predictions, measure actual outcomes, calculate errors  
**Produces**:
- ΔError = Error_MG - Error_Legacy per event
- Improvement rate (% of events where MG improves)
- Statistical significance
- Per-category effectiveness

**Answers**: "Does MG improve accuracy?" ✅

**Cost**: New experiment, outcomes must be generated  
**Status**: Would create new 17_16_SHADOW_VALIDATION_EVENTS_WITH_OUTCOMES.json  
**Requirement**: Define what "outcome" means (simulation? real skill measurement?)

---

### Option C: Two-Phase Approach

**Phase 1 (17.16A)**: Correction pattern analysis on current 2,400 events  
- Validates mechanism is sensible
- Produces correction behavior report
- Low cost, immediate

**Phase 2 (17.16B)**: Design outcome-based validation  
- Run new predictions with outcome capture
- Measure improvement
- Answers the core behavioral question

---

## Recommendation

**Start with Option A (17.16A): Correction Pattern Analysis**

This will:
1. ✅ Analyze correction mechanism sensibility
2. ✅ Validate signal extraction is working
3. ✅ Check for category-level anomalies
4. ✅ Confirm determinism across full pipeline
5. ✅ Identify edge cases or problematic patterns

**Then Plan 17.16B**: Outcome-based validation  
This will:
1. ✅ Answer "Does MG improve accuracy?"
2. ✅ Provide statistical significance
3. ✅ Determine production readiness

---

## Next Steps

### If proceeding with Option A (17.16A Analysis):

Build analysis script to produce:

```json
{
  "analysis": "17_16_CORRECTION_PATTERN_ANALYSIS",
  "phase": "17.16A",
  "events_analyzed": 2400,
  
  "sections": [
    "A. Overall Correction Distribution",
    "B. Signal-Correction Relationships", 
    "C. Category Comparison",
    "D. Seed Comparison",
    "E. Determinism Validation",
    "F. Anomaly Detection",
    "G. Mechanism Sensibility Assessment",
    "H. Readiness for 17.16B Outcome Study"
  ],
  
  "output_files": [
    "17_16_BEHAVIORAL_ANALYSIS_PATTERNS.json",
    "17_16_BEHAVIORAL_ANALYSIS_PATTERNS.md"
  ]
}
```

### If replanning for Option B (17.16B Design):

Design experiment to:
1. Define "actual outcome" (simulation execution? real measurement?)
2. Capture ground truth for all 2,400 prediction scenarios
3. Calculate error deltas
4. Produce outcome-based verdict

---

## Key Insight for User

**What the frozen 17.15 events CAN prove**:
- MG computation is deterministic and reliable
- Corrections are numerically stable
- Mechanism responds to signals appropriately

**What frozen 17.15 events CANNOT prove**:
- Whether corrections improve accuracy
- Whether coefficients are optimal
- Whether MG should be activated

**17.16A will validate**: Mechanism sensibility  
**17.16B will validate**: Behavioral effectiveness  
**Both together will validate**: Production readiness

---

**Status**: Schema analysis complete, ready for user direction on A / B / C approach.
