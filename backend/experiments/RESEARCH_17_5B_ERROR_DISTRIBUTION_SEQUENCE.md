# Phase 17.5B: Error Distribution & Sequence Dynamics Analysis

## Research Question

> **If every individual calibration update has the correct direction, why do some random seeds still produce substantially worse final calibration?**

### Context from 17.5A

Phase 17.5A proved that error direction is preserved **perfectly** (100% accuracy, 1,491/1,491 events) throughout the sign-aware calibration pipeline. This definitively shows:

- ✓ Error signs are computed correctly
- ✓ Deltas are applied in the correct direction
- ✓ Parameter updates preserve directional intent

**So the problem is NOT in individual error-direction mapping.**

## 17.5B Hypothesis

Rather than individual update correctness, we hypothesize that:

**The sequence and distribution of errors — not individual error signs — cause parameter drift and final calibration degradation. Even with 100% directionally-correct updates, persistent error patterns in one direction can accumulate bias.**

## Methodology

### Analyzer Design

The `ErrorDistributionSequenceAnalyzer` computes 5 categories of metrics per seed:

#### 1. Error Balance

- Positive error count and ratio
- Negative error count and ratio
- Mean, median, std dev of signed errors
- Shows whether errors are symmetric or biased

#### 2. Error Magnitude

- Mean, median, max absolute error
- 95th percentile absolute error
- Indicates typical and extreme error sizes

#### 3. Temporal/Sequence Characteristics

- Longest positive error streak
- Longest negative error streak
- Positive-to-negative transitions
- Negative-to-positive transitions
- **5-segment temporal analysis**:
  - Early (0-20% of training)
  - Early-Mid (20-40%)
  - Mid (40-60%)
  - Mid-Late (60-80%)
  - Late (80-100%)
  - Each segment gets its own mean signed error

#### 4. Cumulative Error Trajectory

- Final cumulative (signed) error = sum of all `actual - predicted`
- Final cumulative absolute error = sum of `|actual - predicted|`
- Trajectory arrays for analysis of error evolution over time

#### 5. Category Breakdown

- Per-category error statistics (low_skill_practice, high_motivation, etc.)
- Per-category mean signed and absolute errors
- Identifies which categories drive error patterns

### Execution Model

1. Generate ResearchBenchmarkGenerator(seed) dataset
2. For each training experience (80 per seed):
   - Simulate prediction with current state
   - Compute `actual - predicted` (signed error)
   - Track error in appropriate segment and category
   - Update cumulative error and trajectory
   - Monitor streak patterns and transitions
3. Aggregate all metrics into SeedDistributionResult
4. Repeat for all 5 seeds: [42, 123, 456, 789, 999]

## Key Findings

### Main Comparison Table

| Metric | Seed 42 | Seed 123 | Seed 456 | Seed 789 | Seed 999 |
|--------|---------|----------|----------|----------|----------|
| **Positive errors %** | 68.75% | 65.00% | 70.00% | 63.75% | 67.50% |
| **Negative errors %** | 31.25% | 33.75% | 30.00% | 35.00% | 32.50% |
| **Mean signed error** | 3.2281 | 3.3719 | 3.3469 | 3.0812 | 3.3219 |
| **Mean absolute error** | 5.0531 | 5.2219 | 5.2156 | 5.0312 | 4.9344 |
| **Max absolute error** | 17.50 | 17.75 | 17.25 | 19.00 | 16.50 |
| **Longest pos streak** | 4 | 4 | 4 | 4 | 4 |
| **Longest neg streak** | 2 | 2 | 2 | 3 | 3 |
| **Pos→Neg transitions** | 20 | 23 | 22 | 22 | 22 |
| **Neg→Pos transitions** | 19 | 22 | 21 | 21 | 21 |
| **Final cumulative error** | 258.25 | 269.75 | 267.75 | 246.50 | 265.75 |
| **Final MAE** | 5.0531 | 5.2219 | 5.2156 | 5.0312 | 4.9344 |

### Key Observations

#### ✓ Finding 1: Error Distribution Is Remarkably Similar

All seeds show:
- Positive errors dominate (63-70%)
- Similar error magnitudes (5.0-5.2 MAE)
- Streak patterns nearly identical (longest positive = 4, longest negative = 2-3)
- Few transitions (20-23)

**Implication**: Error distribution per se is NOT what distinguishes seeds.

#### ✓ Finding 2: Final Cumulative Error Shows Variation

| Seed | Cumulative Signed Error | Notes |
|------|-------------------------|-------|
| 42 | 258.25 | Successful (from 17.4A) |
| 123 | 269.75 | Successful |
| **456** | 267.75 | Problematic |
| **789** | 246.50 | Problematic — **LOWEST** cumulative error |
| **999** | 265.75 | Problematic |

**Surprise**: Seed 789 has the LOWEST final cumulative error (246.50), but it's still problematic in 17.4A results.

**Implication**: Total cumulative error magnitude alone doesn't determine final calibration performance. The problem is more subtle than "which direction errors accumulate."

#### ✓ Finding 3: Temporal Segments Show Distinct Patterns

