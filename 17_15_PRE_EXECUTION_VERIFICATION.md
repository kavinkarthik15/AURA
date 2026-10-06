# 17.15 Pre-Execution Verification

**Date:** 2026-08-14  
**Phase:** 17.15  
**Status:** IN PROGRESS (Verification Phase)  
**Objective:** Verify MG-enabled shadow validation is ready to execute

---

## Verification Checklist

### Section A: Code Integrity (MG Frozen Since 17.13B)

**Requirement:** MG code must be unchanged since 17.13B freeze  
**Rationale:** Ensure we're testing the same MG implementation that was validated

- [ ] **A1:** Verify `backend/compatibility/mg_compatibility.py` hash matches 17.13B checkpoint
- [ ] **A2:** Verify `backend/compatibility/mg_config.py` is frozen (immutable dataclass)
- [ ] **A3:** Verify `backend/services/transition_engine.py` unchanged since 17.13B
- [ ] **A4:** Verify `backend/services/simulation_engine.py` only has shadow recorder changes (17.14A)
- [ ] **A5:** Confirm no MG coefficient modifications since 17.13B

**Verification Method:**
```bash
# Verify against 17.13B frozen checkpoint
git diff RESEARCH_CHECKPOINT_17_13B_MG_INTEGRATION_VALIDATED.md
# Should show zero MG logic changes
```

---

### Section B: Configuration & Enablement

**Requirement:** MG config prepared for shadow execution without production impact  
**Rationale:** MG must execute, but only in shadow/observational mode

- [ ] **B1:** Verify `MGCompatibilityConfig.enabled` is correctly set to `False` by default
- [ ] **B2:** Verify runtime override mechanism exists to set `enabled=True` for shadow only
- [ ] **B3:** Verify `rollout_percentage=0.0` (no actual activation)
- [ ] **B4:** Confirm all coefficients frozen from 17.13B
- [ ] **B5:** Verify shadow_event_recorder parameter present in SimulationEngine

**Verification Method:**
```python
from backend.compatibility.mg_config import MGCompatibilityConfig
config = MGCompatibilityConfig()
assert config.enabled == False  # Default is safe
assert config.rollout_percentage == 0.0  # No production activation
# Verify immutability
try:
    config.enabled = True
    assert False, "Config should be frozen"
except FrozenInstanceError:
    pass  # Expected
```

---

### Section C: Production Path Protection

**Requirement:** Production simulation path must remain legacy-controlled  
**Rationale:** 17.15 tests shadow mode; production must never use MG output

- [ ] **C1:** Verify SimulationEngine default path uses legacy_prediction only
- [ ] **C2:** Verify MG computation is guarded by shadow_event_recorder parameter
- [ ] **C3:** Verify state progression uses only legacy prediction
- [ ] **C4:** Verify user history writes unaffected by MG computation
- [ ] **C5:** Confirm production instantiation doesn't pass shadow_event_recorder

**Verification Method:**
```python
from backend.services.simulation_engine import SimulationEngine
from backend.compatibility.mg_config import MGCompatibilityConfig

# Verify default (production) path
engine_prod = SimulationEngine(shadow_event_recorder=None)
# MG should not execute; assert by checking recorder is None

# Verify shadow path
events = []
engine_shadow = SimulationEngine(shadow_event_recorder=events.append)
# MG should execute and append to events
```

---

### Section D: Shadow Recorder Integrity

**Requirement:** Shadow recorder (17.14A) is operational and isolated  
**Rationale:** Observation must not interfere with production; capture all 14 fields

- [ ] **D1:** Verify shadow_event_recorder exception handling (failure isolation)
- [ ] **D2:** Verify all 14 observability fields defined in recorder
- [ ] **D3:** Verify recorder captures mg_shadow_prediction with MG enabled
- [ ] **D4:** Verify recorder captures mg_correction with actual correction values
- [ ] **D5:** Confirm 17.14A tests still pass (baseline recorder correctness)

**Verification Method:**
```python
from backend.tests.test_simulation_engine import *
# Run all 6 tests from 17.14A
# All should pass
pytest backend/tests/test_simulation_engine.py -v
```

---

### Section E: MG Enablement for Shadow (New for 17.15)

**Requirement:** MG must be enableable in shadow mode without affecting production  
**Rationale:** 17.15 is first run where MG actually computes; need controlled activation

- [ ] **E1:** Verify mechanism to enable MG shadow computation (config override or parameter)
- [ ] **E2:** Verify MG enabled config does NOT affect production (still uses legacy)
- [ ] **E3:** Verify signal extraction method is callable and returns valid values
- [ ] **E4:** Verify correction computation method is callable without state mutation
- [ ] **E5:** Verify fallback logic is callable and doesn't crash on errors

**Verification Method:**
```python
from backend.compatibility.mg_compatibility import MGCompatibilityLayer
from backend.services.simulation_engine import SimulationEngine

# Simulate MG enabled scenario
layer = MGCompatibilityLayer(config)
test_state = {"python": 50, "motivation": 0.5}
test_action = "study"
test_category = "low_skill_practice"

legacy_pred = {"success": 0.7, "growth": 0.1}
mg_pred, metadata = layer.apply(legacy_pred, test_state, test_action, test_category)

assert mg_pred is not None, "MG computation should return prediction"
assert metadata.source in ["legacy", "mg", "fallback"], "Metadata should be valid"
```

