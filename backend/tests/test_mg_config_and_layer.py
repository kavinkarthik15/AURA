"""
Unit tests for MGCompatibilityConfig and MGCompatibilityLayer.

Tests basic functionality of configuration and compatibility layer.
"""

import pytest

from backend.compatibility.mg_compatibility import MGCompatibilityLayer, PredictionMetadata
from backend.compatibility.mg_config import MGCompatibilityConfig


class TestMGCompatibilityConfig:
    """Test MGCompatibilityConfig dataclass."""

    def test_default_config_disabled(self):
        """Default config should have MG disabled."""
        config = MGCompatibilityConfig()
        assert config.enabled is False
        assert config.use_motivation is False
        assert config.use_goals is False
        assert not config.is_active()

    def test_config_validation_passes_for_disabled(self):
        """Disabled config should always be valid."""
        config = MGCompatibilityConfig()
        is_valid, error = config.validate()
        assert is_valid
        assert error == ""

    def test_config_validation_fails_with_use_motivation_but_zero_coeff(self):
        """Should fail if use_motivation=True but motivation_coefficient=0."""
        config = MGCompatibilityConfig(
            enabled=True,
            use_motivation=True,
            use_goals=True,
            motivation_coefficient=0.0,  # Should be non-zero
            goals_coefficient=0.5,
            rollout_percentage=100.0,
        )
        is_valid, error = config.validate()
        assert not is_valid
        assert "motivation_coefficient is 0.0" in error

    def test_config_validation_coefficient_drift_tolerance(self):
        """Coefficient drift tolerance should be in [0, 1]."""
        config = MGCompatibilityConfig(coefficient_drift_tolerance=1.5)
        is_valid, error = config.validate()
        assert not is_valid
        assert "drift_tolerance" in error

    def test_config_validation_rollout_percentage(self):
        """Rollout percentage should be in [0, 100]."""
        config = MGCompatibilityConfig(rollout_percentage=150.0)
        is_valid, error = config.validate()
        assert not is_valid
        assert "rollout_percentage" in error

    def test_config_to_dict(self):
        """Should export to dict."""
        config = MGCompatibilityConfig(enabled=False, rollout_percentage=50.0)
        data = config.to_dict()
        assert data["enabled"] is False
        assert data["rollout_percentage"] == 50.0

    def test_config_from_dict(self):
        """Should create from dict."""
        data = {"enabled": True, "rollout_percentage": 25.0, "motivation_coefficient": 0.5}
        config = MGCompatibilityConfig.from_dict(data)
        assert config.enabled is True
        assert config.rollout_percentage == 25.0

    def test_stage_profiles(self):
        """Test stage profile creation."""
        stage0 = MGCompatibilityConfig.stage_0_disabled()
        assert not stage0.is_active()

        stage1 = MGCompatibilityConfig.stage_1_shadow(motivation_coefficient=0.5, goals_coefficient=0.5)
        assert stage1.use_motivation is True
        assert stage1.use_goals is True
        assert stage1.rollout_percentage == 0.0

        stage2 = MGCompatibilityConfig.stage_2_controlled(rollout_percentage=50.0)
        assert stage2.enabled is True
        assert stage2.rollout_percentage == 50.0

        stage3 = MGCompatibilityConfig.stage_3_full()
        assert stage3.enabled is True
        assert stage3.rollout_percentage == 100.0


