# 17.16B Architecture Inspection — Outcome Generation Mechanism

**Date**: 2026-08-14  
**Status**: Architecture inspection complete  
**Conclusion**: Existing system has legitimate ground truth mechanism ready for 17.16B

---

## Overview

The AURA system already contains a complete state-transition model with ground truth. We can leverage this for 17.16B outcome-based validation.

---

## Component Analysis

### 1. Experience Model (backend/models/experience.py)

**Complete ground-truth record:**

```python
class Experience(BaseModel):
    experience_id: str              # Unique identifier
    timestamp: datetime             # When it occurred
    user_id: str                    # User who had experience
    experience_type: str            # "learning", "project", "course", etc.
    
    state_before: Dict              # ← INITIAL STATE (t)
    action: str                     # ← ACTION TAKEN
    context: Dict                   # ← CONTEXT (motivation, goals, etc.)
    
    state_after: Dict               # ← ACTUAL RESULT (t+1) [GROUND TRUTH]
    state_delta: Dict               # ← ACTUAL CHANGE (state_after - state_before)
    
    outcome_value: float            # ← SUCCESS RATE [0.0, 1.0]
    experience_confidence: float    # ← Confidence in this outcome
    experience_weight: float        # ← Weight for aggregation
```

**Key insight**: `state_after` is the ground truth we need for 17.16B!

---

### 2. TransitionEngine (backend/services/transition_engine.py)

**Makes predictions based on similar experiences:**

```python
def predict_skill_growth(current_state, action) -> Dict:
    """
    Finds similar experiences with that (state, action) pair
    Returns predicted skill gains based on weighted average of similar cases
    """

def predict_success_probability(current_state, action) -> float:
    """
    Returns success probability [0.0, 1.0] based on similar experiences
    """

def predict_future_state(current_state, action) -> Dict:
    """
    Returns current_state + predicted_growth
    This is the LEGACY prediction (no MG correction)
    """
```

**How it works:**
1. Given (state, action) pair
2. Find similar historical experiences
3. Aggregate state_delta values from similar cases
4. Return predicted state (t+1)

---

### 3. SimulationEngine (backend/services/simulation_engine.py)

**Current flow (relevant sections):**

```python
def simulate_action(current_state, action, category=None):
    # Legacy prediction path
    predicted_growth = self.transition_engine.predict_skill_growth(current_state, action)
    future_state = dict(current_state)
    for skill, gain in predicted_growth.items():
        future_state[skill] = int(current_state.get(skill, 0) + gain)
    
    confidence = max(0.0, min(1.0, 0.5 + predicted_success * 0.4))
    
    legacy_prediction = {
        "current_state": dict(current_state),
        "predicted_future_state": future_state,
        "confidence": round(confidence, 2),
        "expected_outcome": self._classify_outcome(predicted_success),
    }
    
    # MG Compatibility Layer Hook
    corrected_prediction, mg_metadata = self.mg_layer.apply(
        legacy_prediction, current_state, action, category=category
    )
    
    return corrected_prediction  # ← Returns final prediction (MG or legacy)
```

**Missing piece**: The current simulation doesn't execute the action or capture actual_state_after.

---

## 17.16B Prediction Horizon Definition

```
TIME:        t           t+1           t+2
             │            │             │
             ↓            ↓             ↓
State(t) ────→ Action ────→ State(t+1)
             │            │             │
             │            │             └─ Actual outcome
             │            │
    ┌────────┴────────┐    │
    │                 │    │
  Legacy          MG    │
prediction       prediction   │
    │                 │    │
    └─────┬───────────┘    │
          │                │
      Predictions   Ground Truth
          │                │
          └────ΔError──────┘
```

**Prediction horizon**: State(t) → State(t+1)
- **Input**: Current state + action taken
- **Prediction**: What should state(t+1) be?
- **Ground truth**: What state(t+1) actually was

---

## Proposed 17.16B Outcome Record

New data structure for paired comparison:

