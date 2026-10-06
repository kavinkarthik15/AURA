import unittest

from backend.memory.memory_manager import MemoryManager
from backend.memory.working_memory import WorkingMemory


class WorkingMemoryTests(unittest.TestCase):
    def test_session_lifecycle_and_cleanup(self) -> None:
        memory = WorkingMemory()
        session_id = memory.create_session()
        stored = memory.store({"type": "goal", "value": "Finish assignment", "importance": 0.95})

        self.assertTrue(session_id.startswith("WM-"))
        self.assertEqual(memory.retrieve({"working_memory_id": session_id})[0]["type"], "goal")
        snapshot = memory.end_session(session_id)

        self.assertEqual(snapshot["working_memory_id"], session_id)
        self.assertEqual(memory.retrieve({"working_memory_id": session_id}), [])
        self.assertIsNone(memory.active_session_id)
        self.assertTrue(stored["memory_id"].startswith("WMR-"))

    def test_updates_filters_and_snapshot(self) -> None:
        memory = WorkingMemory()
        session_id = memory.create_session()
        record = memory.store({"type": "confidence", "value": 0.5})
        updated = memory.update(record["memory_id"], {"value": 0.83})

        self.assertEqual(updated["value"], 0.83)
        self.assertEqual(memory.retrieve({"working_memory_id": session_id, "type": "confidence"})[0]["value"], 0.83)
        self.assertEqual(len(memory.snapshot(session_id)["records"]), 1)

    def test_manager_exposes_cognitive_working_memory_operations(self) -> None:
        manager = MemoryManager()
        session_id = manager.create_working_session()
        manager.set_working_goal("Placement")
        manager.add_working_constraint(("python", 80))
        manager.set_working_strategy("optimization")
        manager.store_working_reflection({"decision": "accept"})

        snapshot = manager.working_snapshot(session_id)
        record_types = {record["type"] for record in snapshot["records"]}

        self.assertEqual(snapshot["working_memory_id"], session_id)
        self.assertEqual(record_types, {"goal", "constraint", "strategy", "reflection"})
        self.assertEqual(manager.working_health()["active_sessions"], 1)
        manager.end_working_session(session_id)
        self.assertEqual(manager.working_health()["active_sessions"], 0)


if __name__ == "__main__":
    unittest.main()
