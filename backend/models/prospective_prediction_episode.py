from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EpisodeStatus(StrEnum):
    PREDICTION_FROZEN = "PREDICTION_FROZEN"
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    AWAITING_OUTCOME = "AWAITING_OUTCOME"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    EXCLUDED = "EXCLUDED"
    MISSING_OUTCOME = "MISSING_OUTCOME"


class EpisodeEventType(StrEnum):
    EPISODE_CREATED = "EPISODE_CREATED"
    PREDICTION_FROZEN = "PREDICTION_FROZEN"
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    OUTCOME_DUE = "OUTCOME_DUE"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    EPISODE_EXCLUDED = "EPISODE_EXCLUDED"
    OUTCOME_MISSING = "OUTCOME_MISSING"


class OutcomeSource(StrEnum):
    USER_REPORTED = "USER_REPORTED"
    SYSTEM_OBSERVED = "SYSTEM_OBSERVED"
    ASSESSMENT = "ASSESSMENT"
    EXTERNAL_MEASUREMENT = "EXTERNAL_MEASUREMENT"
    VERIFIED_EVENT = "VERIFIED_EVENT"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PredictionTarget(FrozenModel):
    target_name: str = Field(min_length=1)
    target_dimension: Literal["skill"]
    target_unit: str = Field(min_length=1)
    target_scale: str = Field(min_length=1)
    measurement_method: str = Field(min_length=1)
    horizon_seconds: int = Field(gt=0)
    valid_range: tuple[float, float] = (0.0, 100.0)

    @field_validator("horizon_seconds", mode="before")
    @classmethod
    def reject_boolean_horizon(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("horizon_seconds must be a positive integer")
        return value

    @field_validator("target_name", "target_unit", "target_scale", "measurement_method")
    @classmethod
    def strip_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target fields must not be blank")
        return value

    @field_validator("valid_range")
    @classmethod
    def validate_valid_range(cls, value: tuple[float, float]) -> tuple[float, float]:
        lower, upper = value
        if not math.isfinite(lower) or not math.isfinite(upper) or lower >= upper:
            raise ValueError("valid_range must have finite bounds with lower less than upper")
        if lower < 0 or upper > 100:
            raise ValueError("career skill valid_range must be within [0, 100]")
        return value

    @field_validator("target_scale")
    @classmethod
    def require_supported_skill_scale(cls, value: str) -> str:
        if value.strip() != "0-100":
            raise ValueError("career skill targets must use the supported 0-100 scale")
        return value


class PredictionBundle(FrozenModel):
    base_prediction: dict[str, Any]
    mg_prediction: dict[str, Any]
    base_model_version: str = Field(min_length=1)
    mg_model_version: str = Field(min_length=1)
    mg_coefficients_version: str = Field(min_length=1)
    mg_configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("base_model_version", "mg_model_version", "mg_coefficients_version")
    @classmethod
    def validate_version_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("version identifiers must not be blank")
        return value


class OutcomeProvenance(FrozenModel):
    source_type: OutcomeSource
    collection_method: str = Field(min_length=1)
    recorded_by: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    observed_at: datetime
    quality: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    @field_validator("source_type", mode="before")
    @classmethod
    def reject_non_observation_sources(cls, value: Any) -> Any:
        forbidden = {
            "prediction",
            "simulation",
            "digital_twin",
            "synthetic",
            "legacy_prediction",
        }
        if isinstance(value, str) and value.strip().lower() in forbidden:
            raise ValueError(f"{value!r} is not an acceptable observed-outcome source")
        return value

    @field_validator("collection_method", "recorded_by", "evidence_id")
    @classmethod
    def strip_non_empty_provenance(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("provenance identifiers must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_aware_observation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("quality", mode="before")
    @classmethod
    def validate_quality_number(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("quality must be a finite number between 0 and 1")
        return value


class ObservedOutcome(FrozenModel):
    target_name: str = Field(min_length=1)
    target_dimension: Literal["skill"]
    target_unit: str = Field(min_length=1)
    target_scale: str = Field(min_length=1)
    value: int | float
    provenance: OutcomeProvenance

    @field_validator("value", mode="before")
    @classmethod
    def validate_finite_numeric_value(cls, value: Any) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("outcome value must be a finite number")
        if not math.isfinite(value):
            raise ValueError("outcome value must be a finite number")
        return value


class ProspectivePredictionEpisode(FrozenModel):
    episode_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    created_at: datetime
    prediction_timestamp: datetime
    pre_action_state: dict[str, int]
    action: str
    context: dict[str, Any]
    predictions: PredictionBundle
    target: PredictionTarget
    action_started_at: datetime | None = None
    action_completed_at: datetime | None = None
    performed_action: str | None = None
    outcome_due_at: datetime
    observed_outcome: ObservedOutcome | None = None
    outcome_quality: float | None = Field(default=None, ge=0.0, le=1.0)
    status: EpisodeStatus
    exclusion_reason: str | None = None
    missing_outcome_reason: str | None = None

    @field_validator("created_at", "prediction_timestamp", "action_started_at", "action_completed_at", "outcome_due_at")
    @classmethod
    def require_aware_episode_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("episode timestamps must include a timezone")
        return value

    @field_validator("pre_action_state")
    @classmethod
    def validate_pre_action_skills(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("pre_action_state must not be empty")
        for name, skill_value in value.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("skill names must be non-empty strings")
            if isinstance(skill_value, bool) or not isinstance(skill_value, int) or not 0 <= skill_value <= 100:
                raise ValueError("pre_action_state skill values must be integers in [0, 100]")
        return value


class EpisodeAuditEvent(FrozenModel):
    event_id: int | None = None
    episode_id: str
    timestamp: datetime
    event_type: EpisodeEventType
    metadata: dict[str, Any] = Field(default_factory=dict)


class EligibilityResult(FrozenModel):
    eligible: bool
    reasons: tuple[str, ...] = ()
