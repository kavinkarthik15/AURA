from __future__ import annotations

from typing import Iterable

from backend.ai.planning_policy import PlanningPolicy


class PolicyVisualizer:
    def render_markdown(self, policy: PlanningPolicy, state: dict, goal: str, actions: Iterable[str]) -> str:
        predictions = policy.predict(state, goal, list(actions))
        lines = [f"# Policy Dashboard: {goal}", "", "| Action | Probability | Confidence | Support |", "|---|---:|---:|---:|"]
        for prediction in predictions:
            bars = "█" * max(1, round(prediction.probability * 10))
            lines.append(f"| {prediction.action} {bars} | {prediction.probability:.2f} | {prediction.confidence:.2f} | {prediction.support_count} |")
        lines.extend(["", f"Policy entropy: {policy.normalized_entropy(state, goal, list(actions)):.2f}", f"Mode: {policy.exploration_mode(state, goal, list(actions))}"])
        return "\n".join(lines)