```python
{
    "event_id": str,
    "seed": int,
    "category": str,
    
    # Initial state
    "state_before": Dict,
    
    # Action and context
    "action": str,
    "context": Dict,
    
    # PREDICTIONS (computed from frozen coefficients)
    "legacy_prediction": Dict,      # predict_future_state(state, action)
    "mg_prediction": Dict,          # legacy + mg_correction(...)
    
    # ACTUAL OUTCOME (from experiences or simulation)
    "actual_state_after": Dict,     # Ground truth: what happened
    "actual_state_delta": Dict,     # actual - state_before
    "actual_success_value": float,  # [0.0, 1.0]
    
    # ERROR CALCULATION
    "error_legacy": float,          # |actual - legacy_pred|
    "error_mg": float,              # |actual - mg_pred|
    "delta_error": float,           # error_mg - error_legacy
    
    # STATISTICAL TAGS
    "mg_improved": bool,            # delta_error < 0
    "result_tie": bool,             # delta_error ≈ 0
    "mg_worsened": bool,            # delta_error > 0
}
```

---

## How to Generate Actual Outcomes

**Option 1: Use Historical Experiences (RECOMMENDED)**

```python
# For each prediction event in 17.15 shadow events:

# 1. Match to similar historical experiences
similar_experiences = find_similar_experiences(
    state_before=event["state_before"],
    action=event["action"]
)

# 2. Use aggregated state_delta as ground truth
if similar_experiences:
    actual_state_delta = aggregate_deltas(similar_experiences)
    actual_state_after = state_before + actual_state_delta

# 3. Calculate errors
error_legacy = calculate_error(
    actual_state_after,
    event["legacy_prediction"]["predicted_future_state"]
)
error_mg = calculate_error(
    actual_state_after,
    event["mg_prediction"]["predicted_future_state"]
)
delta_error = error_mg - error_legacy
```

**Strengths**:
- ✅ Uses real historical data
- ✅ Grounded in actual user experiences
- ✅ Legitimate ground truth
- ✅ Repeatable and verifiable

**Limitations**:
- Some (state, action) pairs might have few or no examples
- Outcome is historical average, not deterministic

---

**Option 2: Use Weighted Simulation**

```python
# For each prediction event:

# 1. Predict outcome using TransitionEngine.predict_future_state()
# 2. But use actual historical success rates to simulate outcomes
# 3. Add slight randomness based on outcome_confidence

actual_state_after = legacy_predict_future_state(state, action)
# Add stochastic variation if success is uncertain
if outcome_confidence < 1.0:
    apply_stochastic_variation(actual_state_after, outcome_confidence)
```

**Strengths**:
- All events have outcomes
- Consistent with TransitionEngine logic

**Weaknesses**:
- Outcome is synthetic, not truly ground truth
- Circular: using legacy predictor as "ground truth"
- Less scientifically rigorous

---

**Recommended Approach: Hybrid**

```
Use Option 1 (historical experiences) where available (strong matches)
Fall back to Option 2 (weighted simulation) where few/no matches
Tag each outcome with "evidence_type": "historical" | "simulated"
In analysis, can separate results by evidence type
```

---

## Data Flow for 17.16B

```
17.15 Frozen Events (2,400)
    ├─ Each has:
    │  ├─ state_before
    │  ├─ action
    │  ├─ legacy_prediction
    │  └─ mg_prediction
    │
    ↓
17.16B Outcome Generation
    ├─ For each event:
    │  ├─ Find similar experiences
    │  ├─ Generate actual_state_after
    │  └─ Calculate errors
    │
    ↓
17.16B Outcome Dataset
    └─ 2,400 paired records with:
       ├─ Predictions (legacy, MG)
       ├─ Ground truth (actual)
       ├─ Errors (legacy, MG, Δ)
       └─ Tags (category, seed, evidence type)
    
    ↓
17.16B Statistical Analysis
    ├─ Mean/median ΔError
    ├─ Win/loss/tie distribution
    ├─ Paired significance test
    ├─ Effect size
    ├─ Per-category results
    └─ Per-seed consistency
```

---

## Prediction Horizon Formalization

**For a single prediction event:**

```
Time:    t                         t+1
         │                         │
         ├─ state_before          ├─ actual_state_after [GROUND TRUTH]
         ├─ action                │  (from historical experiences)
         ├─ context               │
         │                         │
    ┌────┴─────┐                  │
    │           │                  │
  Legacy       MG              ├─ COMPARE
  Prediction   Prediction      │
    │           │              │
    └─────┬─────┘              │
          │                    │
          └────────────────────┘
```

**Error Calculation:**

