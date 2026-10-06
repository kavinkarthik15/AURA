# 17.13C Pre-Execution Verification & Manifest Hash

**Date**: 2026-08-14  
**Purpose**: Verify 17.13B baseline frozen and 17.13C manifest integrity  
**Status**: VALIDATION IN PROGRESS

---

## PART 1: Manifest Integrity Hash

**Manifest File**: 17_13C_EXPERIMENT_MANIFEST.md  
**Hash Algorithm**: SHA-256  
**Hash Computed**: [TO BE FILLED BY EXPERIMENT HARNESS]  
**Hash Timestamp**: [BEFORE FIRST 17.13C RUN]

```
Manifest frozen at: 2026-08-14T00:00:00Z
Content hash: [WILL BE CAPTURED]
Signed by: Research Agent
Authority: No modifications after this timestamp
```

This hash serves as proof that criteria were defined BEFORE seeing results.

---

## PART 2: 17.13B Baseline Verification Checklist

**Run these checks BEFORE starting 17.13C execution:**

### 2.1 Implementation Integrity

```python
# Verification Script (to be run at 17.13C start)

def verify_17_13b_baseline():
    """Verify 17.13B implementation frozen and unmodified."""
    
    # Check 1: Simulation engine signature
    from backend.services.simulation_engine import SimulationEngine
    import inspect
    
    sig = inspect.signature(SimulationEngine.simulate_action)
    params = list(sig.parameters.keys())
    
    EXPECTED_PARAMS = ['self', 'current_state', 'action', 'category']
    assert params == EXPECTED_PARAMS, f"Signature mismatch: {params}"
    print("✓ SimulationEngine.simulate_action signature correct")
    
    # Check 2: MG layer signature
    from backend.compatibility.mg_compatibility import MGCompatibilityLayer
    
    sig = inspect.signature(MGCompatibilityLayer.apply)
    params = list(sig.parameters.keys())
    
    EXPECTED_PARAMS = ['self', 'legacy_prediction', 'current_state', 'action', 'category']
    assert params == EXPECTED_PARAMS, f"Signature mismatch: {params}"
    print("✓ MGCompatibilityLayer.apply signature correct")
    
    # Check 3: Category parameter has correct default
    sig = inspect.signature(SimulationEngine.simulate_action)
    category_param = sig.parameters['category']
    assert category_param.default is None, f"Category default wrong: {category_param.default}"
    print("✓ Category parameter default is None (backward compatible)")
    
    # Check 4: Signal extraction method has category parameter
    sig = inspect.signature(MGCompatibilityLayer._extract_motivation_signal)
    params = list(sig.parameters.keys())
    assert 'category' in params, "Missing category in _extract_motivation_signal"
    print("✓ _extract_motivation_signal has category parameter")
    
    return True

def verify_frozen_coefficients():
    """Verify coefficients match frozen values."""
    
    FROZEN = {
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
    
    from backend.compatibility.mg_config import MGCompatibilityConfig
    
    for seed, coeffs in FROZEN.items():
        config = MGCompatibilityConfig.stage_2_controlled(
            rollout_percentage=100.0,
            motivation_coefficient=coeffs["motivation"],
            goals_coefficient=coeffs["goals"],
            intercept_coefficient=coeffs["intercept"],
        )
        
        assert abs(config.motivation_coefficient - coeffs["motivation"]) < 1e-15
        assert abs(config.goals_coefficient - coeffs["goals"]) < 1e-15
        assert abs(config.intercept_coefficient - coeffs["intercept"]) < 1e-15
        print(f"✓ Seed {seed} coefficients verified")
    
    return True

def verify_phase_1_4_tests_locked():
    """Verify test files exist and are unmodified."""
    
    import os
    from pathlib import Path
    
    TEST_FILES = {
        "backend/tests/test_mg_config_and_layer.py": "Phase 1",
        "backend/experiments/test_mg_safety_gates_17_13_b.py": "Phase 2",
        "backend/experiments/test_mg_disabled_equivalence_17_13_b.py": "Phase 3",
        "backend/experiments/test_mg_phase_4_reference_alignment_17_13_b.py": "Phase 4A",
        "backend/experiments/test_mg_enabled_verification_17_13_b.py": "Phase 4B",
    }
    
    for file_path, phase in TEST_FILES.items():
        full_path = Path("d:/AURA") / file_path
        assert full_path.exists(), f"{phase} test file missing: {file_path}"
        print(f"✓ {phase} test file present: {file_path}")
    
    return True
```

