import unittest

from backend.models.goal_state import GoalState
from backend.planning.beam_node import BeamNode
from backend.planning.beam_search import BeamSearch
from backend.planning.state_evaluator import StateEvaluator


class StateEvaluatorTests(unittest.TestCase):
    def test_utility_contribution(self):
        evaluator = StateEvaluator(weights={"utility": 1.0, "goal_alignment": 0.0, "risk": 0.0, "cost": 0.0, "confidence": 0.0})
        result = evaluator.evaluate_state(
            current_state={"python": 40},
            predicted_state={"python": 48},
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.8,
            risk=0.0,
            cost=0.0,
            confidence=0.0,
        )
        self.assertAlmostEqual(result.components["utility"], 0.8)
        self.assertAlmostEqual(result.score, 0.8)

    def test_goal_alignment_contribution(self):
        evaluator = StateEvaluator(weights={"utility": 0.0, "goal_alignment": 1.0, "risk": 0.0, "cost": 0.0, "confidence": 0.0})
        result = evaluator.evaluate_state(
            current_state={"python": 40},
            predicted_state={"python": 70},
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.0,
            risk=0.0,
            cost=0.0,
            confidence=0.0,
        )
        self.assertGreater(result.components["goal_alignment"], 0.0)
        self.assertGreater(result.score, 0.0)

    def test_risk_and_cost_penalties(self):
        evaluator = StateEvaluator(weights={"utility": 0.0, "goal_alignment": 0.0, "risk": 1.0, "cost": 1.0, "confidence": 0.0})
        result = evaluator.evaluate_state(
            current_state={"python": 40},
            predicted_state={"python": 50},
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.0,
            risk=0.5,
            cost=0.7,
            confidence=0.0,
        )
        self.assertLess(result.score, 0.0)
        self.assertAlmostEqual(result.components["risk_penalty"], -0.5)
        self.assertAlmostEqual(result.components["cost_penalty"], -0.7)

    def test_confidence_contribution(self):
        evaluator = StateEvaluator(weights={"utility": 0.0, "goal_alignment": 0.0, "risk": 0.0, "cost": 0.0, "confidence": 1.0})
        result = evaluator.evaluate_state(
            current_state={"python": 40},
            predicted_state={"python": 55},
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.0,
            risk=0.0,
            cost=0.0,
            confidence=0.9,
        )
        self.assertAlmostEqual(result.components["confidence"], 0.9)
        self.assertAlmostEqual(result.score, 0.9)

    def test_weight_changes_affect_ranking(self):
        node_a = BeamNode.root({"python": 40})
        node_a.predicted_state = {"python": 50}
        node_a.accumulated_utility = 0.7
        node_a.accumulated_risk = 0.1
        node_a.accumulated_cost = 0.1
        node_a.goal_alignment = {"Improve Python": 0.8}

        node_b = BeamNode.root({"python": 40})
        node_b.predicted_state = {"python": 60}
        node_b.accumulated_utility = 0.2
        node_b.accumulated_risk = 0.8
        node_b.accumulated_cost = 0.8
        node_b.goal_alignment = {"Improve Python": 0.2}

        weights_a = {"utility": 1.0, "goal_alignment": 1.0, "risk": 0.0, "cost": 0.0, "confidence": 0.0}
        weights_b = {"utility": 0.0, "goal_alignment": 0.0, "risk": 1.0, "cost": 1.0, "confidence": 0.0}

        evaluator = StateEvaluator()
        score_a = evaluator.evaluate_node(node_a, GoalState(goal="Improve Python", target_skills={"python": 80}), weights=weights_a).score
        score_b = evaluator.evaluate_node(node_b, GoalState(goal="Improve Python", target_skills={"python": 80}), weights=weights_b).score
        self.assertGreater(score_a, score_b)

    def test_beam_search_uses_evaluator_for_ranking(self):
        class FakeReasoner:
            def generate_candidates(self, context):
                return []

        root = BeamNode.root({"python": 40})
        root.predicted_state = {"python": 40}
        root.accumulated_utility = 0.6

        beam_search = BeamSearch(beam_width=2, max_depth=1, decision_reasoner=FakeReasoner())
        result = beam_search.search(root, context=None, goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}))
        self.assertEqual(result, [root])

    def test_explanation_metadata_present(self):
        evaluator = StateEvaluator()
        result = evaluator.evaluate_state(
            current_state={"python": 40},
            predicted_state={"python": 70},
            goal_state=GoalState(goal="Improve Python", target_skills={"python": 80}),
            utility=0.7,
            risk=0.2,
            cost=0.1,
            confidence=0.8,
        )
        self.assertIn("score", result.explanation)
        self.assertIn("components", result.explanation)


if __name__ == "__main__":
    unittest.main()
