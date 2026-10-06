"""
17.5A Unit Tests — Error-Signal Provenance Analysis

Tests for:
- CalibrationEvent data model
- SeedProvenanceResult accumulation
- ErrorSignalProvenanceAnalyzer core logic
- Direction matching invariant
- Zero-error and zero-delta handling
- Aggregate statistics computation
"""

import pytest
from datetime import datetime, timezone

from backend.experiments.research_error_signal_provenance_17_5_a import (
    CalibrationEvent,
    SeedProvenanceResult,
    ProvenanceAnalysisResult,
    ErrorSignalProvenanceAnalyzer,
    ResearchPhase17_5_A,
)


class TestCalibrationEvent:
    """Test CalibrationEvent data model."""
    
    def test_create_event_with_positive_match(self):
        """Test creating event where direction matches (positive case)."""
        event = CalibrationEvent(
            seed=42,
            step=1,
            category="python",
            predicted_value=2.5,
            actual_value=3.0,
            raw_error=0.5,
            signed_error=0.5,
            absolute_error=0.5,
            expected_state_bias_before=0.0,
            expected_state_bias_delta=0.0035,  # positive delta for positive error
            expected_state_bias_after=0.0035,
            expected_direction=1,  # positive error
            actual_update_direction=1,  # positive delta
            direction_match=True,
            direction_match_category="match",
        )
        
        assert event.direction_match is True
        assert event.expected_direction == 1
        assert event.actual_update_direction == 1
    
    def test_create_event_with_negative_match(self):
        """Test creating event where direction matches (negative case)."""
        event = CalibrationEvent(
            seed=42,
            step=2,
            category="ml",
            predicted_value=3.5,
            actual_value=2.8,
            raw_error=-0.7,
            signed_error=-0.7,
            absolute_error=0.7,
            expected_state_bias_before=0.01,
            expected_state_bias_delta=-0.0049,  # negative delta for negative error
            expected_state_bias_after=0.0051,
            expected_direction=-1,  # negative error
            actual_update_direction=-1,  # negative delta
            direction_match=True,
            direction_match_category="match",
        )
        
        assert event.direction_match is True
        assert event.expected_direction == -1
        assert event.actual_update_direction == -1
    
    def test_create_event_with_mismatch(self):
        """Test creating event where direction MISMATCHES."""
        event = CalibrationEvent(
            seed=789,
            step=5,
            category="highskill",
            predicted_value=2.0,
            actual_value=3.0,
            raw_error=1.0,
            signed_error=1.0,
            absolute_error=1.0,
            expected_state_bias_before=0.0,
            expected_state_bias_delta=-0.007,  # negative delta for positive error (MISMATCH)
            expected_state_bias_after=-0.007,
            expected_direction=1,  # positive error
            actual_update_direction=-1,  # negative delta (WRONG)
            direction_match=False,
            direction_match_category="mismatch",
        )
        
        assert event.direction_match is False
        assert event.expected_direction == 1
        assert event.actual_update_direction == -1
    
    def test_zero_error_event(self):
        """Test event where error is zero (should be skipped)."""
        event = CalibrationEvent(
            seed=42,
            step=3,
            category="python",
            predicted_value=2.5,
            actual_value=2.5,
            raw_error=0.0,
            signed_error=0.0,
            absolute_error=0.0,
            expected_state_bias_before=0.01,
            expected_state_bias_delta=0.0,
            expected_state_bias_after=0.01,
            expected_direction=0,
            actual_update_direction=0,
            direction_match=True,  # Zero errors don't count as mismatches
            direction_match_category="skip_zero_error",
        )
        
        assert event.direction_match_category == "skip_zero_error"
        assert event.direction_match is True
    
    def test_zero_delta_event(self):
        """Test event where delta is zero (should be skipped)."""
        event = CalibrationEvent(
            seed=42,
            step=4,
            category="javascript",
            predicted_value=2.0,
            actual_value=2.5,
            raw_error=0.5,
            signed_error=0.5,
            absolute_error=0.5,
            expected_state_bias_before=0.1,
            expected_state_bias_delta=0.0,  # No delta applied
            expected_state_bias_after=0.1,
            expected_direction=1,
            actual_update_direction=0,
            direction_match=True,  # Zero deltas don't count as mismatches
            direction_match_category="skip_zero_delta",
        )
        
        assert event.direction_match_category == "skip_zero_delta"
        assert event.direction_match is True


