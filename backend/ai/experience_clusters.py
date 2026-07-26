from __future__ import annotations

from typing import Any, Dict, List


class ExperienceClusterer:
    def __init__(self) -> None:
        self.version = "clustering_v1"

    def cluster(self, experiences: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        clusters: Dict[str, List[Dict[str, Any]]] = {
            "Placement": [],
            "Research": [],
            "Fitness": [],
            "Learning": [],
            "Career": [],
            "Projects": [],
        }
        for experience in experiences:
            goal = str(experience.get("goal_name") or experience.get("goal") or "").lower()
            if "placement" in goal:
                clusters["Placement"].append(experience)
            elif "research" in goal:
                clusters["Research"].append(experience)
            elif "fitness" in goal:
                clusters["Fitness"].append(experience)
            elif "career" in goal:
                clusters["Career"].append(experience)
            elif "project" in goal or "projects" in goal:
                clusters["Projects"].append(experience)
            else:
                clusters["Learning"].append(experience)
        return clusters
