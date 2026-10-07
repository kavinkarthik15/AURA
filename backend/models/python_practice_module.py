from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ModuleDomain = Literal[
    "variables_and_types",
    "control_flow",
    "functions",
    "collections",
    "debugging_reasoning",
    "problem_solving",
]


class ModuleExercise(BaseModel):
    exercise_id: str = Field(min_length=1)
    domain: ModuleDomain
    required: bool = True
    max_points: int = Field(ge=1, le=50)
    prompt: str = Field(min_length=1)
    expected_answer: Any
    execution_contract: dict[str, Any] | None = None
    scoring_method: Literal["exact_match", "code_output", "boolean"] = "exact_match"


class PythonPracticeModule(BaseModel):
    module_id: str = Field(min_length=1)
    module_version: str = Field(min_length=1)
    exercise_ids: list[str] = Field(min_length=1)
    competency_domains: list[str] = Field(min_length=1)
    expected_duration_minutes: int = Field(ge=1)
    required_exercises: list[str] = Field(min_length=1)
    optional_exercises: list[str] = Field(default_factory=list)
    completion_threshold: dict[str, int] = Field(default_factory=lambda: {"required_exercises_to_pass": 3})
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 1, "retry_only_required": True})
    module_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    exercises: list[ModuleExercise] = Field(min_length=1)

    @field_validator("required_exercises")
    @classmethod
    def validate_required_exercises(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("module requires at least one required exercise")
        return value

    @field_validator("completion_threshold")
    @classmethod
    def validate_threshold(cls, value: dict[str, int]) -> dict[str, int]:
        if "required_exercises_to_pass" not in value:
            raise ValueError("completion_threshold must include required_exercises_to_pass")
        if value["required_exercises_to_pass"] <= 0:
            raise ValueError("required_exercises_to_pass must be positive")
        return value


class PythonPracticeCompletion(BaseModel):
    completion_id: str = Field(min_length=1)
    participant_id: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    module_version: str = Field(min_length=1)
    module_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    completed_at: datetime
    required_exercises_passed: int = Field(ge=0)
    completion_status: Literal["complete", "incomplete"]
    completion_evidence_id: str = Field(min_length=1)
    exercise_attempts: dict[str, int] = Field(default_factory=dict)
    exercise_results: dict[str, bool] = Field(default_factory=dict)

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_aware_timestamps(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("practice completion timestamps must include a timezone")
        return value

    @field_validator("completed_at")
    @classmethod
    def require_completion_after_start(cls, value: datetime, info: Any) -> datetime:
        started_at = info.data.get("started_at")
        if started_at is not None and value <= started_at:
            raise ValueError("practice completion must occur after module start")
        return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()
