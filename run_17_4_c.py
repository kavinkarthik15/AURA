#!/usr/bin/env python3
"""
Runner script for Phase 17.4C experiment.

Executes the full clipped/confidence-gated signed update experiment:
- 5 calibration variants
- 5 random seeds  
- Comprehensive metrics collection and analysis
"""

import json
from pathlib import Path
from datetime import datetime

# Add backend to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.experiments.research_sign_aware_clipping_confidence_gating_17_4_c import (
    run_research_phase_17_4_c,
)


def save_17_4_c_results(result, output_dir: str = 'backend/experiments/results'):
    """Save 17.4C results to JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filepath = output_path / 'research_17_4_c_clipped_confidence_gated.json'
    
    with open(filepath, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    
    print(f"\n[OK] Results saved to: {filepath}")


def run_full_experiment():
    """Run the full Phase 17.4C experiment."""
    print(f"\n{'='*80}")
    print("PHASE 17.4C: Full Experiment Run")
    print(f"{'='*80}")
    print("Configuration:")
    print(f"  Seeds: [42, 123, 456, 789, 999]")
    print(f"  Variants: 5 (original, sign-aware-17.3, clipped, confidence-gated, both)")
    print(f"  Total experiments: 5 variants × 5 seeds = 25")
    print(f"  Clipping bound: 0.06 (default)")
    print(f"  Error threshold: 0.5 (default)")
    print(f"{'='*80}\n")
    
    result = run_research_phase_17_4_c(
        seeds=[42, 123, 456, 789, 999],
        learning_rate=0.007,
        clipping_bound=0.06,
        error_threshold=0.5,
    )
    
    save_17_4_c_results(result)
    
    return result


def run_quick_test():
    """Run a quick test with fewer seeds."""
    print(f"\n{'='*80}")
    print("PHASE 17.4C: Quick Test Run (2 seeds)")
    print(f"{'='*80}")
    print("Configuration:")
    print(f"  Seeds: [42, 123] (quick test)")
    print(f"  Variants: 2 (original, sign-aware-17.3)")
    print(f"  Total experiments: 2 variants × 2 seeds = 4")
    print(f"{'='*80}\n")
    
    result = run_research_phase_17_4_c(
        seeds=[42, 123],
        learning_rate=0.007,
    )
    
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Phase 17.4C experiment')
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick test with fewer seeds (default: false)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to JSON (default: false)'
    )
    
    args = parser.parse_args()
    
    if args.quick:
        result = run_quick_test()
    else:
        result = run_full_experiment()
        if not args.no_save:
            save_17_4_c_results(result)
    
    print(f"\n{'='*80}")
    print("Experiment complete")
    print(f"{'='*80}\n")
