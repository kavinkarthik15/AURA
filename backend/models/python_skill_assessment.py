from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AssessmentDomain = Literal[
    "variables_and_types",
    "control_flow",
    "functions",
    "collections",
    "debugging_reasoning",
    "problem_solving",
]


class AssessmentItem(BaseModel):
    item_id: str = Field(min_length=1)
    form_id: str = Field(min_length=1)
    domain: AssessmentDomain
    maximum_points: int = Field(ge=1, le=100)
    scoring_method: Literal["exact_match", "true_false", "multiple_choice", "code_output"]
    prompt: str = Field(min_length=1)
    expected_answer: Any
    execution_contract: dict[str, Any] | None = None
    required: bool = True


class AssessmentBlueprint(BaseModel):
    blueprint_id: str = Field(min_length=1)
    blueprint_version: str = Field(min_length=1)
    domains: dict[str, int]
    form_a_id: str = Field(min_length=1)
    form_b_id: str = Field(min_length=1)
    assessment_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("domains")
    @classmethod
    def validate_domain_weights(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("blueprint must define at least one domain")
        total = sum(value.values())
        if total != 100:
            raise ValueError("blueprint weights must sum to 100")
        for domain_name, weight in value.items():
            if weight <= 0:
                raise ValueError(f"domain weight for {domain_name!r} must be positive")
        return value


class AssessmentForm(BaseModel):
    form_id: str = Field(min_length=1)
    form_version: str = Field(min_length=1)
    blueprint_id: str = Field(min_length=1)
    assessment_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    items: list[AssessmentItem]

    @field_validator("items")
    @classmethod
    def ensure_items_present(cls, value: list[AssessmentItem]) -> list[AssessmentItem]:
        if not value:
            raise ValueError("assessment form must contain at least one item")
        return value


class AssessmentAssignment(BaseModel):
    participant_id: str = Field(min_length=1)
    assignment_group: Literal["AB", "BA"]
    baseline_form: Literal["python_skill_form_a_v1", "python_skill_form_b_v1"]
    followup_form: Literal["python_skill_form_a_v1", "python_skill_form_b_v1"]
    assignment_method: Literal["sha256_user_id_first_bit"]

    @field_validator("followup_form")
    @classmethod
    def require_counterbalanced_form(
        cls,
        value: str,
        info: Any,
    ) -> str:
        baseline_form = info.data.get("baseline_form")
        if baseline_form == value:
            raise ValueError("baseline and follow-up forms must differ")
        return value

    @model_validator(mode="after")
    def validate_group_mapping(self) -> AssessmentAssignment:
        expected = (
            ("python_skill_form_a_v1", "python_skill_form_b_v1")
            if self.assignment_group == "AB"
            else ("python_skill_form_b_v1", "python_skill_form_a_v1")
        )
        if (self.baseline_form, self.followup_form) != expected:
            raise ValueError("assessment forms do not match counterbalanced assignment group")
        return self


class AssessmentResult(BaseModel):
    assessment_id: str = Field(min_length=1)
    participant_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    pilot_id: str = Field(min_length=1)
    form_id: str = Field(min_length=1)
    form_version: str = Field(min_length=1)
    raw_score: int = Field(ge=0)
    aura_python_skill: float = Field(ge=0.0, le=100.0)
    completed: bool
    missing_items: list[str] = Field(default_factory=list)
    invalid_items: list[str] = Field(default_factory=list)
    instrument_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()