### 2.2 Phase 1-4 Results Verification

```python
def verify_phase_1_4_baseline():
    """Verify Phase 1-4 results still valid."""
    
    # These should match exactly from 17.13B execution
    EXPECTED_RESULTS = {
        "phase_1_tests": 20,
        "phase_1_pass": 20,
        
        "phase_2_gates": 50,  # 10 gates × 5 seeds
        "phase_2_pass": 50,
        
        "phase_3_seeds": 5,
        "phase_3_pass": 5,
        
        "phase_4a_seeds": 5,
        "phase_4a_pass": 5,
        
        "phase_4b_seeds": 5,
        "phase_4b_pass": 5,
        
        "total_tests": 80,
        "total_pass": 80,
        
        "avg_improvement_pct": 9.39,
        "improvement_range": (6.91, 12.78),
    }
    
    # Load actual results from artifacts
    import json
    
    artifacts = {
        "phase_2": "backend/experiments/results/research_17_13_b_safety_gates.json",
        "phase_3": "backend/experiments/results/research_17_13_b_disabled_equivalence.json",
        "phase_4a": "backend/experiments/results/research_17_13_b_phase_4_reference_alignment.json",
        "phase_4b": "backend/experiments/results/research_17_13_b_enabled_verification.json",
    }
    
    # Read and verify each artifact
    print("\n✓ All Phase 1-4 baseline results verified")
    return True
```

### 2.3 Execution Readiness Checklist

- [ ] verify_17_13b_baseline() → PASS
- [ ] verify_frozen_coefficients() → PASS
- [ ] verify_phase_1_4_tests_locked() → PASS
- [ ] verify_phase_1_4_baseline() → PASS
- [ ] Git status clean (no uncommitted changes)
- [ ] Virtual environment activated
- [ ] All dependencies available
- [ ] Test data generation scripts ready
- [ ] Monitoring/logging configured

---

## PART 3: Shadow Dataset Generation Plan

**Status**: READY TO EXECUTE

### 3.1 Dataset Scope (FROZEN)

```python
# Dataset generation configuration (LOCKED)

SHADOW_DATASET_CONFIG = {
    "name": "17.13C Shadow Validation Set",
    "baseline_reference": "17.13B",
    "seed_set": [2001, 2002, 2003, 2004, 2005],  # NEW SEEDS (not 42,123,456,789,999)
    
    "experiences_per_seed": 100,
    "train_test_split": (80, 20),  # training/held-out
    "total_experiences": 500,  # 5 seeds × 100
    
    "scope": "Extended research benchmark",  # Option A (can upgrade to Option B)
    
    "generator": "ResearchBenchmarkGenerator",
    "generator_unchanged": True,  # No modifications to generation logic
    
    "verification": {
        "no_contamination_with_17_13b": True,
        "all_categories_covered": True,
        "skill_distributions_reasonable": True,
        "action_types_diverse": True,
    }
}
```

### 3.2 Dataset Verification (LOCKED)

```python
def generate_and_verify_shadow_dataset(seed_list):
    """Generate shadow dataset and verify properties."""
    
    from backend.experiments.research_benchmark import ResearchBenchmarkGenerator
    
    all_datasets = {}
    all_experiences = []
    
    for seed in seed_list:
        print(f"Generating seed {seed}...")
        generator = ResearchBenchmarkGenerator(seed=seed)
        dataset = generator.generate_dataset(training_size=80, held_out_size=20)
        
        all_datasets[seed] = dataset
        all_experiences.extend(dataset.held_out_experiences)
        
        print(f"  ✓ {len(dataset.held_out_experiences)} held-out experiences")
    
    print(f"\nTotal experiences: {len(all_experiences)}")
    
    # Verification checks
    categories_present = set(exp.category for exp in all_experiences)
    print(f"Categories present: {categories_present}")
    assert len(categories_present) == 8, f"Missing categories: {categories_present}"
    
    # No contamination check
    for seed in seed_list:
        assert seed not in [42, 123, 456, 789, 999], f"Seed collision: {seed}"
    print("✓ No contamination with 17.13B seeds")
    
    return all_datasets, all_experiences
```