class TestSeedProvenanceResult:
    """Test SeedProvenanceResult aggregation."""
    
    def test_empty_result(self):
        """Test creating empty result."""
        result = SeedProvenanceResult(
            seed=42,
            total_events=0,
            events_with_nonzero_error=0,
            events_with_nonzero_delta=0,
            total_direction_matches=0,
            total_mismatches=0,
            direction_accuracy=0.0,
            events_skipped_zero_error=0,
            events_skipped_zero_delta=0,
        )
        
        assert result.seed == 42
        assert result.direction_accuracy == 0.0
    
    def test_perfect_accuracy(self):
        """Test result with 100% direction accuracy."""
        result = SeedProvenanceResult(
            seed=123,
            total_events=10,
            events_with_nonzero_error=9,
            events_with_nonzero_delta=9,
            total_direction_matches=9,
            total_mismatches=0,
            direction_accuracy=1.0,
            events_skipped_zero_error=0,
            events_skipped_zero_delta=1,
        )
        
        assert result.direction_accuracy == 1.0
        assert result.total_mismatches == 0
    
    def test_degraded_accuracy(self):
        """Test result with degraded direction accuracy (simulating seed 789/999)."""
        result = SeedProvenanceResult(
            seed=789,
            total_events=20,
            events_with_nonzero_error=18,
            events_with_nonzero_delta=18,
            total_direction_matches=14,  # 78% match rate
            total_mismatches=4,
            direction_accuracy=14 / 18,
            events_skipped_zero_error=1,
            events_skipped_zero_delta=1,
        )
        
        assert result.direction_accuracy == pytest.approx(0.7778, rel=0.01)
        assert result.total_mismatches == 4
    
    def test_category_statistics(self):
        """Test category breakdown in result."""
        result = SeedProvenanceResult(
            seed=42,
            total_events=20,
            events_with_nonzero_error=20,
            events_with_nonzero_delta=20,
            total_direction_matches=20,
            total_mismatches=0,
            direction_accuracy=1.0,
            events_skipped_zero_error=0,
            events_skipped_zero_delta=0,
            category_stats={
                "python": {"total": 10, "matches": 10, "mismatches": 0, "violations": []},
                "javascript": {"total": 10, "matches": 10, "mismatches": 0, "violations": []},
            }
        )
        
        assert len(result.category_stats) == 2
        assert result.category_stats["python"]["matches"] == 10
        assert result.category_stats["python"]["mismatches"] == 0


class TestProvenanceAnalysisResult:
    """Test complete analysis result."""
    
    def test_create_result(self):
        """Test creating analysis result."""
        result = ProvenanceAnalysisResult(
            analysis_date=datetime.now(timezone.utc).isoformat(),
            total_seeds=5,
            seeds=[42, 123, 456, 789, 999],
            learning_rate=0.007,
        )
        
        assert result.total_seeds == 5
        assert len(result.seeds) == 5
        assert result.learning_rate == 0.007
    
    def test_aggregate_statistics(self):
        """Test aggregate statistics across seeds."""
        result = ProvenanceAnalysisResult(
            analysis_date=datetime.now(timezone.utc).isoformat(),
            total_seeds=2,
            seeds=[42, 789],
            learning_rate=0.007,
            aggregate_matches=100,
            aggregate_mismatches=10,
        )
        
        # Should compute aggregated accuracy
        total = result.aggregate_matches + result.aggregate_mismatches
        expected_accuracy = result.aggregate_matches / total if total > 0 else 0.0
        
        # Manually set for this test
        result.aggregate_direction_accuracy = expected_accuracy
        
        assert result.aggregate_direction_accuracy == pytest.approx(0.9091, rel=0.01)


class TestErrorSignalProvenanceAnalyzer:
    """Test the core analyzer logic."""
    
    def test_sign_function(self):
        """Test sign computation."""
        analyzer = ErrorSignalProvenanceAnalyzer(seed=42, learning_rate=0.007)
        
        assert analyzer._sign(0.5) == 1
        assert analyzer._sign(-0.5) == -1
        assert analyzer._sign(0.0) == 0
        assert analyzer._sign(0.0001) == 1
        assert analyzer._sign(-0.0001) == -1
    
    def test_analyzer_initialization(self):
        """Test analyzer can be created with custom parameters."""
        analyzer = ErrorSignalProvenanceAnalyzer(seed=789, learning_rate=0.005)
        
        assert analyzer.seed == 789
        assert analyzer.learning_rate == 0.005
        assert len(analyzer.events) == 0


