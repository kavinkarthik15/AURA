#!/usr/bin/env python3
"""Run Phase 4 enabled verification test"""
import sys
import os

# Clear cached backend modules
modules_to_clear = [name for name in sys.modules if 'backend' in name]
for name in modules_to_clear:
    del sys.modules[name]

sys.path.insert(0, 'd:\\AURA')
os.chdir('d:\\AURA')

# Run the test
with open('d:\\AURA\\backend\\experiments\\test_mg_enabled_verification_17_13_b.py', 'r') as f:
    code = f.read()
    exec(code, {'__name__': '__main__', '__file__': 'd:\\AURA\\backend\\experiments\\test_mg_enabled_verification_17_13_b.py'})