---

### Section F: Seed Set & Reproducibility

**Requirement:** Seed set is frozen and reproducible  
**Rationale:** 17.15 uses new seeds; must be fixed before execution for reproducibility

- [ ] **F1:** Define seed set for 17.15 (e.g., [1000, 2000, 3000, 4000, 5000, 6000])
- [ ] **F2:** Verify seeds are different from 17.14A (new test scenarios)
- [ ] **F3:** Verify Python random seed can be set and produces deterministic output
- [ ] **F4:** Confirm seed list frozen and documented

**Verification Method:**
```python
import random
import numpy as np

seeds = [1000, 2000, 3000, 4000, 5000, 6000]

for seed in seeds:
    random.seed(seed)
    np.random.seed(seed)
    # Verify deterministic output
    val1 = random.random()
    
    random.seed(seed)
    np.random.seed(seed)
    val2 = random.random()
    
    assert val1 == val2, f"Seed {seed} should be deterministic"
```

---

### Section G: Artifact Integrity from 17.14A

**Requirement:** All 17.14A frozen artifacts must be present and verified  
**Rationale:** 17.15 builds on 17.14A; must preserve previous work

- [ ] **G1:** Verify `17_14A_SHADOW_VALIDATION_EVENTS.json` present (400 events)
- [ ] **G2:** Verify `17_14A_SAFETY_ANALYSIS_RESULTS.json` present
- [ ] **G3:** Verify `17_14A_DECISION_GATE_RESULT.json` present
- [ ] **G4:** Verify `RESEARCH_CHECKPOINT_17_14A_INSTRUMENTATION_FREEZE.json` present
- [ ] **G5:** Verify all checksums match (SHA-256 hashes)

**Verification Method:**
```bash
ls -la d:/AURA/17_14A_*.json
ls -la d:/AURA/RESEARCH_CHECKPOINT_17_14A_*.md
ls -la d:/AURA/RESEARCH_CHECKPOINT_17_14A_*.json
```

---

### Section H: Test Coverage & Baseline

**Requirement:** All pre-17.15 tests pass (regression check)  
**Rationale:** Verify no unintended side effects before new run

- [ ] **H1:** `test_simulation_engine.py` (6 tests for shadow recorder) — ALL PASS
- [ ] **H2:** `test_goal_planner.py` — ALL PASS
- [ ] **H3:** `test_experience_service.py` — ALL PASS
- [ ] **H4:** `test_transition_engine.py` — ALL PASS
- [ ] **H5:** No new test failures since 17.14A baseline

**Verification Method:**
```bash
cd d:/AURA
python -m pytest backend/tests/ -v --tb=short
# All tests must pass; no new failures
```

---

### Section I: Documentation & Readiness

**Requirement:** All 17.15 planning documents complete  
**Rationale:** Clear acceptance criteria and execution plan

- [ ] **I1:** `17_15_EXPERIMENT_MANIFEST.md` — acceptance criteria frozen
- [ ] **I2:** `17_15_PRE_EXECUTION_VERIFICATION.md` — this document complete
- [ ] **I3:** `17_15_PRE_EXECUTION_SUMMARY.md` — status summary created
- [ ] **I4:** `17_15_READY_FOR_EXECUTION.md` — go/no-go decision created
- [ ] **I5:** All constraints documented (no MG activation in production)

**Verification Method:**
```bash
ls -la d:/AURA/17_15_*.md
# All 4 documents should exist
```

---

## Verification Results Summary

### Status by Section

| Section | Name | Status | Notes |
|---------|------|--------|-------|
| A | Code Integrity | ⏳ PENDING | To be verified against 17.13B |
| B | Configuration | ⏳ PENDING | Config immutability to be confirmed |
| C | Production Protection | ⏳ PENDING | Default path verification needed |
| D | Shadow Recorder | ⏳ PENDING | 17.14A test baseline needed |
| E | MG Enablement | ⏳ PENDING | Shadow mode activation to be tested |
| F | Seed Set | ⏳ PENDING | Seeds to be defined and frozen |
| G | Artifact Integrity | ⏳ PENDING | Checksums to be verified |
| H | Test Coverage | ⏳ PENDING | Full test suite to be run |
| I | Documentation | ⏳ PENDING | 17.15 documents to be created |

---

## Gate Decision Logic

### PASS (Ready for Execution)
```
IF all sections A-I are PASS:
  DECISION = READY FOR EXECUTION
  ACTION = Proceed to 17.15 shadow run
  CONSTRAINT = Do not modify any code; only execute
```

### BLOCKED (Not Ready)
```
IF any section is FAIL or BLOCKED:
  DECISION = NOT READY
  ACTION = Investigate failures; fix issues
  CONSTRAINT = Do not execute until all sections pass
```

---

## Next Steps

1. **Execute verification for each section (A-I)**
2. **Document results in 17_15_PRE_EXECUTION_SUMMARY.md**
3. **Apply gate decision in 17_15_READY_FOR_EXECUTION.md**
4. **If PASS: Execute shadow run**
5. **If FAIL: Investigate and iterate**

---

*This verification document will be updated as each section is checked.*
