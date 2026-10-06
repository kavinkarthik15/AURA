#!/usr/bin/env python3
"""Quick test to verify the MG layer accepts category parameter"""
import sys
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
result, metadata = layer.apply(legacy_prediction, current_state, action, category="high_skill_practice")
print(f"Success! Layer accept category parameter.")
print(f"Result keys: {list(result.keys())}")
print(f"Metadata: {metadata}")
