#!/usr/bin/env python3
"""Run Phase 4 alignment test with proper context"""
import sys
import os

# Clear cached backend modules
modules_to_clear = [name for name in sys.modules if 'backend' in name]
for name in modules_to_clear:
    del sys.modules[name]

sys.path.insert(0, 'd:\\AURA')
os.chdir('d:\\AURA')

# Now run the test with proper context
with open('d:\\AURA\\backend\\experiments\\test_mg_phase_4_reference_alignment_17_13_b.py', 'r') as f:
    code = f.read()
    # Replace __file__ with the actual file path
    code = code.replace('__file__', '"d:\\\\AURA\\\\backend\\\\experiments\\\\test_mg_phase_4_reference_alignment_17_13_b.py"')
    exec(code, {'__name__': '__main__', '__file__': 'd:\\AURA\\backend\\experiments\\test_mg_phase_4_reference_alignment_17_13_b.py'})
