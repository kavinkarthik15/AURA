import unittest

from backend.planning.beam_search import BeamSearch
from backend.planning.beam_node import BeamNode
from backend.planning.candidate_selector import CandidateSelector
from backend.ai.context_builder import PlanningContext
from backend.ai.decision_reasoner import DecisionCandidate, Prediction, Evidence


class SequencedFakeDecisionReasoner:
    """Fake that returns a different set for the first call, then another set for subsequent calls.

    generate_candidates will be called per expansion (per node). We increment an internal counter to distinguish the
    initial root expansion from later expansions.
    """

    def __init__(self):
        self.call_count = 0

    def generate_candidates(self, context):
        self.call_count += 1
        if self.call_count == 1:
            # first expansion (root): three candidates with utilities 1,5,2
            return [
                DecisionCandidate(decision_id="D1", action="a1", goal_supported="G1", expected_outcome="", prediction=Prediction(utility=1.0), evidence=Evidence(reasoning="r1")),
                DecisionCandidate(decision_id="D2", action="a2", goal_supported="G1", expected_outcome="", prediction=Prediction(utility=5.0), evidence=Evidence(reasoning="r2")),
                DecisionCandidate(decision_id="D3", action="a3", goal_supported="G1", expected_outcome="", prediction=Prediction(utility=2.0), evidence=Evidence(reasoning="r3")),
            ]
        # subsequent expansions: two children per node with utilities 4 and 1
        return [
            DecisionCandidate(decision_id="SX1", action="sx1", goal_supported="G1", expected_outcome="", prediction=Prediction(utility=4.0), evidence=Evidence(reasoning="sr1")),
            DecisionCandidate(decision_id="SX2", action="sx2", goal_supported="G1", expected_outcome="", prediction=Prediction(utility=1.0), evidence=Evidence(reasoning="sr2")),
        ]


class BeamSearchTests(unittest.TestCase):
    def test_beam_search_pruning_and_depth(self):
        root_state = {"python_skill": 10}
        root = BeamNode.root(root_state)
        context = PlanningContext(goal="G1", current_state=root_state)

        fake = SequencedFakeDecisionReasoner()
        bs = BeamSearch(beam_width=2, max_depth=2, decision_reasoner=fake)
        survivors = bs.search(root, context)

        # After first expansion, candidates utilities: [1,5,2] -> keep 5 and 2
        # After second expansion, children accumulated utilities: 5+4=9,5+1=6,2+4=6,2+1=3 -> top 2 are 9 and 6
        utilities = sorted([n.accumulated_utility for n in survivors], reverse=True)
        self.assertEqual(len(survivors), 2)
        self.assertAlmostEqual(utilities[0], 9.0)
        self.assertAlmostEqual(utilities[1], 6.0)

    def test_beam_search_uses_simulation_engine_for_probabilistic_transitions(self):
        from backend.services.simulation_engine import SimulationEngine

        root_state = {"python": 10}
        root = BeamNode.root(root_state)
        context = PlanningContext(goal="G1", current_state=root_state)

        fake = SequencedFakeDecisionReasoner()
        simulation_engine = SimulationEngine()
        bs = BeamSearch(
            beam_width=2,
            max_depth=1,
            decision_reasoner=fake,
            simulation_engine=simulation_engine,
        )

        survivors = bs.search(root, context)
        self.assertGreaterEqual(len(survivors), 1)
        for node in survivors:
            if node.probabilistic_transition is not None:
                self.assertGreater(len(node.probabilistic_transition.possible_states), 1)
                self.assertAlmostEqual(sum(node.probabilistic_transition.probabilities), 1.0, places=4)
                self.assertIn("action", node.probabilistic_transition.context)

    def test_end_to_end_digital_twin_metadata_survives(self):
        from backend.services.simulation_engine import SimulationEngine

        root_state = {"python": 10}
        root = BeamNode.root(root_state)
        context = PlanningContext(goal="G1", current_state=root_state)

        fake = SequencedFakeDecisionReasoner()
        simulation_engine = SimulationEngine()
        bs = BeamSearch(
            beam_width=3,
            max_depth=1,
            decision_reasoner=fake,
            simulation_engine=simulation_engine,
            risk_sensitivity=0.5,
            uncertainty_sensitivity=0.5,
        )

        survivors = bs.search(root, context)
        self.assertGreaterEqual(len(survivors), 1)

        # Find at least one node that represents a probabilistic branch
        branch_nodes = [n for n in survivors if getattr(n, "branch_snapshot", None) is not None]
        self.assertGreaterEqual(len(branch_nodes), 1)

        for node in branch_nodes:
            # Basic probabilistic transition checks
            self.assertIsNotNone(node.probabilistic_transition)
            self.assertGreater(len(node.probabilistic_transition.possible_states), 1)
            self.assertAlmostEqual(sum(node.probabilistic_transition.probabilities), 1.0, places=4)

            # Branch metadata preserved on BeamNode
            self.assertIsNotNone(node.branch_snapshot_id)
            self.assertIsNotNone(node.branch_probability)
            self.assertIsInstance(node.state_diff, dict)
            self.assertIsInstance(node.branch_snapshot, object)

            parent = node.parent
            self.assertIsNotNone(parent)
            # simulation_id preserved from the initial snapshot creation
            expected_sim_id = f"beam-{parent.node_id}"
            self.assertEqual(node.branch_snapshot.simulation_id, expected_sim_id)

            # snapshot id and parent snapshot id preserved
            self.assertEqual(node.branch_snapshot.snapshot_id, node.branch_snapshot_id)
            self.assertEqual(node.branch_snapshot.parent_snapshot_id, parent.node_id)

            # step preserved (snapshot.step should equal child.depth)
            self.assertEqual(node.branch_snapshot.step, node.depth)

            # action preserved in both transition and snapshot metadata
            self.assertEqual(node.probabilistic_transition.action, str(node.decision.action))
            self.assertIn("action", node.branch_snapshot.metadata)
            self.assertEqual(node.branch_snapshot.metadata.get("action"), str(node.decision.action))

        # Multiple branches: ensure siblings from same parent/decision are independent
        sibling_map = {}
        for n in branch_nodes:
            key = (n.parent.node_id, getattr(n.decision, "decision_id", None))
            sibling_map.setdefault(key, []).append(n)

        for key, siblings in sibling_map.items():
            if len(siblings) <= 1:
                continue
            ids = [s.branch_snapshot_id for s in siblings]
            probs = [s.branch_probability for s in siblings]
            self.assertEqual(len(set(ids)), len(ids))
            self.assertAlmostEqual(sum(probs), 1.0, places=3)

        # Trajectory evaluation and risk/uncertainty scoring
        scores = []
        for n in survivors:
            evald = bs.evaluate_trajectory(n, context)
            self.assertIn("trajectory_score", evald)
            self.assertIn("cumulative_risk", evald)
            self.assertIn("cumulative_uncertainty", evald)
            scores.append((n, float(evald.get("trajectory_score", 0.0))))

        # BeamSearch selects the best-scoring trajectory
        best_node, best_score = max(scores, key=lambda t: t[1])
        active_scores = [s for _, s in scores]
        self.assertEqual(best_score, max(active_scores))