```
Given:
  - S_actual: actual state after (ground truth from experiences)
  - S_legacy: legacy prediction of state after
  - S_mg: MG-corrected prediction of state after

Calculate:
  E_legacy = ||S_actual - S_legacy||   (distance/error)
  E_mg = ||S_actual - S_mg||           (distance/error)
  ΔE = E_mg - E_legacy

Interpret:
  ΔE < 0: MG closer to actual (MG wins)
  ΔE = 0: Equally close (tie)
  ΔE > 0: Legacy closer to actual (Legacy wins)
```

---

## Experience Database Summary

**Current experiences.json contains:**
- ~10-50 historical experiences
- Each with state_before, action, state_after (ground truth)
- outcome_value indicating success
- experience_confidence and experience_weight for aggregation

**Available for 17.16B matching:**
- All 2,400 shadow events from 17.15 can be matched to historical experiences
- Most common actions: "Complete Python Project", "Complete DSA Course", etc.
- Skills tracked: python, dsa, project_mgmt, ml, etc.

---

## Critical Design Decisions for 17.16B

### 1. **Error Metric** ⚠️

Which distance metric for ||S_actual - S_pred||?

**Options:**
- L1 (Manhattan): Sum of absolute differences across skills
- L2 (Euclidean): Square root of sum of squared differences
- Per-skill MAE: Calculate error separately for each skill
- Max difference: Maximum error across any skill

**Recommendation**: L1 (per-skill MAE) most interpretable for this domain

### 2. **Aggregation Across Skills** ⚠️

Skills vary in magnitude (python can be 0-100, goals 0-1).

Should we:
- Normalize before comparison?
- Weight different skills equally?
- Use per-skill analysis as primary?

**Recommendation**: Normalize by skill; report per-skill results separately

### 3. **Event Filtering** ⚠️

Some (state, action) pairs might have no historical examples.

Should we:
- Include all 2,400 events?
- Filter to only "high confidence" matches?
- Separate "high confidence" vs "fallback" in analysis?

**Recommendation**: Include all; tag by confidence level; separate in analysis

### 4. **Statistical Test** ⚠️

Which test for "Did MG significantly improve predictions?"

**Options:**
- Paired t-test (ΔE across events)
- Wilcoxon signed-rank (if non-normal)
- Sign test (just counting wins/losses)
- Bootstrap confidence interval

**Recommendation**: Paired t-test + sign test for robustness

### 5. **Decision Criteria (Pre-defined)** ⚠️

Before running 17.16B, define:

```
IF mean(ΔE) < -0.1 AND p-value < 0.05 AND >60% wins:
    → MG IMPROVED significantly
    
ELSE IF |mean(ΔE)| < 0.05:
    → NO MEANINGFUL DIFFERENCE
    → Discuss complexity vs benefit
    
ELSE IF mean(ΔE) > 0.1 AND p-value < 0.05:
    → MG DEGRADED predictions
    → Reject or revise
```

**Recommendation**: Define thresholds before analysis to avoid p-hacking

---

## Next Steps

### Immediate (17.16B Design):

1. ✅ Inspect existing experience model (DONE)
2. ✅ Confirm ground truth mechanism exists (DONE)
3. 🔄 Design outcome generation logic
   - How to match shadow events to historical experiences?
   - How to handle no-match cases?
   - How to aggregate state_delta?
4. 🔄 Define error metric and normalization
5. 🔄 Design statistical analysis framework

### Then (17.16B Execution):

1. Generate actual_state_after for all 2,400 events
2. Calculate error_legacy and error_mg for each
3. Compute ΔError distribution
4. Run paired statistical tests
5. Produce behavioral verdict

### Key Constraint:

**FREEZE 17.13B COEFFICIENTS DURING 17.16B**

We test the existing coefficients as-is. No tuning until 17.16B completes.

---

## Scientific Hierarchy Reminder

```
17.15: Mechanical Validity       → ✅ PASS
   "Does MG compute correctly?"
   
17.16A: Mechanism Sensibility    → ✅ PASS
   "Is the correction logic well-designed?"
   
17.16B: Behavioral Effectiveness → ⏳ PENDING
   "Do corrections improve accuracy?"
   
17.17: Optimization (if needed)  → ⏳ PENDING
   "Should we tune coefficients?"
   
17.18: Production Readiness      → ⏳ PENDING
   "Is MG ready for production?"
```

**We are NOT at 17.17 yet.** We must complete 17.16B first.

---

**Status**: Architecture inspection complete. Ready to design 17.16B experiment framework.
