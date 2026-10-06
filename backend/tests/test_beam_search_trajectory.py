import unittest

from backend.ai.context_builder import PlanningContext
from backend.ai.decision_reasoner import DecisionCandidate, Evidence, Prediction
from backend.models.goal_state import GoalState
from backend.planning.adaptive_weight_provider import AdaptiveWeightProvider
from backend.planning.beam_node import BeamNode
from backend.planning.beam_search import BeamSearch
from backend.planning.planning_context import PlanningContext as PlanningContextModel
from backend.planning.trajectory_evaluator import TrajectoryEvaluator


class TrajectoryRankingFakeReasoner:
    def generate_candidates(self, context):
        current_state = context.current_state or {}
        if current_state.get("python") == 50:
            return [
                DecisionCandidate(
                    decision_id="A1",
                    action="strong_immediate",
                    goal_supported="goal",
                    expected_outcome="",
                    prediction=Prediction(utility=0.90, risk=0.1, cost=0.1, confidence=0.8, predicted_state={"python": 70}),
                    evidence=Evidence(reasoning="short-term win"),
                ),
                DecisionCandidate(
                    decision_id="B1",
                    action="weaker_immediate",
                    goal_supported="goal",
                    expected_outcome="",
                    prediction=Prediction(utility=0.70, risk=0.1, cost=0.1, confidence=0.8, predicted_state={"python": 90}),
                    evidence=Evidence(reasoning="longer-term win"),
                ),
            ]
        return []


