#!/usr/bin/env python
import subprocess
import sys

# Run research tests
print("=" * 80)
print("17.2A Mechanism Analysis Tests")
print("=" * 80)

result = subprocess.run(
    [sys.executable, "-m", "pytest", 
     "backend/experiments/test_research_mechanism_analysis_17_2_a.py",
     "-v", "--tb=short"],
    cwd="D:/AURA"
)

sys.exit(result.returncode)
