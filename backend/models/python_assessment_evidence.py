from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssessmentPhase(StrEnum):
    BASELINE = "BASELINE"
    FOLLOWUP = "FOLLOWUP"


class EnrollmentStatus(StrEnum):
    ENROLLED = "ENROLLED"


class ProspectivePilotEnrollment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    enrollment_id: str = Field(min_length=1)
    pilot_id: str = Field(min_length=1)
    participant_id: str = Field(min_length=1)
    target_name: str = Field(min_length=1)
    target_unit: str = Field(min_length=1)
    assignment_group: Literal["AB", "BA"]
    baseline_form_id: Literal["python_skill_form_a_v1", "python_skill_form_b_v1"]
    followup_form_id: Literal["python_skill_form_a_v1", "python_skill_form_b_v1"]
    enrolled_at: datetime
    protocol_version: str = Field(min_length=1)
    protocol_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: EnrollmentStatus = EnrollmentStatus.ENROLLED

    @field_validator("enrolled_at")
    @classmethod
    def require_aware_enrollment_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("enrolled_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_assigned_forms(self) -> ProspectivePilotEnrollment:
        expected = (
            ("python_skill_form_a_v1", "python_skill_form_b_v1")
            if self.assignment_group == "AB"
            else ("python_skill_form_b_v1", "python_skill_form_a_v1")
        )
        if (self.baseline_form_id, self.followup_form_id) != expected:
            raise ValueError("enrollment forms do not match counterbalanced assignment")
        return self


class AssessmentProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_type: Literal["ASSESSMENT"]
    collection_method: str = Field(min_length=1)
    recorded_by: str = Field(min_length=1)
    assessment_session_id: str = Field(min_length=1)
    instrument_version: str = Field(min_length=1)
    observed_at: datetime
    notes: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("provenance observed_at must include a timezone")
        return value


class AssessmentSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assessment_session_id: str = Field(min_length=1)
    pilot_id: str = Field(min_length=1)
    enrollment_id: str = Field(min_length=1)
    episode_id: str | None = None
    participant_id: str = Field(min_length=1)
    assignment_group: Literal["AB", "BA"]
    phase: AssessmentPhase
    form_id: Literal["python_skill_form_a_v1", "python_skill_form_b_v1"]
    form_version: str = Field(min_length=1)
    form_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    submitted_at: datetime
    evidence_id: str = Field(min_length=1)
    responses: dict[str, Any]
    raw_score: int = Field(ge=0, le=100)
    aura_python_skill: float = Field(ge=0, le=100)
    scoring_version: str = Field(min_length=1)
    instrument_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_version: str = Field(min_length=1)
    protocol_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: AssessmentProvenance
    validation_status: Literal["VALID_FINALIZED"] = "VALID_FINALIZED"

    @field_validator("started_at", "submitted_at")
    @classmethod
    def require_aware_timestamps(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_submission_interval_and_score(self) -> AssessmentSession:
        if self.started_at >= self.submitted_at:
            raise ValueError("started_at must be earlier than submitted_at")
        if not math.isclose(self.aura_python_skill, float(self.raw_score), rel_tol=0, abs_tol=0):
            raise ValueError("aura_python_skill must equal raw_score")
        if self.form_hash != self.instrument_hash:
            raise ValueError("form_hash and instrument_hash must match")
        if self.phase is AssessmentPhase.BASELINE and self.episode_id is not None:
            raise ValueError("baseline evidence must remain unlinked until prediction freeze")
        if self.phase is AssessmentPhase.FOLLOWUP and self.episode_id is None:
            raise ValueError("follow-up evidence must be linked to a frozen episode")
        identity = self.enrollment_id if self.phase is AssessmentPhase.BASELINE else self.episode_id
        if self.evidence_id != f"{self.pilot_id}:{self.participant_id}:{identity}:{self.assessment_session_id}":
            raise ValueError("evidence_id does not match assessment ownership")
        if self.provenance.assessment_session_id != self.assessment_session_id:
            raise ValueError("provenance session ID does not match assessment")
        if self.provenance.instrument_version != self.form_version:
            raise ValueError("provenance instrument version does not match assessment form")
        if self.provenance.observed_at != self.submitted_at:
            raise ValueError("provenance observed_at must match submitted_at")
        expected_forms = (
            ("python_skill_form_a_v1", "python_skill_form_b_v1")
            if self.assignment_group == "AB"
            else ("python_skill_form_b_v1", "python_skill_form_a_v1")
        )
        expected_form = expected_forms[0 if self.phase is AssessmentPhase.BASELINE else 1]
        if self.form_id != expected_form:
            raise ValueError("assessment form does not match assignment group and phase")
        return self


class PilotReadinessResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ready: bool
    protocol_hash_valid: bool
    artifact_bindings_valid: bool
    measurement_artifacts_valid: bool
    action_module_valid: bool
    secure_execution_backend_available: bool
    secure_execution_backend_health_check: bool
    secure_backend_type: Literal["docker_container", "unavailable"]
    security_execution_gate: Literal["PASS", "FAIL", "BLOCKED_ENVIRONMENT_DEPENDENCY"]
    evidence_validation_service_available: bool
    owner_approval: bool
    blockers: tuple[str, ...] = ()
