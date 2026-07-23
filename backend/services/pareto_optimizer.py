from typing import Dict, List


class ParetoOptimizer:
    def find_pareto_front(self, plans: List[Dict]) -> List[Dict]:
        front = []
        for candidate in plans:
            dominated = False
            for other in plans:
                if other is candidate:
                    continue
                if self._dominates(other, candidate):
                    dominated = True
                    break
            if not dominated:
                front.append(candidate)
        return front

    def _dominates(self, left: Dict, right: Dict) -> bool:
        left_objectives = left.get("objectives", {})
        right_objectives = right.get("objectives", {})
        if not left_objectives or not right_objectives:
            return False

        better_or_equal = True
        strictly_better = False

        for key in ["goal_progress", "python_growth", "project_growth", "confidence"]:
            left_val = left_objectives.get(key, 0)
            right_val = right_objectives.get(key, 0)
            if left_val < right_val:
                better_or_equal = False
                break
            if left_val > right_val:
                strictly_better = True

        for key in ["difficulty", "time_cost", "energy_cost"]:
            left_val = left_objectives.get(key, 0)
            right_val = right_objectives.get(key, 0)
            if left_val > right_val:
                better_or_equal = False
                break
            if left_val < right_val:
                strictly_better = True

        return better_or_equal and strictly_better