class BeamSearchTrajectoryTests(unittest.TestCase):
    def _make_candidate(self, decision_id: str, action: str, predicted_state: dict, utility: float = 1.0, risk: float = 0.1, cost: float = 0.2, confidence: float = 0.8):
        return DecisionCandidate(
            decision_id=decision_id,
            action=action,
            goal_supported="goal",
            expected_outcome="",
            prediction=Prediction(
                utility=utility,
                risk=risk,
                cost=cost,
                confidence=confidence,
                expected_state_change={k: float(v) - float(predicted_state.get("baseline", 0.0)) for k, v in predicted_state.items() if k != "baseline"},
                predicted_state={k: float(v) for k, v in predicted_state.items() if k != "baseline"},
            ),
            evidence=Evidence(reasoning=f"reasoning for {decision_id}"),
        )

    def test_single_node_trajectory_can_be_evaluated(self):
        root = BeamNode.root({"python": 50})
        root.predicted_state = {"python": 60}
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})

        beam = BeamSearch(trajectory_evaluator=TrajectoryEvaluator())
        result = beam.evaluate_trajectory(root, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal)

        self.assertIsNotNone(result)
        self.assertEqual(result["horizon"], 1)
        self.assertIn("trajectory_score", result)
        self.assertIn("step_evaluations", result)

    def test_multistep_branch_produces_trajectory_evaluation(self):
        root = BeamNode.root({"python": 50})
        root.predicted_state = {"python": 50}

        child = BeamNode(
            decision=self._make_candidate("D1", "practice", {"python": 60}),
            current_state={"python": 50},
            predicted_state={"python": 60},
            decision_history=["D1"],
            accumulated_utility=2.0,
        )
        child.parent = root
        root.children.append(child)

        grandchild = BeamNode(
            decision=self._make_candidate("D2", "practice", {"python": 75}),
            current_state={"python": 60},
            predicted_state={"python": 75},
            decision_history=["D1", "D2"],
            accumulated_utility=5.0,
        )
        grandchild.parent = child
        child.children.append(grandchild)

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        beam = BeamSearch(trajectory_evaluator=TrajectoryEvaluator())
        result = beam.evaluate_trajectory(grandchild, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal)

        self.assertIsNotNone(result)
        self.assertEqual(result["horizon"], 2)
        self.assertEqual(len(result["step_evaluations"]), 2)
        self.assertGreater(result["trajectory_score"], 0.0)

    def test_step_evaluations_are_preserved(self):
        root = BeamNode.root({"python": 50})
        child = BeamNode(
            decision=self._make_candidate("D1", "practice", {"python": 65}),
            current_state={"python": 50},
            predicted_state={"python": 65},
            decision_history=["D1"],
            accumulated_utility=1.0,
        )
        child.parent = root
        root.children.append(child)

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        beam = BeamSearch(trajectory_evaluator=TrajectoryEvaluator())
        result = beam.evaluate_trajectory(child, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal)

        self.assertEqual(len(result["step_evaluations"]), 1)
        self.assertIn("expected_value", result["step_evaluations"][0])

    def test_missing_trajectory_evaluator_falls_back_safely(self):
        root = BeamNode.root({"python": 50})
        root.predicted_state = {"python": 60}
        beam = BeamSearch()
        result = beam.evaluate_trajectory(root, PlanningContext(goal="Improve Python", current_state={"python": 50}))
        self.assertIsNone(result)

    def test_trajectory_rank_can_prefer_longer_term_gain_over_immediate_utility(self):
        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        root = BeamNode.root({"python": 50})
        context = PlanningContext(goal="Improve Python", current_state={"python": 50})
        beam = BeamSearch(beam_width=2, max_depth=1, decision_reasoner=TrajectoryRankingFakeReasoner(), trajectory_evaluator=TrajectoryEvaluator())

        survivors = beam.search(root, context, goal)

        self.assertEqual(len(survivors), 2)
        winner = max(survivors, key=lambda node: beam.evaluate_trajectory(node, context, goal)["trajectory_score"])
        self.assertEqual(winner.decision.decision_id, "B1")

    def test_end_to_end_trajectory_selection_prefers_long_term_best(self):
        class EndToEndReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                if current_state.get("python") == 50:
                    return [
                        DecisionCandidate(
                            decision_id="A",
                            action="short_term_win",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(utility=0.90, risk=0.1, cost=0.1, confidence=0.8, predicted_state={"python": 70}),
                            evidence=Evidence(reasoning="higher immediate utility"),
                        ),
                        DecisionCandidate(
                            decision_id="B",
                            action="long_term_win",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(utility=0.70, risk=0.1, cost=0.1, confidence=0.8, predicted_state={"python": 90}),
                            evidence=Evidence(reasoning="better long-term trajectory"),
                        ),
                    ]
                if current_state.get("python") == 70:
                    return [
                        DecisionCandidate(
                            decision_id="A2",
                            action="continue_a",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(utility=0.40, risk=0.2, cost=0.1, confidence=0.7, predicted_state={"python": 75}),
                            evidence=Evidence(reasoning="modest continuation"),
                        )
                    ]
                if current_state.get("python") == 90:
                    return [
                        DecisionCandidate(
                            decision_id="B2",
                            action="continue_b",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(utility=0.45, risk=0.1, cost=0.1, confidence=0.9, predicted_state={"python": 98}),
                            evidence=Evidence(reasoning="strong continuation"),
                        )
                    ]
                return []

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        root = BeamNode.root({"python": 50})
        context = PlanningContext(goal="Improve Python", current_state={"python": 50})
        beam = BeamSearch(beam_width=2, max_depth=2, decision_reasoner=EndToEndReasoner(), trajectory_evaluator=TrajectoryEvaluator())

        survivors = beam.search(root, context, goal)
        winner = max(survivors, key=lambda node: beam.evaluate_trajectory(node, context, goal)["trajectory_score"])
        non_winning_scores = [
            beam.evaluate_trajectory(node, context, goal)["trajectory_score"]
            for node in survivors
            if node is not winner
        ]

        self.assertIn("B", winner.decision_history)
        self.assertTrue(non_winning_scores)
        self.assertGreater(
            beam.evaluate_trajectory(winner, context, goal)["trajectory_score"],
            max(non_winning_scores),
        )

    def test_beam_width_and_max_depth_are_respected(self):
        class WidthDepthReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                return [
                    DecisionCandidate(
                        decision_id=f"C{i}",
                        action=f"action_{i}",
                        goal_supported="goal",
                        expected_outcome="",
                        prediction=Prediction(utility=float(i), risk=0.1, cost=0.1, confidence=0.7, predicted_state={"python": current_state.get("python", 0) + i}),
                        evidence=Evidence(reasoning=f"candidate {i}"),
                    )
                    for i in range(1, 6)
                ]

        beam = BeamSearch(beam_width=2, max_depth=3, decision_reasoner=WidthDepthReasoner(), trajectory_evaluator=TrajectoryEvaluator())
        root = BeamNode.root({"python": 50})
        survivors = beam.search(root, PlanningContext(goal="Improve Python", current_state={"python": 50}), GoalState(goal="Improve Python", target_skills={"python": 80}))

        self.assertEqual(len(survivors), 2)
        self.assertTrue(all(node.depth <= 3 for node in survivors))

    def test_explainability_payload_retains_decisions_states_and_evidence(self):
        root = BeamNode.root({"python": 50})
        root.decision = DecisionCandidate(
            decision_id="EX1",
            action="practice",
            goal_supported="goal",
            expected_outcome="",
            prediction=Prediction(utility=0.8, risk=0.1, cost=0.1, confidence=0.9, predicted_state={"python": 60}),
            evidence=Evidence(reasoning="clear progress"),
        )
        root.predicted_state = {"python": 60}
        beam = BeamSearch(trajectory_evaluator=TrajectoryEvaluator())
        result = beam.evaluate_trajectory(root, PlanningContext(goal="Improve Python", current_state={"python": 50}), GoalState(goal="Improve Python", target_skills={"python": 80}))

        self.assertIn("trajectory_score", result)
        self.assertIn("step_evaluations", result)
        self.assertIn("explanation", result)
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["horizon"], 1)

    def test_existing_beamnode_behavior_remains_unchanged(self):
        root = BeamNode.root({"python": 20})
        child = BeamNode(
            decision=self._make_candidate("D1", "practice", {"python": 25}),
            current_state={"python": 20},
            predicted_state={"python": 25},
            accumulated_utility=2.0,
        )
        root.add_child(child)

        self.assertEqual(root.depth, 0)
        self.assertEqual(child.parent, root)
        self.assertEqual(child.current_state, {"python": 20})
        self.assertEqual(child.predicted_state, {"python": 25})
        self.assertEqual(root.children[0], child)

    def test_context_aware_beam_selection_changes_branch_ranking(self):
        class ContextAwareReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                if current_state.get("python") == 50:
                    return [
                        DecisionCandidate(
                            decision_id="SAFE",
                            action="safe_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=0.6,
                                risk=0.02,
                                cost=0.05,
                                confidence=0.95,
                                predicted_state={"python": 74},
                            ),
                            evidence=Evidence(reasoning="steady, predictable outcome"),
                        ),
                        DecisionCandidate(
                            decision_id="RISKY",
                            action="risky_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=3.2,
                                risk=0.9,
                                cost=0.2,
                                confidence=0.2,
                                predicted_state={"python": 99},
                            ),
                            evidence=Evidence(reasoning="high upside but volatile"),
                        ),
                    ]
                return []

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        beam = BeamSearch(
            beam_width=2,
            max_depth=1,
            decision_reasoner=ContextAwareReasoner(),
            trajectory_evaluator=TrajectoryEvaluator(adaptive_weight_provider=AdaptiveWeightProvider()),
        )

        risk_averse_context = PlanningContextModel(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.1,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )
        risk_tolerant_context = PlanningContextModel(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.9,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )

        risk_averse_survivors = beam.search(BeamNode.root({"python": 50}), PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_averse_context)
        risk_tolerant_survivors = beam.search(BeamNode.root({"python": 50}), PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_tolerant_context)

        risk_averse_scores = {node.decision.decision_id: beam.evaluate_trajectory(node, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_averse_context)["trajectory_score"] for node in risk_averse_survivors}
        risk_tolerant_scores = {node.decision.decision_id: beam.evaluate_trajectory(node, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_tolerant_context)["trajectory_score"] for node in risk_tolerant_survivors}

        self.assertGreater(risk_averse_scores["SAFE"], risk_averse_scores["RISKY"])
        self.assertNotEqual(risk_averse_scores["SAFE"], risk_tolerant_scores["SAFE"])
        self.assertNotEqual(risk_averse_scores["RISKY"], risk_tolerant_scores["RISKY"])

    def test_context_aware_beam_selection_stabilizes_full_pipeline(self):
        class FullPipelineReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                if current_state.get("python") == 50:
                    return [
                        DecisionCandidate(
                            decision_id="SAFE",
                            action="safe_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=0.6,
                                risk=0.02,
                                cost=0.05,
                                confidence=0.95,
                                predicted_state={"python": 74},
                            ),
                            evidence=Evidence(reasoning="steady and predictable"),
                        ),
                        DecisionCandidate(
                            decision_id="RISKY",
                            action="risky_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=1.5,
                                risk=0.6,
                                cost=0.1,
                                confidence=0.4,
                                predicted_state={"python": 95},
                            ),
                            evidence=Evidence(reasoning="high upside but volatile"),
                        ),
                    ]
                return []

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        beam = BeamSearch(
            beam_width=2,
            max_depth=1,
            decision_reasoner=FullPipelineReasoner(),
            trajectory_evaluator=TrajectoryEvaluator(adaptive_weight_provider=AdaptiveWeightProvider()),
        )

        risk_averse_context = PlanningContextModel(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.1,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )
        risk_tolerant_context = PlanningContextModel(
            current_state={"python": 50},
            goal_state=goal,
            risk_tolerance=0.9,
            uncertainty_tolerance=0.5,
            confidence=0.5,
        )

        risk_averse_survivors = beam.search(BeamNode.root({"python": 50}), PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_averse_context)
        risk_tolerant_survivors = beam.search(BeamNode.root({"python": 50}), PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_tolerant_context)

        risk_averse_scores = {
            node.decision.decision_id: beam.evaluate_trajectory(node, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_averse_context)["trajectory_score"]
            for node in risk_averse_survivors
        }
        risk_tolerant_scores = {
            node.decision.decision_id: beam.evaluate_trajectory(node, PlanningContext(goal="Improve Python", current_state={"python": 50}), goal, risk_tolerant_context)["trajectory_score"]
            for node in risk_tolerant_survivors
        }

        self.assertGreater(risk_averse_scores["SAFE"], risk_averse_scores["RISKY"])
        self.assertNotEqual(risk_averse_scores["SAFE"], risk_tolerant_scores["SAFE"])
        self.assertNotEqual(risk_averse_scores["RISKY"], risk_tolerant_scores["RISKY"])
        self.assertEqual(risk_averse_survivors[0].decision_history, ["SAFE"])
        self.assertEqual(risk_tolerant_survivors[0].decision_history, ["SAFE"])
        self.assertIn("SAFE", [node.decision.decision_id for node in risk_averse_survivors])
        self.assertIn("SAFE", [node.decision.decision_id for node in risk_tolerant_survivors])

    def test_beam_search_supports_risk_sensitive_ranking(self):
        class RiskAwareReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                if current_state.get("python") == 50:
                    return [
                        DecisionCandidate(
                            decision_id="RISKY",
                            action="risky_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=1.0,
                                risk=0.55,
                                cost=0.1,
                                confidence=0.7,
                                predicted_state={"python": 90},
                            ),
                            evidence=Evidence(reasoning="high expected value"),
                        ),
                        DecisionCandidate(
                            decision_id="SAFE",
                            action="safe_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=0.82,
                                risk=0.08,
                                cost=0.1,
                                confidence=0.8,
                                predicted_state={"python": 80},
                            ),
                            evidence=Evidence(reasoning="lower risk"),
                        ),
                    ]
                return []

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        context = PlanningContext(goal="Improve Python", current_state={"python": 50})

        neutral = BeamSearch(beam_width=2, max_depth=1, decision_reasoner=RiskAwareReasoner(), trajectory_evaluator=TrajectoryEvaluator())
        sensitive = BeamSearch(
            beam_width=2,
            max_depth=1,
            decision_reasoner=RiskAwareReasoner(),
            trajectory_evaluator=TrajectoryEvaluator(risk_sensitivity=1.5, uncertainty_sensitivity=1.0),
        )

        neutral_survivors = neutral.search(BeamNode.root({"python": 50}), context, goal)
        sensitive_survivors = sensitive.search(BeamNode.root({"python": 50}), context, goal)

        neutral_ranking = sorted(
            [neutral.evaluate_trajectory(node, context, goal)["trajectory_score"] for node in neutral_survivors],
            reverse=True,
        )
        sensitive_ranking = sorted(
            [sensitive.evaluate_trajectory(node, context, goal)["trajectory_score"] for node in sensitive_survivors],
            reverse=True,
        )

        self.assertGreater(neutral_ranking[0], sensitive_ranking[0] if len(sensitive_ranking) > 0 else 0.0)
        self.assertEqual(len(sensitive_survivors), 2)
        self.assertTrue(
            any(node.decision.decision_id == "SAFE" for node in sensitive_survivors)
        )

    def test_beam_search_uses_uncertainty_penalty_in_selection(self):
        class UncertainReasoner:
            def generate_candidates(self, context):
                current_state = context.current_state or {}
                if current_state.get("python") == 50:
                    return [
                        DecisionCandidate(
                            decision_id="CERTAIN",
                            action="certain_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=0.8,
                                risk=0.1,
                                cost=0.1,
                                confidence=0.9,
                                predicted_state={"python": 75},
                            ),
                            evidence=Evidence(reasoning="stable"),
                        ),
                        DecisionCandidate(
                            decision_id="UNCERTAIN",
                            action="uncertain_path",
                            goal_supported="goal",
                            expected_outcome="",
                            prediction=Prediction(
                                utility=0.9,
                                risk=0.1,
                                cost=0.1,
                                confidence=0.5,
                                predicted_state={"python": 85},
                            ),
                            evidence=Evidence(reasoning="wide outcome spread"),
                        ),
                    ]
                return []

        goal = GoalState(goal="Improve Python", target_skills={"python": 80})
        context = PlanningContext(goal="Improve Python", current_state={"python": 50})

        neutral = BeamSearch(beam_width=2, max_depth=1, decision_reasoner=UncertainReasoner(), trajectory_evaluator=TrajectoryEvaluator())
        uncertain_sensitive = BeamSearch(
            beam_width=2,
            max_depth=1,
            decision_reasoner=UncertainReasoner(),
            trajectory_evaluator=TrajectoryEvaluator(risk_sensitivity=0.0, uncertainty_sensitivity=2.0),
        )

        neutral_scores = {node.decision.decision_id: neutral.evaluate_trajectory(node, context, goal)["trajectory_score"] for node in neutral.search(BeamNode.root({"python": 50}), context, goal)}
        sensitive_scores = {node.decision.decision_id: uncertain_sensitive.evaluate_trajectory(node, context, goal)["trajectory_score"] for node in uncertain_sensitive.search(BeamNode.root({"python": 50}), context, goal)}

        self.assertIn("CERTAIN", sensitive_scores)
        self.assertIn("UNCERTAIN", sensitive_scores)
        self.assertGreater(sensitive_scores["CERTAIN"], sensitive_scores["UNCERTAIN"])
        self.assertGreater(neutral_scores["UNCERTAIN"], sensitive_scores["UNCERTAIN"])


if __name__ == "__main__":
    unittest.main()