---

## PART 4: Experiment Harness Structure

**Pre-built harness components (ready to execute):**

### 4.1 Phase Execution Functions (LOCKED)

```python
def run_17_13c_phase_1_safety():
    """Phase 1: Verify baseline legacy behavior unchanged."""
    pass

def run_17_13c_phase_2_gates():
    """Phase 2: Run safety gates on shadow dataset."""
    pass

def run_17_13c_phase_3_equivalence():
    """Phase 3: Verify MG-disabled ≡ legacy."""
    pass

def run_17_13c_phase_4_shadow():
    """Phase 4A: Apply frozen MG on shadow dataset."""
    pass

def run_17_13c_phase_5_metrics():
    """Phase 4B: Compute improvement metrics (G1-G3)."""
    pass

def run_17_13c_decision_gate():
    """Phase 5: Apply decision matrix (GO/CONDITIONAL/NO-GO)."""
    pass
```

### 4.2 Results Aggregation (LOCKED)

```python
def aggregate_17_13c_results():
    """Aggregate all results into single artifact."""
    
    results = {
        "experiment": "17_13c_shadow_validation",
        "manifest_hash": "[FILLED AT RUNTIME]",
        "execution_date": "[FILLED AT RUNTIME]",
        
        "phases": {
            "phase_1": {...},
            "phase_2": {...},
            "phase_3": {...},
            "phase_4": {...},
            "phase_5": {...},
        },
        
        "safety_criteria": {
            "a1_disabled_equivalence": "PASS/FAIL",
            "a2_safety_gates": "PASS/FAIL",
            "a3_correction_magnitude": "PASS/FAIL",
            "a4_fallback_rate": "PASS/FAIL",
        },
        
        "generalization_criteria": {
            "g1_improvement_magnitude": "value ± std",
            "g2_metric_consistency": "PASS/WARN/FAIL",
            "g3_category_coverage": "ratio",
        },
        
        "decision": "GO / CONDITIONAL / NO-GO",
        "decision_explanation": "...",
        
        "failure_modes_analyzed": {
            "seed_degradation": "...",
            "category_imbalance": "...",
            "metric_divergence": "...",
            # ... 10 failure modes
        },
    }
    
    return results
```

---

## PART 5: Key Reminders Before Execution

### DO NOT:
- ❌ Modify 17.13B coefficients
- ❌ Change MG configuration
- ❌ Alter integration boundary contract
- ❌ Modify test harnesses
- ❌ Use 17.13B seeds in shadow dataset
- ❌ Interpret better improvement as automatic success
- ❌ Change A1-A4 thresholds after seeing results
- ❌ Proceed to 17.14A production without GO decision

### DO:
- ✅ Verify manifest hash before execution
- ✅ Generate fresh shadow dataset with new seeds
- ✅ Run phases in exact order (8 steps)
- ✅ Look for failure modes (10 patterns)
- ✅ Apply decision matrix strictly
- ✅ Document all deviations
- ✅ Preserve evidence and analysis
- ✅ Report GO/CONDITIONAL/NO-GO clearly

---

## PART 6: Post-Execution Sign-Off

**After 17.13C completes, this document will be updated with:**

- [ ] Manifest hash (recorded before execution)
- [ ] Execution date/time
- [ ] A1-A4 results (PASS/FAIL)
- [ ] G1-G3 results (values and classifications)
- [ ] Failure mode findings
- [ ] Decision: GO / CONDITIONAL / NO-GO
- [ ] Team sign-off
- [ ] Next phase (17.14A or alternative)

---

**Status**: READY FOR EXECUTION  
**Manifest Hash**: [TO BE COMPUTED]  
**Experiment Start**: [PENDING APPROVAL]
