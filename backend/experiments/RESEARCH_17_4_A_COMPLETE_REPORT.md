# Phase 17.4A: Multi-Seed Robustness Validation — Complete Report

## Executive Summary

**Status**: ✗ CRITICAL FAILURE — Sign-aware calibration mechanism discovered to be **unstable across random seeds**

**Test Criterion**: Sign-aware must outperform baseline on ≥80% of seeds (4/5)  
**Actual Performance**: Only 40% win rate (2/5 seeds)  
**Direction Accuracy**: Degraded by 17-20 percentage points on later seeds  
**Risk Level**: 🔴 HIGH — Not production-ready

---

## 17.4A Experimental Design

**Purpose**: Validate that Phase 17.3 sign-aware calibration fix generalizes across independent random seeds, confirming that improvement isn't specific to seed=42.

**Methodology**:
- Test 5 seeds: [42, 123, 456, 789, 999]
- Each seed runs: original calibrator AND sign-aware calibrator
- Compare metrics: MAE, direction accuracy, negative-bias accuracy
- Success criterion: sign-aware wins on ≥4/5 seeds

**No algorithm changes during 17.4A** — Pure validation experiment.

---

## Results Summary

### Per-Seed Breakdown

| Seed | Original MAE | Sign-Aware MAE | Δ MAE | Δ Dir.Acc | Winner | Status |
|------|------|------|-------|------|--------|--------|
| 42 | 5.4125 | 5.3125 | -0.1000 | 0.0% | ✓ SA | PASS |
| 123 | 5.0750 | 4.9750 | -0.1000 | 0.0% | ✓ SA | PASS |
| 456 | 5.2500 | 5.3500 | +0.1000 | 0.0% | ✗ Orig | FAIL |
| 789 | 4.8250 | 4.9750 | +0.1500 | -17.5% | ✗ Orig | CRITICAL |
| 999 | 4.5875 | 4.7125 | +0.1250 | -20.0% | ✗ Orig | CRITICAL |

### Aggregate Statistics

```
Total seeds tested:                    5
Sign-aware wins:                       2 (40%) ✗ BELOW 80% THRESHOLD
Sign-aware losses:                     3 (60%)
Seeds with MAE regression:             3 (60%)
Seeds with direction accuracy drop:    2 (40%, both -17% to -20%)

Mean original improvement:             +0.7575 MAE
Mean sign-aware improvement:           +0.7225 MAE
Mean improvement delta (SA - Orig):    -0.0350 (sign-aware WORSE on average)

Direction Accuracy Changes:
  Seed 42:   0.0% (unchanged)
  Seed 123:  0.0% (unchanged)
  Seed 456:  0.0% (unchanged)
  Seed 789:  -17.5% (80% → 62.5%) 🔴 CRITICAL
  Seed 999:  -20.0% (86% → 66%) 🔴 CRITICAL
```

---

## Critical Findings

### Finding 1: Sign-Aware Calibrator Loses Consistently

**Pattern**: Performance degrades as seeds advance

```
Seed 42  (first)  → +0.1000 improvement (WIN)
Seed 123 (second) → +0.1000 improvement (WIN)
Seed 456 (third)  → -0.1000 degradation (LOSS)
Seed 789 (fourth) → -0.1500 degradation (LOSS) + Direction ACC -17.5%
Seed 999 (fifth)  → -0.1250 degradation (LOSS) + Direction ACC -20.0%
```

**Implication**: The improvement from 17.3A (seed 42) does NOT generalize. The fix has introduced a **seed-dependent vulnerability**.

### Finding 2: Direction Accuracy Catastrophically Degrades

Seeds 789 and 999 show massive direction accuracy drops:

```
Seed 789:  80.00% → 62.50% (loss of 17.5 percentage points)
Seed 999:  86.25% → 66.25% (loss of 20.0 percentage points)
```

**Category-level degradation (Seed 789 example)**:
- low_skill_practice: 100% → 75% (-25%)
- medium_skill_practice: 100% → 75% (-25%)
- low_motivation: 91.67% → 66.67% (-25%)
- high_motivation: 100% → 75% (-25%)
- mixed_skills: 100% → 75% (-25%)
- project_completion: 100% → 75% (-25%)

These aren't minor regressions — they're systematic **degradation across 7/8 categories**.

### Finding 3: Over-Correction in Learned Biases

Debug analysis of seed 789 reveals the sign-aware calibrator is **aggressively over-correcting**:

```
Parameter Changes (Seed 789):
  dsa:                   2.6250 → 0.3360  (-87.2%)
  machine_learning:      3.2580 → 2.8520  (-12.5%)
  projects:              3.2920 → 2.7950  (-15.1%)
  python:                2.7020 → -0.0350 (-101.3%, REVERSED SIGN!)

Average bias reduction:  -49.2%
```

**Critical Issue**: The `python` bias reverses sign (-0.035 instead of +2.702), fundamentally changing the direction of correction.

**Root Cause**: The learning rate (0.007) that works well with absolute errors is **too aggressive** when applied to signed errors, which can accumulate as large negative deltas.

### Finding 4: Negative-Bias Direction Accuracy Unchanged

**Expected**: Sign-aware should improve negative-bias category accuracy.  
**Actual**: Identical to original on ALL seeds.

