# Phase 17.4A: Multi-Seed Robustness Validation — Critical Findings

## Executive Summary

**Status**: ✗ FAILED — Sign-aware calibration does NOT meet robustness criteria

**Success Criterion**: Sign-aware outperforms on ≥80% of seeds (4/5)  
**Actual Result**: Sign-aware wins on only 40% of seeds (2/5)

## Results by Seed

### Overview Table

| Seed | Original MAE | Sign-Aware MAE | Delta | Winner | Dir Acc (Orig) | Dir Acc (SA) | Δ Acc |
|------|--------------|----------------|-------|--------|------|------|-------|
| 42   | 5.4125 | 5.3125 | -0.1000 | ✓ SA | 75.0% | 75.0% | 0.0% |
| 123  | 5.0750 | 4.9750 | -0.1000 | ✓ SA | 77.5% | 77.5% | 0.0% |
| 456  | 5.2500 | 5.3500 | +0.1000 | ✗ Orig | 78.75% | 78.75% | 0.0% |
| 789  | 4.8250 | 4.9750 | +0.1500 | ✗ Orig | 80.0% | 62.5% | -17.5% |
| 999  | 4.5875 | 4.7125 | +0.1250 | ✗ Orig | 86.25% | 66.25% | -20.0% |

### Statistics

```
Mean original improvement:      0.7575
Mean sign-aware improvement:    0.7225
Mean improvement delta:        -0.0350 (sign-aware WORSE on average)

Median improvement delta:      -0.1000
Min improvement delta:         -0.1500 (seed 789)
Max improvement delta:         +0.1000 (seed 42, 123)

Std deviation of delta:         0.1114

Win rate (sign-aware):          40.0% (2/5)
Seeds with regression:          3/5 (60%)
```

## Critical Issues

### Issue 1: Inconsistent Direction Accuracy on Later Seeds

**Symptoms**:
- Seed 42, 123: Direction accuracy unchanged (both ≈75%)
- Seed 456: Direction accuracy unchanged (78.75%)
- **Seed 789: DEGRADED from 80% → 62.5% (-17.5 percentage points)**
- **Seed 999: DEGRADED from 86.25% → 66.25% (-20 percentage points)**

**Implication**: On seeds 789 and 999, the sign-aware calibrator is making **worse directional predictions**, not just slightly worse MAE but fundamentally different error behavior.

### Issue 2: Majority Seed Regression

**Pattern**:
- Seed 42: +0.1 improvement
- Seed 123: +0.1 improvement
- Seed 456: -0.1 degradation
- Seed 789: -0.15 degradation
- Seed 999: -0.125 degradation

**Trend**: The performance DEGRADES on later seeds (789, 999 are later in the sequence and show worst results).

### Issue 3: Negative-Bias Direction Accuracy Static

**Pattern**: Negative-bias direction accuracy is **identical** between original and sign-aware on ALL seeds:
- Seed 42: 50.0% both
- Seed 123: 60.41% both
- Seed 456: 54.16% both
- Seed 789: 70.84% both
- Seed 999: 66.66% both

**Implication**: The sign-aware calibrator is not improving negative-bias learning on ANY seed. The 17.3B analysis showed it SHOULD differ, but here they're identical. This suggests something is fundamentally different between how the benchmark was set up in 17.3A vs how it's being executed in 17.4A.

## Investigation Hypotheses

### Hypothesis 1: Signed Error Magnitude Issue
The signed errors might be causing excessively large deltas on certain datasets. The learning rate of 0.007 may need seed-dependent adjustment.

### Hypothesis 2: Boundary Interaction
When deltas become negative, they might hit different boundary conditions than the existing calibrator. The `max_delta` constraint (0.12) could interact differently with negative values.

### Hypothesis 3: Dataset-Specific Patterns
Seeds 789 and 999 might have specific error signal patterns that make negative deltas harmful. For example, if those seeds have more symmetric error distributions, the directional information might be less useful.

### Hypothesis 4: Implementation Regression
The 17.3A experiment might have had a subtle difference in setup (e.g., how the comparison is done) that made sign-aware look better on seed 42, but when run identically across all seeds, the mechanism shows weakness.

### Hypothesis 5: Direction Accuracy Metric Interaction
The direction accuracy metric might be particularly sensitive to signed errors on certain seeds, measuring how well the calibrator predicts the direction of future errors. On seeds with higher baseline accuracy (789: 80%, 999: 86%), the sign-aware approach might be introducing noise.

## What 17.3 Didn't Show

Looking back at 17.3A and 17.3B results:
- Both experiments used **only seed 42**
- Both showed sign-aware wins (+0.1 MAE improvement)
- **We did not test sign-aware on any other seed before declaring success**

The 17.2 analysis was correct that error-sign information was lost, but the fix (sign-aware calibrator) may have introduced a **new problem: seed sensitivity**.

## Recommended Next Steps

### Option 1: Investigate the Sign-Aware Mechanism (17.4B Debugging)
- Compare signed error signals across seeds
- Check if deltas are bounded correctly on different seeds
- Verify learned parameters don't diverge unexpectedly
- Adjust learning rate or bound strategy per seed

### Option 2: Revert to Root Cause Analysis (Back to 17.2)
- The problem was error-sign loss in the pipeline
- Instead of changing the calibrator, we could:
  - Use signed errors but with the **existing calibrator formula**
  - Apply absolute value after the directional update was made
  - Use a different mechanism to incorporate sign information

### Option 3: Implement Seed-Aware Calibrator (17.4B Alternative)
- Create variant that adjusts learning rate based on error distribution
- Add adaptive bounds that respond to signed error magnitudes
- Test if seed-specific adaptation helps

### Option 4: Accept Limited Applicability (Documentation)
- Document that sign-aware works well on seeds with certain characteristics
- Create seed classification (which seeds benefit from sign-aware?)
- Recommend using original calibrator unless seeds meet criteria

## Critical Decision Point

**The 17.3 conclusion was premature**. We validated on seed 42 only and declared the fix "ready for production evaluation." Testing on additional seeds reveals:

1. ✗ The improvement does NOT generalize
2. ✗ Direction accuracy DEGRADES on some seeds
3. ✗ No improvement to negative-bias learning (actual identical to original)

**This means 17.4A has discovered a critical limitation in the 17.3 fix that must be addressed before any production deployment.**

## Test Summary

- Total seeds tested: 5
- Seeds where sign-aware wins: 2/5 (40%)
- Seeds with MAE regression: 3/5 (60%)
- Seeds with direction accuracy degradation: 2/5 (40%)
- Seeds with negative-bias improvement: 0/5 (0%)

**Verdict**: The sign-aware calibration mechanism as implemented is NOT robust. Further investigation and refinement required.
