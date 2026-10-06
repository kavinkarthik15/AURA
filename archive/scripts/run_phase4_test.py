#!/usr/bin/env python3
"""Run Phase 4 alignment test with module reloading"""
import sys
import importlib

# Clear cached backend modules
modules_to_clear = [name for name in sys.modules if 'backend' in name]
for name in modules_to_clear:
    del sys.modules[name]

sys.path.insert(0, 'd:\\AURA')

# Now run the test
exec(open('d:\\AURA\\backend\\experiments\\test_mg_phase_4_reference_alignment_17_13_b.py').read())
