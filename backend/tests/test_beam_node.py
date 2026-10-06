import unittest

from backend.planning.beam_node import BeamNode
from backend.planning.beam_registry import BeamTree
from backend.ai.decision_reasoner import DecisionCandidate, Prediction, Evidence


class BeamNodeTests(unittest.TestCase):
    def test_node_creation_and_root(self):
        root_state = {"python": 3, "confidence": 0.5}
        root = BeamNode.root(root_state)
        self.assertEqual(root.node_id, "ROOT")
        self.assertEqual(root.current_state, root_state)
        self.assertEqual(root.predicted_state, root_state)

    def test_parent_child_links_and_accumulation(self):
        root = BeamNode.root({"python": 3, "confidence": 0.5})
        # create a fake decision candidate
        pred = Prediction(reward=0.6, risk=0.1, cost=0.05, utility=0.45, expected_state_change={"python": 2}, predicted_state={"python": 5, "confidence": 0.6})
        ev = Evidence(supporting_experiences=["ep1"], supporting_knowledge=["kn1"], reasoning="Because practice works")
        dc = DecisionCandidate(decision_id="DEC-1", action="Practice", goal_supported="G1", expected_outcome="improve")
        dc.prediction = pred
        dc.evidence = ev

        child = BeamNode.from_decision(dc, root)
        root.add_child(child)

        self.assertIn(child, root.children)
        self.assertEqual(child.parent, root)
        self.assertAlmostEqual(child.accumulated_reward, 0.6)
        self.assertAlmostEqual(child.accumulated_cost, 0.05)
        self.assertAlmostEqual(child.accumulated_risk, 0.1)
        self.assertAlmostEqual(child.accumulated_utility, 0.45)
        self.assertEqual(child.decision_history, ["DEC-1"])
        self.assertEqual(child.predicted_state.get("python"), 5)

    def test_beam_tree_registry(self):
        root = BeamNode.root({"python": 3})
        tree = BeamTree(root=root, beam_width=2, max_depth=2)
        self.assertEqual(tree.active_nodes, [root])
        # create a child and add
        pred = Prediction(reward=0.2, risk=0.05, cost=0.01, utility=0.18, expected_state_change={"python": 1}, predicted_state={"python": 4})
        ev = Evidence(supporting_experiences=["ep2"], supporting_knowledge=["kn2"], reasoning="small practice")
        dc = DecisionCandidate(decision_id="DEC-2", action="SmallPractice", goal_supported="G1", expected_outcome="small")
        dc.prediction = pred
        dc.evidence = ev
        child = BeamNode.from_decision(dc, root)
        tree.add_active(child)
        self.assertIn(child, tree.active_nodes)
        tree.mark_completed(child)
        self.assertIn(child, tree.completed_nodes)
        self.assertNotIn(child, tree.active_nodes)


if __name__ == "__main__":
    unittest.main()
