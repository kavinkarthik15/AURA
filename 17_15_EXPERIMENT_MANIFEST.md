# 17.15 Experiment Manifest: MG-Enabled Shadow Validation

**Phase:** 17.15  
**Date Created:** 2026-08-14  
**Status:** FROZEN (Planning Phase)  
**Objective:** Validate MG safety under enabled shadow computation

---

## Executive Summary

**17.14A proved:** Instrumentation is safe; production is protected.  
**17.15 must prove:** MG computation is safe when enabled.

This is the first run where MG actually executes (in shadow mode). The goal is to measure MG behavior under realistic conditions and determine if it is safe for production consideration.

### Key Distinction

```
17.14A (MG DISABLED):
  Input → Legacy Prediction → PRODUCTION (only path)
  
17.15 (MG ENABLED in shadow):
  Input → Legacy Prediction → PRODUCTION (authority)
       ↘ MG Shadow Computation → OBSERVATIONAL ONLY (not authority)
```

MG computes, but doesn't override production. We observe what it would do.

---

## Acceptance Criteria Matrix

### Category 1: MG Computation Correctness

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| MG Execution | Signal extraction, correction logic, metadata assembly | All 400+ events complete with mg_shadow_prediction computed | HIGH if no errors |
| Computation Stability | MG logic handles all state categories without exceptions | 0 unexpected MG errors across all categories | HIGH if all categories tested |
| Determinism | Same input (state, action, category) produces same output | Repeated calls with fixed seed produce identical predictions | HIGH if seed validation passes |
| Signal Validity | Motivation and goals signals extract within expected ranges | Signal values fall within documented bounds | MEDIUM (bounds TBD by analysis) |

### Category 2: Legacy Authority & Production Protection

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| Legacy Primacy | Production path controlled by legacy prediction only | `legacy_prediction` is always used for actual state progression | HIGH if verified in code path |
| No Mutation | MG shadow branch does not mutate production state | All state snapshots before/after MG show 0 changes | HIGH if state checksums identical |
| Prediction Integrity | Legacy prediction unaffected by MG shadow execution | `legacy_prediction` matches standalone legacy run | HIGH if artifact comparison succeeds |
| Recovery Path | Production can roll back if MG shadow fails | Fallback triggers, legacy continues, 0 production impact | HIGH if tested in safety suite |

### Category 3: Correction & Fallback Behavior

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| Correction Application | MG corrections computed and recorded in shadow | All correction_applied flags correctly reflect MG output | HIGH if schema valid |
| Correction Magnitude | MG corrections don't wildly diverge from legacy | Correction magnitude distribution within reasonable bounds | MEDIUM (baseline TBD) |
| Fallback Triggering | Fallback logic activates when MG computation fails | Fallback rate > 0% OR confirmed never triggered (both valid) | HIGH if fallback_triggered field accurately reflects |
| Fallback Safety | Fallback logic never corrupts production state | 0 unexpected exceptions during fallback invocation | HIGH if error handling verified |

### Category 4: Latency & Observability

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| MG Latency Measurable | Real MG computation time recorded | mg_latency_ms > 0 for all/most events (not 0 as in 17.14A) | HIGH if latency varies by category |
| Latency Acceptable | MG overhead doesn't create production risk | 95th percentile latency < shadow SLA threshold | MEDIUM (threshold TBD) |
| Observability Complete | All 14 fields populated with MG-enabled data | Same schema completeness as 17.14A | HIGH if audit passes |
| Metadata Integrity | Signals, corrections, errors all correctly recorded | No null/missing values in required observation fields | HIGH if schema validation passes |

### Category 5: State Integrity & Distribution

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| No State Corruption | MG shadow cannot mutate user/simulation state | User history unmodified; simulation state clean | HIGH if checksums match baseline |
| Category Coverage | MG tested across all skill/motivation levels | All 4+ state categories produce valid MG output | HIGH if all categories have events |
| Seed Diversity | Behavior consistent across different random seeds | Same state+action produces expected variance across seeds | MEDIUM (pattern recognition) |
| Pathological Behavior | No unexplained outliers or degenerate cases | Error rate, fallback rate, latency outliers within tolerance | MEDIUM (requires threshold setting) |

### Category 6: Error Isolation & Robustness

| Criterion | Definition | Pass Condition | Confidence |
|-----------|-----------|-----------------|------------|
| MG Errors Caught | MG exceptions don't crash production | mg_error field captures all exceptions; 0 unhandled | HIGH if error types logged |
| Error Recovery | Production continues when MG encounters errors | Fallback or legacy fallthrough succeeds after MG error | HIGH if recovery path tested |
| Observer Reliability | Shadow recorder isolates from MG errors | Recorder exceptions don't affect event capture | HIGH if recorder tested separately (17.14A) |
| Graceful Degradation | MG disabled safely if needed | MG can be disabled at runtime; legacy continues | HIGH if config immutability preserved |

---

## Test Parameters

