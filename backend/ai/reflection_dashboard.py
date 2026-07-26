from __future__ import annotations

from typing import Any, Dict, List


class ReflectionDashboard:
    def summarize(self, reflections: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not reflections:
            return {
                "average_reflection_score": 0.0,
                "replanning_rate": 0.0,
                "confidence_distribution": {},
                "common_assumptions": [],
                "self_critique_statistics": {},
                "reflection_timeline": [],
            }
        avg = round(sum(item.get("reflection_score", 0.0) for item in reflections) / len(reflections), 4)
        return {
            "average_reflection_score": avg,
            "replanning_rate": round(sum(1 for item in reflections if item.get("decision") == "replan") / len(reflections), 4),
            "confidence_distribution": {
                "low": sum(1 for item in reflections if item.get("confidence", 0.0) < 0.5),
                "medium": sum(1 for item in reflections if 0.5 <= item.get("confidence", 0.0) < 0.75),
                "high": sum(1 for item in reflections if item.get("confidence", 0.0) >= 0.75),
            },
            "common_assumptions": ["skill_level", "time_available_hours"],
            "self_critique_statistics": {"needs_replanning": sum(1 for item in reflections if item.get("self_critique", {}).get("status") == "needs_replanning")},
            "reflection_timeline": [
                {
                    "reasoning": item.get("reasoning_summary", ""),
                    "reflection": item.get("reflection", ""),
                    "revision": item.get("decision", ""),
                    "outcome": item.get("outcome", ""),
                    "lesson_learned": item.get("lesson_learned", ""),
                }
                for item in reflections
            ],
        }
