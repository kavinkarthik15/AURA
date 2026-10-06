#!/usr/bin/env python3
"""Force reload of modules to test category parameter"""
import sys
import importlib

# Clear any cached imports
modules_to_clear = [name for name in sys.modules if 'backend' in name]
for name in modules_to_clear:
    del sys.modules[name]

sys.path.insert(0, 'd:\\AURA')

from backend.compatibility.mg_compatibility import MGCompatibilityLayer, MGCompatibilityConfig, PredictionMetadata

# Create a test configuration
config = MGCompatibilityConfig.stage_0_disabled()
layer = MGCompatibilityLayer(config)

# Create test inputs
current_state = {"python": 75, "dsa": 70, "machine_learning": 65, "projects": 80}
action = "high_skill_practice"
legacy_prediction = {
    "current_state": current_state,
    "predicted_future_state": {"python": 78, "dsa": 72, "machine_learning": 67, "projects": 82},
    "confidence": 0.8,
    "expected_outcome": "success"
}

# Test with category
try:
    result, metadata = layer.apply(legacy_prediction, current_state, action, category="high_skill_practice")
    print("SUCCESS! Layer accepts category parameter.")
    print(f"Result type: {type(result)}")
    print(f"Metadata type: {type(metadata)}")
except TypeError as e:
    print(f"FAILED with TypeError: {e}")
    import traceback
    traceback.print_exc()
