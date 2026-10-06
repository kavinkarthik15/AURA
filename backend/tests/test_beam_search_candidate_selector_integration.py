from __future__ import annotations

from backend.ai.context_builder import PlanningContext
from backend.models.goal_state import GoalState
from backend.planning.beam_node import BeamNode
from backend.planning.beam_search import BeamSearch
from backend.planning.candidate_selector import CandidateSelector
from backend.planning.planning_context import PlanningContext as PlanningContextModel


class FakeReasoner:
    def generate_candidates(self, context):
        return []


def test_beam_search_uses_candidate_selector_when_enabled() -> None:
    root = BeamNode.root({"python": 10})
    context = PlanningContext(goal="G1", current_state={"python": 10})
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})
    selector = CandidateSelector(enabled=True, fallback_action="fallback")

    beam = BeamSearch(beam_width=1, max_depth=1, decision_reasoner=FakeReasoner(), candidate_selector=selector)
    survivors = beam.search(root, context, goal_state=goal, planning_context=PlanningContextModel(current_state={"python": 10}, goal_state=goal))

    assert survivors == [root]
    assert getattr(root, "metadata", {}).get("selected_action") is None


def test_beam_search_remains_backward_compatible_when_selector_disabled() -> None:
    root = BeamNode.root({"python": 10})
    context = PlanningContext(goal="G1", current_state={"python": 10})
    goal = GoalState(goal="Improve Python", target_skills={"python": 80})

    beam = BeamSearch(beam_width=1, max_depth=1, decision_reasoner=FakeReasoner())
    survivors = beam.search(root, context, goal_state=goal, planning_context=PlanningContextModel(current_state={"python": 10}, goal_state=goal))

    assert survivors == [root]
