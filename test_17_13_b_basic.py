#!/usr/bin/env python
"""17.13B Implementation Basic Test"""

import sys
sys.path.insert(0, '/d:/AURA')

print("=" * 80)
print("17.13B IMPLEMENTATION BASIC TEST")
print("=" * 80)

# Test 1: MGCompatibilityConfig
print("\n[1/3] Testing MGCompatibilityConfig...")
try:
    from backend.compatibility.mg_config import MGCompatibilityConfig
    
    config = MGCompatibilityConfig()
    assert config.enabled is False
    assert not config.is_active()
    is_valid, error = config.validate()
    assert is_valid
    
    print("✓ MGCompatibilityConfig working correctly")
    print(f"  - Default: enabled={config.enabled}, is_active={config.is_active()}")
    
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: MGCompatibilityLayer
print("\n[2/3] Testing MGCompatibilityLayer...")
try:
    from backend.compatibility.mg_compatibility import MGCompatibilityLayer
    
    layer = MGCompatibilityLayer(config)
    legacy_pred = {
        "current_state": {"python": 50},
        "predicted_future_state": {"python": 55},
        "confidence": 0.8,
    }
    state = {"skills": {"python": 50}}
    
    result, metadata = layer.apply(legacy_pred, state, "Python Project")
    assert result == legacy_pred
    assert metadata.source == "legacy"
    
    print("✓ MGCompatibilityLayer working correctly")
    print(f"  - Disabled mode returns legacy unchanged")
    print(f"  - Metadata source: {metadata.source}")
    
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: SimulationEngine integration
print("\n[3/3] Testing SimulationEngine integration...")
try:
    from backend.services.simulation_engine import SimulationEngine
    
    engine = SimulationEngine(mg_config=config)
    assert hasattr(engine, 'mg_layer')
    assert isinstance(engine.mg_layer, MGCompatibilityLayer)
    
    print("✓ SimulationEngine integration working correctly")
    print(f"  - Has mg_layer attribute")
    print(f"  - mg_layer is MGCompatibilityLayer instance")
    
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL BASIC TESTS PASSED ✓")
print("=" * 80)
print("\nImplementation is ready for safety gate validation.")
print("\nNext steps:")
print("  1. Run full safety gate suite: test_mg_safety_gates_17_13_b.py")
print("  2. Run 5-seed disabled-mode equivalence validation")
print("  3. Run 5-seed enabled-mode verification")