if __name__ == "__main__":
    unittest.main()
import unittest

from backend.models.goal_state import GoalState
from backend.services.beam_search_planner import BeamSearchPlanner


class BeamSearchPlannerTests(unittest.TestCase):
    def test_beam_search_returns_a_plan(self) -> None:
        planner = BeamSearchPlanner()
        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = planner.search(current_state, goal_state, beam_width=3, max_depth=3)

        self.assertTrue(result["best_plan"])
        self.assertGreaterEqual(len(result["best_plan"]), 1)
        self.assertGreaterEqual(result["plans_evaluated"], result["beam_width"])
        self.assertIn("score", result)
        self.assertIn("search_trace", result)
        self.assertIsNotNone(result["score"])

    def test_beam_search_uses_digital_twin_hook_without_changing_default_behavior(self) -> None:
        selector = CandidateSelector(enabled=True, fallback_action="fallback")
        planner = BeamSearchPlanner(candidate_selector=selector)
        current_state = {"python": 10, "dsa": 5, "projects": 1}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = planner.search(current_state, goal_state, beam_width=2, max_depth=1)

        self.assertFalse(result["use_digital_twin"])
        self.assertFalse(result["digital_twin_enabled"])
        self.assertIsNone(result["digital_twin_selection"])
        self.assertTrue(result["best_plan"])
        self.assertIsNone(result.get("digital_twin_advisory"))
        self.assertIn("recommended_action", result)
        self.assertEqual(result["recommended_plan_actions"], [result["recommended_action"]])
        self.assertEqual(result["recommended_action"], result["best_plan"][0])

    def test_beam_search_selects_digital_twin_candidates_when_enabled(self) -> None:
        selector = CandidateSelector(enabled=True, fallback_action="fallback")
        planner = BeamSearchPlanner(candidate_selector=selector)
        current_state = {"python": 10, "dsa": 5, "projects": 1}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

        result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

        self.assertTrue(result["use_digital_twin"])
        self.assertTrue(result["digital_twin_enabled"])
        self.assertIsNotNone(result["digital_twin_selection"])
        self.assertIn("action", result["digital_twin_selection"])
        self.assertIn("selection_reason", result["digital_twin_selection"])
        self.assertIn("digital_twin_decision_signal", result)
        self.assertIsInstance(result["digital_twin_decision_signal"], dict)
        self.assertIn("normalized_score", result["digital_twin_decision_signal"])
        self.assertIn("digital_twin_advisory", result)
        self.assertIsInstance(result["digital_twin_advisory"], dict)
        self.assertIn("first_action", result["digital_twin_advisory"])
        self.assertIn("best_sequence", result["digital_twin_advisory"])
        self.assertEqual(result["recommended_action"], result["digital_twin_advisory"]["first_action"])
        self.assertEqual(result["recommended_plan_actions"], [result["recommended_action"]])


if __name__ == "__main__":
    unittest.main()
