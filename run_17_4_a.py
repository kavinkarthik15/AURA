"""Run full Phase 17.4A multi-seed robustness validation."""

from backend.experiments.research_sign_aware_robustness_17_4_a import (
    run_research_sign_aware_robustness_17_4_a,
    save_17_4_a_results,
)

if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 17.4A: MULTI-SEED ROBUSTNESS VALIDATION")
    print("=" * 70)
    print("\nExecuting sign-aware calibration robustness test across 5 seeds...")
    print("Seeds: [42, 123, 456, 789, 999]\n")
    
    # Run with all 5 seeds
    result = run_research_sign_aware_robustness_17_4_a(
        seeds=[42, 123, 456, 789, 999]
    )
    
    # Save results to JSON
    save_17_4_a_results(result)
    
    print("\n" + "=" * 70)
    if result.success_criterion_met:
        print("✓ SUCCESS: Sign-aware calibration is ROBUST across seeds")
    else:
        print("✗ WARNING: Sign-aware calibration shows seed sensitivity")
    print("=" * 70)
