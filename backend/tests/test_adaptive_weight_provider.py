from backend.models.goal_state import GoalState
from backend.planning.adaptive_weight_provider import AdaptiveWeightProvider
from backend.planning.planning_context import PlanningContext


def test_adaptive_weights_respect_risk_tolerance():
    provider = AdaptiveWeightProvider()
    goal = GoalState(goal="Safe Growth", target_skills={"focus": 60})
    low_risk_context = PlanningContext(
        current_state={"focus": 40},
        goal_state=goal,
        risk_tolerance=0.9,
        uncertainty_tolerance=0.5,
        confidence=0.5,
    )
    high_risk_context = PlanningContext(
        current_state={"focus": 40},
        goal_state=goal,
        risk_tolerance=0.1,
        uncertainty_tolerance=0.5,
        confidence=0.5,
    )

    low_risk_weights = provider.provide_weights(low_risk_context)
    high_risk_weights = provider.provide_weights(high_risk_context)

    assert low_risk_weights["risk"] < high_risk_weights["risk"]


def test_adaptive_weights_respect_uncertainty_tolerance():
    provider = AdaptiveWeightProvider()
    goal = GoalState(goal="Robust Growth", target_skills={"resilience": 70})
    low_uncertainty_context = PlanningContext(
        current_state={"resilience": 50},
        goal_state=goal,
        risk_tolerance=0.5,
        uncertainty_tolerance=0.9,
        confidence=0.5,
    )
    high_uncertainty_context = PlanningContext(
        current_state={"resilience": 50},
        goal_state=goal,
        risk_tolerance=0.5,
        uncertainty_tolerance=0.1,
        confidence=0.5,
    )

    low_uncertainty_weights = provider.provide_weights(low_uncertainty_context)
    high_uncertainty_weights = provider.provide_weights(high_uncertainty_context)

    assert low_uncertainty_weights["uncertainty"] < high_uncertainty_weights["uncertainty"]


def test_adaptive_weight_distribution_is_normalized():
    provider = AdaptiveWeightProvider()
    goal = GoalState(goal="Balanced Growth", target_skills={"adaptability": 75})
    context = PlanningContext(
        current_state={"adaptability": 45},
        goal_state=goal,
        risk_tolerance=0.4,
        uncertainty_tolerance=0.6,
        confidence=0.8,
    )

    weights = provider.provide_weights(context)
    assert abs(sum(weights.values()) - 1.0) < 1e-6
    assert all(0.0 <= value <= 1.0 for value in weights.values())


def test_adaptive_weight_provider_rejects_invalid_context():
    provider = AdaptiveWeightProvider()
    goal = GoalState(goal="Invalid Growth", target_skills={"stability": 80})

    try:
        PlanningContext(
            current_state={"stability": 50},
            goal_state=goal,
            risk_tolerance=1.2,
            uncertainty_tolerance=-0.1,
            confidence=0.5,
        )
        assert False, "Expected PlanningContext validation to fail"
    except ValueError:
        pass
