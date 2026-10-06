from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List

from backend.consolidation.pattern_models import PatternCandidate
from backend.consolidation.pattern_registry import PatternRegistry
from backend.models.experience import Experience


class PatternDetector:
    def __init__(self, registry: PatternRegistry | None = None) -> None:
        self.registry = registry or PatternRegistry()

    def detect_patterns(self, experiences: List[Experience]) -> List[PatternCandidate]:
        active_experiences = [experience for experience in experiences if self._is_active(experience)]
        if not active_experiences:
            return []

        grouped: Dict[tuple[str, str], List[Experience]] = defaultdict(list)
        for experience in active_experiences:
            key = self._group_key(experience)
            grouped[key].append(experience)

        patterns: List[PatternCandidate] = []
        start_time = time.perf_counter()
        for key, group in grouped.items():
            if len(group) < 2:
                continue
            pattern_type = self._classify_pattern(group)
            if not pattern_type:
                continue

            support_count = len(group)
            confidence = self._score_confidence(group, support_count)
            importance = self._score_importance(group)
            candidate = PatternCandidate(
                pattern_type=pattern_type,
                confidence=confidence,
                importance=importance,
                support_count=support_count,
                episode_ids=[experience.experience_id for experience in group],
                summary=self._build_summary(pattern_type, group),
                evidence=self._build_evidence(group),
            )
            patterns.append(candidate)
            self.registry.record(pattern_type, candidate.confidence, candidate.support_count, self._elapsed_ms(start_time))

        return patterns

    def _is_active(self, experience: Experience) -> bool:
        context = (experience.context or {})
        status = context.get("status")
        if status is None:
            return True
        return str(status).upper() not in {"ARCHIVED", "DELETED", "DEPRECATED"}

    def _classify_pattern(self, group: List[Experience]) -> str | None:
        outcomes = [experience.outcome_value for experience in group]
        if self._is_habit(group):
            return "Habit"
        if self._is_goal_progress(group):
            return "Goal Progress"
        if all(value > 0 for value in outcomes):
            if self._has_success_language(group):
                return "Repeated Success"
        if all(value < 0 for value in outcomes):
            if self._has_failure_language(group):
                return "Repeated Failure"
        if self._is_preference(group):
            return "Preference"
        return None

    def _group_key(self, experience: Experience) -> tuple[str, str]:
        context = experience.context or {}
        for field in ["goal", "skill", "topic", "activity"]:
            value = str(context.get(field, "")).strip()
            if value:
                return field, value
        tags = sorted(str(tag) for tag in context.get("tags", []) if tag)
        return "tags", "|".join(tags)

    def _is_habit(self, group: List[Experience]) -> bool:
        if len(group) < 2:
            return False
        activities = {str((experience.context or {}).get("activity", "")).lower() for experience in group}
        return len(activities) == 1 and any(activities) and "study" in activities

    def _is_preference(self, group: List[Experience]) -> bool:
        topics = {str((experience.context or {}).get("topic", "")).lower() for experience in group}
        return len(group) >= 2 and len(topics) == 1 and any(topics)

    def _is_goal_progress(self, group: List[Experience]) -> bool:
        actions = [str((experience.context or {}).get("activity", "")).lower() for experience in group]
        values = [experience.outcome_value for experience in group]
        return len(values) >= 2 and values[-1] >= values[0] and all(value >= 0 for value in values) and any("solve" in action or "solved" in action or "start" in action for action in actions)

    def _has_success_language(self, group: List[Experience]) -> bool:
        actions = [str((experience.context or {}).get("activity", "")).lower() for experience in group]
        return any("complete" in action or "finish" in action or "implement" in action or "build" in action or "project" in action for action in actions)

    def _has_failure_language(self, group: List[Experience]) -> bool:
        actions = [str((experience.context or {}).get("activity", "")).lower() for experience in group]
        return any("fail" in action or "mock" in action or "round" in action or "test" in action for action in actions)

    def _score_confidence(self, group: List[Experience], support_count: int) -> float:
        repetition = min(support_count / 3.0, 1.0)
        average_importance = sum(experience.experience_weight for experience in group) / max(1, len(group))
        average_confidence = sum(experience.experience_confidence for experience in group) / max(1, len(group))
        score = (0.5 * repetition) + (0.3 * average_importance) + (0.2 * average_confidence)
        return round(min(max(score, 0.0), 1.0), 3)

    def _score_importance(self, group: List[Experience]) -> float:
        return round(sum(experience.experience_weight for experience in group) / max(1, len(group)), 3)

    def _build_summary(self, pattern_type: str, group: List[Experience]) -> str:
        return f"{pattern_type} observed across {len(group)} experiences"

    def _build_evidence(self, group: List[Experience]) -> List[Dict[str, Any]]:
        return [
            {
                "experience_id": experience.experience_id,
                "outcome_value": experience.outcome_value,
                "confidence": experience.experience_confidence,
                "importance": experience.experience_weight,
            }
            for experience in group
        ]

    def _elapsed_ms(self, start_time: float) -> float:
        return round((time.perf_counter() - start_time) * 1000.0, 3)