```
Seed 42:   50.0% (both) — IDENTICAL
Seed 123:  60.4% (both) — IDENTICAL
Seed 456:  54.2% (both) — IDENTICAL
Seed 789:  70.8% (both) — IDENTICAL
Seed 999:  66.7% (both) — IDENTICAL
```

This means the mechanism is **not learning more correct directions for negative-bias categories as 17.3B promised**.

---

## Root Cause Analysis

### The Over-Correction Problem

**Formula Comparison**:
```
Original:    delta = 0.007 × |error|        (always positive, max 0.0012)
Sign-aware:  delta = 0.007 × signed_error  (can be ±0.0070 or more)
```

When seed 789's error distribution has many **large negative signed errors**, the calibrator accumulates large negative deltas, pushing biases far below their optimal values.

**Example**: If high_skill_practice receives -7, -8, -9 signed errors:
```
Original:  delta = 0.007 × 7 = +0.049  (increases expected_state_bias)
Sign-aware: delta = 0.007 × (-7) = -0.049  (decreases expected_state_bias)
```

Across many such experiences, the sign-aware version can push the bias negative, which is **worse than not adjusting at all**.

### Why Seed 42 and 123 Work

On seeds 42 and 123, the error distributions are apparently more balanced or symmetric, so the signed corrections don't over-correct.

On seeds 789 and 999 (which already have high original accuracy ~80-86%), the signed errors create **too much correction**, introducing noise into an already-good calibration.

---

## Why 17.3 Didn't Catch This

1. **Single-seed validation**: 17.3A and 17.3B only tested seed=42
2. **No robustness check**: Didn't validate across multiple seeds before declaring "ready for evaluation"
3. **17.2 was correct about problem**: Error-sign loss WAS the issue
4. **17.3 solution has limitations**: Restoring sign information without proper safeguards causes over-correction

---

## Decision Point: What Went Wrong

The 17.3 fix attempted to solve the root cause (lost error signs) but introduced a **new problem: seed-dependent instability**.

**Three possible explanations**:

1. **Learning Rate Too Aggressive** (Most Likely)
   - The 0.007 rate works for absolute errors but not signed errors
   - Solution: Reduce to ~0.003-0.004 for sign-aware variant

2. **Bounds Insufficient**  
   - The 0.12 max_delta bound works for positive deltas but not the full ±range of signed deltas
   - Solution: Implement separate bounds for signed errors

3. **Fundamental Mechanism Flaw**
   - Using raw signed errors with learning rate optimization may not be the right approach
   - Solution: Use signs but with absolute magnitude formula (alternative approach)

---

## What This Means for Production

### ✗ Cannot Deploy Current Sign-Aware Variant
- 60% of seeds show degradation
- 40% of seeds show critical direction accuracy loss
- Parameter convergence is unstable across seeds

### ✓ Error-Sign Loss Problem Is Real
- 17.2D analysis correctly identified asymmetric learning
- The problem exists; the solution needs refinement

### ⚠️ Next Phase Must Address This
- Implement safeguards against over-correction
- Validate with multiple seeds before calling "ready"
- Consider alternative approaches to incorporating sign information

---

## Recommended Next Actions

### Option 1: Refine Sign-Aware Calibrator (17.4B)
1. **Reduce learning rate** for sign-aware to 0.003-0.004
2. **Add adaptive bounds** that scale with signed error magnitude
3. **Validate on same 5 seeds** — must achieve ≥80% win rate
4. **Test on balanced dataset** (don't rely on 75-25 imbalance)

### Option 2: Alternative Fix Strategy (17.4C)
1. Keep signed errors in pipeline (correct)
2. But apply formula: `delta = learning_rate * abs(signed_error) * sign(signed_error)`
3. This uses sign information but with bounded magnitude
4. May avoid over-correction while preserving directional information

### Option 3: Hybrid Approach (17.4D)
1. Use original calibrator by default
2. Only use sign-aware when error distribution is balanced
3. Add seed-dependent calibrator selection logic

---

## Timeline

**What Happened**:
- ✓ Phase 17.2: Correctly identified asymmetric learning (error-sign loss)
- ✓ Phase 17.3: Implemented sign-aware fix, validated on seed 42
- ✗ Phase 17.4A: Discovered fix doesn't generalize to other seeds

**Where We Are**:
- Confirmed: Error-sign information IS needed
- Problem: Naive application causes over-correction
- Status: Back to the drawing board for implementation

**What's Next**:
- Implement refined sign-aware mechanism with safeguards
- OR explore alternative approaches to incorporating sign information
- Validate across all 5 seeds before production deployment

---

## Test Summary

**Unit Tests**: 
- 11/11 pass (17.4A specific tests)
- 142/142 pass (entire test suite)

**Integration**:
- No regressions in backend tests
- All 17.1, 17.2, 17.3 tests still passing

---

## Conclusion

Phase 17.4A has revealed a critical limitation in the Phase 17.3 sign-aware calibration fix. While the identification of error-sign loss (Phase 17.2) was correct, the solution of using raw signed errors with the existing learning rate creates **instability across different random seeds**.

The fix must be refined before any production deployment. The next phase (17.4B or alternative) should focus on implementing safeguards against over-correction while preserving the directional information that is genuinely needed.

**Bottom Line**: The sign-aware mechanism is **not production-ready** in its current form. Further development required.
