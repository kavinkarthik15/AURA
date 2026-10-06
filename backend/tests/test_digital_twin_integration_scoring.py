import copy

from backend.models.goal_state import GoalState
from backend.planning.candidate_selector import CandidateSelector
from backend.planning.candidate_selector import CandidateActionResult
from backend.planning.digital_twin_score_translator import DigitalTwinScoreTranslator
from backend.services.beam_search_planner import BeamSearchPlanner
from backend.services.goal_plan_service import GoalPlanService


def test_disable_digital_twin_preserves_ranking() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    disabled_selector_planner = BeamSearchPlanner(candidate_selector=CandidateSelector(enabled=False, fallback_action="fallback"))
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    baseline = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=False)
    disabled_baseline = disabled_selector_planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=False)

    assert baseline["best_plan"] == disabled_baseline["best_plan"]
    assert baseline["search_trace"] == disabled_baseline["search_trace"]
    assert baseline["digital_twin_planner_adjustment"]["adjustment"] == 0.0
    assert disabled_baseline["digital_twin_planner_adjustment"]["adjustment"] == 0.0


def test_enabled_digital_twin_biases_candidate_ranking() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

    assert result["use_digital_twin"] is True
    assert result["digital_twin_enabled"] is True
    assert result["digital_twin_planner_adjustment"]["enabled"] is True
    assert "adjustment" in result["digital_twin_planner_adjustment"]


def test_zero_adjustment_preserves_baseline_ranking() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

    if result["digital_twin_planner_adjustment"]["adjustment"] == 0.0:
        baseline = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=False)
        assert baseline["best_plan"] == result["best_plan"]


def test_invalid_adjustment_uses_baseline_score() -> None:
    selector = CandidateSelector(enabled=False, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)
    baseline = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=False)

    assert result["best_plan"] == baseline["best_plan"]
    assert result["digital_twin_planner_adjustment"]["adjustment"] == 0.0


def test_positive_adjustment_boosts_candidate_score() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

    adjustment = result["digital_twin_planner_adjustment"]["adjustment"]
    assert adjustment >= 0.0


def test_negative_adjustment_penalizes_candidate_score() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

    assert result["digital_twin_planner_adjustment"]["adjustment"] >= -0.2


def test_bound_enforcement_limits_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = translator.translate(
        CandidateActionResult(
            action="study",
            score=100.0,
            probability=1.0,
            risk=0.0,
            uncertainty=0.0,
            selection_reason="trajectory_score",
            metadata={},
        )
    )
    adjustment = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=5.0, max_adjustment=0.2)

    assert abs(adjustment.adjustment) <= 0.2


def test_beam_width_works_with_adjustment() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = planner.search(current_state, goal_state, beam_width=3, max_depth=2, use_digital_twin=True)

    assert len(result.get("best_plan", [])) >= 1
    assert result["search_metrics"]["beam_width"] == 3


def test_no_mutation_of_original_candidate_objects() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})
    baseline_state = copy.deepcopy(current_state)

    planner.search(current_state, goal_state, beam_width=2, max_depth=1, use_digital_twin=True)

    assert current_state == baseline_state


def test_goal_plan_service_propagates_adjustment_metadata() -> None:
    selector = CandidateSelector(enabled=True, fallback_action="fallback")
    planner = BeamSearchPlanner(candidate_selector=selector)
    service = GoalPlanService(beam_search_planner=planner)
    current_state = {"python": 10, "dsa": 5, "projects": 1}
    goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})

    result = service.recommend_goal_plan(current_state, goal_state, use_digital_twin=True)

    assert result["use_digital_twin"] is True
    assert result["digital_twin_planner_adjustment"]["enabled"] is True