Seed 42 (successful):
- Early: 3.81 → Early-Mid: 3.23 → Mid: 2.64 → Mid-Late: 3.06 → Late: 3.39
- Mean trend: Down in middle, recovery at end

Seed 789 (problematic):
- Early: 2.58 → Early-Mid: 2.81 → Mid: 3.66 → Mid-Late: 3.72 → Late: 2.64
- Mean trend: Up in middle, strong recovery at end

**Implication**: Successful and problematic seeds may have different temporal error **profiles**. Successful seeds show **earlier error amplitude reduction**, while problematic seeds show **elevated mid-training errors**.

#### ✓ Finding 4: Category-Level Variations

All categories show similar mean signed errors across seeds, BUT some asymmetries:

- **project_completion**: Highest positive error across all seeds (12.9–15.6)
- **medium_skill_practice**: High positive error (6.1–7.7)
- **high_skill_practice**: Consistent negative error (-2.8 to -4.0)
- **plateau**: Consistent negative error (-2.6 to -3.8)

**Implication**: Category structure doesn't explain seed differences; error patterns within categories are consistent.

## Critical Interpretation

### What the Data DOES Tell Us

1. **Error distributions are similar**, not seed-dependent
2. **Cumulative error magnitude doesn't correlate with performance** (seed 789 has lowest, but fails)
3. **Temporal segments show variation** in mean signed error evolution
4. **Streaks and transitions** are nearly identical across seeds

### What This Means for the Problem

The seed-dependent failures observed in 17.4A are **not explained by**:

- ✗ Asymmetric error distribution (all balanced ~65-70% positive)
- ✗ Error magnitude differences (all similar MAE ~5.0-5.2)
- ✗ Streak patterns (all have longest positive = 4, longest negative = 2-3)
- ✗ Total cumulative error direction (seed 789 has lowest but still fails)

**The problem must be in**:

1. **HOW errors sequence over time** — not just total magnitude
2. **WHEN maximum errors occur** — early vs late training impact differently
3. **FEATURE INTERACTIONS** — opposing errors on shared parameters
4. **PARAMETER COUPLING** — how one error affects others downstream

## Connections to 17.4A

Recall from 17.4A:

```
Seed 42: MAE = 0.0412 ✓ (best)
Seed 123: MAE = 0.0421 ✓ (good)
Seed 456: MAE = 0.0751 ✗ (poor)
Seed 789: MAE = 0.0782 ✗ (worst)
Seed 999: MAE = 0.0753 ✗ (poor)
```

But 17.5B shows:

```
Final MAE (error magnitude):
Seed 42: 5.0531
Seed 123: 5.2219
Seed 456: 5.2156
Seed 789: 5.0312  ← Similar to seed 42!
Seed 999: 4.9344  ← Best!
```

**Key insight**: The error **magnitude** during training (17.5B) does NOT predict final **calibration quality** (17.4A).

This strongly suggests the problem is NOT raw error magnitude, but how errors interact with the calibration mechanism.

## Recommended Next Steps: 17.5C

Based on 17.5B findings, investigate:

1. **Temporal ordering effects** — Do errors in early vs late training have different impact?
2. **Feature-specific error dynamics** — Which state fields have the problematic sequences?
3. **Calibration parameter trajectories** — How does `expected_state_bias` evolve for problematic seeds?
4. **Error correlation structure** — Do problematic seeds have correlated errors on related features?

## Test Results

✓ **35/35 tests passing** (26 unit + 9 integration)

Test coverage includes:
- Data model validation (all metrics classes)
- Analyzer core methods (sign, percentile, error computation)
- Single-seed analysis end-to-end
- Orchestrator execution across all 5 seeds
- Result serialization to JSON
- Diagnostic properties (comparison structure, measurability, completeness)

## Files Generated

1. **Analyzer**: `backend/experiments/research_error_distribution_sequence_17_5_b.py` (590 lines)
2. **Tests**: `backend/experiments/test_research_error_distribution_sequence_17_5_b.py` (430 lines)
3. **Results**: `backend/experiments/results/research_17_5_b_error_distribution_sequence.json`
4. **Documentation**: This file

## Conclusion

Phase 17.5B successfully **measured and compared** error distribution and sequence dynamics across all 5 seeds. While the analysis reveals that error distributions are remarkably **similar**, not **different**, it also identifies important **temporal variations** in how errors evolve during training.

The key finding is **negative**: raw error distribution and magnitude do NOT explain seed-dependent failures. This **eliminates a hypothesis** and points us toward **feature interaction** and **temporal dynamics** as the true explanatory variables.

This is precisely the diagnostic function 17.5B was designed to fulfill: **identifying what statistical properties DO distinguish successful from unsuccessful seeds.**

**Confidence**: HIGH — Measurements are reproducible, comprehensive, and machine-generated from all 400 training experiences (80 × 5 seeds).

---

## Next Research Phase: 17.5C

**Focus**: Feature-specific temporal dynamics and parameter coupling effects

**Goal**: Identify which state features drive the seed-dependent instability

**Expected outcome**: Precision diagnosis of the root cause, enabling targeted solution in production pipeline
