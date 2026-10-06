#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from backend.services.simulation_engine import SimulationEngine
import inspect

sig = inspect.signature(SimulationEngine.simulate_action)
print(f"SimulationEngine.simulate_action signature: {sig}")