### Run Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **MG Enabled** | `true` (shadow mode) | First actual MG execution |
| **Simulation Count** | 100+ simulations | Sufficient for statistical behavior |
| **Event Types** | 4 categories (low/med/high skill, edge case) | Cover state space |
| **Seed Strategy** | New seed set (different from 17.14A) | Test generalization |
| **Seed Count** | 6 seeds (or more) | Determinism + distribution testing |
| **Total Events** | 400+ (100 sims × 4 categories) | Comparable to 17.14A |
| **Legacy Baseline** | Run shadow with MG disabled first (optional sanity check) | Confirm identical to 17.14A |
| **Shadow Recorder** | Active (production must be protected) | Capture all 14 observability fields |
| **Fallback Strategy** | Test both "never triggered" and "triggered" scenarios | Verify fallback robustness |

### Seed Set (TBD — to be frozen before execution)

```
Seeds: [1000, 2000, 3000, 4000, 5000, 6000]
(or alternative deterministic sequence)
```

### State Categories (Fixed, from 17.14A)

```
1. Low skill (python=20-30)
2. Medium skill (python=50-60)
3. High skill (python=80-90)
4. Edge case (empty state dict)
```

---

## Safety Questions (17.15 Specific)

### Q1: Does MG computation execute correctly?
**Answer sourced from:** Event analysis  
**Pass criteria:** 
- MG computations complete for all events
- Signal extraction produces valid values
- Corrections computed without exception

### Q2: Does MG remain observational (not authoritative)?
**Answer sourced from:** Legacy vs. MG comparison  
**Pass criteria:**
- Production path uses only legacy prediction
- MG prediction is shadow-only
- State progression unaffected by MG computation

### Q3: Does MG handle errors gracefully?
**Answer sourced from:** Error rate and fallback analysis  
**Pass criteria:**
- Fallback triggers when MG fails (or confirmed never needed)
- All exceptions captured in mg_error field
- 0 unhandled MG errors crash production

### Q4: Is MG latency acceptable?
**Answer sourced from:** Latency distribution  
**Pass criteria:**
- mg_latency_ms > 0 (actual computation happening)
- No pathological outliers (e.g., >5s for shadow)
- Latency consistent across categories (or acceptable variance)

---

## Constraints & Non-Goals

### DO ✅
- [ ] Enable MG in shadow mode for first time
- [ ] Measure actual MG behavior
- [ ] Collect comprehensive observability data
- [ ] Test across all state categories
- [ ] Preserve immutability of frozen 17.14A/17.13B artifacts
- [ ] Use new seeds (generalization test)
- [ ] Document all MG behavior without modification

### DO NOT ❌
- [ ] Activate MG in production/default path
- [ ] Modify MG coefficients based on 17.15 results (save for post-analysis)
- [ ] Tune MG logic mid-run
- [ ] Skip pre-execution verification
- [ ] Modify 17.14A artifacts
- [ ] Claim production readiness before safety analysis
- [ ] Enable MG without shadow recorder protection

---

## Acceptance & Readiness Levels

### READY FOR EXECUTION
- [ ] Pre-execution verification PASSES
- [ ] All frozen artifacts present and checksummed
- [ ] MG config prepared (enabled=True, shadow mode)
- [ ] Seed set frozen
- [ ] Production path verified as legacy-only
- [ ] Shadow recorder confirmed operational

### NOT READY / BLOCKED
- [ ] Pre-execution verification FAILS
- [ ] MG code changes since 17.13B freeze
- [ ] Shadow recorder status uncertain
- [ ] Production code path uncertain
- [ ] Any 17.14A artifact integrity compromised

---

## Exit Criteria

### SUCCESS → Proceed to 17.15 Safety Analysis
- All 400+ events recorded
- MG executed for every event (no skips)
- 0 unhandled MG errors
- Production path confirmed unaffected
- All 14 observability fields populated
- Shadow recorder maintained isolation

### FAILURE → Investigate Before Proceeding
- MG computation crashes (unhandled exception)
- Production path was mutated
- Events lost or corrupted
- Shadow recorder failed
- Significant outliers require explanation

---

## Freeze Checklist

**This manifest is FROZEN when all items are checked:**

- [ ] Acceptance criteria matrix finalized
- [ ] Test parameters defined
- [ ] Safety questions documented
- [ ] Constraints articulated
- [ ] Exit criteria specified
- [ ] Pre-execution verification document complete
- [ ] This manifest checksummed and archived

**Frozen Date:** [Pending pre-execution verification]  
**Frozen By:** Research gate  
**Frozen Hash:** [To be computed]

---

## Next Documents in Sequence

1. ✅ **17_15_EXPERIMENT_MANIFEST.md** (this document) — Acceptance criteria
2. ⏳ **17_15_PRE_EXECUTION_VERIFICATION.md** — Checklist before execution
3. ⏳ **17_15_PRE_EXECUTION_SUMMARY.md** — Status summary
4. ⏳ **17_15_READY_FOR_EXECUTION.md** — Go/no-go decision

---

*This document is immutable. To modify acceptance criteria, create a new frozen version (e.g., 17_15_EXPERIMENT_MANIFEST_v2.md) and document the change rationale.*
