"""
Tests for 17.6A: State Transition × Calibration Interaction.

Validates the observational framework and summary outputs without changing
calibration logic.
"""

from datetime import datetime
from pathlib import Path

import pytest

from backend.experiments.research_state_transition_calibration_17_6_a import (
    ResearchPhase17_6_A,
    StateTransitionCalibrationAnalyzer,
    StateTransitionEvent,
    TransitionBucketSummary,
    TransitionInteractionResult,
)


class TestStateTransitionEvent:
    def test_creation(self):
        event = StateTransitionEvent(
            seed=42,
            category="high_skill_practice",
            step=3,
            state_before={"python": 40, "dsa": 35},
            state_after={"python": 52, "dsa": 42},
            feature_delta={"python": 12, "dsa": 7},
            prediction={"python": 45, "dsa": 36},
            actual={"python": 52, "dsa": 42},
            signed_error={"python": 7, "dsa": 6},
            bias_before={"python": 0.1, "dsa": 0.2},
            bias_delta={"python": 0.14, "dsa": 0.12},
            bias_after={"python": 0.24, "dsa": 0.32},
            transition_magnitude=9.5,
            number_of_features_changed=2,
            largest_feature_change="python",
            direction_of_state_change="positive",
        )
        assert event.seed == 42
        assert event.direction_of_state_change == "positive"


class TestTransitionBucketSummary:
    def test_creation(self):
        summary = TransitionBucketSummary(
            bucket_name="large_transitions",
            event_count=10,
            mean_signed_error=1.5,
            mean_abs_error=2.5,
            mean_bias_delta=0.2,
            mean_abs_bias_drift=0.4,
            direction_accuracy=0.8,
            final_prediction_error=5.0,
        )
        assert summary.bucket_name == "large_transitions"
        assert summary.direction_accuracy == 0.8


class TestTransitionInteractionResult:
    def test_to_dict(self):
        result = TransitionInteractionResult(
            analysis_date=datetime.now().isoformat(),
            learning_rate=0.007,
            total_seeds=1,
            seed_results={42: {"stable": TransitionBucketSummary("stable", 1, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)}},
        )
        payload = result.to_dict()
        assert payload["total_seeds"] == 1
        assert "42" in payload["seed_results"]


class TestStateTransitionCalibrationAnalyzer:
    def test_initialization(self):
        analyzer = StateTransitionCalibrationAnalyzer(seed=42, learning_rate=0.007)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007

    def test_analyze_seed_returns_result(self):
        analyzer = StateTransitionCalibrationAnalyzer(seed=42, learning_rate=0.007)
        result = analyzer.analyze_seed()
        assert isinstance(result, dict)
        assert "stable" in result
        assert "large" in result
        assert result["stable"].event_count > 0


@pytest.mark.slow
class TestPhase17_6_AIntegration:
    def test_orchestrator_run(self):
        orchestrator = ResearchPhase17_6_A(learning_rate=0.007)
        result = orchestrator.run()
        assert isinstance(result, TransitionInteractionResult)
        assert result.total_seeds == 5
        assert len(result.seed_results) == 5

    def test_results_file_written(self):
        orchestrator = ResearchPhase17_6_A(learning_rate=0.007)
        orchestrator.run()
        path = Path("backend/experiments/results/research_17_6_a_state_transition_calibration.json")
        assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
