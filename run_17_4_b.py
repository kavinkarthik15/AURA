"""Run full Phase 17.4B Learning Rate Refinement experiment."""

from backend.experiments.research_sign_aware_refinement_17_4_b import (
    run_research_sign_aware_refinement_17_4_b,
    save_17_4_b_results,
)

if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 17.4B: SIGN-AWARE CALIBRATION LEARNING RATE REFINEMENT")
    print("=" * 70)
    print("\nTesting 6 learning rates across 5 seeds to find optimal robustness...")
    print("Learning rates: [0.007, 0.005, 0.003, 0.002, 0.001]")
    print("Seeds: [42, 123, 456, 789, 999]\n")
    print("Success criterion: ≥80% win rate with no severe degradation\n")
    
    # Run with all learning rates and seeds
    result = run_research_sign_aware_refinement_17_4_b(
        seeds=[42, 123, 456, 789, 999],
        learning_rates=[0.007, 0.005, 0.003, 0.002, 0.001]
    )
    
    # Save results to JSON
    save_17_4_b_results(result)
    
    print("\n" + "=" * 70)
    if result.recommended_learning_rate == 0.007:
        print("ℹ  Recommended: Current learning rate (0.007) - NO REFINEMENT NEEDED")
    else:
        print(f"✓ RECOMMENDATION: Use learning rate {result.recommended_learning_rate}")
        print(f"   This provides better robustness across seeds")
    print("=" * 70)
