from __future__ import annotations

from typing import Any, Dict, List


class AssumptionDetector:
    def detect(self, goal: str, context: Dict[str, Any], evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        assumptions = []
        categories = {
            "time_available_hours": "Time Assumptions",
            "skill_level": "Skill Assumptions",
            "internet_available": "Environmental Assumptions",
            "resource_available": "Resource Assumptions",
            "behavioral_pattern": "Behavioral Assumptions",
        }
        for key, category in categories.items():
            if key in context:
                assumptions.append({
                    "assumption": key,
                    "category": category,
                    "value": context[key],
                    "supported": bool(evidence.get(key, False)),
                })
        return assumptions