class TestResearchPhase17_5_A:
    """Test the orchestrator."""
    
    def test_initialize_with_defaults(self):
        """Test initializing with default seeds."""
        phase = ResearchPhase17_5_A()
        
        assert phase.seeds == [42, 123, 456, 789, 999]
        assert phase.learning_rate == 0.007
    
    def test_initialize_with_custom_seeds(self):
        """Test initializing with custom seeds."""
        phase = ResearchPhase17_5_A(seeds=[1, 2, 3], learning_rate=0.01)
        
        assert phase.seeds == [1, 2, 3]
        assert phase.learning_rate == 0.01
    
    @pytest.mark.slow
    def test_run_analysis_seed_42(self):
        """Test running full analysis on single seed (integration test)."""
        # Run just seed 42 for quick validation
        phase = ResearchPhase17_5_A(seeds=[42], learning_rate=0.007)
        result = phase.run()
        
        # Basic validation
        assert result.total_seeds == 1
        assert 42 in result.seed_results
        
        seed_result = result.seed_results[42]
        assert seed_result.seed == 42
        
        # Should have detected some events
        assert seed_result.total_events > 0
        
        # Should have computed direction accuracy
        assert 0.0 <= seed_result.direction_accuracy <= 1.0
    
    @pytest.mark.slow
    def test_run_quick_validation(self):
        """Quick validation with limited data (integration test)."""
        # Run just one seed with small dataset for validation
        phase = ResearchPhase17_5_A(seeds=[42])
        result = phase.run()
        
        # Result should be complete
        assert result.total_seeds >= 1
        assert result.aggregate_direction_accuracy >= 0.0
        assert len(result.key_findings) > 0


class TestDirectionInvariant:
    """Test the core invariant: expected_direction == actual_update_direction."""
    
    def test_positive_error_positive_delta_match(self):
        """Invariant: positive error + positive delta = MATCH."""
        event = CalibrationEvent(
            seed=42, step=0, category="test",
            predicted_value=1.0, actual_value=2.0,
            raw_error=1.0, signed_error=1.0, absolute_error=1.0,
            expected_state_bias_before=0.0,
            expected_state_bias_delta=0.007,
            expected_state_bias_after=0.007,
            expected_direction=1,  # positive
            actual_update_direction=1,  # positive
            direction_match=True,
            direction_match_category="match",
        )
        
        assert event.expected_direction == event.actual_update_direction
        assert event.direction_match is True
    
    def test_negative_error_negative_delta_match(self):
        """Invariant: negative error + negative delta = MATCH."""
        event = CalibrationEvent(
            seed=42, step=1, category="test",
            predicted_value=2.0, actual_value=1.0,
            raw_error=-1.0, signed_error=-1.0, absolute_error=1.0,
            expected_state_bias_before=0.01,
            expected_state_bias_delta=-0.007,
            expected_state_bias_after=0.003,
            expected_direction=-1,  # negative
            actual_update_direction=-1,  # negative
            direction_match=True,
            direction_match_category="match",
        )
        
        assert event.expected_direction == event.actual_update_direction
        assert event.direction_match is True
    
    def test_positive_error_negative_delta_mismatch(self):
        """Invariant: positive error + negative delta = MISMATCH."""
        event = CalibrationEvent(
            seed=789, step=2, category="test",
            predicted_value=1.0, actual_value=2.0,
            raw_error=1.0, signed_error=1.0, absolute_error=1.0,
            expected_state_bias_before=0.0,
            expected_state_bias_delta=-0.007,  # WRONG direction
            expected_state_bias_after=-0.007,
            expected_direction=1,  # positive error
            actual_update_direction=-1,  # negative delta (MISMATCH)
            direction_match=False,
            direction_match_category="mismatch",
        )
        
        assert event.expected_direction != event.actual_update_direction
        assert event.direction_match is False
    
    def test_negative_error_positive_delta_mismatch(self):
        """Invariant: negative error + positive delta = MISMATCH."""
        event = CalibrationEvent(
            seed=999, step=3, category="test",
            predicted_value=2.0, actual_value=1.0,
            raw_error=-1.0, signed_error=-1.0, absolute_error=1.0,
            expected_state_bias_before=0.01,
            expected_state_bias_delta=0.007,  # WRONG direction
            expected_state_bias_after=0.017,
            expected_direction=-1,  # negative error
            actual_update_direction=1,  # positive delta (MISMATCH)
            direction_match=False,
            direction_match_category="mismatch",
        )
        
        assert event.expected_direction != event.actual_update_direction
        assert event.direction_match is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
