import unittest

from backend.consolidation.consolidation_engine import ConsolidationEngine
from backend.memory.memory_manager import MemoryManager
from backend.models.experience import Experience


class ConsolidationEngineTests(unittest.TestCase):
    def test_consolidation_run_produces_report(self) -> None:
        manager = MemoryManager()
        engine = ConsolidationEngine(memory_manager=manager)
        experiences = [
            Experience(
                experience_id="exp_1",
                state_before={"value": 0},
                action="Implemented feature",
                context={"goal": "Build app", "skill": "python", "topic": "backend", "activity": "build"},
                state_after={"value": 1},
                state_delta={"value": 1},
                outcome_value=0.9,
                experience_confidence=0.8,
                experience_weight=0.9,
            ),
            Experience(
                experience_id="exp_2",
                state_before={"value": 0},
                action="Completed milestone",
                context={"goal": "Build app", "skill": "python", "topic": "backend", "activity": "build"},
                state_after={"value": 1},
                state_delta={"value": 1},
                outcome_value=0.8,
                experience_confidence=0.7,
                experience_weight=0.8,
            ),
        ]

        report = engine.run(experiences)
        self.assertEqual(report["metrics"]["patterns_analyzed"], 1)
        self.assertGreaterEqual(report["metrics"]["candidates_generated"], 1)
        self.assertIn("run_id", report)
        self.assertIn("metrics", report)
