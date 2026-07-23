import unittest

from backend.services.execution_engine import ExecutionEngine


class ExecutionEngineTests(unittest.TestCase):
    def test_start_execution(self) -> None:
        engine = ExecutionEngine()
        state = engine.start_execution("Plan A", "Goal", ["Python Project", "DSA Practice", "Hackathon"])

        self.assertEqual(state.status, "RUNNING")
        self.assertEqual(state.current_step, 1)
        self.assertEqual(state.progress, 0.0)

    def test_complete_first_action(self) -> None:
        engine = ExecutionEngine()
        engine.start_execution("Plan A", "Goal", ["Python Project", "DSA Practice", "Hackathon"])
        engine.complete_current_action()

        state = engine.get_execution()
        self.assertIn("Python Project", state.completed_actions)
        self.assertEqual(state.progress, 0.33)
        self.assertEqual(state.current_step, 2)

    def test_skip_action(self) -> None:
        engine = ExecutionEngine()
        engine.start_execution("Plan A", "Goal", ["Python Project", "DSA Practice", "Hackathon"])
        engine.skip_current_action()

        state = engine.get_execution()
        self.assertIn("Python Project", state.skipped_actions)
        self.assertEqual(state.current_step, 2)

    def test_fail_action(self) -> None:
        engine = ExecutionEngine()
        engine.start_execution("Plan A", "Goal", ["Python Project", "DSA Practice", "Hackathon"])
        engine.fail_current_action()

        state = engine.get_execution()
        self.assertIn("Python Project", state.failed_actions)

    def test_finish_execution(self) -> None:
        engine = ExecutionEngine()
        engine.start_execution("Plan A", "Goal", ["Python Project", "DSA Practice", "Hackathon"])
        engine.complete_current_action()
        engine.complete_current_action()
        engine.complete_current_action()
        state = engine.finish_execution()

        self.assertEqual(state.status, "COMPLETED")
        self.assertEqual(state.progress, 1.0)
        self.assertIsNotNone(state.started_at)
        self.assertIsNotNone(state.updated_at)
        self.assertIsNotNone(state.completed_at)


if __name__ == "__main__":
    unittest.main()
