#!/usr/bin/env python3
import json

with open('backend/experiments/results/research_17_2_a_mechanism_analysis.json') as f:
    data = json.load(f)

print('=== 17.2A Mechanism Analysis Summary ===')
print(f'Seed: {data["seed"]}')
print(f'Initial MAE: {data["initial_mae"]}')
print(f'Final MAE: {data["final_mae"]}')
improvement_pct = data["total_mae_reduction"]/data["initial_mae"]*100
print(f'Total Improvement: {data["total_mae_reduction"]} ({improvement_pct:.1f}%)')
print(f'Convergence Rate: {data["convergence_rate"]:.1f}%')
print(f'Is Learning: {data["is_learning"]}')
print(f'Is Converging: {data["is_converging"]}')
print()
print('Category Bias Distances (avg distance from true bias):')
for cat, dist in data['category_bias_distances'].items():
    acc = data['category_direction_accuracy'][cat]
    print(f'  {cat}: {dist:.4f} (direction accuracy: {acc:.1f}%)')
print()
print('Explanation:')
print(data['learning_explanation'])
