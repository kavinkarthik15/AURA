"""
Multi-Experience Lineage Check

Trace multiple held-out experiences to identify whether the 
single-experience match (exp_idx=0) generalizes to all 20.
"""

import os, sys
os.chdir(r'd:\AURA')
sys.path.insert(0, r'd:\AURA')

from backend.experiments.test_mg_prediction_lineage_17_13_b import run_lineage_diagnostic

print("\n" + "="*80)
print("MULTI-EXPERIENCE LINEAGE CHECK")
print("="*80)

divergences = []
matches = []

for exp_idx in range(5):  # Check first 5 held-out experiences
    try:
        lineage = run_lineage_diagnostic(exp_idx=exp_idx)
        
        result = {
            "exp_idx": exp_idx,
            "experience_id": lineage.experience_id,
            "motivation_match": lineage.motivation_match,
            "goals_match": lineage.goals_match,
            "correction_match": lineage.correction_match,
            "layer_output_match": lineage.layer_output_match,
            "mae_match": lineage.mae_match,
            "first_divergence": lineage.first_divergence,
            "t12a_mae_delta": lineage.t12a_mae_delta,
            "t13b_mae_delta": lineage.t13b_mae_delta,
        }
        
        if lineage.first_divergence:
            divergences.append(result)
        else:
            matches.append(result)
            
    except Exception as e:
        print(f"Error on exp_idx {exp_idx}: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Matches (no divergence): {len(matches)}")
print(f"Divergences: {len(divergences)}")

print("\nMatched experiences:")
for m in matches:
    print(f"  [{m['exp_idx']}] {m['experience_id']}")
    print(f"       17.12A MAE delta: {m['t12a_mae_delta']:.6f}")
    print(f"       17.13B MAE delta: {m['t13b_mae_delta']:.6f}")

print("\nDiverged experiences:")
for d in divergences:
    print(f"  [{d['exp_idx']}] {d['experience_id']}")
    print(f"       First divergence: {d['first_divergence']}")
    print(f"       17.12A MAE delta: {d['t12a_mae_delta']:.6f}")
    print(f"       17.13B MAE delta: {d['t13b_mae_delta']:.6f}")

print("\n" + "="*80)