class TestMGCompatibilityLayer:
    """Test MGCompatibilityLayer."""

    def test_layer_creation(self):
        """Should create layer with config."""
        config = MGCompatibilityConfig()
        layer = MGCompatibilityLayer(config)
        assert layer.config == config

    def test_layer_disabled_returns_legacy(self):
        """With MG disabled, should return legacy prediction unchanged."""
        config = MGCompatibilityConfig(enabled=False)
        layer = MGCompatibilityLayer(config)

        legacy_pred = {
            "current_state": {"python": 50},
            "predicted_future_state": {"python": 55},
            "confidence": 0.8,
        }
        state = {"skills": {"python": 50}}

        result, metadata = layer.apply(legacy_pred, state, "Python Project")

        assert result == legacy_pred  # Should be unchanged
        assert metadata.source == "legacy"
        assert metadata.correction_applied is False

    def test_layer_extracts_motivation_signal(self):
        """Should extract motivation from skills using category-based mapping."""
        config = MGCompatibilityConfig()
        layer = MGCompatibilityLayer(config)

        # Low skill state
        state_low = {"python": 20, "dsa": 25, "machine_learning": 15, "projects": 18}
        motivation_low = layer._extract_motivation_signal(state_low, "action")
        assert motivation_low == 0.0  # mean = 19.5 < 30

        # High skill state
        state_high = {"python": 70, "dsa": 75, "machine_learning": 65, "projects": 80}
        motivation_high = layer._extract_motivation_signal(state_high, "action")
        assert motivation_high == 1.0  # mean = 72.5 >= 60

        # Medium skill state
        state_med = {"python": 45, "dsa": 40, "machine_learning": 50, "projects": 35}
        motivation_med = layer._extract_motivation_signal(state_med, "action")
        assert motivation_med == 0.5  # mean = 42.5, 30 <= x < 60

    def test_layer_extracts_goals_signal(self):
        """Should extract goals from goals dict."""
        config = MGCompatibilityConfig()
        layer = MGCompatibilityLayer(config)

        state = {"goals": {"goal1": 1, "goal2": 0, "goal3": 1, "goal4": 1, "goal5": 0}}

        goals = layer._extract_goals_signal(state, "action")
        assert 0.0 <= goals <= 1.0
        # 3 non-zero goals out of 5 = 0.6
        assert abs(goals - 0.6) < 0.01

    def test_layer_matches_17_12a_flat_state_goals_signal(self):
        """Production compatibility must mirror the validated flat-state Goals mapping."""
        config = MGCompatibilityConfig()
        layer = MGCompatibilityLayer(config)

        state = {
            "python": 32,
            "dsa": 28,
            "machine_learning": 30,
            "projects": 36,
        }
        action = "Research Paper"

        goals = layer._extract_goals_signal(state, action)
        expected = ((32 + 28 + 30 + 36) / 4.0 / 100.0) * 0.8

        assert abs(goals - expected) < 1e-9

    def test_layer_validates_signals(self):
        """Should reject invalid signals (NaN, Inf, out of range)."""
        config = MGCompatibilityConfig()
        layer = MGCompatibilityLayer(config)

        # Valid signals
        assert layer._validate_signals(0.5, 0.5) is True

        # NaN
        import math

        assert layer._validate_signals(math.nan, 0.5) is False

        # Inf
        assert layer._validate_signals(float("inf"), 0.5) is False

        # Out of range
        assert layer._validate_signals(1.5, 0.5) is False
        assert layer._validate_signals(-0.5, 0.5) is False

    def test_layer_computes_correction(self):
        """Should compute β₀ + β_M·M + β_G·G."""
        config = MGCompatibilityConfig(
            use_motivation=True,
            use_goals=True,
            motivation_coefficient=0.5,
            goals_coefficient=0.3,
            intercept_coefficient=0.1,
        )
        layer = MGCompatibilityLayer(config)

        correction = layer._compute_correction(motivation_signal=0.6, goals_signal=0.4)
        # 0.1 + 0.5*0.6 + 0.3*0.4 = 0.1 + 0.3 + 0.12 = 0.52
        assert abs(correction - 0.52) < 0.01

    def test_layer_applies_correction_to_prediction(self):
        """Should apply correction to predicted_future_state."""
        config = MGCompatibilityConfig(use_motivation=True, use_goals=True)
        layer = MGCompatibilityLayer(config)

        legacy_pred = {
            "predicted_future_state": {
                "python": 55,
                "dsa": 60,
                "machine_learning": 45,
                "projects": 70,
            }
        }

        corrected = layer._apply_correction_to_prediction(legacy_pred, correction=5.0)

        # Correction should be applied to all skills
        assert corrected["predicted_future_state"]["python"] == 60  # 55 + 5
        assert corrected["predicted_future_state"]["dsa"] == 65  # 60 + 5
        assert corrected != legacy_pred  # Should be a new dict

    def test_layer_preserves_fractional_correction(self):
        """Small MG corrections must not be truncated to zero-effect integer values."""
        config = MGCompatibilityConfig(use_motivation=True, use_goals=True)
        layer = MGCompatibilityLayer(config)

        legacy_pred = {"predicted_future_state": {"python": 55, "dsa": 60}}
        corrected = layer._apply_correction_to_prediction(legacy_pred, correction=0.2875)

        assert corrected["predicted_future_state"]["python"] == 55.2875
        assert corrected["predicted_future_state"]["dsa"] == 60.2875

    def test_layer_fallback_on_invalid_signals(self):
        """Should fallback to legacy on invalid signals."""
        config = MGCompatibilityConfig(
            enabled=True,
            use_motivation=True,
            use_goals=True,
            fallback_on_invalid_signals=True,
        )
        layer = MGCompatibilityLayer(config)

        legacy_pred = {"predicted_future_state": {"python": 55}}
        state = {"skills": {}}  # Empty state will produce invalid signals

        result, metadata = layer.apply(legacy_pred, state, "action")

        assert result == legacy_pred  # Should fallback to legacy
        assert metadata.source == "fallback"
        assert metadata.fallback_triggered is True

    def test_layer_fallback_rate_tracking(self):
        """Should track fallback rate."""
        config = MGCompatibilityConfig(enabled=False)
        layer = MGCompatibilityLayer(config)

        # Make multiple calls
        legacy_pred = {"predicted_future_state": {"python": 55}}
        state = {"skills": {"python": 50}}

        for _ in range(5):
            layer.apply(legacy_pred, state, "action")

        # All should be legacy (no fallback), so fallback_rate = 0
        assert layer.get_fallback_rate() == 0.0

    def test_layer_metadata_export(self):
        """Should export metadata correctly."""
        metadata = PredictionMetadata(
            source="mg", correction_applied=True, motivation_signal=0.5
        )
        data = metadata.to_dict()

        assert data["source"] == "mg"
        assert data["correction_applied"] is True
        assert data["motivation_signal"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
