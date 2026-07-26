from __future__ import annotations

from typing import Any, Dict, Iterable

from backend.ai.planning_policy import PlanningPolicy, PolicySample


class PolicyEvaluator:
    def evaluate(self, policy: PlanningPolicy, samples: Iterable[PolicySample]) -> Dict[str, Any]:
        sample_list = list(samples)
        if not sample_list:
            return {
                "policy_version": policy.policy_version,
                "training_date": policy.training_date,
                "samples": 0,
                "top_action_accuracy": 0.0,
                "average_probability": 0.0,
                "coverage": 0.0,
                "coverage_by_state": {},
                "coverage_by_goal": {},
                "average_entropy": 0.0,
            }

        correct = 0
        probabilities = []
        entropies = []
        supported = 0
        candidate_actions = list(policy.action_scores)
        state_totals: Dict[str, int] = {}
        state_supported: Dict[str, int] = {}
        goal_totals: Dict[str, int] = {}
        goal_supported: Dict[str, int] = {}

        for sample in sample_list:
            actions = candidate_actions.copy() or [sample.action]
            if sample.action not in actions:
                actions.append(sample.action)
            predictions = policy.predict(sample.state, sample.goal, actions)
            probability = next((item.probability for item in predictions if item.action == sample.action), 0.0)
            probabilities.append(probability)
            entropies.append(policy.normalized_entropy(sample.state, sample.goal, actions))
            is_supported = any(item.action == sample.action and item.support_count > 0 for item in predictions)
            if is_supported:
                supported += 1
            if predictions and predictions[0].action == sample.action:
                correct += 1

            goal = sample.goal or "unspecified"
            goal_totals[goal] = goal_totals.get(goal, 0) + 1
            if is_supported:
                goal_supported[goal] = goal_supported.get(goal, 0) + 1
            for state_key in sample.state:
                state_totals[state_key] = state_totals.get(state_key, 0) + 1
                if is_supported:
                    state_supported[state_key] = state_supported.get(state_key, 0) + 1

        return {
            "policy_version": policy.policy_version,
            "training_date": policy.training_date,
            "samples": len(sample_list),
            "top_action_accuracy": round(correct / len(sample_list), 4),
            "average_probability": round(sum(probabilities) / len(probabilities), 4),
            "coverage": round(supported / len(sample_list), 4),
            "coverage_by_state": {
                key: round(state_supported.get(key, 0) / total, 4)
                for key, total in state_totals.items()
            },
            "coverage_by_goal": {
                key: round(goal_supported.get(key, 0) / total, 4)
                for key, total in goal_totals.items()
            },
            "average_entropy": round(sum(entropies) / len(entropies), 4),
        }
