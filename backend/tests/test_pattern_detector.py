import unittest
from datetime import datetime

from backend.consolidation.pattern_detector import PatternDetector
from backend.models.experience import Experience


class PatternDetectorTests(unittest.TestCase):
    def _experience(self, experience_id: str, goal: str, topic: str, action: str, outcome_value: float,
                    confidence: float = 0.7, importance: float = 0.8, activity: str | None = None,
                    tags: list[str] | None = None, status: str | None = None) -> Experience:
        return Experience(
            experience_id=experience_id,
            state_before={"value": 0},
            action=action,
            context={
                "goal": goal,
                "skill": "python",
                "topic": topic,
                "activity": activity or action,
                "tags": tags or [],
                "status": status,
            },
            state_after={"value": 1},
            state_delta={"value": 1},
            outcome_value=outcome_value,
            experience_confidence=confidence,
            experience_weight=importance,
        )

    def test_empty_experience_list_returns_no_patterns(self) -> None:
        detector = PatternDetector()
        self.assertEqual(detector.detect_patterns([]), [])

    def test_single_experience_returns_no_patterns(self) -> None:
        detector = PatternDetector()
        experiences = [self._experience("exp_1", "Build app", "backend", "Implemented feature", 0.9)]
        self.assertEqual(detector.detect_patterns(experiences), [])

    def test_repeated_success_detection(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Build app", "backend", "Implemented feature", 0.9),
            self._experience("exp_2", "Build app", "backend", "Completed milestone", 0.8),
            self._experience("exp_3", "Build app", "backend", "Finished sprint", 0.7),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "Repeated Success")
        self.assertEqual(patterns[0].support_count, 3)
        self.assertGreaterEqual(patterns[0].confidence, 0.0)

    def test_repeated_failure_detection(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Interview prep", "interview", "Failed mock", -0.8),
            self._experience("exp_2", "Interview prep", "interview", "Failed round", -0.7),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "Repeated Failure")
        self.assertEqual(patterns[0].support_count, 2)

    def test_habit_detection(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Study", "algorithms", "Study morning", 0.4, activity="study"),
            self._experience("exp_2", "Study", "algorithms", "Study morning", 0.3, activity="study"),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "Habit")
        self.assertEqual(patterns[0].support_count, 2)

    def test_preference_detection(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Build UI", "flutter", "Built widget", 0.6),
            self._experience("exp_2", "Build UI", "flutter", "Built screen", 0.5),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "Preference")
        self.assertEqual(patterns[0].support_count, 2)

    def test_goal_progress_detection(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "DSA", "arrays", "Solved 50", 0.5),
            self._experience("exp_2", "DSA", "arrays", "Solved 120", 0.7),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "Goal Progress")
        self.assertEqual(patterns[0].support_count, 2)

    def test_confidence_calculation_uses_scored_components(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Build app", "backend", "Implemented feature", 0.9, confidence=0.8, importance=0.9),
            self._experience("exp_2", "Build app", "backend", "Completed milestone", 0.8, confidence=0.7, importance=0.8),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertGreaterEqual(patterns[0].confidence, 0.0)
        self.assertLessEqual(patterns[0].confidence, 1.0)

    def test_archived_and_deleted_experiences_are_ignored(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Build app", "backend", "Implemented feature", 0.9, status="ARCHIVED"),
            self._experience("exp_2", "Build app", "backend", "Completed milestone", 0.8, status="DELETED"),
            self._experience("exp_3", "Build app", "backend", "Finished sprint", 0.7),
            self._experience("exp_4", "Build app", "backend", "Delivered release", 0.8),
        ]

        patterns = detector.detect_patterns(experiences)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].support_count, 2)

    def test_registry_statistics_are_recorded(self) -> None:
        detector = PatternDetector()
        experiences = [
            self._experience("exp_1", "Build app", "backend", "Implemented feature", 0.9),
            self._experience("exp_2", "Build app", "backend", "Completed milestone", 0.8),
        ]

        detector.detect_patterns(experiences)
        stats = detector.registry.statistics()
        self.assertGreaterEqual(stats["patterns_generated"], 1)
        self.assertIn("Repeated Success", stats["pattern_types"])
        self.assertGreaterEqual(stats["average_confidence"], 0.0)
        self.assertGreaterEqual(stats["average_support"], 1.0)
