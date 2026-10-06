# 17.10D: Mapping Equivalence / Controlled Reproduction — Results & Conclusion

## Experiment Overview

**Objective:** Determine whether the 17.9 MGB improvement can be reproduced inside the real 17.10A compatibility boundary when the mathematical mapping is held exactly constant.

**Design:** Compare the exact 17.9 correction coefficients when applied directly versus when routed through the 17.10B integration path.

**Result:** The 17.9 mapping reproduces identically, but the 17.9 "improvement" is not reproducible across all five seeds.

---

## Key Finding

```
17.9 mapping IDENTICAL to 17.10B mapping
        ↓
But 17.9 MGB improvement is SEED-DEPENDENT
        ↓
MGB > MG only on seeds 42, 123
MGB < MG on seeds 456, 789, 999
```

This reveals the root cause of the apparent 17.9 ↔ 17.10B contradiction:

> **The problem is not the compatibility boundary or the mapping. The problem is that the 17.9 experiment itself did not produce a stable, reproducible improvement across all seeds.**

---

## Gate Results Summary

| Gate | Description | Result | Evidence |
|------|---|---|---|
| **1** | Mapping Equivalence | ✅ PASS 5/5 | Coefficient structure is correct; models fit properly |
| **2** | Legacy Invariance | ✅ PASS 5/5 | M=G=B=0 equals Legacy exactly |
| **3** | MGB Reproduction | ⚠️ PARTIAL 2/5 | Seeds 42, 123 only |
| **4** | Incremental Behavior | ⚠️ PARTIAL 2/5 | Only 2 seeds show Δ < -1% |
| **5** | Causal Activation | ✅ PASS 5/5 | All dimensions cause prediction changes |

**Gate 3 & 4 failure:** MGB does not reproduce the 17.9 improvement consistently.

---

## Per-Seed Analysis

### Seed 42: ✅ MGB improves MG
- ΔMAE (MGB − MG): **−0.1014**
- Gate 3: ✅ PASS
- Gate 4: ✅ PASS

### Seed 123: ✅ MGB improves MG
- ΔMAE (MGB − MG): **−0.0673**
- Gate 3: ✅ PASS
- Gate 4: ✅ PASS

### Seed 456: ❌ MGB worsens MG
- ΔMAE (MGB − MG): **+0.1545**
- Gate 3: ❌ FAIL
- Gate 4: ❌ FAIL

### Seed 789: ❌ MGB worsens MG
- ΔMAE (MGB − MG): **+0.0022**
- Gate 3: ❌ FAIL
- Gate 4: ❌ FAIL

### Seed 999: ❌ MGB worsens MG
- ΔMAE (MGB − MG): **+0.0505**
- Gate 3: ❌ FAIL
- Gate 4: ❌ FAIL

---

## Critical Insight

The 17.9 experiment reported that MGB < MG (improvement), but this was **only true for seeds 42 and 123**.

When the same 17.9 correction model is applied to seeds 456, 789, and 999, **Behavior actually hurts performance**.

This means:

1. **Behavior is not a robust global improvement.** It helps some seeds and hurts others.
2. **The 17.9 conclusion was overstated.** The experiment cherry-picked favorable seeds or the "improvement" was an artifact of the correction model fitting rather than a true signal.
3. **The compatibility boundary is working correctly.** It reproduces the 17.9 semantics exactly.
4. **The root cause was behavior all along.** Not the boundary, not the mapping, but the feature itself.

---

## Research Chain Conclusion

```
17.9: "MGB improves MG"
   │
   └─→ 17.10A: Compatibility layer disabled
       │
       └─→ 17.10B: Integration test
           │       Result: MGB > MG (regression)
           │
           └─→ 17.10C: Diagnostic
               │       Result: Behavior is contextually useful, not robust
               │
               └─→ 17.10D: Controlled reproduction
                   │       Result: 17.9 mapping is correct,
                   │              but improvement is NOT reproducible
                   │              across all seeds
                   │
                   └─→ CONCLUSION: Behavior fails the reproducibility test
```

---

## Final Research Position

### Primary Candidate
**Motivation + Goals (MG)**

**Justification:**
- Reproduces consistently across all five seeds
- No seed-dependent variance
- Stable integration through 17.10A boundary
- Does not require post-hoc tuning

### Experimental Candidate
**Motivation + Goals + Behavior (MGB)**

**Status:** Research artifact only

**Justification:**
- Fails reproducibility gate (2/5 seeds)
- Fails incremental behavior gate (2/5 seeds)
- Seed-dependent improvement suggests overfitting or noise
- Cannot be recommended for production

### No Production Activation

All new representations remain research-only. No production path is activated at this stage.

---

## Recommendation for Next Steps

### If production representation is needed:
1. **Use Motivation + Goals** as the foundation.
2. Do not include Behavior without further investigation.

### If further research is desired:
1. **Investigate why Behavior helps seeds 42, 123 but hurts 456, 789, 999.**
   - Is it a data artifact?
   - Is it a seed-specific feature distribution?
   - Is the behavior signal too coarse?

2. **Consider alternative feature constructions** (not tuning toward MGB).
   - Different behavior normalization
   - Action-conditioned behavior
   - Temporal behavior patterns

3. **Do not proceed to 17.10E (shadow validation) with MGB** until reproducibility is established.

---

## Artifact Location

[research_17_10_d_mapping_equivalence.json](../results/research_17_10_d_mapping_equivalence.json)

Contains per-seed coefficients, gate results, and evidence for this conclusion.
