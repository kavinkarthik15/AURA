#!/usr/bin/env python
"""Quick test of 17.13B implementation."""

import sys
import traceback

print("Testing MGCompatibilityConfig and MGCompatibilityLayer import...")

try:
    from backend.compatibility.mg_config import MGCompatibilityConfig
    print("✓ MGCompatibilityConfig imported successfully")
    
    # Test default config
    config = MGCompatibilityConfig()
    assert config.enabled is False
    assert not config.is_active()
    print(f"✓ Default config: enabled={config.enabled}, is_active={config.is_active()}")
    
    # Test validation
    is_valid, error = config.validate()
    assert is_valid
    print(f"✓ Config validation passed")
    
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from backend.compatibility.mg_compatibility import MGCompatibilityLayer, PredictionMetadata
    print("✓ MGCompatibilityLayer imported successfully")
    
    # Test layer creation
    layer = MGCompatibilityLayer(config)
    print(f"✓ Layer created with config")
    
    # Test disabled mode
    legacy_pred = {
        "current_state": {"python": 50},
        "predicted_future_state": {"python": 55},
        "confidence": 0.8,
    }
    state = {"skills": {"python": 50}}
    
    result, metadata = layer.apply(legacy_pred, state, "Python Project")
    assert result == legacy_pred
    assert metadata.source == "legacy"
    print(f"✓ Disabled mode returns legacy prediction unchanged")
    
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from backend.services.simulation_engine import SimulationEngine
    print("✓ SimulationEngine imported successfully with MG integration")
    
    engine = SimulationEngine(mg_config=config)
    assert hasattr(engine, 'mg_layer')
    print(f"✓ SimulationEngine has MG layer")
    
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL BASIC TESTS PASSED")
print("="*60)
print("\nReady to run 5-seed safety gate tests.")
