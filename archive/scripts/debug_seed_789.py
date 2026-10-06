"""Debug why sign-aware calibrator degrades on seed 789."""

from backend.experiments.research_sign_aware_calibration_17_3_a import (
    ResearchSignAwareCalibration17_3_A,
)


def debug_seed_789():
    """Investigate seed 789 direction accuracy degradation."""
    
    print("=" * 70)
    print("DEBUGGING SEED 789: Direction Accuracy Degradation")
    print("=" * 70)
    
    # Run the comparison for seed 789
    comparison = ResearchSignAwareCalibration17_3_A(seed=789)
    result = comparison.run()
    
    print("\nDetailed Metrics for Seed 789:")
    print("-" * 70)
    
    # Original calibrator
    orig = result.existing_calibrator_result
    print("\nORIGINAL CALIBRATOR:")
    print(f"  MAE: {orig.held_out_mae:.4f}")
    print(f"  Direction Accuracy: {orig.direction_accuracy:.4f} (80.00%)")
    print(f"  Category Accuracies:")
    for cat, acc in sorted(orig.category_accuracies.items()):
        print(f"    {cat:30s}: {acc:.4f}")
    print(f"  Final Bias:")
    for key, bias in sorted(orig.final_expected_state_bias.items()):
        print(f"    {key:30s}: {bias:+.4f}")
    
    # Sign-aware calibrator
    sa = result.sign_aware_calibrator_result
    print("\nSIGN-AWARE CALIBRATOR:")
    print(f"  MAE: {sa.held_out_mae:.4f}")
    print(f"  Direction Accuracy: {sa.direction_accuracy:.4f} (62.50% - DEGRADED!)")
    print(f"  Category Accuracies:")
    for cat, acc in sorted(sa.category_accuracies.items()):
        orig_acc = orig.category_accuracies.get(cat, 0.0)
        delta = acc - orig_acc
        status = "↓ WORSE" if delta < -0.05 else "↑ BETTER" if delta > 0.05 else "→ SAME"
        print(f"    {cat:30s}: {acc:.4f} ({status:10s} from {orig_acc:.4f})")
    
    print(f"  Final Bias:")
    for key, bias in sorted(sa.final_expected_state_bias.items()):
        orig_bias = orig.final_expected_state_bias.get(key, 0.0)
        delta = bias - orig_bias
        print(f"    {key:30s}: {bias:+.4f} (Δ {delta:+.4f})")
    
    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS:")
    print("=" * 70)
    
    # Find which categories got worse
    worse_categories = []
    for cat, sa_acc in sa.category_accuracies.items():
        orig_acc = orig.category_accuracies.get(cat, 0.0)
        if sa_acc < orig_acc - 0.05:
            worse_categories.append((cat, orig_acc, sa_acc, orig_acc - sa_acc))
    
    if worse_categories:
        print("\nCategories where sign-aware got WORSE:")
        for cat, orig_acc, sa_acc, delta in sorted(worse_categories, key=lambda x: -x[3]):
            print(f"  {cat:30s}: {orig_acc:.2%} → {sa_acc:.2%} ({-delta:.2%} worse)")
    else:
        print("\nNo categories show significant degradation.")
    
    # Compare learned biases
    print("\nBias Learning Comparison:")
    orig_neg_bias = [orig.final_expected_state_bias.get(k, 0) for k in ["dsa", "ml", "projects"]]
    sa_neg_bias = [sa.final_expected_state_bias.get(k, 0) for k in ["dsa", "ml", "projects"]]
    
    print(f"  Original avg bias (sample): {sum(orig_neg_bias) / 3:.4f}")
    print(f"  Sign-aware avg bias (sample): {sum(sa_neg_bias) / 3:.4f}")
    
    # Check if sign-aware biases are converging differently
    print("\nParameter Change Pattern:")
    for key in sorted(orig.final_expected_state_bias.keys())[:5]:
        orig_b = orig.final_expected_state_bias.get(key, 0.0)
        sa_b = sa.final_expected_state_bias.get(key, 0.0)
        delta = sa_b - orig_b
        pct_change = (delta / orig_b * 100) if orig_b != 0 else 0
        print(f"  {key:30s}: {orig_b:+.4f} → {sa_b:+.4f} ({delta:+.4f}, {pct_change:+.1f}%)")


if __name__ == "__main__":
    debug_seed_789()
