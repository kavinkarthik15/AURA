import unittest

from backend.planning.beam_expander import BeamExpander
from backend.planning.beam_node import BeamNode
from backend.ai.context_builder import PlanningContext
from backend.ai.decision_reasoner import DecisionCandidate, Prediction, Evidence


class FakeDecisionReasoner:
    def __init__(self, candidates):
        self._candidates = candidates

    def generate_candidates(self, context):
        return list(self._candidates)


class BeamExpanderTests(unittest.TestCase):
    def setUp(self):
        self.root_state = {"python_skill": 10, "confidence": 0.5}
        self.root = BeamNode.root(self.root_state)
        self.context = PlanningContext(goal="G1", current_state=self.root_state)

    def make_candidate(self, idx, reward=1.0, cost=0.1, risk=0.05, utility=0.85, predicted_state=None, reasoning=None):
        pred = Prediction(reward=reward, cost=cost, risk=risk, utility=utility, predicted_state=predicted_state or {"python_skill": 12})
        ev = Evidence(reasoning=reasoning or f"reason-{idx}")
        return DecisionCandidate(decision_id=f"DEC-{idx}", action=f"Action-{idx}", goal_supported="G1", expected_outcome="outcome", prediction=pred, evidence=ev)

    def test_expansion_count_and_parent_link(self):
        cand_list = [self.make_candidate(i) for i in range(3)]
        fake = FakeDecisionReasoner(cand_list)
        children = BeamExpander.expand(self.root, self.context, decision_reasoner=fake)
        self.assertEqual(len(children), 3)
        for child, cand in zip(children, cand_list):
            self.assertEqual(child.parent, self.root)

    def test_decision_history_and_utility_accumulation(self):
        # parent has some accumulated utility already
        self.root.accumulated_utility = 8.0
        cand = self.make_candidate(1, utility=5.0)
        fake = FakeDecisionReasoner([cand])
        children = BeamExpander.expand(self.root, self.context, decision_reasoner=fake)
        child = children[0]
        self.assertEqual(child.decision_history, ["DEC-1"])
        self.assertAlmostEqual(child.accumulated_utility, 13.0)

    def test_predicted_state_propagation_and_reasoning_trace(self):
        # ensure parent's predicted_state becomes child's current_state
        self.root.predicted_state = {"python_skill": 11, "confidence": 0.55}
        cand = self.make_candidate(2, predicted_state={"python_skill": 14, "confidence": 0.7}, reasoning="Because tests")
        fake = FakeDecisionReasoner([cand])
        children = BeamExpander.expand(self.root, self.context, decision_reasoner=fake)
        child = children[0]
        # current_state must equal parent's predicted_state
        self.assertEqual(child.current_state, self.root.predicted_state)
        # predicted_state must equal candidate.prediction.predicted_state
        self.assertEqual(child.predicted_state, cand.prediction.predicted_state)
        # reasoning trace contains parent's trace plus new entry
        self.assertTrue(any(entry.get("reasoning") == "Because tests" for entry in child.reasoning_trace))


if __name__ == "__main__":
    unittest.main()
